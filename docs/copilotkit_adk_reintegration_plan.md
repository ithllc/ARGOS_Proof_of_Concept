# CopilotKit and ADK Web UI Co-existence Technical Plan

**Document Version:** 1.0  
**Date:** November 16, 2025

## 1. Executive Summary

This document provides a comprehensive technical plan to restore CopilotKit integration for the production frontend while maintaining the ADK Web UI for development and debugging purposes. The plan addresses the critical misunderstanding in commit `1eae0f1` (sixth commit) where the ADK Web UI replaced CopilotKit instead of coexisting with it.

### Problem Statement

1. **Main Application Conflict**: The `main.py` was refactored to use ADK's `get_fast_api_app()`, which replaced the original FastAPI application that served CopilotKit endpoints.
2. **Frontend Broken**: The React frontend in `/frontend` uses CopilotKit and cannot function without proper backend integration.
3. **TypeScript Errors**: The `VoiceInterface.tsx` has JSX-related TypeScript configuration issues.
4. **Missing AG-UI Integration**: The CopilotKit documentation references `ag_ui_adk` package for ADK integration, but this is not currently installed or configured.

## 2. Architecture Overview

### 2.1. Current (Broken) Architecture

```
FastAPI App (main.py)
├── ADK Web UI (get_fast_api_app) - Port 8000
├── /ws/live endpoint (voice handler)
└── [Missing] CopilotKit endpoints
```

### 2.2. Target Architecture

```
FastAPI App (main.py) - Port 8000 (Production)
├── CopilotKit endpoints (/copilotkit/*)
├── Custom API routes (/api/*)
├── /ws/live endpoint (voice handler)
└── WebSocket for frontend (/ws/{client_id})

ADK Debug App (debug.py) - Port 8001 (Development Only)
├── ADK Web UI (for agent debugging)
└── Agent discovery and testing interface
```

## 3. Key Findings from Research

### 3.1. CopilotKit SDK Structure

The local CopilotKit repository at `/llm_models_python_code_src/CoPilotKit/sdk-python` contains:
- `copilotkit.integrations.fastapi`: FastAPI integration module
- `copilotkit.sdk.CopilotKitRemoteEndpoint`: Core SDK for agent/action registration
- Support for LangGraph agents (but NOT Google ADK directly)

### 3.2. AG-UI Package Confusion

**Critical Discovery**: The CopilotKit documentation at `https://docs.copilotkit.ai/adk/quickstart` references an `ag_ui_adk` package that is:
- **NOT part of the local CopilotKit repository**
- **NOT currently installed in the project**
- **A separate package** required for Google ADK integration with CopilotKit

This is the missing link for ADK + CopilotKit integration.

### 3.3. Frontend Dependencies

The frontend `package.json` shows:
- `@copilotkit/react-core: ^0.1.0`
- `@copilotkit/react-ui: ^0.1.0`
- `react: ^18.2.0`
- **Missing**: TypeScript configuration (`tsconfig.json`)

## 4. Technical Implementation Plan

### Phase 1: Install Required Dependencies

#### Step 1.1: Install AG-UI ADK Package

**File to Edit**: `/llm_models_python_code_src/ARGOS_POS/pyproject.toml`

**Prompt for Coding Agent:**

"Add the `ag_ui_adk` package to the dependencies in `/llm_models_python_code_src/ARGOS_POS/pyproject.toml`. This package is required for integrating Google ADK agents with CopilotKit via the AG-UI protocol.

Under the `[tool.poetry.dependencies]` section, add:
```
ag_ui_adk = ">=0.1.0"
```

After adding this dependency, run `poetry lock` and `poetry install` to update the environment."

**Why This is Needed**: The `ag_ui_adk` package provides the `ADKAgent` wrapper and `add_adk_fastapi_endpoint` function that bridges Google ADK agents to the CopilotKit/AG-UI protocol.

---

#### Step 1.2: Install CopilotKit SDK

**Prompt for Coding Agent:**

"Install the CopilotKit Python SDK from the local repository. Navigate to `/llm_models_python_code_src/CoPilotKit/sdk-python` and run:

```bash
cd /llm_models_python_code_src/CoPilotKit/sdk-python
pip install -e .
```

This will install the `copilotkit` package in editable mode, allowing us to use the FastAPI integration module."

