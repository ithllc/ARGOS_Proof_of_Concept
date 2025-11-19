# Fix Docker Build Failure: NPM Dependency Conflict

## 1. Issue Analysis

### Symptoms
The Cloud Build process failed during the `npm install` step with an `ERESOLVE` error.
The error message indicates a dependency conflict:
`Could not resolve dependency: peerOptional typescript@"^3.2.1 || ^4" from react-scripts@5.0.1`
`Found: typescript@5.9.3`

### Root Cause
The project is using `react-scripts@5.0.1`, which has a peer dependency on TypeScript versions `^3.2.1` or `^4`. However, the project's `package.json` specifies `typescript@"^5.4.0"`, which resolves to version 5.x (specifically 5.9.3 in the build). This version mismatch causes `npm install` to fail in strict mode.

### Solution
We can resolve this by instructing `npm` to ignore peer dependency conflicts using the `--legacy-peer-deps` flag. This is a common and generally safe workaround for `react-scripts` v5 with newer TypeScript versions.

## 2. Technical Plan

### Step 1: Update `Dockerfile`
Modify the `RUN npm install` instruction in the `build-step` stage.
*   **Change**: `RUN npm install`
*   **To**: `RUN npm install --legacy-peer-deps`

## 3. Coding Agent Prompts

### Prompt 1: Fix Dockerfile NPM Install

```text
You need to fix the `Dockerfile` to resolve the NPM dependency conflict.

1.  Read `Dockerfile`.
2.  Locate the line: `RUN npm install` (in the `build-step` stage).
3.  Replace it with: `RUN npm install --legacy-peer-deps`
```
