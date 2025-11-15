# Mini-ARGOS POC Architecture

**Document Version:** 1.1
**Date:** November 15, 2025

## 1. Overview

This document provides an overview of the technical architecture for the Mini-ARGOS Proof-of-Concept (POC), which is based on "POC Idea #5" from the `scaled_down_ideas_claude.md` document. The system is designed as a multi-agent collaboration platform for analyzing research papers and synthesizing novel applications.

The architecture emphasizes modularity, real-time interaction, and state persistence, leveraging a modern stack of AI and cloud-native technologies.

## 2. Architectural Diagram

The system follows a distributed, event-driven architecture where agents communicate and coordinate through a central message bus (Redis). A dedicated configuration module ensures that environment variables are loaded correctly at startup.

```
+-------------------+      +-----------------+      +---------------------+
|   .env File       |----->|  Config Loader  |----->|  Python Scripts     |
| (API Keys, etc.)  |      |  (config.py)    |      | (main.py, agents/*) |
+-------------------+      +-----------------+      +---------------------+
                                                            |
                                                            v
+-------------------+      +-----------------+      +---------------------+
| User Interface    |----->| FastAPI Gateway |----->|  Coordinator Agent  |
| (React/CopilotKit)|      | (main.py)       |      |  (coordinator.py)   |
+-------------------+      +-------+---------+      +----------+----------+
      ^                            |                           | (DSPy for Decomposition)
      | (WebSocket for UI updates) |                           |
      |                            |                           v
+-----+----------------------------+---------------------------+-----+
|                             Redis Message Bus                     |
|                                                                   |
|  - Task Queues (LISTS: `tasks:research`)                          |
|  - Task State (HASHES: `task:<id>`)                               |
|  - Results Cache (HASHES: `paper:<id>`, `synthesis:<id>`)         |
|  - Notifications (PUBSUB: `agent:activity`)                       |
+-------------------------------------------------------------------+
      |                           |                           |
      v                           v                           v
+----------+----------+ +----------+----------+ +----------+----------+
|  Research Agent   | |   Planning Agent  | |  Analysis Agent   |
|  (research.py)    | |   (planning.py)   | |  (analysis.py)    |
+-------------------+ +-------------------+ +-------------------+
      | (Tavily for Search)
      | (PyPDF2 for Parsing)
      v
+-------------------+
| External Sources  |
| (arXiv, Web Pages)|
+-------------------+
```

## 3. Core Components

### 3.1. Configuration (`src/config.py`)
-   **Purpose**: To centralize and manage environment variables.
-   **Responsibilities**:
    -   Uses the `python-dotenv` library to automatically find and load the `.env` file from the project root (`ARGOS_POS/.env`).
    -   Makes environment variables (like API keys and Redis connection details) available to the entire application.
    -   Logs a warning if the `.env` file is not found, preventing silent failures.
    -   This module is imported at the top of all key scripts to ensure variables are loaded before they are needed.

### 3.2. FastAPI Gateway (`src/main.py`)
-   **Purpose**: Serves as the primary entry point for all incoming requests.
-   **Responsibilities**:
    -   Exposes RESTful API endpoints (e.g., `/api/decompose`) to initiate agent workflows.
    -   Manages WebSocket connections for real-time communication with the frontend.
    -   Delegates initial user queries to the `CoordinatorAgent`.

### 3.3. Redis (`src/redis_client.py`)
-   **Purpose**: Acts as the central nervous system for the entire application. It is used for messaging, state management, and caching.
-   **Data Structures Used**:
    -   **Lists**: For creating FIFO (First-In, First-Out) task queues (e.g., `tasks:research`).
    -   **Hashes**: To store detailed state information for each task (`task:<id>`) and the content of parsed papers (`paper:<id>`).
    -   **Pub/Sub**: For broadcasting real-time notifications about agent activity (`agent:activity`), allowing the frontend and other components to listen for events.
    -   **Strings with TTL**: For caching synthesis and analysis results.

### 3.4. Agents (`src/agents/`)

The system is composed of specialized agents that perform distinct functions.

#### a. Coordinator Agent (`coordinator.py`)
-   **Trigger**: Receives a high-level query from the user via the FastAPI gateway.
-   **Function**: Its primary role is **task decomposition**.
-   **Tooling**: It uses **DSPy** with a Google Gemini model to intelligently break down a complex query into a series of simple, actionable search tasks. If DSPy is unavailable (e.g., no API key), it falls back to a heuristic-based method.
-   **Output**: Pushes the decomposed tasks into the `tasks:research` queue in Redis.

