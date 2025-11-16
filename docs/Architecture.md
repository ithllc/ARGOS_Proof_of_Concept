# Mini-ARGOS POC Architecture

**Document Version:** 1.1
**Date:** November 15, 2025

## 1. Overview

This document provides an overview of the technical architecture for the Mini-ARGOS Proof-of-Concept (POC), which is based on "POC Idea #5" from the `scaled_down_ideas_claude.md` document. The system is designed as a multi-agent collaboration platform for analyzing research papers and synthesizing novel applications.

The architecture emphasizes modularity, real-time interaction, and state persistence, leveraging a modern stack of AI and cloud-native technologies.

## 2. Architectural Diagram

The system has been refactored to use the Google Agent Development Kit (ADK) as its core backend framework. The ADK handles agent loading and serves a development UI.

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

## 3. Core Components

### 3.1. Configuration (`src/config.py`)
-   **Purpose**: To centralize and manage environment variables.
-   **Responsibilities**:
    -   Uses the `python-dotenv` library to automatically find and load the `.env` file from the project root (`ARGOS_POS/.env`).
    -   Makes environment variables (like API keys and Redis connection details) available to the entire application.
    -   Logs a warning if the `.env` file is not found, preventing silent failures.
    -   This module is imported at the top of all key scripts to ensure variables are loaded before they are needed.

### 3.2. FastAPI Gateway (`src/main.py`)
-   **Purpose**: Serves as the primary entry point for the application.
-   **Responsibilities**:
    -   Uses the `get_fast_api_app` function from the Google Agent Development Kit (ADK).
    -   This function automatically discovers and loads all ADK-compatible agents from the `src/agents/` directory.
    -   It serves the ADK's built-in web UI for development and testing, which can be used to interact with the loaded agents.
    -   Manages the underlying API endpoints required for the ADK framework to operate.
    -   Includes a dedicated WebSocket endpoint (`/ws/live`) for real-time voice interaction with the ADK Live protocol.

### 3.3. Redis (`src/redis_client.py`)
-   **Purpose**: Acts as the central nervous system for the entire application. It is used for messaging, state management, and caching.
-   **Data Structures Used**:
    -   **Lists**: For creating FIFO (First-In, First-Out) task queues (e.g., `tasks:research`).
    -   **Hashes**: To store detailed state information for each task (`task:<id>`) and the content of parsed papers (`paper:<id>`).
    -   **Pub/Sub**: For broadcasting real-time notifications about agent activity (`agent:activity`), allowing the frontend and other components to listen for events.
    -   **Strings with TTL**: For caching synthesis and analysis results.

### 3.4. Voice Handler (`src/voice_handler.py`)
-   **Purpose**: Manages real-time audio streaming and interaction with Google Cloud Speech-to-Text (STT) and Text-to-Speech (TTS) APIs, and facilitates communication with the `CoordinatorAgent` via Redis.
-   **Responsibilities**:
    -   Receives audio chunks from the frontend via the `/ws/live` WebSocket.
    -   Streams audio to Google Cloud STT for transcription.
    -   Publishes transcribed text to a dedicated Redis queue (`tasks:coordinator_voice_input`) for the `CoordinatorAgent`.
    -   Subscribes to a Redis Pub/Sub channel (`session:<id>:response`) to receive text and multi-modal responses from the `CoordinatorAgent`.
    -   Streams text from the `CoordinatorAgent` (via Redis) to Google Cloud TTS for audio synthesis.
    -   Sends synthesized audio and multi-modal content URLs back to the frontend via the WebSocket.

### 3.5. Multi-Modal Tools (`src/multi_modal_tools.py`)
-   **Purpose**: Provides `FunctionTool`s for generating images and videos using Google Cloud AI Platform models.
-   **Responsibilities**:
    -   `generate_architecture_image`: Takes a textual description and calls Imagen 3 to generate an image.
    -   `generate_example_video`: Takes a textual description and calls Veo to generate a video.
    -   Returns URLs of the generated media.

### 3.6. Agents (`src/agents/`)

The system is composed of specialized agents that perform distinct functions.

#### a. Coordinator Agent (`coordinator.py`)
-   **Trigger**: Receives a high-level query from the user via the FastAPI gateway, or processes voice input tasks pulled from the `tasks:coordinator_voice_input` Redis queue (pushed by the `VoiceHandler`).
-   **Function**: Its primary role is **task decomposition** and orchestrating responses, including multi-modal outputs. It uses a dedicated `process_voice_input` tool to handle voice-originated requests.
-   **Tooling**: It uses **DSPy** with a Google Gemini model to intelligently break down a complex query into a series of simple, actionable search tasks. It also leverages `FunctionTool`s for multi-modal generation (Imagen 3 for images, Veo for videos). If DSPy is unavailable (e.g., no API key), it falls back to a heuristic-based method for task decomposition.
-   **Output**: Pushes the decomposed tasks into the `tasks:research` queue in Redis, or directly invokes multi-modal tools and publishes their results (text and/or media URLs) back to the `VoiceHandler` via a Redis Pub/Sub channel (`session:<id>:response`).

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

## 5. Frontend (`frontend/`)

-   **Framework**: React, intended to be used with **CopilotKit**.
-   **Purpose**: Provides a user-friendly interface for interacting with the agent system.
-   **Key Features**:
    -   A chat interface for submitting queries.
    -   A real-time dashboard to monitor the status and activity of each agent by subscribing to the Redis `agent:activity` channel via the WebSocket.
    -   Components to visualize the results of the paper analysis and synthesis.
    -   **Voice Interface (`VoiceInterface.tsx`)**: A new component enabling real-time voice interaction (microphone input, audio playback) and dynamic display of generated multi-modal content (images, videos) from the agents.

## 6. Local Development and Testing

-   **Environment Management**: A central `config.py` module loads environment variables from a `.env` file, making configuration straightforward.
-   **Virtual Environment**: All Python dependencies are managed via a `.venv` virtual environment and a `pyproject.toml` file.
-   **Unit Testing**: A comprehensive unit test suite is maintained in the `tests/` directory, using Python's `unittest` framework.
    -   **Mocking**: All external dependencies (Redis, MCP clients, LLMs) are mocked using `unittest.mock` and a custom `MockRedisClient`, allowing for fast, isolated, and reliable local testing.
    -   **Test Runner**: A `run_tests.sh` script is provided to execute the entire test suite, ensuring the correct Python path and environment are used.
    -   **Test Plans**: Detailed test plans and results are documented in `tests/docs/`.
````

