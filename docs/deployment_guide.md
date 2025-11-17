# ARGOS POC Deployment Guide

**Version:** 1.0
**Date:** November 15, 2025

This document summarizes the refactoring of the ARGOS POC project to make it compatible with the Google Agent Development Kit (ADK) and provides instructions for deploying it to Google Cloud.

## 1. Project Refactoring for ADK Compatibility

The project was refactored to align with the architecture and conventions of the Google Agent Development Kit.

### 1.1. Agent Refactoring

All agents (`Coordinator`, `Research`, `Planning`, `Analysis`) were refactored from simple Python classes into ADK-compatible `LlmAgent`s. Their core logic is now exposed as tools that the `LlmAgent` can use.

-   **New Structure:** Each agent now resides in its own subdirectory within `src/agents/` (e.g., `src/agents/coordinator/`).
-   **`agent.py`:** Each agent's subdirectory contains an `agent.py` file that defines a `root_agent` variable, which is an instance of `LlmAgent`. This is the standard pattern expected by the ADK's `AgentLoader`.

### 1.2. FastAPI Server

The production FastAPI gateway is implemented in `src/main.py` and serves as the primary entry point for the ARGOS POC. Key design goals are to expose REST endpoints used by the frontend, provide WebSocket endpoints for real-time audio and live communication, and optionally register CopilotKit/AG-UI endpoints if the optional dependencies are present.

Important design choices:

- Production vs. Dev separation: `src/main.py` is the production FastAPI application (run on port 8000 in development). ADK's `get_fast_api_app()` is retained only for the ADK debugging UI and moved into `src/debug.py` so that the ADK web UI runs on a separate port (8001) and does not replace or conflict with the production app.
- Optional CopilotKit / AG-UI registration: `main.py` attempts to register CopilotKit endpoints via `copilotkit.integrations.fastapi.add_fastapi_endpoint` and also registers AG-UI-wrapped ADK agents using `ag_ui_adk.ADkAgent` when those packages are installed. When missing, the server runs normally with no CopilotKit endpoints.

Example: The main app exposes the following functionality when dependencies are installed:

- GET `/` — Health check
- GET `/status` — Application status
- POST `/api/decompose` — Uses the Coordinator decomposition tools
- GET `/api/papers` — High-level paper retrieval from Redis
- WebSocket `/ws/{client_id}` — Broadcast channel for dashboard features
- WebSocket `/ws/live` — Voice audio streaming (retains prior ADK Live behavior)
- AG-UI / CopilotKit endpoints — `/copilotkit` (general remote endpoint) and individual ADK agent endpoints such as `/copilotkit/coordinator`, `/copilotkit/research`, etc. These are registered only if `copilotkit` and/or `ag_ui_adk` are installed.

If you need to see the original `main.py` from the previous commit, you can fetch it for reference with Git:

```bash
cd /llm_models_python_code_src/ARGOS_POS
git show f881136:src/main.py
```

How to run production and debug servers locally:

1) Run the main application (production FastAPI gateway):

```bash
cd /llm_models_python_code_src/ARGOS_POS
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

2) (Optional) Run the ADK Debug UI (development-only):

```bash
cd /llm_models_python_code_src/ARGOS_POS
python -m src.debug
# Debug UI available: http://localhost:8001
```

3) Start the frontend and point it to the CopilotKit endpoint if available:

```bash
cd /llm_models_python_code_src/ARGOS_POS/frontend
npm start
# Frontend: http://localhost:3000
```

Installing the optional CopilotKit/AG-UI dependencies for full integration:

```bash
cd /llm_models_python_code_src/ARGOS_POS
poetry add ag_ui_adk
poetry install

# Install local CopilotKit SDK (development only)
cd /llm_models_python_code_src/CoPilotKit/sdk-python
pip install -e .
```

Notes:
- Keep `src/debug.py` as a development-only tool — it runs `get_fast_api_app(..., web=True)` so you don't accidentally expose the ADK debug UI in production. `main.py` remains the production API that the React frontend integrates with.
- If you rely on CopilotKit endpoints in the frontend, ensure `copilotkit` is installed in the same Python environment as the FastAPI app and that the CopilotKit SDK’s `add_fastapi_endpoint` is available to `main.py`.

### 1.3. Dependency Management

The `pyproject.toml` was updated to resolve dependency conflicts and to add required integrations. Key additions:

- `ag_ui_adk`: Provides the bridge between Google ADK agents and AG-UI/CopilotKit
- `copilotkit`: Local CopilotKit Python SDK (linked via `path` to `CoPilotKit/sdk-python`) to enable CopilotKit endpoints

A `requirements.txt` file was generated from the `pyproject.toml`. New dependencies for Google Cloud Speech-to-Text, Text-to-Speech, and AI Platform (for Imagen/Veo) were added to support the ADK Live and multi-modal features.

## 2. Deployment Artifacts

The following files were created to prepare the application for deployment.

### 2.1. `Dockerfile`

A `Dockerfile` was created in the `ARGOS_POS` directory of the local repository to containerize the application. Ensure that your `requirements.txt` file (generated from `pyproject.toml`) includes all necessary Google Cloud dependencies (e.g., `google-cloud-speech`, `google-cloud-texttospeech`, `google-cloud-aiplatform`).

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Set the PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2. `cloudbuild.yaml`

A `cloudbuild.yaml` file was created in the `ARGOS_POS` directory to automate the build and deployment process on Google Cloud.

```yaml
steps:
# Build the container image
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-poc-repo/argos-poc:latest', '.']

