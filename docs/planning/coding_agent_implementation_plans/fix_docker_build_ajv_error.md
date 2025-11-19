# Fix Docker Build Failure: Missing AJV Dependency

## 1. Issue Analysis

### Symptoms
The Cloud Build process failed during the `npm run build` step with the error:
`Error: Cannot find module 'ajv/dist/compile/codegen'`
This error occurs within `react-scripts` -> `terser-webpack-plugin` -> `schema-utils` -> `ajv-keywords`.

### Root Cause
This is a known issue with `react-scripts` v5 when used with newer versions of `npm` (v7+) and dependency resolution. The `ajv` package is a peer dependency that isn't being correctly hoisted or resolved, leading to a `MODULE_NOT_FOUND` error at runtime during the build process.

### Solution
Explicitly install `ajv` as a dev dependency in the `frontend/package.json`. This ensures the package is available in the `node_modules` tree for `react-scripts` to use.

## 2. Technical Plan

### Step 1: Update `frontend/package.json`
Add `ajv` (version `^8.0.0`) to the `devDependencies` section.

## 3. Coding Agent Prompts

### Prompt 1: Add AJV Dependency

```text
You need to fix the missing `ajv` dependency error.

1.  Read `frontend/package.json`.
2.  Add `"ajv": "^8.0.0"` to the `devDependencies` object.
```
