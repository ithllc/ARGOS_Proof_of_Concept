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

The `src/main.py` was simplified to use the ADK's `get_fast_api_app` function. This function handles the creation of the FastAPI application, agent loading, and serves the ADK's built-in web UI. It also now includes a dedicated WebSocket endpoint (`/ws/live`) for real-time voice interaction.

```python
# src/main.py
from google.adk.cli.fast_api import get_fast_api_app
import os

agents_dir = os.path.join(os.path.dirname(__file__), "agents")

app = get_fast_api_app(
    agents_dir=agents_dir,
    web=True,
)
```

### 1.3. Dependency Management

The `pyproject.toml` was updated to resolve dependency conflicts between `google-adk` and other packages. The `copilotkit` package was removed as it was causing conflicts and is not needed when using the ADK's built-in web UI. A `requirements.txt` file was generated from the `pyproject.toml`. New dependencies for Google Cloud Speech-to-Text, Text-to-Speech, and AI Platform (for Imagen/Veo) were added to support the ADK Live and multi-modal features.

## 2. Deployment Artifacts

The following files were created to prepare the application for deployment.

### 2.1. `Dockerfile`

A `Dockerfile` was created in the `ARGOS_POS` directory to containerize the application. Ensure that your `requirements.txt` file (generated from `pyproject.toml`) includes all necessary Google Cloud dependencies (e.g., `google-cloud-speech`, `google-cloud-texttospeech`, `google-cloud-aiplatform`).

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
  args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-repo/argos-pos:latest', '.']

# Push the container image to Artifact Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-repo/argos-pos:latest']

# Deploy container image to Cloud Run
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
  - 'run'
  - 'deploy'
  - 'argos-pos-service' # You can change this service name
  - '--image'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-repo/argos-pos:latest'
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
- 'us-central1-docker.pkg.dev/$PROJECT_ID/argos-repo/argos-pos:latest'
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
gcloud artifacts repositories create argos-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for ARGOS project"
```

**Step 3: Submit the Build to Cloud Build**

Now you can submit your application to Cloud Build. This command will read the `cloudbuild.yaml` file, build the image, push it to Artifact Registry, and deploy it to Cloud Run.

Before you run the command, make sure you are in the root of the project directory (`/llm_models_python_code_src`).

```bash
gcloud builds submit --config ARGOS_POS/cloudbuild.yaml .
```

**Important:** The `cloudbuild.yaml` file has placeholders for your environment variables (`GOOGLE_API_KEY`, `REDIS_HOST`, `REDIS_PORT`). For a production deployment, it is highly recommended to store these secrets in [Google Secret Manager](https://cloud.google.com/secret-manager) and grant your Cloud Run service access to them. Additionally, ensure the Cloud Run service account has the necessary IAM roles for Google Cloud Speech-to-Text, Text-to-Speech, and AI Platform services (e.g., `roles/speech.viewer`, `roles/texttospeech.viewer`, `roles/aiplatform.user`). For a quick test, you can replace the placeholder values directly in the `cloudbuild.yaml` file, but be careful not to commit them to your repository.
