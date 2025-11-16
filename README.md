# Mini-ARGOS POC - ADK Version

The Mini-ARGOS Proof-of-Concept is a sophisticated, multi-agent system designed to automate and accelerate the research and analysis process. It emulates a team of specialized AI agents that collaborate to break down complex user queries, find and analyze relevant research papers, and synthesize novel concepts and applications from the source material.

This system can be used by researchers, analysts, and strategists to rapidly discover synergies between different fields of study, assess the feasibility of combining new technologies, and generate innovative ideas. By leveraging voice commands and real-time updates, it acts as an interactive partner in the exploration and ideation process, significantly reducing the manual effort required to conduct in-depth literature reviews.

## Prerequisites
- Python 3.11+
- A `GOOGLE_API_KEY` for Gemini, required for DSPy-based task decomposition.
- Google Cloud credentials configured for Speech-to-Text, Text-to-Speech, and AI Platform (for Imagen/Veo).

## Getting Started

The project is now a standard Google Agent Development Kit (ADK) application.

1.  **Create `.env` file**:
    In the `ARGOS_POS` root directory, create a `.env` file.

    ```
    # Required for DSPy-powered task decomposition.
    # If not provided, the system falls back to a simple heuristic.
    GOOGLE_API_KEY=your_google_api_key_here

    # Set to "mock" for offline testing without a real Tavily API key.
    TAVILY_API_KEY=mock

    # Redis connection details
    REDIS_HOST=localhost
    REDIS_PORT=6379
    ```

2.  **Install Dependencies**:
    ```bash
    # Create and activate a virtual environment
    python3 -m venv .venv
    source .venv/bin/activate

    # Install requirements
    pip install -r requirements.txt
    ```

3.  **Start Redis**:
    You need a running Redis instance. The easiest way is with Docker.
    ```bash
    docker run --name mini-argos-redis -p 6379:6379 -d redis:7-alpine
    ```

4.  **Run the Application**:
    ```bash
    export PYTHONPATH=$(pwd)/src
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```

## How to Use the Application

Once the application is running, open your web browser and navigate to:

**`http://localhost:8000`**

You will see the ADK's built-in web UI. From there, you can select an agent (e.g., `coordinator`) and interact with it directly to start the analysis process.

**Using the Voice Interface:**
Navigate to the frontend application (e.g., `http://localhost:3000` if running the React app separately). Use the "Start Recording" button in the Voice Interface to begin real-time voice interaction. The Coordinator Agent can now process your spoken queries and generate multi-modal responses (images and videos) which will be displayed directly in the UI.

## ADK Live and Multi-Modal Capabilities

This POC now integrates Google Agent Development Kit (ADK) Live for real-time voice interaction and multi-modal generation capabilities.

-   **Real-time Voice Interaction**: The system supports streaming Speech-to-Text (STT) and Text-to-Speech (TTS) via a WebSocket connection, enabling natural language conversations with the Coordinator Agent.
-   **Multi-Modal Output**: The Coordinator Agent can now generate images using Google Cloud Imagen 3 and videos using Google Cloud Veo, based on user prompts. These generated media are displayed directly in the frontend.

## Deployment

For instructions on how to build and deploy this application to Google Cloud, please see the detailed guide at:

[**ARGOS POC Deployment Guide**](./docs/deployment_guide.md)

## Component Notes

### DSPy Integration
- The `CoordinatorAgent` now uses `dspy` and a Google Gemini model to intelligently decompose user queries into actionable tasks.
- This requires a valid `GOOGLE_API_KEY` in your `.env` file.
- If the key is missing or invalid, the agent will automatically fall back to a simpler, non-AI heuristic for decomposition.

### Tavily Fallback
- If `TAVILY_API_KEY` is not set or is set to `mock`, the `ResearchAgent` will use a mock client (`src/mocks/tavily_mock.py`).
- This mock client returns local sample papers, allowing for offline development and testing of the research and parsing pipeline.


