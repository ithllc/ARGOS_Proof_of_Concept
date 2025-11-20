import json
import os
import uuid
import logging
from typing import List

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from multi_modal_tools import generate_architecture_image, generate_example_video

import dspy
from redis_client import redis_client

logger = logging.getLogger(__name__)

class DecomposeQuery(dspy.Signature):
    """Decompose a complex research query into a series of simpler, actionable search tasks."""

    query = dspy.InputField(desc="The user's complex research query.")
    tasks = dspy.OutputField(
        desc="A JSON list of simple, actionable search tasks. Each task should be a string."
    )

def decompose_and_dispatch(query: str, session_id: str | None = None) -> List[str]:
    """Decompose a high-level user request into multiple search/parse tasks."""
    logger.info(f"Decomposing query: {query}, session_id: {session_id}")
    tasks = []
    
    # DSPy logic
    api_key = os.getenv("GOOGLE_API_KEY")
    dspy_enabled = False
    if api_key:
        try:
            llm = dspy.LM("gemini/gemini-1.5-flash-latest", api_key=api_key)
            dspy.settings.configure(lm=llm)
            dspy_enabled = True
        except Exception as e:
            logger.error(f"DSPy initialization failed: {e}")
            dspy_enabled = False

    if dspy_enabled:
        try:
            decompose_predictor = dspy.Predict(DecomposeQuery)
            result = decompose_predictor(query=query)
            tasks = json.loads(result.tasks)
            logger.info(f"DSPy decomposed tasks: {tasks}")
        except Exception as e:
            logger.error(f"DSPy decomposition failed: {e}")
            dspy_enabled = False

    if not dspy_enabled:
        logger.info("Using fallback decomposition logic")
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
    logger.info(f"Dispatched {len(pushed_task_ids)} tasks")
    return pushed_task_ids

async def process_voice_input(query: str, session_id: str, response_channel: str):
    """Processes a voice input query, decides on action, and publishes response."""
    logger.info(f"Processing voice input: {query}, session_id: {session_id}")
    response_data = {"type": "agent_response", "session_id": session_id}

    # Simple heuristic for demonstration:
    if "diagram" in query.lower() or "architecture image" in query.lower():
        logger.info("Generating architecture image")
        image_url = await generate_architecture_image(query)
        response_data["text"] = "Here is the architecture image you requested."
        response_data["media_url"] = image_url
        response_data["media_type"] = "image"
    elif "video" in query.lower() or "example video" in query.lower():
        logger.info("Generating example video")
        video_url = await generate_example_video(query)
        response_data["text"] = "Here is the video you requested."
        response_data["media_url"] = video_url
        response_data["media_type"] = "video"
    else:
        # Fallback to existing decomposition logic
        logger.info("Delegating to decompose_and_dispatch")
        tasks = decompose_and_dispatch(query, session_id)
        response_data["text"] = f"I've decomposed your query into {len(tasks)} tasks."
        # In a real scenario, you might wait for research results before responding.
        # For now, just acknowledge the decomposition.

    logger.info(f"Publishing response to {response_channel}")
    redis_client.publish_message(response_channel, json.dumps(response_data))
    return "Voice input processed."



root_agent = LlmAgent(
    name="coordinator",
    instruction="You are the coordinator agent. Your job is to decompose a user's query into a series of search tasks, or generate multi-modal content if requested.",
    tools=[
        # Decomposes a complex research query into a series of simpler, actionable search tasks.
        FunctionTool(
            func=decompose_and_dispatch,
        ),
        # Generates a software architecture image based on a textual description using Imagen 3.
        FunctionTool(
            func=generate_architecture_image,
        ),
        # Generates a short video based on a textual description of a real-world scenario using Veo.
        FunctionTool(
            func=generate_example_video,
        ),
        # Processes a voice input query, decides whether to decompose it or generate multi-modal content, and publishes the response.
        FunctionTool(
            func=process_voice_input,
        ),
    ]
)
