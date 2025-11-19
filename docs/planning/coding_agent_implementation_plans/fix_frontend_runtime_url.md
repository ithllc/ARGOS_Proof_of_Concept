# Fix Frontend Build and Serving Issues

## 1. Issue Analysis

### Symptoms
1.  **Frontend Build**: The `Dockerfile` build might fail if `react-scripts` encounters TypeScript errors or if the `index.html` is missing (though we verified `index.html` exists).
2.  **Static File Serving**: The `src/main.py` file has been updated to serve static files, but the `Dockerfile` needs to ensure the build artifacts are actually copied to the correct location (`/app/frontend/build`).
3.  **Runtime URL**: The `App.tsx` file still has a hardcoded `runtimeUrl="http://localhost:8000/copilotkit"`. This will fail in production because the browser will try to connect to `localhost` instead of the Cloud Run URL.

### Root Cause
*   **Hardcoded URL**: `App.tsx` uses `localhost`.
*   **Potential Build Path Mismatch**: We need to ensure the `Dockerfile` copies the build output to `/app/frontend/build` as expected by `main.py`.

### Solution
1.  **Update `App.tsx`**: Use a relative URL for `runtimeUrl`. Since the frontend is served from the same domain as the backend (Cloud Run), a relative path `/copilotkit` will automatically use the correct origin.
2.  **Verify Dockerfile**: Ensure the `COPY --from=build-step` instruction places files in `/app/frontend/build`.

## 2. Technical Plan

### Step 1: Update `frontend/src/App.tsx`
Modify `App.tsx` to use a relative URL for the `CopilotKit` runtime.
*   **Change**: `runtimeUrl="http://localhost:8000/copilotkit"`
*   **To**: `runtimeUrl="/copilotkit"`

### Step 2: Verify Dockerfile Paths (No changes needed if correct)
The `Dockerfile` currently has:
`COPY --from=build-step /app/frontend/build /app/frontend/build`
And `main.py` uses:
`FRONTEND_BUILD_DIR = "/app/frontend/build"`
This matches.

## 3. Coding Agent Prompts

### Prompt 1: Update App.tsx Runtime URL

```text
You need to update `frontend/src/App.tsx` to use a relative URL for the backend connection.

1.  Read `frontend/src/App.tsx`.
2.  Locate the `CopilotKit` component.
3.  Change the `runtimeUrl` prop from `"http://localhost:8000/copilotkit"` to `"/copilotkit"`.
    *   *Reasoning*: Since the frontend is served by the same backend in Cloud Run, a relative path is the most robust way to connect, avoiding CORS issues and hardcoded domains.
```
