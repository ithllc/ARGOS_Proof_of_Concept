import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import asyncio
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

# Ensure environment is loaded early
import config

from agents.coordinator.agent import decompose_and_dispatch, process_voice_input
from redis_client import redis_client
from voice_handler import VoiceHandler
import json

# Optional CopilotKit/AG-UI imports (install via pyproject.toml / pip if not already present)
try:
    from copilotkit.integrations.fastapi import add_fastapi_endpoint, handler as copilotkit_handler
    from copilotkit.sdk import CopilotKitRemoteEndpoint
    logger.info("Successfully imported CopilotKit.")
except Exception as e:
    logger.error(f"CRITICAL: Failed to import CopilotKit: {e}")
    add_fastapi_endpoint = None
    CopilotKitRemoteEndpoint = None
    copilotkit_handler = None

try:
    from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
    logger.info("Successfully imported AG-UI ADK.")
except Exception as e:
    logger.error(f"CRITICAL: Failed to import AG-UI ADK: {e}")
    ADKAgent = None
    add_adk_fastapi_endpoint = None

app = FastAPI(title="ARGOS POC - Production API")

# Middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {request.headers}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Background worker for voice tasks
async def voice_task_worker():
    logger.info("Starting voice task worker")
    while True:
        try:
            task_json = redis_client.pop_task("tasks:coordinator_voice_input")
            if task_json:
                logger.info(f"Processing voice task: {task_json}")
                task = json.loads(task_json)
                payload = task.get("payload", {})
                query = payload.get("query")
                session_id = payload.get("session_id")
                response_channel = payload.get("response_channel")
                
                if query and session_id and response_channel:
                    await process_voice_input(query, session_id, response_channel)
            else:
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in voice task worker: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(voice_task_worker())

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[], # Clear explicit list to rely on regex
    allow_origin_regex=".*", # Allow all origins regex (required for allow_credentials=True with wildcard)
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
        logger.info(f"WebSocket connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/api/health") # Renamed from "/" to "/api/health"
async def read_root():
    logger.info("Health check endpoint called")
    return {"message": "Mini-ARGOS POC is running"}


@app.get("/status")
async def get_status():
    logger.info("Status endpoint called")
    return {"status": "ok"}


@app.post("/api/decompose")
async def api_decompose(payload: dict = Body(...)):
    query = payload.get("query")
    session_id = payload.get("session_id")
    logger.info(f"Decompose API called with query: {query}, session_id: {session_id}")

    task_ids = decompose_and_dispatch(query, session_id=session_id)
    return {"tasks": task_ids}


@app.get("/api/papers")
async def get_papers():
    logger.info("Get papers endpoint called")
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
    logger.info("New connection attempt to /ws/live")
    await websocket.accept()
    logger.info("Connection accepted for /ws/live")
    voice_handler = VoiceHandler(websocket)
    try:
        await voice_handler.handle_audio_stream()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected from /ws/live")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/live: {e}")
    finally:
        await voice_handler.close()


@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    logger.info("New connection attempt to /ws/events")
    await websocket.accept()
    logger.info("Connection accepted for /ws/events")
    pubsub = None
    try:
        pubsub = redis_client.subscribe_to_channel("agent:activity")
        if not pubsub:
            logger.error("Could not connect to Redis Pub/Sub")
            await websocket.close(code=1011, reason="Could not connect to Redis Pub/Sub.")
            return

        while True:
            # Check for new message without blocking
            message = pubsub.get_message(ignore_subscribe_messages=True)
            if message and 'data' in message:
                logger.info(f"Broadcasting event: {message['data']}")
                await websocket.send_text(message['data'])
            await asyncio.sleep(0.1)  # Prevent busy-waiting
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected from /ws/events")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/events: {e}")
    finally:
        if pubsub:
            pubsub.close()


# ==============================================================================
# CopilotKit / AG-UI Integration for ADK Agents
# ==============================================================================

# logger.info(f"Checking CopilotKit availability: add_fastapi_endpoint={add_fastapi_endpoint is not None}, CopilotKitRemoteEndpoint={CopilotKitRemoteEndpoint is not None}")

# # Only attempt to add CopilotKit endpoints if package is available
# if add_fastapi_endpoint and CopilotKitRemoteEndpoint:
#     try:
#         # Build a CopilotKit SDK instance exposing the ADK agents.
#         def make_agents(context):
#             # Lazy import here to avoid circular imports during import time
#             from agents.coordinator.agent import root_agent as coordinator_adk_agent
#             from agents.research.agent import root_agent as research_adk_agent
#             from agents.planning.agent import root_agent as planning_adk_agent
#             from agents.analysis.agent import root_agent as analysis_adk_agent
#
#             # CopilotKit expects its agents to be passed in a list
#             return [coordinator_adk_agent, research_adk_agent, planning_adk_agent, analysis_adk_agent]
#
#         sdk = CopilotKitRemoteEndpoint(agents=make_agents)
#         add_fastapi_endpoint(app, sdk, "/copilotkit")
#         
#         # Workaround: Manually register the root path because add_fastapi_endpoint only registers subpaths
#         if copilotkit_handler:
#             @app.api_route("/copilotkit", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
#             async def handle_copilotkit_root(request: Request):
#                 # Inject 'path' into path_params so the handler works
#                 request.scope["path_params"]["path"] = ""
#                 return await copilotkit_handler(request, sdk)
#
#         logger.info("CopilotKit endpoint registered at /copilotkit")
#     except Exception as e:
#         logger.error(f"Failed to register CopilotKit endpoints: {e}")
# else:
#     logger.warning("CopilotKit packages not available, skipping endpoint registration.")


# AG-UI ADK integration (optional)
# Triggering deployment for ADK fix
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

        # Map coordinator to /copilotkit to serve as the main entry point
        add_adk_fastapi_endpoint(app, coordinator_wrapper, path="/copilotkit")
        
        # Also keep specific endpoints if needed
        add_adk_fastapi_endpoint(app, coordinator_wrapper, path="/copilotkit/coordinator")
        add_adk_fastapi_endpoint(app, research_wrapper, path="/copilotkit/research")
        add_adk_fastapi_endpoint(app, planning_wrapper, path="/copilotkit/planning")
        add_adk_fastapi_endpoint(app, analysis_wrapper, path="/copilotkit/analysis")

        logger.info("AG-UI ADK endpoints registered under /copilotkit and subpaths")
    except Exception as e:
        logger.error(f"Failed to register AG-UI ADK endpoints: {e}")

# ==============================================================================
# Serve Frontend Static Files
# ==============================================================================

# Directory where the frontend build artifacts are located
FRONTEND_BUILD_DIR = "/app/frontend/build"

# Serve static files from the 'static' subdirectory of the frontend build
app.mount("/static", StaticFiles(directory=f"{FRONTEND_BUILD_DIR}/static"), name="static")

# Route for the root URL, serving the main index.html
@app.get("/")
async def serve_index():
    return FileResponse(f"{FRONTEND_BUILD_DIR}/index.html")

# Catch-all route for client-side routing (SPA history mode)
# This should be the very last route registered
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if the requested path is a file that exists in the build directory
    # If it's an API route or other specific server-side route, it would have been matched before this.
    file_path = os.path.join(FRONTEND_BUILD_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(f"{FRONTEND_BUILD_DIR}/index.html")
