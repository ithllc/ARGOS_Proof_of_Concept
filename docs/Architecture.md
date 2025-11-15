# Mini-ARGOS POC Architecture

**Document Version:** 1.1
**Date:** November 15, 2025

## 1. Overview

This document provides an overview of the technical architecture for the Mini-ARGOS Proof-of-Concept (POC), which is based on "POC Idea #5" from the `scaled_down_ideas_claude.md` document. The system is designed as a multi-agent collaboration platform for analyzing research papers and synthesizing novel applications.

The architecture emphasizes modularity, real-time interaction, and state persistence, leveraging a modern stack of AI and cloud-native technologies.

## 2. Architectural Diagram

The system follows a distributed, event-driven architecture where agents communicate and coordinate through a central message bus (Redis).

```
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

### 3.1. FastAPI Gateway (`src/main.py`)
-   **Purpose**: Serves as the primary entry point for all incoming requests.
-   **Responsibilities**:
    -   Exposes RESTful API endpoints (e.g., `/api/decompose`) to initiate agent workflows.
    -   Manages WebSocket connections for real-time communication with the frontend.
    -   Delegates initial user queries to the `CoordinatorAgent`.

### 3.2. Redis (`src/redis_client.py`)
-   **Purpose**: Acts as the central nervous system for the entire application. It is used for messaging, state management, and caching.
-   **Data Structures Used**:
    -   **Lists**: For creating FIFO (First-In, First-Out) task queues (e.g., `tasks:research`).
    -   **Hashes**: To store detailed state information for each task (`task:<id>`) and the content of parsed papers (`paper:<id>`).
    -   **Pub/Sub**: For broadcasting real-time notifications about agent activity (`agent:activity`), allowing the frontend and other components to listen for events.
    -   **Strings with TTL**: For caching synthesis and analysis results.

### 3.3. Agents (`src/agents/`)

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
    -   **Tavily**: To perform web searches and find relevant papers. It can be run with a mock client for offline development.
    -   **Paper Parser** (`paper_parser.py`): To extract text from URLs, supporting both HTML pages and PDF documents (`PyPDF2`).
-   **Output**: Stores the extracted text and metadata in Redis Hashes (`paper:<id>`) and updates the task's state to `COMPLETED`.

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

-   **Docker Compose**: A `docker-compose.yml` file is provided to simplify local setup by managing the Redis container and the application environment.
-   **Mocking**: The system is designed for offline development.
    -   The `TavilyClient` can be replaced by a `MockTavilyClient` by setting `TAVILY_API_KEY=mock` in the `.env` file.
    -   The `CoordinatorAgent` falls back to a non-AI heuristic if a `GOOGLE_API_KEY` is not provided for DSPy.
-   **Unit Testing**: The architecture supports local unit tests for individual agents and components. (Testing framework to be set up).
