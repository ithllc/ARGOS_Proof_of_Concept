from google.adk.cli.fast_api import get_fast_api_app
import os
from fastapi import WebSocket, WebSocketDisconnect
from ARGOS_POS.src.voice_handler import VoiceHandler

# The agents are in the 'agents' subdirectory of the 'src' directory.
# The get_fast_api_app expects the path to be relative to the current working directory.
# When running with uvicorn from the root of the project, the path should be 'ARGOS_POS/src/agents'.
agents_dir = os.path.join(os.path.dirname(__file__), "agents")

app = get_fast_api_app(
    agents_dir=agents_dir,
    web=True,
)

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
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
