# Research Plan: Removing CoPilotKit and Tavily from ARGOS POC

## 1. Objective
To determine the feasibility and implications of removing CoPilotKit and Tavily from the ARGOS POC project, replacing them with a custom frontend implementation and the Google ADK `deep-search` agent (using Google Search).

## 2. Current Architecture Analysis
*   **Frontend**: React application using `@copilotkit/react-core` and `@copilotkit/react-ui`.
    *   **Dependency**: Relies on `CopilotSidebar` for chat interface and `useCoAgent` (likely) for state synchronization.
    *   **Communication**: Uses CopilotKit's runtime protocol for streaming and state updates.
*   **Backend**: Python (FastAPI/ADK) with `LlmAgent`.
    *   **Search**: Currently uses `Tavily` via an MCP client (`get_tavily_mcp_client`).
    *   **State**: Uses Redis for some event publishing (`agent:activity`), but relies on CopilotKit for the main chat/agent loop.

## 3. Proposed Replacement Analysis

### 3.1. Replacing Tavily with ADK Deep Search
*   **Candidate**: `google.adk.agents.deep-search` (specifically `google.adk.tools.google_search`).
*   **Feasibility**: **High**.
    *   The ADK `deep-search` example demonstrates a robust research pipeline (`section_planner`, `section_researcher`, `research_evaluator`) that is more sophisticated than a simple Tavily search loop.
    *   **Requirement**: The `google_search` tool in ADK requires a Google Search API key and Programmable Search Engine ID (or Vertex AI Search configuration). This is a standard configuration and eliminates the dependency on Tavily.

### 3.2. Replacing CoPilotKit with Custom Frontend
*   **Challenge**: CoPilotKit provides "out-of-the-box" streaming, UI components, and state synchronization.
*   **Replacement Strategy**:
    *   **Chat UI**: Implement a standard Chat interface (Message list + Input box). This is standard React development.
    *   **Streaming/Events**:
        *   **Current**: CopilotKit handles the stream.
        *   **Proposed**: Use **Server-Sent Events (SSE)** or **WebSockets**.
        *   **Mechanism**: The Backend Agent publishes events (thoughts, search results, final answers) to a Redis channel. A FastAPI endpoint streams these events to the frontend.
    *   **Shared State**:
        *   **Current**: `useCoAgent` syncs a JSON object.
        *   **Proposed**: Explicit Event-Driven Updates. When the agent updates the "Research Plan" or "Findings", it emits an event with the new data. The Frontend listens and updates its local state (Redux/Context).
*   **Feasibility**: **High**.
    *   While it requires writing more "plumbing" code (WebSocket handler, Chat UI), it provides absolute control and removes the "black box" nature of CopilotKit.
    *   **Standardization**: Using WebSockets/SSE is a standard industry practice for LLM streaming, arguably more "standard" than a specific vendor SDK like CopilotKit.

## 4. Comparison: Complexity vs. Control

| Feature | CoPilotKit + Tavily | Custom Frontend + ADK Deep Search |
| :--- | :--- | :--- |
| **Setup Speed** | Fast (if it works out of the box) | Medium (requires building UI/Socket logic) |
| **Customization** | Limited by SDK capabilities | Unlimited (Full control over UI/UX) |
| **Search Quality** | Dependent on Tavily | Dependent on Google Search + ADK Logic (High) |
| **Debugging** | Harder (Middleware abstraction) | Easier (Direct code control) |
| **Cost** | CopilotKit (Free/Pro) + Tavily ($) | Google Cloud Costs (Search API) |

## 5. Conclusion & Recommendation
It is **feasible** and **recommended** to proceed with the replacement if the goal is to reduce dependency complexity and gain full control over the agent's behavior and UI presentation.

*   **Tavily** can be immediately replaced by the ADK `deep-search` logic.
*   **CoPilotKit** can be replaced by a custom React frontend communicating via WebSockets/SSE with the FastAPI backend.

## 6. Next Steps
1.  Generate the `ArchitectureWithOutCoPilotKitandTavily.md` document detailing the new design.
2.  Refactor `ARGOS_POC` backend to integrate `deep-search` agents.
3.  Build the custom frontend components.
