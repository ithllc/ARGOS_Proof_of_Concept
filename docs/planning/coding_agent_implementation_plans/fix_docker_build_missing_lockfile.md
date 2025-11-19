# Fix Docker Build Failure: Missing package-lock.json

## 1. Issue Analysis

### Symptoms
The Cloud Build process failed during the Docker build step with the error:
`COPY failed: file not found in build context or excluded by .dockerignore: stat frontend/package-lock.json: file does not exist`

### Root Cause
The `Dockerfile` attempts to copy `frontend/package-lock.json` in Step 3:
`COPY frontend/package.json frontend/package-lock.json ./`

However, checking the `frontend/` directory contents reveals that `package-lock.json` does **not** exist in the repository. Only `package.json` is present. This is common in projects that haven't been built locally or where the lock file wasn't committed.

### Solution
Update the `Dockerfile` to only copy `package.json` initially. `npm install` will generate a lock file (or just install from `package.json`), which is sufficient for the build.

## 2. Technical Plan

### Step 1: Update `Dockerfile`
Modify the `COPY` instruction in the `build-step` stage.
*   **Change**: `COPY frontend/package.json frontend/package-lock.json ./`
*   **To**: `COPY frontend/package.json ./`

## 3. Coding Agent Prompts

### Prompt 1: Fix Dockerfile COPY Instruction

```text
You need to fix the `Dockerfile` because `frontend/package-lock.json` does not exist.

1.  Read `Dockerfile`.
2.  Locate the line: `COPY frontend/package.json frontend/package-lock.json ./`
3.  Replace it with: `COPY frontend/package.json ./`
```
