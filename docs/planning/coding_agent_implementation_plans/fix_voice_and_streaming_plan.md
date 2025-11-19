# Technical Plan: Fix Voice Recording and Event Streaming in ARGOS POC

## Problem Analysis

### 1. Voice Recording Issue
**Symptoms:**
- User reports that clicking "Start Recording" immediately toggles back to "Stop Recording" (or stops immediately) without recording.
- No voice data is processed.

**Root Causes:**
- **WebSocket URL:** `VoiceInterface.tsx` uses a hardcoded `ws://localhost:8000/ws/live`. This fails when deployed to Cloud Run (or any non-localhost environment), causing an immediate connection error which closes the socket and stops recording.
- **Race Condition:** The `onaudioprocess` handler in `VoiceInterface.tsx` captures the `ws` state variable which is initially `null`. Even if `setWs` is called, the closure might not update immediately or correctly within the `ScriptProcessorNode` callback context.
- **Backend Async/Sync Mismatch:** `voice_handler.py` attempts to use `await` inside a synchronous generator expression passed to the synchronous `speech_client.streaming_recognize`. This is invalid Python async usage and will likely fail or block the event loop.

### 2. Event Streaming Issue
**Symptoms:**
- "None of the events from the coordinator agent are being streamed and visible" in both Chat and Voice interfaces.
- User expects to see intermediate steps (e.g., "Dispatched tasks...", "Transcribed text...").

**Root Causes:**
- **Chat (CopilotKit):** The `CopilotKit` integration in `main.py` (via `LlmAgent` or `ADKAgent`) does not automatically capture Redis `agent:activity` pub/sub messages and stream them to the CopilotKit frontend. The standard `LlmAgent` execution model is request-response.
- **Voice:** The `VoiceHandler` only subscribes to `session:{id}:response` (final response), ignoring `agent:activity`.
- **Frontend:** There is no UI component active in `App.tsx` that listens for and displays these system-wide or session-specific event logs. `AgentStatus.jsx` exists but is a static placeholder and is not used.

## Proposed Solution

### 1. Fix Voice Recording
- **Frontend:** Update `VoiceInterface.tsx` to dynamically determine the WebSocket URL based on `window.location`. Refactor the `startRecording` logic to ensure the WebSocket is open before attaching the audio processor, or use a `useRef` for the WebSocket to avoid closure staleness.
- **Backend:** Refactor `voice_handler.py` to use `SpeechAsyncClient` from `google.cloud.speech`. Use an asynchronous generator to yield audio chunks from the WebSocket to the Google Speech API.

### 2. Enable Event Streaming
- **Backend:** Create a new WebSocket endpoint `/ws/events` in `main.py`. This endpoint will subscribe to the Redis `agent:activity` channel and stream all messages to connected clients.
- **Frontend:** 
    - Update `AgentStatus.jsx` to connect to `/ws/events` and display a real-time log of agent activities.
    - Integrate `<AgentStatus />` into `App.tsx` so it is visible alongside the Voice and Chat interfaces.
    - (Optional) Update `VoiceHandler` to also forward transcription events to the frontend via the existing voice WebSocket for immediate feedback.

## Step-by-Step Implementation Plan

### Step 1: Fix Backend Voice Handler
**File:** `src/voice_handler.py`
- Replace `speech.SpeechClient` with `speech.SpeechAsyncClient`.
- Rewrite `handle_audio_stream` to use an async generator for request streaming.
- Ensure proper exception handling and resource cleanup.

### Step 2: Create Event Streaming Endpoint
**File:** `src/main.py`
- Add a new WebSocket route `/ws/events`.
- Implement logic to subscribe to Redis `agent:activity` and broadcast messages to the websocket.

### Step 3: Fix Frontend Voice Interface
**File:** `frontend/src/VoiceInterface.tsx`
- Change WebSocket URL to use `window.location.protocol` and `window.location.host`.
- Use `useRef` for the WebSocket instance to ensure `onaudioprocess` always accesses the current active socket.
- Add error handling to log WebSocket connection failures clearly.

### Step 4: Implement Agent Status & Integrate
**File:** `frontend/src/AgentStatus.jsx`
- Implement WebSocket connection to `/ws/events`.
- Render a list of events (Agent, Status, Details).

**File:** `frontend/src/App.tsx`
- Import and add `<AgentStatus />` to the main layout.

## Redis Verification Instructions (for Human intervention only, skip and go straight to the "Prompts for Coding Agent" for your tasks)
To verify events in Redis manually:
1.  Access the environment where Redis is running.
2.  Run `redis-cli`.
3.  Subscribe to the activity channel: `SUBSCRIBE agent:activity`
4.  Trigger an action in the app. You should see JSON messages appear.

## Prompts for Coding Agent

### Prompt 1: Fix Backend Voice Handler
```text
Refactor `src/voice_handler.py` to fix asynchronous generator issues.
1. Import `SpeechAsyncClient` from `google.cloud.speech`.
2. In `VoiceHandler.__init__`, initialize `self.speech_client` as `speech.SpeechAsyncClient()`.
3. Create a new async method `_request_generator(self)` that yields `speech.StreamingRecognizeRequest` objects. It should loop while `self.websocket` is connected, await `self.websocket.receive_bytes()`, and yield the content. Handle `WebSocketDisconnect` gracefully.
4. Update `handle_audio_stream` to use `await self.speech_client.streaming_recognize(config=self.streaming_config, requests=self._request_generator())`.
5. Ensure the rest of the logic (Redis publishing, TTS) remains intact.
```

### Prompt 2: Create Event Streaming Endpoint
```text
Update `src/main.py` to add a real-time event streaming endpoint.
1. Add a new WebSocket endpoint `@app.websocket("/ws/events")`.
2. In this endpoint, accept the connection.
3. Create a Redis pubsub instance using `redis_client.subscribe_to_channel("agent:activity")` (you may need to update `redis_client.py` if this method doesn't return a raw pubsub object or use `redis_client.client.pubsub()`).
4. Enter a loop that listens for messages on the pubsub channel and sends them as text/JSON to the websocket.
5. Handle `WebSocketDisconnect` to close the pubsub connection.
```

### Prompt 3: Fix Frontend Voice Interface
```text
Update `frontend/src/VoiceInterface.tsx` to fix WebSocket connection issues.
1. Remove the hardcoded `ws://localhost:8000` URL. Construct the URL dynamically: `const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'; const wsUrl = \`\${protocol}//\${window.location.host}/ws/live\`;`.
2. Use a `useRef` to store the WebSocket instance (`wsRef`) instead of just state, or ensure the `onaudioprocess` callback uses the ref to access the active socket.
3. In `startRecording`, initialize the WebSocket and assign it to the ref.
4. In `onaudioprocess`, check `wsRef.current && wsRef.current.readyState === WebSocket.OPEN` before sending data.
5. Ensure `stopRecording` closes the socket and cleans up refs.
```

### Prompt 4: Implement Agent Status & Integrate
```text
1. Rewrite `frontend/src/AgentStatus.jsx` to be a functional component that:
   - Connects to `/ws/events` (dynamically determined URL like VoiceInterface).
   - Maintains a list of received events in state.
   - Renders these events in a scrollable list, showing timestamp, agent name, and status.
2. Update `frontend/src/App.tsx` to import `AgentStatus` and render it. Place it inside the `<main>` tag, perhaps above or below the `VoiceInterface`.
```
