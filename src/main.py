from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

# Ensure environment is loaded early
import config

from agents.coordinator.agent import decompose_and_dispatch
from redis_client import redis_client
from voice_handler import VoiceHandler

# Optional CopilotKit/AG-UI imports (install via pyproject.toml / pip if not already present)
try:
    from copilotkit.integrations.fastapi import add_fastapi_endpoint
    from copilotkit.sdk import CopilotKitRemoteEndpoint
except Exception:
    add_fastapi_endpoint = None
    CopilotKitRemoteEndpoint = None

try:
    from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
except Exception:
    ADKAgent = None
    add_adk_fastapi_endpoint = None

app = FastAPI(title="ARGOS POC - Production API")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def read_root():
    return {"message": "Mini-ARGOS POC is running"}


@app.get("/status")
async def get_status():
    return {"status": "ok"}


@app.post("/api/decompose")
async def api_decompose(payload: dict = Body(...)):
    query = payload.get("query")
    session_id = payload.get("session_id")

    task_ids = decompose_and_dispatch(query, session_id=session_id)
    return {"tasks": task_ids}


@app.get("/api/papers")
async def get_papers():
    keys = redis_client.client.keys("paper:*")[:20]
    papers = []
    for k in keys:
        p = redis_client.get_all_hash_fields(k)
        papers.append({"title": p.get("title", ""), "url": p.get("url", ""), "id": k})
    return {"papers": papers}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")


@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    voice_handler = VoiceHandler(websocket)
    try:
        while True:
            await voice_handler.handle_audio_stream()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await voice_handler.close()


# ==============================================================================
# CopilotKit / AG-UI Integration for ADK Agents
# ==============================================================================

# Only attempt to add CopilotKit endpoints if package is available
if add_fastapi_endpoint and CopilotKitRemoteEndpoint:
    try:
        # Build a CopilotKit SDK instance exposing the ADK agents.
        def make_agents(context):
            # Lazy import here to avoid circular imports during import time
            from agents.coordinator.agent import root_agent as coordinator_adk_agent
            from agents.research.agent import root_agent as research_adk_agent
            from agents.planning.agent import root_agent as planning_adk_agent
            from agents.analysis.agent import root_agent as analysis_adk_agent

            # CopilotKit expects its agents to be passed in a list
            return [coordinator_adk_agent, research_adk_agent, planning_adk_agent, analysis_adk_agent]

        sdk = CopilotKitRemoteEndpoint(agents=make_agents)
        add_fastapi_endpoint(app, sdk, "/copilotkit")
        print("CopilotKit endpoint registered at /copilotkit")
    except Exception as e:
        print("Failed to register CopilotKit endpoints:", e)


# AG-UI ADK integration (optional)
if ADKAgent and add_adk_fastapi_endpoint:
    try:
        from agents.coordinator.agent import root_agent as coordinator_adk_agent
        from agents.research.agent import root_agent as research_adk_agent
        from agents.planning.agent import root_agent as planning_adk_agent
        from agents.analysis.agent import root_agent as analysis_adk_agent

        coordinator_wrapper = ADKAgent(
            adk_agent=coordinator_adk_agent,
            app_name="argos_poc",
            user_id="default_user",
            session_timeout_seconds=3600,
            use_in_memory_services=True
        )

        research_wrapper = ADKAgent(
            adk_agent=research_adk_agent,
            app_name="argos_poc",
            user_id="default_user",
            session_timeout_seconds=3600,
            use_in_memory_services=True
        )

        planning_wrapper = ADKAgent(
            adk_agent=planning_adk_agent,
            app_name="argos_poc",
            user_id="default_user",
            session_timeout_seconds=3600,
            use_in_memory_services=True
        )

        analysis_wrapper = ADKAgent(
            adk_agent=analysis_adk_agent,
            app_name="argos_poc",
            user_id="default_user",
            session_timeout_seconds=3600,
            use_in_memory_services=True
        )

        add_adk_fastapi_endpoint(app, coordinator_wrapper, path="/copilotkit/coordinator")
        add_adk_fastapi_endpoint(app, research_wrapper, path="/copilotkit/research")
        add_adk_fastapi_endpoint(app, planning_wrapper, path="/copilotkit/planning")
        add_adk_fastapi_endpoint(app, analysis_wrapper, path="/copilotkit/analysis")

        print("AG-UI ADK endpoints registered under /copilotkit/*")
    except Exception as e:
        print("Failed to register AG-UI ADK endpoints:", e)