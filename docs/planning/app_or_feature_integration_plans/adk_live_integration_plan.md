# ADK Live and Multi-Modal Generation Integration Plan

**Document Version:** 1.0
**Date:** November 15, 2025

## 1. Overview

This document outlines the technical plan to integrate the Google Agent Development Kit (ADK) Live functionality for real-time voice interaction and to add new multi-modal output capabilities (image and video generation) to the Mini-ARGOS POC.

This plan addresses the gap identified between the intended architecture of POC Idea #5 and the current text-based implementation. The goal is to create a truly multi-modal, interactive agent system.

## 2. Architectural Changes

The core of this plan is to introduce a real-time, streaming layer for voice and to equip the `CoordinatorAgent` with new tools.

### 2.1. New Architectural Diagram

```
+----------------------+      +---------------------+      +-------------------------+
|   Frontend UI        |----->|  FastAPI Gateway    |----->| ADK Live Coordinator    |
| (React/VoiceInterface)|      | (main.py)           |      | (coordinator.py)        |
| - Mic Input          |      | - /ws/live WebSocket|      | - Handles STT/TTS       |
| - Audio Playback     |      +---------------------+      | - Invokes Tools         |
+----------------------+                 ^                   +------------+------------+
        ^                                |                                |
        | (Audio Stream)                 | (Text Stream)                  | (Tool Calls)
        v                                v                                v
+----------------------+      +---------------------+      +-------------------------+
| Google Cloud STT/TTS |<---->|  Voice Handler      |<---->|   Multi-Modal Tools     |
| - Speech-to-Text     |      | (voice_handler.py)  |      | (multi_modal_tools.py)  |
| - Text-to-Speech     |      +---------------------+      | - Imagen 3 (Image Gen)  |
+----------------------+                                   | - Veo (Video Gen)       |
                                                           +-------------------------+
```
The existing multi-agent system (Research, Planning, Analysis agents) will still be invoked by the `CoordinatorAgent` via the Redis message bus as before.

### 2.2. Component Updates

-   **`src/main.py`**: Will be updated to include a dedicated WebSocket endpoint (`/ws/live`) to handle the ADK Live protocol.
-   **`src/agents/coordinator/agent.py`**: The `CoordinatorAgent` will be refactored to be the primary "Live Agent." It will process the streaming text from Speech-to-Text, decide when to speak, and when to invoke tools (including the new multi-modal tools).
-   **`src/voice_handler.py` (New File)**: This new module will contain the logic for handling the audio stream from the WebSocket and interacting with Google Cloud's Speech-to-Text and Text-to-Speech APIs.
-   **`src/multi_modal_tools.py` (New File)**: This new module will define the `FunctionTool`s for generating images with Imagen 3 and videos with Veo.
-   **`frontend/src/VoiceInterface.tsx` (New File)**: A new React component will be created to handle microphone access, stream audio to the backend, and play back the synthesized speech from the backend.

## 3. Detailed Implementation Plan & Prompts

### 3.1. New Dependencies

The `pyproject.toml` file will be updated to include:
```toml
[tool.poetry.dependencies]
# ... existing dependencies
google-cloud-speech = ">=2.21.0"
google-cloud-texttospeech = ">=2.14.0"
google-cloud-aiplatform = ">=1.56.0" # For Imagen and Veo
```

### Prompt 1: Backend WebSocket and Voice Handler

"Your task is to update the backend to support real-time voice interaction using ADK Live.

1.  In `src/main.py`, add a new WebSocket endpoint at `/ws/live`. This endpoint will be responsible for handling the bidirectional communication for ADK Live.
2.  Create a new file `src/voice_handler.py`. Implement a `VoiceHandler` class that takes a WebSocket connection. This class will:
    -   Receive audio chunks from the client.
    -   Stream the audio to the Google Cloud Speech-to-Text API.
    -   Receive the transcribed text and pass it to the `CoordinatorAgent`.
    -   Receive text from the `CoordinatorAgent` and stream it to the Google Cloud Text-to-Speech API.
    -   Stream the synthesized audio back to the client via the WebSocket.
3.  Update `src/agents/coordinator/agent.py` to integrate with the `VoiceHandler`."

### Prompt 2: Multi-Modal Generation Tools

"Your task is to create new tools for the `CoordinatorAgent` to generate images and videos.

1.  Create a new file `src/multi_modal_tools.py`.
2.  Inside this file, define two new `FunctionTool`s:
    -   `generate_architecture_image`: This tool will take a textual description of a software architecture as input. It will use the Google Cloud AI Platform client library to call the **Imagen 3** model to generate a diagram. It should return the URL of the generated image.
    -   `generate_example_video`: This tool will take a textual description of a real-world scenario as input. It will use the Google Cloud AI Platform client library to call the **Veo** model to generate a short video. It should return the URL of the generated video.
3.  Update `src/agents/coordinator/agent.py` to include these new tools in its toolset, allowing the agent to decide when to use them based on the user's request (e.g., 'show me a diagram of this' or 'create a video example')."

### Prompt 3: Frontend Voice Interface

"Your task is to build the frontend component for voice interaction.

1.  Create a new file `frontend/src/VoiceInterface.tsx`.
2.  This React component should:
    -   Request microphone permission from the user.
    -   On a button press (e.g., a microphone icon), open a WebSocket connection to the `/ws/live` endpoint on the backend.
    -   Capture audio from the microphone and stream it through the WebSocket.
    -   Receive audio chunks back from the WebSocket for TTS playback.
    -   Use the browser's Audio API to play back the received audio stream in real-time.
    -   Handle connection state (connecting, open, closed) and display appropriate UI feedback.
3.  **Implement the multi-modal display logic:**
    -   The component must also listen for the agent's text messages that are sent alongside the audio.
    -   It should parse these text messages to detect if they contain a URL for a generated image or video.
    -   Maintain a state to hold the current media URL and type (e.g., `media: {url: string, type: 'image' | 'video' | null}`).
    -   Conditionally render an `<img>` or `<video>` tag based on the media type in a designated view area (similar to an iframe or webview). The `<video>` element should be muted and have the `playsinline` attribute for better mobile compatibility.
4.  **Implement auto-play for videos:**
    -   When the TTS audio stream from the backend has finished playing, the component should detect this using the `onended` event of the HTMLAudioElement.
    -   Inside the `onended` event handler, if the current media type is 'video', the component will call the `.play()` method on the `<video>` element to start the video automatically.
5.  Integrate the `VoiceInterface` component and the new media view area into the main `App.tsx`."
