# Fix Docker Build Failure: Invalid CopilotKit Version

## 1. Issue Analysis

### Symptoms
The Cloud Build process failed during `npm install` with the error:
`npm error code ETARGET`
`npm error notarget No matching version found for @copilotkit/react-core@^0.1.0.`

### Root Cause
The `frontend/package.json` file requests version `^0.1.0` of `@copilotkit/react-core` and `@copilotkit/react-ui`.
However, the current version of these packages on the npm registry is much higher (e.g., `1.10.x`). The requested version `0.1.0` likely does not exist or is not available.

### Solution
Update `frontend/package.json` to use the latest stable versions of the CopilotKit packages. We will also add `@copilotkit/runtime` as recommended by the official documentation.

## 2. Technical Plan

### Step 1: Update `frontend/package.json`
Modify the `dependencies` section in `frontend/package.json`.
*   Update `@copilotkit/react-core` to `^1.0.0`.
*   Update `@copilotkit/react-ui` to `^1.0.0`.
*   Add `@copilotkit/runtime` with version `^1.0.0` (optional but recommended by docs).

## 3. Coding Agent Prompts

### Prompt 1: Update package.json Dependencies

```text
You need to update `frontend/package.json` to use valid versions of the CopilotKit packages.

1.  Read `frontend/package.json`.
2.  In the `dependencies` object:
    *   Change `"@copilotkit/react-core": "^0.1.0"` to `"@copilotkit/react-core": "^1.0.0"`.
    *   Change `"@copilotkit/react-ui": "^0.1.0"` to `"@copilotkit/react-ui": "^1.0.0"`.
    *   Add `"@copilotkit/runtime": "^1.0.0"`.
```
