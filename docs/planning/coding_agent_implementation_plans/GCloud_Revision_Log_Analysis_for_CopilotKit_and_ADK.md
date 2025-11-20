# GCloud Revision Log Analysis for CopilotKit and ADK

## Problem Analysis
The current deployment on Cloud Run is failing with a 500 Internal Server Error.
**Error:** `AttributeError: 'LlmAgent' object has no attribute 'dict_repr'`
**Location:** `src/main.py` inside `CopilotKitRemoteEndpoint` initialization.
**Cause:** The `CopilotKitRemoteEndpoint` from `copilotkit.sdk` expects agent objects that implement the `dict_repr` method (and likely others). The `LlmAgent` from `google.adk.agents` does not implement this interface. The current code attempts to pass `LlmAgent` instances directly to `CopilotKitRemoteEndpoint`.

## Proposed Solution
The user provided documentation/snippet indicates that for Google ADK agents, the `ag_ui_adk` package should be used instead of (or as a wrapper for) the standard CopilotKit SDK integration.
The `ag_ui_adk` package provides `ADKAgent` and `add_adk_fastapi_endpoint`.

The `src/main.py` file already contains code to use `ag_ui_adk`, but it is currently:
1.  Optional (inside a try/except block).
2.  Co-existing with the failing `CopilotKitRemoteEndpoint` block.
3.  Mapping agents to specific subpaths (e.g., `/copilotkit/coordinator`).

**Action Plan:**
1.  **Remove the failing `CopilotKitRemoteEndpoint` block**: This block is fundamentally incompatible with `LlmAgent` objects without a wrapper.
2.  **Promote `ag_ui_adk` integration**: Ensure the `ADKAgent` and `add_adk_fastapi_endpoint` code is the primary integration path.
3.  **Endpoint Adjustment**: The frontend is known to query `/copilotkit` (based on previous 405 errors). The current `ag_ui_adk` setup maps to `/copilotkit/coordinator`. I will modify the mapping to expose the `coordinator` agent at `/copilotkit` to match the frontend's expectation, or ensure the frontend can handle the subpaths. Assuming the frontend expects a single endpoint at `/copilotkit`, I will map the coordinator there.

## Implementation Steps & GCloud Commands

### 1. Modify `src/main.py`
*   Comment out or remove the `CopilotKitRemoteEndpoint` section.
*   Update the `ADKAgent` section to map the coordinator agent to `/copilotkit`.

### 2. Deploy to Cloud Run
Execute the build and deploy command to update the service.

```bash
gcloud builds submit --tag gcr.io/argos-poc/argos-poc-api .
gcloud run deploy argos-poc-api --image gcr.io/argos-poc/argos-poc-api --platform managed --region us-central1 --allow-unauthenticated
```

### 3. Verify Deployment
Check the logs to ensure the service starts without errors and handles requests.

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=argos-poc-api" --limit 20 --format json
```

### 4. Validation
*   Verify that `POST /copilotkit` (or `GET /copilotkit/info`) returns a valid response instead of 500.
*   Verify that the `AttributeError` is gone.

## Why these commands?
*   `gcloud builds submit`: To containerize the updated Python code.
*   `gcloud run deploy`: To update the running service with the new container image.
*   `gcloud logging read`: To confirm the fix works in the production environment, as we cannot fully replicate the `google-adk` environment locally.
