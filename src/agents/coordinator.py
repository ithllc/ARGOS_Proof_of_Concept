import json
import os
import uuid
from typing import List

import dspy
from redis_client import redis_client


class DecomposeQuery(dspy.Signature):
    """Decompose a complex research query into a series of simpler, actionable search tasks."""

    query = dspy.InputField(desc="The user's complex research query.")
    tasks = dspy.OutputField(
        desc="A JSON list of simple, actionable search tasks. Each task should be a string."
    )


class CoordinatorAgent:
    """Lightweight coordinator for the POC.

    Responsibilities:
    - Decompose incoming user request into a set of smaller tasks
      (search queries / parsing tasks)
    - Push tasks into Redis task queue `tasks:research`
    - Track task ids and session mapping in Redis
    """

    def __init__(self, redis_client=redis_client):
        self.redis = redis_client
        self._configure_dspy()

    def _configure_dspy(self):
        """Configure DSPy to use Google's Gemini model."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                llm = dspy.Google(model="gemini-1.5-flash-latest", api_key=api_key)
                dspy.settings.configure(lm=llm)
                self.dspy_enabled = True
            except Exception as e:
                print(f"Failed to configure DSPy: {e}")
                self.dspy_enabled = False
        else:
            self.dspy_enabled = False

    def _make_task(self, task_type: str, payload: dict):
        task_id = str(uuid.uuid4())
        data = {"task_id": task_id, "type": task_type, "payload": payload}
        return task_id, json.dumps(data)

    def decompose_and_dispatch(
        self, query: str, session_id: str | None = None
    ) -> List[str]:
        """Decompose a high-level user request into multiple search/parse tasks.

        We use a dspy-based step when available; otherwise a heuristic split.
        """
        tasks = []

        if self.dspy_enabled:
            try:
                # Use a predictor with the defined signature for robust decomposition
                decompose_predictor = dspy.Predict(DecomposeQuery)
                result = decompose_predictor(query=query)
                # The output field 'tasks' should be a JSON string list
                tasks = json.loads(result.tasks)
            except Exception as e:
                print(f"DSPy decomposition failed, falling back to heuristic: {e}")
                # Fallback to heuristic if DSPy fails at runtime
                self.dspy_enabled = False  # Disable for subsequent calls in this instance
        
        if not self.dspy_enabled:
            # Fallback: produce several related search queries for Tavily
            tasks = [
                query,
                f"{query} arXiv pdf",
                f"{query} review article",
                f"{query} survey",
                f"{query} site:arxiv.org",
            ]

        pushed_task_ids = []
        for t in tasks:
            task_id, task_payload = self._make_task(
                "search_and_parse", {"query": t, "session_id": session_id}
            )
            self.redis.push_task("tasks:research", task_payload)
            pushed_task_ids.append(task_id)

        # Lookup table in Redis to track session -> task ids
        if session_id:
            self.redis.set_hash_field(
                f"session:{session_id}", "tasks", json.dumps(pushed_task_ids)
            )

        # Notify listeners
        self.redis.publish_message(
            "agent:activity",
            json.dumps(
                {"agent": "coordinator", "status": "dispatched", "tasks": pushed_task_ids}
            ),
        )
        return pushed_task_ids

    def create_adk_agent(self):
        """Create a simple ADK LlmAgent instance that can be used for decomposition in production.

		Note: this function returns a configured agent object but DOES NOT run it. To run, use `Runner` from
		`google.adk.runners` and the appropriate `SessionService` (InMemory or VertexAI) as required.
		"""
		try:
			from google.adk.agents import LlmAgent

			agent = LlmAgent(
				name="coordinator",
				model="gemini-2.5-flash",
				instruction=(
					"You are the coordinator agent. Break a high-level research request into a short list of "
					"search tasks (one line each). Return a JSON list of tasks. Avoid unnecessary text."
				),
			)
			return agent
		except Exception:
			return None

	async def run_adk_decomposition(self, query: str, user_id: str = "local_user", session_id: str = "local_session") -> list[str]:
		"""Run the ADK LlmAgent decomposition using an InMemorySessionService + Runner.

		This helper demonstrates how to execute an ADK LlmAgent for decomposition.
		It returns a list of task strings parsed from the LLM output.
		"""
		try:
			from google.adk.runners import Runner
			from google.adk.sessions import InMemorySessionService
			from google.genai import types as genai_types

			adk_agent = self.create_adk_agent()
			if adk_agent is None:
				return []

			session_service = InMemorySessionService()
			await session_service.create_session(app_name="mini_argos", user_id=user_id, session_id=session_id)
			runner = Runner(agent=adk_agent, app_name="mini_argos", session_service=session_service)

			tasks = []
			async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=genai_types.Content(parts=[genai_types.Part.from_text(query)])):
				if event.is_final_response():
					text = event.content.parts[0].text
					# attempt to parse JSON list or fallback to splitting lines
					import json
					try:
						tasks = json.loads(text)
					except Exception:
						tasks = [l.strip() for l in text.splitlines() if l.strip()]
			return tasks
		except Exception:
			return []

