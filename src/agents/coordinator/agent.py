import json
import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types

from multi_modal_tools import generate_architecture_image, generate_example_video

import dspy
import config
from redis_client import redis_client
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Shared State Models ---

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchTask(BaseModel):
    id: str = Field(..., description="Unique ID of the task")
    description: str = Field(..., description="Description of the task")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current status of the task")

class ResearchPaper(BaseModel):
    title: str = Field(..., description="Title of the paper")
    url: str = Field(..., description="URL of the paper")
    summary: Optional[str] = Field(None, description="Brief summary of the paper")

class ResearchState(BaseModel):
    query: str = Field("", description="The main research query")
    tasks: List[ResearchTask] = Field(default_factory=list, description="List of decomposed research tasks")
    papers: List[ResearchPaper] = Field(default_factory=list, description="List of found research papers")
    analysis: str = Field("", description="Current analysis or synthesis of findings")
    status: str = Field("idle", description="Overall agent status (idle, researching, analyzing)")

# --- Tool for Updating State ---

def update_research_state(
    tool_context: ToolContext,
    query: Optional[str] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    papers: Optional[List[Dict[str, Any]]] = None,
    analysis: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, str]:
    """
    Update the shared research state. Use this tool to reflect progress in the UI.
    
    Args:
        query: Update the main research query.
        tasks: Update the list of tasks. Provide the full list or new tasks.
        papers: Update the list of papers.
        analysis: Update the textual analysis.
        status: Update the overall status (e.g., 'researching', 'completed').
    """
    try:
        current_state = tool_context.state.get("research_state", {})
        
        if query is not None:
            current_state["query"] = query
        if tasks is not None:
            current_state["tasks"] = tasks
        if papers is not None:
            current_state["papers"] = papers
        if analysis is not None:
            current_state["analysis"] = analysis
        if status is not None:
            current_state["status"] = status

        tool_context.state["research_state"] = current_state
        return {"status": "success", "message": "Research state updated successfully"}
    except Exception as e:
        logger.error(f"Error updating state: {e}")
        return {"status": "error", "message": f"Error updating state: {str(e)}"}

# --- Callbacks ---

def on_before_agent(callback_context: CallbackContext):
    """Initialize research state if it doesn't exist."""
    if "research_state" not in callback_context.state:
        default_state = ResearchState().model_dump()
        callback_context.state["research_state"] = default_state
    return None

def before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Injects the current research state into the system prompt."""
    agent_name = callback_context.agent_name
    if agent_name == "coordinator":
        state_json = "No state yet"
        if "research_state" in callback_context.state:
            try:
                state_json = json.dumps(callback_context.state["research_state"], indent=2)
            except Exception as e:
                state_json = f"Error serializing state: {str(e)}"
        
        # Modify System Prompt
        original_instruction = llm_request.config.system_instruction or types.Content(role="system", parts=[])
        prefix = f"""You are the Coordinator Agent for the ARGOS Research System.
        You collaborate with the user on a shared research workspace.
        
        CURRENT SHARED STATE:
        {state_json}
        
        YOUR RESPONSIBILITIES:
        1. When the user gives a query, use `update_research_state` to update the 'query' field and decompose it into 'tasks'.
        2. As you complete tasks (conceptually), update their status in the 'tasks' list.
        3. If you find papers (simulated or real), add them to the 'papers' list.
        4. Keep the 'analysis' field updated with your findings.
        5. ALWAYS use `update_research_state` to reflect changes in the UI.
        """
        
        if not isinstance(original_instruction, types.Content):
            original_instruction = types.Content(role="system", parts=[types.Part(text=str(original_instruction))])
        if not original_instruction.parts:
            original_instruction.parts.append(types.Part(text=""))

        # Prepend the state info
        modified_text = prefix + "\n\n" + (original_instruction.parts[0].text or "")
        original_instruction.parts[0].text = modified_text
        llm_request.config.system_instruction = original_instruction

    return None

def simple_after_model_modifier(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Stop the consecutive tool calling of the agent if it has just updated state."""
    agent_name = callback_context.agent_name
    if agent_name == "coordinator":
        if llm_response.content and llm_response.content.parts:
            for part in llm_response.content.parts:
                if part.text:
                    callback_context._invocation_context.end_invocation = True
                    break
    return None

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
    if not api_key:
        config.load_google_secrets()
        api_key = os.getenv("GOOGLE_API_KEY")

    dspy_enabled = False
    if api_key:
        try:
            llm = dspy.LM("gemini/gemini-2.0-flash-exp", api_key=api_key)
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
    model="gemini-2.0-flash-exp",
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