# Push the container image to Artifact Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-poc-repo/argos-poc:latest']

# Deploy container image to Cloud Run
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
  - 'run'
  - 'deploy'
  - 'argos-pos-service' # You can change this service name
  - '--image'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-poc-repo/argos-poc:latest'
  - '--region'
  - 'us-central1'
  - '--platform'
  - 'managed'
  - '--allow-unauthenticated'
  - '--port'
  - '8000'
  # The following environment variables are needed by the application.
  # You should set these to your actual values, preferably using Secret Manager.
  - '--set-env-vars'
  - 'GOOGLE_API_KEY=your-google-api-key'
  - '--set-env-vars'
  - 'REDIS_HOST=your-redis-host'
  - '--set-env-vars'
  - 'REDIS_PORT=your-redis-port'

images:
- 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-poc-repo/argos-poc:latest'
```

## 3. Deployment Instructions

Here's what you need to do to deploy your application to Google Cloud:

**Step 1: Enable Google Cloud APIs**

You need to enable the Cloud Build, Cloud Run, Artifact Registry, Speech-to-Text, Text-to-Speech, and AI Platform APIs for your Google Cloud project. You can do this by running the following commands in your terminal:

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

**Step 2: Create an Artifact Registry Repository**

You need a repository to store your container images. Create one with the following command (you only need to do this once per project):

```bash
gcloud artifacts repositories create argos-poc-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for ARGOS project"
```

**Step 2.5: Create a Memorystore for Redis Instance and Secrets**

For the deployed application to connect to Redis, you need a cloud-hosted Redis instance. You will also secure its connection details using Secret Manager.

1.  **Enable the Redis and Secret Manager APIs:**
    ```bash
    gcloud services enable redis.googleapis.com
    gcloud services enable secretmanager.googleapis.com
    ```

2.  **Create a Memorystore for Redis instance:**
    This command creates a basic Redis instance. For production, you may need to configure VPC networking.
    ```bash
    gcloud redis instances create argos-redis --size=1 --region=us-central1
    ```

3.  **Get the Redis instance details:**
    Note the `host` and `port` from the output of this command.
    ```bash
    gcloud redis instances describe argos-redis --region=us-central1
    ```

4.  **Create secrets for the Redis connection:**
    Replace `<YOUR_REDIS_HOST>` and `<YOUR_REDIS_PORT>` with the values from the previous step.
    ```bash
    echo -n "<YOUR_REDIS_HOST>" | gcloud secrets create ARGOS_REDIS_HOST --data-file=-
    echo -n "<YOUR_REDIS_PORT>" | gcloud secrets create ARGOS_REDIS_PORT --data-file=-
    ```
5.  **Create secrets for your API keys:**
    Replace the placeholder values with your actual keys.
    ```bash
    echo -n "your-google-api-key" | gcloud secrets create ARGOS_GOOGLE_API_KEY --data-file=-
    echo -n "your-tavily-api-key" | gcloud secrets create ARGOS_TAVILY_API_KEY --data-file=-
    ```

**Step 3: Submit the Build to Cloud Build**

Now you can submit your application to Cloud Build. This command will read the `cloudbuild.yaml` file, build the image, push it to Artifact Registry, and deploy it to Cloud Run.

Before you run the command, make sure you are in the root of the project directory (`/llm_models_python_code_src`).

```bash
gcloud builds submit --config ARGOS_POS/cloudbuild.yaml .
```

**Important:** The `cloudbuild.yaml` file has placeholders for your environment variables (`GOOGLE_API_KEY`, `REDIS_HOST`, `REDIS_PORT`, `TAVILY_API_KEY`). For a production deployment, it is highly recommended to store these secrets in [Google Secret Manager](https://cloud.google.com/secret-manager) and grant your Cloud Run service access to them. Additionally, ensure the Cloud Run service account has the necessary IAM roles for Google Cloud Speech-to-Text, Text-to-Speech, and AI Platform services (e.g., `roles/speech.viewer`, `roles/texttospeech.viewer`, `roles/aiplatform.user`). For a quick test, you can replace the placeholder values directly in the `cloudbuild.yaml` file, but be careful not to commit them to your repository.
