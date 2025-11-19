# Serve Frontend from Cloud Run

## 1. Issue Analysis

### Current State
The user has confirmed that the `frontend/` directory is present in the deployed container (via `COPY . .` in `Dockerfile`).
However, the `main.py` (FastAPI app) is currently only serving API endpoints and WebSockets. It is **not** configured to serve the static frontend files.
Additionally, the frontend code is in source format (React/TypeScript) and needs to be **built** into static HTML/JS/CSS assets before it can be served. The current `Dockerfile` uses a Python base image and does not include Node.js or a build step for the frontend.

### Problem
When the user visits the Cloud Run URL, they see the JSON response `{"message": "Mini-ARGOS POC is running"}` from the root endpoint `/`, instead of the React application.

## 2. Solution

To serve the frontend from the same Cloud Run service, we need to:
1.  **Build the Frontend**: Update the build process to compile the React app into static assets.
2.  **Serve Static Files**: Update `main.py` to serve these static assets from the root URL.

## 3. Technical Plan

### Step 1: Update `Dockerfile` for Multi-Stage Build
Modify `Dockerfile` to use a multi-stage build:
*   **Stage 1 (Node.js)**: Install dependencies and build the React app (`npm run build`).
*   **Stage 2 (Python)**: Copy the built assets from Stage 1 into the Python container (e.g., to `/app/frontend/build`).

### Step 2: Update `main.py` to Serve Static Files
Modify `src/main.py` to:
*   Mount the static assets directory (`/app/frontend/build`) to a path (e.g., `/static` or root).
*   Add a catch-all route (or specific root route) to serve `index.html` for the Single Page Application (SPA) to work correctly.
*   **Important**: The API endpoints must take precedence over the static files.

## 4. Coding Agent Prompts

### Prompt 1: Update Dockerfile

```text
You need to update the `Dockerfile` to build the React frontend.

1.  Read `Dockerfile`.
2.  Convert it to a multi-stage build.
3.  **Stage 1**: Use `node:18-alpine` as `build-step`.
    *   Workdir: `/app/frontend`
    *   Copy `frontend/package.json` and `frontend/package-lock.json`.
    *   Run `npm install`.
    *   Copy the `frontend/` directory.
    *   Run `npm run build`.
4.  **Stage 2**: Use the existing `python:3.11-slim-buster` image.
    *   Keep existing Python setup steps.
    *   Add a step to copy the build artifacts: `COPY --from=build-step /app/frontend/build /app/frontend/build`.
```

### Prompt 2: Update main.py

```text
You need to update `src/main.py` to serve the built frontend.

1.  Read `src/main.py`.
2.  Import `StaticFiles` from `fastapi.staticfiles`.
3.  Mount the static directory: `app.mount("/static", StaticFiles(directory="/app/frontend/build/static"), name="static")`.
    *   *Note: Check the actual build structure of React. Usually `npm run build` creates a `build` folder with `static/` inside it, plus `index.html` at the root of `build`.*
    *   Actually, it's better to mount the whole build folder to `/` but keep API routes working.
    *   **Better Approach**:
        *   Mount `/static` to `/app/frontend/build/static`.
        *   Create a route for `/` that returns `FileResponse("/app/frontend/build/index.html")`.
        *   (Optional) Add a catch-all route for SPA history mode if needed, but start with root.
4.  **Constraint**: Ensure `read_root` (the current `/` handler) is either removed or moved to `/api/health`.
```