#### b. Research Agent (`research.py`)
-   **Trigger**: Listens for and pulls tasks from the `tasks:research` Redis queue.
-   **Function**: Executes web searches and extracts content from research papers.
-   **Tooling**:
    -   **Tavily (via MCP)**: The agent communicates with a `TavilyMCP` server, which is a Node.js application that wraps the `tavily-python` library. A dedicated Python client (`src/mcp_client.py`) manages this server as a subprocess and communicates with it over `stdio`, making the interaction seamless and language-agnostic. This adheres to the Model Context Protocol (MCP) for standardized tool interaction.
    -   **Paper Parser** (`paper_parser.py`): To extract text from URLs, supporting both HTML pages and PDF documents.
-   **Output**: Stores the extracted text and metadata in Redis Hashes (`paper:<id>`) and updates the task's state to `COMPLETED`.

#### c. Planning Agent (`planning.py`)
-   **Trigger**: Can be invoked after the `ResearchAgent` has processed one or more papers.
-   **Function**: Synthesizes information from multiple documents to find conceptual overlaps and potential applications.
-   **Tooling**: Uses a custom keyword analysis algorithm. It identifies words that appear in multiple documents (excluding common English "stop words") and ranks them by overall frequency to find the most relevant overlapping terms. This approach replaced an earlier implementation that used TF-IDF, as it proved more robust for the short and varied texts encountered.
-   **Output**: Stores a synthesis report (including concept overlap, a feasibility score, and example applications) in Redis.

#### d. Analysis Agent (`analysis.py`)
-   **Trigger**: Can be invoked after the `PlanningAgent` has created a synthesis.
-   **Function**: Assesses the overall feasibility and potential of the synthesized concepts.
-   **Tooling**: Uses **DSPy** with a local Ollama model to generate a structured analysis (strengths, weaknesses, opportunities) based on the synthesis report.
-   **Output**: Produces a final analysis report, stored in Redis.

## 4. Frontend (`frontend/`)

-   **Framework**: React, intended to be used with **CopilotKit**.
-   **Purpose**: Provides a user-friendly interface for interacting with the agent system.
-   **Key Features**:
    -   A chat interface for submitting queries.
    -   A real-time dashboard to monitor the status and activity of each agent by subscribing to the Redis `agent:activity` channel via the WebSocket.
    -   Components to visualize the results of the paper analysis and synthesis.

## 5. Local Development and Testing

-   **Environment Management**: A central `config.py` module loads environment variables from a `.env` file, making configuration straightforward.
-   **Virtual Environment**: All Python dependencies are managed via a `.venv` virtual environment and a `pyproject.toml` file.
-   **Unit Testing**: A comprehensive unit test suite is maintained in the `tests/` directory, using Python's `unittest` framework.
    -   **Mocking**: All external dependencies (Redis, MCP clients, LLMs) are mocked using `unittest.mock` and a custom `MockRedisClient`, allowing for fast, isolated, and reliable local testing.
    -   **Test Runner**: A `run_tests.sh` script is provided to execute the entire test suite, ensuring the correct Python path and environment are used.
    -   **Test Plans**: Detailed test plans and results are documented in `tests/docs/`.
````

#### c. Planning Agent (`planning.py`)
-   **Trigger**: Can be invoked after the `ResearchAgent` has processed one or more papers.
-   **Function**: Synthesizes information from multiple documents to find conceptual overlaps and potential applications.
-   **Tooling**: Uses `scikit-learn`'s TF-IDF vectorizer to identify common, important terms across different texts.
-   **Output**: Stores a synthesis report (including concept overlap, a feasibility score, and example applications) in Redis.

#### d. Analysis Agent (`analysis.py`)
-   **Trigger**: Can be invoked after the `PlanningAgent` has created a synthesis.
-   **Function**: Assesses the overall feasibility of the synthesized concepts.
-   **Output**: Produces a final feasibility score and rationale, stored in Redis.

## 4. Frontend (`frontend/`)

-   **Framework**: React, intended to be used with **CopilotKit**.
-   **Purpose**: Provides a user-friendly interface for interacting with the agent system.
-   **Key Features**:
    -   A chat interface for submitting queries.
    -   A real-time dashboard to monitor the status and activity of each agent by subscribing to the Redis `agent:activity` channel via the WebSocket.
    -   Components to visualize the results of the paper analysis and synthesis.

## 5. Local Development and Testing

-   **Environment Management**: A central `config.py` module loads environment variables from a `.env` file, making configuration straightforward.
-   **Docker Compose**: A `docker-compose.yml` file is provided to simplify local setup by managing the Redis container and the application environment.
-   **Mocking**: The system is designed for offline development.
    -   The `TavilyClient` can be replaced by a `MockTavilyClient` by setting `TAVILY_API_KEY=mock` in the `.env` file.
    -   The `CoordinatorAgent` falls back to a non-AI heuristic if a `GOOGLE_API_KEY` is not provided for DSPy.
-   **Unit Testing**: The architecture supports local unit tests for individual agents and components. (Testing framework to be set up).
