# Missing Coding Logic from Prompts 1, 2, 3, and 4

This document lists the discrepancies and missing implementation details found when comparing the current codebase against the requirements outlined in `technical_plan_poc5.md` and `scaled_down_ideas_claude.md` for POC Idea #5.

### 1. Full Google Agent Development Kit (ADK) Integration (Prompt 3)

-   **Status:** Incomplete
-   **Observation:** The agent files (`coordinator.py`, `research.py`, `planning.py`, `analysis.py`) define Python classes but do not fully integrate with the `google-adk` framework. The plan specifies using `LlmAgent` and a `Runner` for orchestration. While helper methods like `create_adk_agent` exist, the primary logic (e.g., `decompose_and_dispatch`) does not use the ADK execution model.
-   **Required Fix:** The agents' core methods need to be refactored to be executed by an ADK `Runner`, and their state should be managed via `session.state` as intended by the ADK framework, rather than direct Redis calls within the agent logic.

### 2. ADK Live Voice Integration (Prompt 3 & 4)

-   **Status:** Not Implemented
-   **Observation:** The `voice_handler.py` file is empty. The FastAPI WebSocket endpoint in `main.py` is a placeholder and does not integrate with ADK Live for speech-to-text or text-to-speech. The frontend `VoiceInterface.jsx` is likely a static component without the client-side logic to connect to ADK Live.
-   **Required Fix:** Implement the `voice_handler.py` to process audio streams using the Google Cloud Speech-to-Text API. The FastAPI WebSocket needs to be updated to handle the ADK Live protocol. The `CoordinatorAgent` must be modified to stream spoken responses back using Text-to-Speech.

### 3. Robust Task State Management (Prompt 2)

-   **Status:** Partially Implemented
-   **Observation:** The system uses Redis lists for task queues and publishes notifications. However, the detailed state tracking for each task (e.g., `PENDING` → `ASSIGNED` → `IN_PROGRESS` → `COMPLETED`) using Redis Hashes, as specified in the `scaled_down_ideas_claude.md` document, is not present. Agents do not update a central state hash for the tasks they are processing.
-   **Required Fix:** Modify the agents to update the status of a task in a dedicated Redis Hash (e.g., `HSET "task:123" "status" "IN_PROGRESS"`) as they execute. This is crucial for the frontend to monitor agent activity accurately.

### 4. Frontend Interactivity and Data Visualization (Prompt 4)

-   **Status:** Incomplete
-   **Observation:** The React components for the frontend exist, but they are likely static placeholders. The logic to connect to the WebSocket for real-time updates, visualize agent status from Redis pub/sub messages, and render the analysis results (like concept maps or feasibility scores) is missing.
-   **Required Fix:** Implement the client-side logic in the React components to:
    -   Connect to the FastAPI WebSocket.
    -   Listen for `agent:activity` messages and update the `AgentStatus` component.
    -   Fetch and display paper analysis results from the `/api/papers` endpoint.
    -   Visualize the output of the `PlanningAgent` and `AnalysisAgent`.

### 5. DSPy Integration for Task Decomposition (Prompt 3)

-   **Status:** Incomplete
-   **Observation:** The `CoordinatorAgent` includes a `try...except` block for `dspy`, but it's designed to fail gracefully and fall back to a simple heuristic. A properly configured DSPy module that connects to a language model for robust task decomposition is not implemented.
-   **Required Fix:** Configure a `dspy` language model (like `dspy.Google`) and implement a proper `dspy.Module` for the decomposition logic in the `CoordinatorAgent`. This requires setting up the necessary API keys and environment. Refer to the `/llm_models_python_code_src/DSPy` code base to understand how to use dspy.
