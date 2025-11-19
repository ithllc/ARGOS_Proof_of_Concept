# Fix Redis Connection Timeout in Cloud Run

## 1. Issue Analysis

### Symptoms
The Cloud Run service `argos-pos-service` fails to start, resulting in `504 Upstream Request Timeout` errors when accessed.
The logs show a `redis.exceptions.TimeoutError: Timeout connecting to server` during the initialization of the application (specifically in `redis_client.py`).

### Root Cause
The application is attempting to connect to a Redis instance (Google Cloud Memorystore) using its private IP address. However, the Cloud Run service is **not configured with a Serverless VPC Access Connector**.

Without a VPC Connector, Cloud Run services cannot reach resources within a VPC network (like Memorystore) via their private IP addresses. The connection attempt times out (Errno 110), causing the application startup to fail.

Additionally, the `RedisClient` initialization in `src/redis_client.py` performs a `ping()` operation at module import time. When this fails, it raises an unhandled exception that crashes the Gunicorn worker process, leading to a crash loop.

## 2. Solution

To fix this issue, we need to:
1.  **Configure VPC Access**: Update the deployment configuration (`cloudbuild.yaml`) to attach the Cloud Run service to the appropriate Serverless VPC Access Connector.
2.  **Improve Error Handling**: Update `src/redis_client.py` to handle connection timeouts gracefully during initialization, preventing the entire application from crashing if Redis is temporarily unreachable.

## 3. Technical Plan

### Step 1: Update Deployment Configuration
Modify `cloudbuild.yaml` to include the `--vpc-connector` flag in the `gcloud run deploy` command.
*   **Action**: Add `--vpc-connector=YOUR_VPC_CONNECTOR_NAME` to the arguments.
*   **Note**: The user/developer needs to provide the actual name of the VPC connector created in the GCP project.

### Step 2: Robust Redis Initialization
Modify `src/redis_client.py` to:
*   Explicitly catch `redis.exceptions.TimeoutError` and `redis.exceptions.ConnectionError`.
*   Log the error but allow the `RedisClient` to instantiate with `self.client = None` (or a disconnected state) instead of crashing.
*   This ensures the app can start even if Redis is flaky, although endpoints requiring Redis will still fail (but with better error responses).

## 4. Coding Agent Prompts

### Prompt 1: Update `cloudbuild.yaml`

```text
You need to update the `cloudbuild.yaml` file to configure the VPC connector for the Cloud Run service.

1.  Read `cloudbuild.yaml`.
2.  In the `gcloud run deploy` step (the last step), add a new argument: `'--vpc-connector=projects/argos-proof-of-concept/locations/us-central1/connectors/argos-pos-vpc-connector'`.
    *   *Note: I am assuming the connector name is `argos-pos-vpc-connector` based on the project naming convention. If you don't know the name, use a placeholder like `VPC_CONNECTOR_NAME` and add a comment.*
3.  Ensure the indentation is correct (YAML list item).
```

### Prompt 2: Improve `src/redis_client.py`

```text
You need to improve the error handling in `src/redis_client.py` to prevent the application from crashing if Redis is unreachable at startup.

1.  Read `src/redis_client.py`.
2.  In the `__init__` method of `RedisClient`, update the `try...except` block.
3.  Add a specific handler for `redis.exceptions.TimeoutError` in addition to `redis.exceptions.ConnectionError`.
4.  Ensure that if an error occurs, `self.client` is set to `None` and a clear error message is printed/logged, but the exception is NOT raised.
5.  This will allow the application to start even if the initial `ping()` fails.
```
