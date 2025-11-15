# Technical Plan: POC Idea #5 - Mini-ARGOS with Agent Collaboration & State Persistence + ADK Live

**Document Version:** 1.0
**Date:** November 15, 2025

## 1. Project Overview

This document outlines the technical plan for implementing a proof-of-concept (POC) of a "Mini-ARGOS" system. This POC is based on "POC Idea #5" from the `scaled_down_ideas_claude.md` document.

The system will feature a multi-agent architecture with three specialized agents (Coordinator, Research, Planning/Analysis) that collaborate to analyze research papers and synthesize novel applications. The POC will leverage Google's Agent Development Kit (ADK) with the Live API for voice interaction, Redis for state persistence and messaging, Tavily for web search, and CopilotKit for the user interface.

## 2. Architecture

The architecture is designed for real-time, interactive, and multi-modal (voice and text) agent collaboration.

```
Voice/Text Input → ADK Live Agent → FastAPI Gateway → Coordinator Agent
       ↓                                                      ↓
  (Speech-to-Text)                                     Redis (State Store)
       ↓                                                      ↓
  Text Processing                    ┌───────────────────────┼───────────────────┐
       ↓                              ↓                       ↓                   ↓
  WebSocket ←→          Research Agent (PDF/Web)    Planning Agent      Analysis Agent
                        (Tavily + Doc Parsing)      (Synthesis)         (Feasibility)
                                     ↓                       ↓                   ↓
                                     └─────────→ Redis Results ←────────────────┘
                                                     ↓
                                            Text-to-Speech ← CopilotKit Dashboard
                                                     ↓          (Real-time Agent Monitor)
                                              Voice Output
```

## 3. Technology Stack

- **Backend Framework**: FastAPI
- **Agent Framework**: Google Agent Development Kit (ADK)
- **Language Model**: Gemini 2.0 (via ADK)
- **Database/Messaging**: Redis (Google Cloud Memorystore for deployment)
- **Web Search**: Tavily MCP
- **Frontend**: React with CopilotKit
- **Deployment**: Docker, Google Cloud Run
- **Voice Interaction**: ADK Live API, Google Cloud Speech-to-Text, Google Cloud Text-to-Speech

## 4. Local Development Setup

### 4.1. Python Environment

A virtual environment will be created within the `/llm_models_python_code_src/ARGOS_POS` directory to maintain dependency isolation.

**Command to create virtual environment:**
```bash
python3 -m venv /llm_models_python_code_src/ARGOS_POS/.venv
source /llm_models_python_code_src/ARGOS_POS/.venv/bin/activate
```

### 4.2. `pyproject.toml`

A `pyproject.toml` file will be used to manage project dependencies and configuration.

```toml
[tool.poetry]
name = "mini-argos-poc"
version = "0.1.0"
description = "A proof-of-concept for a mini-ARGOS system with agent collaboration."
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
google-adk = ">=0.1.0"
agent-starter-pack = ">=0.1.0"
redis = ">=5.0.0"
fastapi = ">=0.104.0"
uvicorn = {extras = ["standard"], version = ">=0.24.0"}
copilotkit = ">=1.0.0"
google-cloud-speech = ">=2.21.0"
google-cloud-texttospeech = ">=2.14.0"
websockets = ">=12.0"
pypdf2 = ">=3.0.0"
pdfplumber = ">=0.10.0"
arxiv = ">=2.0.0"
networkx = ">=3.2"
matplotlib = ">=3.8.0"
scikit-learn = ">=1.3.0"
dspy-ai = "^2.4.3" # For DSPy-powered task decomposition

[tool.poetry.dev-dependencies]
pytest = "^7.4"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

### 4.3. `.gitignore`

A `.gitignore` file will be created to exclude unnecessary files from version control.

```
# Virtual Environment
.venv/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# IDE files
.idea/
.vscode/

# Environment variables
.env

# Local data
*.db
*.sqlite3

# Test reports
htmlcov/
.coverage
```

## 5. Local vs. Cloud Testing

- **Local Testing**:
    - FastAPI server
    - Agent logic (without ADK Live voice)
    - Tavily MCP integration
    - CopilotKit frontend (basic functionality)
    - Redis running in a local Docker container.
- **Google Cloud Testing**:
    - Full ADK Live voice interaction (requires Google Cloud infrastructure).
    - Redis state persistence using Google Cloud Memorystore.
    - End-to-end testing of the deployed application on Cloud Run.

## 6. Tavily API Usage

The free tier of the Tavily API will be used for this POC. As per their documentation at `https://docs.tavily.com/documentation/api-credits`, the free tier has limitations on the number of API calls. This should be sufficient for development and demonstration purposes.

## 7. Prompts for the Coding Agent

### Prompt 1: Project Scaffolding

"You are an expert AI programmer. Your task is to set up the project structure for the 'Mini-ARGOS' POC.

1.  Create the directory structure as defined in the `scaled_down_ideas_claude.md` document under POC #5.
2.  Create the `pyproject.toml` and `.gitignore` files as specified in the technical plan.
3.  Create empty Python files for `main.py`, `redis_client.py`, `schemas.py`, `paper_parser.py`, `voice_handler.py`, and `utils.py`.
4.  Create an `agents` subdirectory with empty `__init__.py`, `coordinator.py`, `research.py`, `planning.py`, and `analysis.py` files.
5.  Create a `frontend` directory with a basic React/CopilotKit setup.

Before you begin, review the directory structures of the following SDKs to understand their internal logic and how they should be integrated:
-   **GOOGLE Agent Development Kit**: `/llm_models_python_code_src/GCP-agent-starter-pack` and `/llm_models_python_code_src/adk-python`
-   **TAVILY MCP**: `/llm_models_python_code_src/TavilyMCP`
-   **COPILOTKIT**: `/llm_models_python_code_src/CoPilotKit`
-   **Google Cloud**: `/llm_models_python_code_src/GCP-python-docs-samples`"

### Prompt 2: Backend Implementation (FastAPI and Redis)

"Continue building the 'Mini-ARGOS' POC. Implement the FastAPI backend and Redis client.

1.  In `src/redis_client.py`, create a Redis client that can connect to a local Redis instance or a Google Cloud Memorystore instance based on environment variables. Implement helper functions for the data structures outlined in the POC #5 Redis plan (Lists for tasks, Hashes for state, etc.).
2.  In `src/schemas.py`, define Pydantic models for tasks, agent status, and paper analysis results.
3.  In `src/main.py`, set up a FastAPI application with a WebSocket endpoint for ADK Live and a simple status endpoint."

### Prompt 3: Agent Implementation

"Now, implement the agents.

1.  In `src/agents/coordinator.py`, create the `CoordinatorAgent` using ADK's `LlmAgent`. It should handle task decomposition using DSPy, manage the task dependency graph, and distribute tasks via Redis.
2.  In `src/agents/research.py`, create the `ResearchAgent`. It should listen for tasks on a Redis channel, use the Tavily MCP to find research papers, and use a PDF parser (implement in `src/paper_parser.py`) to extract content.
3.  In `src/agents/planning.py` and `src/agents/analysis.py`, create the `PlanningAgent` and `AnalysisAgent`. These agents will consume results from the `ResearchAgent`, synthesize concepts, and perform feasibility analysis."

### Prompt 4: Frontend Implementation

"Finally, build the frontend.

1.  In the `frontend` directory, create a React application using CopilotKit.
2.  Implement the dashboard UI as described in POC #5, including:
    - A main chat interface (`useCopilotChat`).
    - An agent status sidebar.
    - A voice interface component for ADK Live.
    - Visualization components for the analysis results."
