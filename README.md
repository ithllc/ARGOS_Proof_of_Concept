# Mini-ARGOS POC - Local Development

This README describes how to run the Mini-ARGOS POC locally, test its different components, and understand its fallback behaviors.

## Prerequisites
- Python 3.11+
- Docker (optional, for Redis)
- A `GOOGLE_API_KEY` for Gemini, required for DSPy-based task decomposition.

## Quick Start (with Docker)

The easiest way to get started is with Docker Compose, which manages the Redis container and the application environment.

1.  **Create `.env` file**:
    In the `ARGOS_POS` root directory, create a `.env` file. You can start by copying `.env.example` if it exists.

    ```
    # Required for DSPy-powered task decomposition.
    # If not provided, the system falls back to a simple heuristic.
    GOOGLE_API_KEY=your_google_api_key_here

    # Set to "mock" for offline testing without a real Tavily API key.
    TAVILY_API_KEY=mock

    # Redis connection details (defaults for Docker Compose setup)
    REDIS_HOST=localhost
    REDIS_PORT=6379
    ```

2.  **Build and Run**:
    ```bash
    # This will build the app image, install dependencies, and start the app and redis services.
    docker compose up --build
    ```
    The FastAPI application will be available at `http://localhost:8000`.

## Manual Setup (without Docker)

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Start Redis**:
    If you're not using the Docker Compose setup, you'll need to run Redis manually.
    ```bash
    # Using Docker is still the easiest way:
    docker run --name mini-argos-redis -p 6379:6379 -d redis:7-alpine
    ```

3.  **Set Environment Variables and Run App**:
    Ensure your `.env` file is created as described above.
    ```bash
    export PYTHONPATH=$(pwd)/src
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```

## How to Use the API

### 1. Decompose a Query
Send a query to the `CoordinatorAgent` to break it down into tasks. This now uses **DSPy** if `GOOGLE_API_KEY` is provided.

```bash
curl -X POST -H 'Content-Type: application/json' \
-d '{"query":"Analyze the synergy between graph neural networks and reinforcement learning for drug discovery"}' \
http://localhost:8000/api/decompose
```

### 2. Run the Worker Process
In a separate terminal, run the `ResearchAgent` to process the tasks created in the previous step.

```bash
# Make sure your virtual environment is activated and PYTHONPATH is set
export PYTHONPATH=$(pwd)/src
python -c "from agents.research import ResearchAgent; ResearchAgent().listen_and_process()"
```

## Component Notes

### DSPy Integration
- The `CoordinatorAgent` now uses `dspy` and a Google Gemini model to intelligently decompose user queries into actionable tasks.
- This requires a valid `GOOGLE_API_KEY` in your `.env` file.
- If the key is missing or invalid, the agent will automatically fall back to a simpler, non-AI heuristic for decomposition.

### Tavily Fallback
- If `TAVILY_API_KEY` is not set or is set to `mock`, the `ResearchAgent` will use a mock client (`src/mocks/tavily_mock.py`).
- This mock client returns local sample papers, allowing for offline development and testing of the research and parsing pipeline.

### ADK Runner Example
You can also run the ADK `LlmAgent` decomposition locally to test the `Coordinator`'s ADK integration. This demonstrates how the agent would run in a full ADK environment.

```bash
export PYTHONPATH=$(pwd)/src
python src/scripts/run_adk_decompose.py
```


