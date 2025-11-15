import json
import os
import uuid
from typing import List

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

import dspy
from redis_client import redis_client


class DecomposeQuery(dspy.Signature):
    """Decompose a complex research query into a series of simpler, actionable search tasks."""

    query = dspy.InputField(desc="The user's complex research query.")
    tasks = dspy.OutputField(
        desc="A JSON list of simple, actionable search tasks. Each task should be a string."
    )

def decompose_and_dispatch(query: str, session_id: str | None = None) -> List[str]:
    """Decompose a high-level user request into multiple search/parse tasks."""
    tasks = []
    
    # DSPy logic
    api_key = os.getenv("GOOGLE_API_KEY")
    dspy_enabled = False
    if api_key:
        try:
            llm = dspy.LM("gemini/gemini-1.5-flash-latest", api_key=api_key)
            dspy.settings.configure(lm=llm)
            dspy_enabled = True
        except Exception:
            dspy_enabled = False

    if dspy_enabled:
        try:
            decompose_predictor = dspy.Predict(DecomposeQuery)
            result = decompose_predictor(query=query)
            tasks = json.loads(result.tasks)
        except Exception:
            dspy_enabled = False

    if not dspy_enabled:
        tasks = [
            query,
            f"{query} arXiv pdf",
            f"{query} review article",
            f"{query} survey",
            f"{query} site:arxiv.org",
        ]

    pushed_task_ids = []
    for t in tasks:
        task_id = str(uuid.uuid4())
        task_payload = json.dumps({"task_id": task_id, "type": "search_and_parse", "payload": {"query": t, "session_id": session_id}})
        redis_client.push_task("tasks:research", task_payload)
        pushed_task_ids.append(task_id)

    if session_id:
        redis_client.set_hash_field(
            f"session:{session_id}", "tasks", json.dumps(pushed_task_ids)
        )

    redis_client.publish_message(
        "agent:activity",
        json.dumps(
            {"agent": "coordinator", "status": "dispatched", "tasks": pushed_task_ids}
        ),
    )
    return pushed_task_ids

root_agent = LlmAgent(
    name="coordinator",
    instruction="You are the coordinator agent. Your job is to decompose a user's query into a series of search tasks.",
    tools=[
        FunctionTool(
            func=decompose_and_dispatch,
            description="Decomposes a complex research query into a series of simpler, actionable search tasks.",
        )
    ]
)
