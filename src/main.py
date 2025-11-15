from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from fastapi import Body

# Load environment variables before other imports
import config

from agents.coordinator import CoordinatorAgent
from redis_client import redis_client
from agents.research import ResearchAgent
from agents.planning import PlanningAgent
from agents.analysis import AnalysisAgent

app = FastAPI()

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
    agent = CoordinatorAgent()
    task_ids = agent.decompose_and_dispatch(query, session_id=session_id)
    return {"tasks": task_ids}


@app.get("/api/papers")
async def get_papers():
    # naive: list last N paper:* entries in redis
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
            # This is where ADK Live would interact
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
