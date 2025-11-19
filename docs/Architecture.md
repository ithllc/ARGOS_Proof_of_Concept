# ARGOS POC Architecture

**Document Version:** 1.2
**Date:** November 19, 2025

## 1. Overview

This document provides an overview of the technical architecture for the Mini-ARGOS Proof-of-Concept (POC), which is based on "POC Idea #5" from the `scaled_down_ideas_claude.md` document. The system is designed as a multi-agent collaboration platform for analyzing research papers and synthesizing novel applications.

The architecture emphasizes modularity, real-time interaction, and state persistence, leveraging a modern stack of AI and cloud-native technologies.

## 2. Architectural Diagram

The system uses a dual-server architecture that separates production functionality from development tooling. The Google Agent Development Kit (ADK) agents are exposed through both a production FastAPI gateway (with CopilotKit integration) and a separate development UI for debugging.

```
+-------------------------+      +------------------------+      +-------------------------+
|   React Frontend UI     |----->|  FastAPI Gateway       |----->| ADK Agent System        |
| (Port 3000)             |      |  (main.py - Port 8000) |      |                         |
| - CopilotKit UI         |      | - CopilotKit Endpoints |      | - Coordinator Agent     |
| - Voice Interface       |      | - /copilotkit/*        |      | - Research Agent        |
| - Agent Activity Log    |      | - /api/* endpoints     |      | - Planning Agent        |
|                         |      | - /ws/live WebSocket   |      | - Analysis Agent        |
|                         |      | - /ws/events WebSocket |      +-------------------------+
+-------------------------+      +------------------------+               |
                                          |                               |
                                          |          +--------------------+
                                          |          |
                                          v          v
                        +------------------+  +---------------------+  +---------------------+
                        |  Redis Layer     |  |  Voice Handler      |  | Multi-Modal Tools   |
                        |                  |  | (voice_handler.py)  |  | (multi_modal_tools)|
                        | - Pub/Sub        |  | - Google STT/TTS    |  | - Imagen 3          |
                        | - Task Queues    |  | - Session Mgmt      |  | - Veo Video         |
                        | - State Storage  |  +---------------------+  +---------------------+
                        +------------------+

+-------------------------+
|  ADK Debug Web UI       |
|  (debug.py - Port 8001) |      [Development Only - Separate Server]
|                         |
| - Agent Testing         |      Access: http://localhost:8001
| - Interactive Debugging |
| - ADK Built-in UI       |      Purpose: Developer tool for testing and
+-------------------------+               debugging ADK agents in isolation
```

## 3. Core Components

### 3.1. Configuration (`src/config.py`)
-   **Purpose**: To centralize and manage environment variables and secrets for both local and cloud deployments.
-   **Responsibilities**:
    -   Uses `python-dotenv` to load a `.env` file for local development.
    -   In Google Cloud, loads secrets from **Google Secret Manager**.
    -   Resolves the GCP project ID automatically.
    -   Fails gracefully if secrets cannot be loaded.

### 3.2. FastAPI Gateway (`src/main.py`)
-   **Purpose**: Serves as the primary entry point for the production application.
-   **Responsibilities**:
    -   Provides RESTful API endpoints (`/api/*`).
    -   Integrates CopilotKit endpoints (`/copilotkit/*`).
    -   Manages WebSocket connections for real-time communication:
        -   `/ws/live`: For real-time voice interaction.
        -   `/ws/events`: For broadcasting agent activity from the Redis `agent:activity` channel to the frontend.

### 3.3. Redis (`src/redis_client.py`)
-   **Purpose**: Acts as the central nervous system for messaging, state management, and caching.
-   **Cloud Deployment**: Requires a Serverless VPC Access Connector for use with Google Cloud Memorystore.
-   **Data Structures Used**: Lists (Task Queues), Hashes (State), Pub/Sub (Notifications), and Strings (Caching).

### 3.4. Voice Handler (`src/voice_handler.py`)
-   **Purpose**: Manages real-time audio streaming and interaction with Google Cloud Speech-to-Text (STT) and Text-to-Speech (TTS).
-   **Responsibilities**:
    -   Receives audio from the frontend via `/ws/live`.
    -   Uses `SpeechAsyncClient` to stream audio to Google Cloud STT for transcription.
    -   Publishes transcribed text to a Redis queue for the `CoordinatorAgent`.
    -   Subscribes to a Redis channel to receive responses from the `CoordinatorAgent`.
    -   Streams synthesized audio and multi-modal content back to the frontend.

### 3.5. Multi-Modal Tools (`src/multi_modal_tools.py`)
-   **Purpose**: Provides tools for generating images and videos.
-   **Responsibilities**:
    -   `generate_architecture_image`: Calls Imagen 3.
    -   `generate_example_video`: Calls Veo.

### 3.6. Agents (`src/agents/`)
-   **Coordinator Agent**: Decomposes user queries and orchestrates responses. Uses DSPy for intelligent task breakdown.
-   **Research Agent**: Executes web searches (Tavily) and parses papers.
-   **Planning Agent**: Synthesizes information from multiple documents.
-   **Analysis Agent**: Assesses the feasibility of synthesized concepts.

## 4. Frontend (`frontend/`)

-   **Framework**: React, integrated with **CopilotKit**.
-   **Purpose**: Provides the user interface, which is now served as static assets directly by the FastAPI application.
-   **Key Features**:
    -   **Chat Interface**: Conversational UI powered by CopilotKit.
    -   **Agent Activity Log (`AgentStatus.tsx`)**: A real-time dashboard that monitors agent activity by connecting to the `/ws/events` WebSocket.
    -   **Voice Interface (`VoiceInterface.tsx`)**: Real-time voice component. The WebSocket connection URL is now determined dynamically, and its state is managed with `useRef` to prevent race conditions.
-   **Build Fix**: The file `AgentStatus.jsx` was renamed to `AgentStatus.tsx` to fix a build failure caused by using TypeScript syntax in a `.jsx` file.

## 5. ADK Debug Web UI (`src/debug.py`)

-   **Purpose**: A development-only tool for testing and debugging ADK agents in isolation.
-   **Framework**: Uses Google ADK's built-in web UI.
-   **Access**: `http://localhost:8001`

## 6. Local Development and Testing

-   **Environment**: Managed via a `.env` file and `pyproject.toml`.
-   **Unit Testing**: Uses Python's `unittest` framework with extensive mocking of external services.

## 7. Cloud Deployment and Infrastructure

-   **CI/CD**: A `cloudbuild.yaml` file defines the pipeline for building the Docker container and deploying to Cloud Run.
-   **VPC Connectivity**: A Serverless VPC Access Connector is required for Cloud Run to communicate with Google Cloud Memorystore.