**Why This is Needed**: The CopilotKit SDK provides the FastAPI integration endpoints that the React frontend expects to communicate with.

---

### Phase 2: Restore and Refactor main.py

#### Step 2.1: Restore Original main.py Structure

**File to Edit**: `/llm_models_python_code_src/ARGOS_POS/src/main.py`

**Prompt for Coding Agent:**

"Restore the structure of `main.py` from commit `f881136` (fifth commit) and integrate both CopilotKit and ADK agent support. Here's the step-by-step process:

1. **Revert to Base Structure**: Use the following command to see the original file:
   ```bash
   cd /llm_models_python_code_src/ARGOS_POS
   git show f881136:src/main.py
   ```

2. **Create New main.py**: Replace the current `/llm_models_python_code_src/ARGOS_POS/src/main.py` with this structure:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from fastapi import Body
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables before other imports
import config

from agents.coordinator import CoordinatorAgent
from redis_client import redis_client
from agents.research import ResearchAgent
from agents.planning import PlanningAgent
from agents.analysis import AnalysisAgent
from voice_handler import VoiceHandler

# Import CopilotKit and AG-UI ADK integration
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit.sdk import CopilotKitRemoteEndpoint
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint

app = FastAPI(title="ARGOS POC - Production API")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
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

@app.get(\"/\")
async def read_root():
    return {\"message\": \"Mini-ARGOS POC is running\"}

@app.get(\"/status\")
async def get_status():
    return {\"status\": \"ok\"}

@app.post(\"/api/decompose\")
async def api_decompose(payload: dict = Body(...)):
    query = payload.get(\"query\")
    session_id = payload.get(\"session_id\")
    agent = CoordinatorAgent()
    task_ids = agent.decompose_and_dispatch(query, session_id=session_id)
    return {\"tasks\": task_ids}

@app.get(\"/api/papers\")
async def get_papers():
    keys = redis_client.client.keys(\"paper:*\")[:20]
    papers = []
    for k in keys:
        p = redis_client.get_all_hash_fields(k)
        papers.append({\"title\": p.get(\"title\", \"\"), \"url\": p.get(\"url\", \"\"), \"id\": k})
    return {\"papers\": papers}

@app.websocket(\"/ws/{client_id}\")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f\"You wrote: {data}\", websocket)
            await manager.broadcast(f\"Client #{client_id} says: {data}\")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f\"Client #{client_id} left the chat\")

@app.websocket(\"/ws/live\")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    voice_handler = VoiceHandler(websocket)
    try:
        while True:
            await voice_handler.handle_audio_stream()
    except WebSocketDisconnect:
        print(\"WebSocket disconnected\")
    except Exception as e:
        print(f\"WebSocket error: {e}\")
    finally:
        await voice_handler.close()
```

3. **Add CopilotKit Integration**: This will be done in the next step."

**Why This is Needed**: The original `main.py` structure supports the frontend application's requirements and includes all necessary endpoints. The ADK `get_fast_api_app()` should not be the primary application; it should be separate for debugging.

---

#### Step 2.2: Integrate ADK Agents with CopilotKit via AG-UI

**File to Edit**: `/llm_models_python_code_src/ARGOS_POS/src/main.py`

**Prompt for Coding Agent:**

"Add CopilotKit integration to the restored `main.py`. This involves creating AG-UI wrappers for each ADK agent and registering them with CopilotKit.

Add the following code to the end of `main.py` (after the WebSocket endpoints):

```python
# ============================================================================
# CopilotKit / AG-UI Integration for ADK Agents
# ============================================================================

import os
from google.adk.agents import LlmAgent

# Load ADK agents
agents_dir = os.path.join(os.path.dirname(__file__), \"agents\")

# Import the ADK agents (these should be LlmAgent instances from your agent files)
# You'll need to modify each agent file to export the root_agent
from agents.coordinator.agent import root_agent as coordinator_adk_agent
from agents.research.agent import root_agent as research_adk_agent
from agents.planning.agent import root_agent as planning_adk_agent
from agents.analysis.agent import root_agent as analysis_adk_agent

# Wrap each ADK agent with the AG-UI ADKAgent wrapper
coordinator_wrapper = ADKAgent(
    adk_agent=coordinator_adk_agent,
    app_name=\"argos_poc\",
    user_id=\"default_user\",  # This should be dynamic in production
    session_timeout_seconds=3600,
    use_in_memory_services=True
)

research_wrapper = ADKAgent(
    adk_agent=research_adk_agent,
    app_name=\"argos_poc\",
    user_id=\"default_user\",
    session_timeout_seconds=3600,
    use_in_memory_services=True
)

planning_wrapper = ADKAgent(
    adk_agent=planning_adk_agent,
    app_name=\"argos_poc\",
    user_id=\"default_user\",
    session_timeout_seconds=3600,
    use_in_memory_services=True
)

analysis_wrapper = ADKAgent(
    adk_agent=analysis_adk_agent,
    app_name=\"argos_poc\",
    user_id=\"default_user\",
    session_timeout_seconds=3600,
    use_in_memory_services=True
)

# Add AG-UI endpoints for each agent
add_adk_fastapi_endpoint(app, coordinator_wrapper, path=\"/copilotkit/coordinator\")
add_adk_fastapi_endpoint(app, research_wrapper, path=\"/copilotkit/research\")
add_adk_fastapi_endpoint(app, planning_wrapper, path=\"/copilotkit/planning\")
add_adk_fastapi_endpoint(app, analysis_wrapper, path=\"/copilotkit/analysis\")

print(\"CopilotKit endpoints registered:\")
print(\"  - /copilotkit/coordinator\")
print(\"  - /copilotkit/research\")
print(\"  - /copilotkit/planning\")
print(\"  - /copilotkit/analysis\")
```

**Important Notes**:
- Each agent subdirectory (e.g., `agents/coordinator/`) must have an `agent.py` file that exports a `root_agent` variable of type `LlmAgent`.
- The `user_id` should ideally come from the session or authentication context in a production system.
- The `/copilotkit/*` paths are where the React frontend will connect to interact with agents."

**Why This is Needed**: The AG-UI ADK integration provides a bridge between Google ADK agents and the CopilotKit frontend. Each agent is exposed as an AG-UI endpoint that the React application can communicate with.

---

### Phase 3: Create Separate ADK Debug Application

#### Step 3.1: Create debug.py for ADK Web UI

**File to Create**: `/llm_models_python_code_src/ARGOS_POS/src/debug.py`

**Prompt for Coding Agent:**

"Create a new file `/llm_models_python_code_src/ARGOS_POS/src/debug.py` that serves the ADK Web UI for development and debugging purposes. This will run on a separate port from the main application.

```python
\"\"\"
ADK Debug Web UI
This is a development-only tool for testing and debugging ADK agents.
Run this alongside the main application on a different port.
\"\"\"

from google.adk.cli.fast_api import get_fast_api_app
import os

# Load environment variables
import config

# The agents are in the 'agents' subdirectory of the 'src' directory
agents_dir = os.path.join(os.path.dirname(__file__), \"agents\")

# Create the ADK debug app with the built-in web UI
debug_app = get_fast_api_app(
    agents_dir=agents_dir,
    web=True,
)

if __name__ == \"__main__\":
    import uvicorn
    print(\"=\"*60)
    print(\"Starting ADK Debug Web UI\")
    print(\"This is for DEVELOPMENT ONLY - use for agent debugging\")
    print(\"Access at: http://localhost:8001\")
    print(\"=\"*60)
    uvicorn.run(debug_app, host=\"0.0.0.0\", port=8001)
```

To run the debug UI:
```bash
cd /llm_models_python_code_src/ARGOS_POS
python -m src.debug
```

This will start the ADK Web UI on port 8001, separate from the production application on port 8000."

**Why This is Needed**: The ADK Web UI is valuable for developers to test and debug agents, but it should not replace the production API. Running it on a separate port allows both systems to coexist.

---

### Phase 4: Fix Frontend TypeScript Configuration

#### Step 4.1: Create tsconfig.json

**File to Create**: `/llm_models_python_code_src/ARGOS_POS/frontend/tsconfig.json`

**Prompt for Coding Agent:**

"Create a TypeScript configuration file `/llm_models_python_code_src/ARGOS_POS/frontend/tsconfig.json` to resolve the JSX-related errors in `VoiceInterface.tsx`.

```json
{
  \"compilerOptions\": {
    \"target\": \"es5\",
    \"lib\": [
      \"dom\",
      \"dom.iterable\",
      \"esnext\"
    ],
    \"allowJs\": true,
    \"skipLibCheck\": true,
    \"esModuleInterop\": true,
    \"allowSyntheticDefaultImports\": true,
    \"strict\": true,
    \"forceConsistentCasingInFileNames\": true,
    \"noFallthroughCasesInSwitch\": true,
    \"module\": \"esnext\",
    \"moduleResolution\": \"node\",
    \"resolveJsonModule\": true,
    \"isolatedModules\": true,
    \"noEmit\": true,
    \"jsx\": \"react-jsx\"
  },
  \"include\": [
    \"src\"
  ]
}
```

The critical fix is the `\"jsx\": \"react-jsx\"` option, which tells TypeScript to use the modern JSX transform that doesn't require importing React in every file."

**Why This is Needed**: The error `"This JSX tag requires the module path 'react/jsx-runtime' to exist"` indicates that TypeScript doesn't know how to handle JSX. The `react-jsx` setting enables the automatic JSX runtime introduced in React 17+.

---

#### Step 4.2: Install TypeScript and Type Definitions

**Prompt for Coding Agent:**

"Update the frontend's `package.json` to include TypeScript and necessary type definitions.

Navigate to `/llm_models_python_code_src/ARGOS_POS/frontend` and run:

```bash
npm install --save-dev typescript @types/react @types/react-dom @types/node
```

This will install:
- `typescript`: The TypeScript compiler
- `@types/react`: Type definitions for React
- `@types/react-dom`: Type definitions for React DOM
- `@types/node`: Type definitions for Node.js APIs"

**Why This is Needed**: The JSX.IntrinsicElements error indicates that TypeScript type definitions for React are missing. These packages provide the necessary type information.

---

### Phase 5: Update Frontend to Use CopilotKit with Multiple Agents

#### Step 5.1: Create CopilotKit Provider

**File to Create**: `/llm_models_python_code_src/ARGOS_POS/frontend/src/App.tsx`

**Prompt for Coding Agent:**

"Create or update `/llm_models_python_code_src/ARGOS_POS/frontend/src/App.tsx` to set up the CopilotKit provider that connects to the backend agents.

```typescript
import React from 'react';
import { CopilotKit } from '@copilotkit/react-core';
import { CopilotSidebar } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import VoiceInterface from './VoiceInterface';

function App() {
  return (
    <CopilotKit 
      runtimeUrl=\"http://localhost:8000/copilotkit/coordinator\"
      agent=\"coordinator\"
    >
      <div className=\"App\">
        <header className=\"App-header\">
          <h1>ARGOS POC - Agent Collaboration Platform</h1>
        </header>
        <main>
          <VoiceInterface />
          <CopilotSidebar
            labels={{
              title: \"ARGOS Assistant\",
              initial: \"Hi! I can help you analyze research papers and synthesize novel applications. What would you like to explore?\"
            }}
          />
        </main>
      </div>
    </CopilotKit>
  );
}

export default App;
```

**Note**: The `runtimeUrl` points to the coordinator agent endpoint. In a more advanced setup, you could create a Next.js runtime that routes to different agents, but for this POC, the coordinator can orchestrate the other agents."

**Why This is Needed**: The CopilotKit provider establishes the connection between the React frontend and the backend agents, enabling the chat interface and agent interactions.

---

### Phase 6: Update Documentation

#### Step 6.1: Update Architecture.md

**File to Edit**: `/llm_models_python_code_src/ARGOS_POS/docs/Architecture.md`

**Prompt for Coding Agent:**

"Update the Architecture document to reflect the new dual-server setup. Modify the section `3.2. FastAPI Gateway` as follows:

```markdown
### 3.2. FastAPI Gateway (`src/main.py`)
-   **Purpose**: Serves as the primary entry point for the production application.
-   **Responsibilities**:
    -   Provides RESTful API endpoints for task decomposition, paper retrieval, and status monitoring.
    -   Manages WebSocket connections for real-time communication (`/ws/{client_id}` and `/ws/live`).
    -   Integrates with CopilotKit via the AG-UI protocol, exposing each ADK agent as an AG-UI endpoint.
    -   Routes: 
        - `/api/*`: Custom API endpoints
        - `/copilotkit/*`: AG-UI endpoints for each agent (coordinator, research, planning, analysis)
        - `/ws/*`: WebSocket endpoints for real-time communication
    -   **Port**: 8000 (production)

### 3.2.1. ADK Debug UI (`src/debug.py`)
-   **Purpose**: Provides a development-only interface for testing and debugging ADK agents.
-   **Responsibilities**:
    -   Uses the `get_fast_api_app` function from Google Agent Development Kit to serve the built-in web UI.
    -   Automatically discovers and loads all ADK-compatible agents from `src/agents/`.
    -   **Port**: 8001 (development only)
    -   **Usage**: Run separately from the main application for agent debugging and testing.
```

Add a new section explaining the integration:

```markdown
### 3.3. CopilotKit Integration via AG-UI

The application uses the `ag_ui_adk` package to bridge Google ADK agents with the CopilotKit frontend framework. Each ADK agent is wrapped in an `ADKAgent` instance and exposed via the AG-UI protocol at dedicated endpoints.

**Integration Flow**:
1. ADK agents are defined as `LlmAgent` instances in their respective `agent.py` files.
2. Each agent is wrapped with `ADKAgent` from the `ag_ui_adk` package.
3. The `add_adk_fastapi_endpoint` function registers the agent at a specific path (e.g., `/copilotkit/coordinator`).
4. The React frontend uses `@copilotkit/react-core` and `@copilotkit/react-ui` to connect to these endpoints.
5. User interactions in the UI are translated to agent invocations, and agent responses are streamed back to the frontend.

This architecture allows the Google ADK agents to be used in a web-based, user-facing application while maintaining their native capabilities.
```"

**Why This is Needed**: Documentation must accurately reflect the system architecture to help developers understand the separation between production and debug environments.

---

#### Step 6.2: Update Deployment Guide

**File to Edit**: `/llm_models_python_code_src/ARGOS_POS/docs/deployment_guide.md`

**Prompt for Coding Agent:**

"Update the deployment guide to correct the information about CopilotKit. Replace the section `1.3. Dependency Management` with:

```markdown
### 1.3. Dependency Management

The `pyproject.toml` was updated to include all necessary dependencies:
- `google-adk`: For ADK agent framework
- `ag_ui_adk`: For integrating ADK agents with CopilotKit/AG-UI
- `copilotkit`: Python SDK for CopilotKit (installed from local repository)
- Google Cloud services: Speech-to-Text, Text-to-Speech, AI Platform
- Other dependencies: FastAPI, Redis, DSPy, etc.

**Important Note on CopilotKit**: 
- The production application (`src/main.py`) integrates CopilotKit for the user-facing frontend.
- The ADK Web UI (`src/debug.py`) is a separate development tool that runs on a different port.
- Both can run simultaneously: main app on port 8000, debug UI on port 8001.

A `requirements.txt` file was generated from the `pyproject.toml` for Docker builds.
```

Add a new section:

```markdown
## 4. Running the Application

### 4.1. Development Mode

For local development, you need to run both the main application and (optionally) the debug UI:

**Terminal 1 - Main Application**:
```bash
cd /llm_models_python_code_src/ARGOS_POS
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd /llm_models_python_code_src/ARGOS_POS/frontend
npm start
```

**Terminal 3 - Debug UI (Optional)**:
```bash
cd /llm_models_python_code_src/ARGOS_POS
python -m src.debug
```

Access points:
- Main Application API: `http://localhost:8000`
- React Frontend: `http://localhost:3000`
- ADK Debug UI: `http://localhost:8001`
```"

**Why This is Needed**: Clear deployment instructions prevent confusion about which component serves which purpose.

---

### Phase 7: Verification and Testing

#### Step 7.1: Verify Agent Endpoints

**Prompt for Coding Agent:**

"After implementing all changes, create a verification script to test that all endpoints are working correctly.

Create `/llm_models_python_code_src/ARGOS_POS/scripts/verify_endpoints.py`:

```python
\"\"\"
Endpoint Verification Script
Tests that all CopilotKit and API endpoints are responding correctly.
\"\"\"

import requests
import json

BASE_URL = \"http://localhost:8000\"

def test_endpoint(url, expected_status=200):
    try:
        response = requests.get(url)
        if response.status_code == expected_status:
            print(f\"✓ {url} - OK\")
            return True
        else:
            print(f\"✗ {url} - Failed (Status: {response.status_code})\")
            return False
    except Exception as e:
        print(f\"✗ {url} - Error: {e}\")
        return False

def test_copilotkit_endpoint(agent_name):
    url = f\"{BASE_URL}/copilotkit/{agent_name}\"
    return test_endpoint(url, expected_status=200)

if __name__ == \"__main__\":
    print(\"Verifying ARGOS POC Endpoints...\")
    print(\"=\"*60)
    
    print(\"\\nAPI Endpoints:\")
    test_endpoint(f\"{BASE_URL}/\")
    test_endpoint(f\"{BASE_URL}/status\")
    test_endpoint(f\"{BASE_URL}/api/papers\")
    
    print(\"\\nCopilotKit / AG-UI Endpoints:\")
    test_copilotkit_endpoint(\"coordinator\")
    test_copilotkit_endpoint(\"research\")
    test_copilotkit_endpoint(\"planning\")
    test_copilotkit_endpoint(\"analysis\")
    
    print(\"\\n\" + \"=\"*60)
    print(\"Verification complete.\")
```

Run this script after starting the main application to verify all endpoints are accessible."

**Why This is Needed**: Automated verification ensures the integration was successful and all components are communicating correctly.

---

## 5. Clarifications and Confirmations

### 5.1. AG-UI vs CopilotKit SDK

**Your Question**: "You need to reconfirm if I am correct about the `ag_ui_adk` package."

**Answer**: **You are correct**. The CopilotKit documentation at `https://docs.copilotkit.ai/adk/quickstart` explicitly shows that integrating Google ADK with CopilotKit requires the `ag_ui_adk` package, which is separate from the CopilotKit SDK itself.

**Key Points**:
1. **ag_ui_adk**: This package provides the `ADKAgent` wrapper class and `add_adk_fastapi_endpoint` function specifically for Google ADK integration.
2. **CopilotKit SDK** (`/llm_models_python_code_src/CoPilotKit/sdk-python`): This is the general CopilotKit Python SDK that works with LangGraph, LangChain, and other frameworks.
3. **Relationship**: AG-UI is the protocol, `ag_ui_adk` is the ADK implementation, and the CopilotKit SDK provides the foundation.

**Installation**:
```bash
pip install ag_ui_adk  # For ADK integration
pip install copilotkit  # General SDK (or use local version)
```

### 5.2. Why This Approach?

The dual-server approach (production + debug) provides:
1. **Separation of Concerns**: Production API separate from development tools
2. **No Conflicts**: Different ports mean no route conflicts
3. **Security**: Debug UI not exposed in production deployments
4. **Flexibility**: Can run either or both as needed

## 6. Rollback Safety

If any issues arise during implementation, you can safely rollback:

```bash
cd /llm_models_python_code_src/ARGOS_POS
git checkout f881136 -- src/main.py  # Restore fifth commit version
```

Then follow this plan step-by-step to build the integration properly.

## 7. Summary of Changes

| Component | Action | Purpose |
|-----------|--------|---------|
| `pyproject.toml` | Add `ag_ui_adk` dependency | Enable ADK-CopilotKit integration |
| `src/main.py` | Restore + extend | Production API with CopilotKit |
| `src/debug.py` | Create new file | Separate ADK debug UI |
| `frontend/tsconfig.json` | Create new file | Fix TypeScript JSX errors |
| `frontend/package.json` | Add TypeScript deps | Support TypeScript compilation |
| `frontend/src/App.tsx` | Create/update | CopilotKit provider setup |
| Documentation | Update multiple files | Reflect new architecture |

## 8. Expected Outcome

After completing this plan:
1. ✅ Production API runs on port 8000 with CopilotKit endpoints
2. ✅ React frontend connects to agents via CopilotKit
3. ✅ ADK Debug UI available on port 8001 for development
4. ✅ No conflicts between systems
5. ✅ TypeScript errors in frontend resolved
6. ✅ Full documentation of architecture

## 9. Next Steps After Implementation

Once this integration is complete, you can:
1. Test the frontend UI with agent interactions
2. Implement the DSPy-powered streaming agents from the previous plan
3. Enhance the admin monitoring interface
4. Deploy to Google Cloud with proper environment separation

---

**Document Status**: Ready for implementation by coding agent.
