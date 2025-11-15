# ARGOS POC - Local Unit Test Plan

**Version:** 1.0
**Date:** November 15, 2025

This document outlines the unit testing strategy for the ARGOS Proof-of-Concept project, focusing on local testing without dependencies on live cloud services.

## 1. Testing Philosophy

The goal of our local unit testing is to verify the correctness of each individual component (agents, clients, utilities) in isolation. This is achieved through extensive use of mocking for external dependencies such as LLMs, APIs (Tavily), and network services (Redis).

This approach ensures that:
- Tests are fast and reliable.
- We can simulate various success and failure scenarios.
- The core business logic of each component is validated independently.

## 2. Completed Unit Tests

The following components have been tested:

### 2.1. `CoordinatorAgent` (`test_coordinator.py`)

-   **[✓] Test DSPy Decomposition**: Verifies that the agent correctly uses a mocked DSPy module to decompose a complex query into a structured list of tasks.
-   **[✓] Test Fallback Decomposition**: Ensures that if the DSPy module fails, the agent gracefully falls back to a simpler string-splitting mechanism to create tasks.
-   **[✓] Test Redis Interaction**: Confirms that the agent correctly pushes the generated tasks onto the appropriate Redis list (`tasks:research`).

### 2.2. `ResearchAgent` (`test_research.py`)

-   **[✓] Test Successful Search (via MCP)**: Verifies that the agent can successfully perform a search by calling the `TavilyMCPClient`. This test mocks the entire MCP client and its response, ensuring the agent correctly processes a successful search result.
-   **[✓] Test Search with No Results**: Ensures the agent handles an empty result set from Tavily gracefully and publishes the correct status message (`no_pdfs_found`) to Redis.
-   **[✓] Test Search Failure**: Simulates an exception during the search process and verifies that the agent catches it and publishes a `search_failed` status message.
-   **[✓] Test Redis Interaction**: Confirms that for successful searches, the agent correctly parses the results, extracts text (mocked), and stores the final paper data in the appropriate Redis hashes.
-   **[✓] Test Asynchronous Operation**: The entire test suite is asynchronous, validating the agent's `async` and `await` patterns.

### 2.3. `PlanningAgent` (`test_planning.py`)

-   **[✓] Test Synthesis with Valid Papers**: Verifies that the agent correctly identifies overlapping keywords (e.g., "quantum", "intersection") from multiple documents stored in Redis. It also confirms that words unique to a single document are excluded from the final overlap list.
-   **[✓] Test Synthesis with No Papers**: Ensures that when given no input, the agent produces an empty result without errors.
-   **[✓] Test Synthesis with Short/Empty Text**: Confirms that the agent's feasibility score is `0.0` and the overlap is empty when the source documents are too short to be meaningful, preventing errors from empty vocabularies.
-   **[✓] Test Redis Interaction**: Verifies that the agent correctly saves the final synthesis to Redis with the correct key and publishes a corresponding message to the `agent:activity` channel.
-   **[✓] Test ADK Agent Creation**: Mocks the `google.adk` library to confirm that the `create_adk_agent` method attempts to instantiate an `LlmAgent` with the correct parameters, and that it fails gracefully if the library is not installed.

## 3. Remaining Local Unit Tests

The following is a plan for the remaining unit tests required to achieve comprehensive local test coverage.

### 2.4. `AnalysisAgent` (`tests/test_analysis.py`)

-   **[✓] Test Successful Feasibility Assessment**: Verifies that the agent correctly aggregates feasibility scores and overlap information from multiple synthesis results stored in Redis, calculates an average score, and saves the final analysis to Redis. It also confirms that an `agent:activity` message is published.
-   **[✓] Test Assessment with No Synthesis Keys**: Ensures that the agent handles an empty list of synthesis keys gracefully, returning a default empty analysis and still saving it to Redis.
-   **[✓] Test Assessment with Non-Existent Synthesis Keys**: Confirms that the agent correctly ignores synthesis keys that are not found in Redis, returning an empty analysis.
-   **[✓] Test Assessment with Malformed JSON Synthesis Data**: Verifies that the agent can gracefully handle synthesis data in Redis that is not valid JSON, excluding it from the aggregation process.
-   **[✓] Test ADK Agent Creation**: Mocks the `google.adk` library to confirm that the `create_adk_agent` method attempts to instantiate an `LlmAgent` with the correct parameters, and that it fails gracefully if the library is not installed.

**Confirmation of `test_analysis.py` functionality:**
The `test_analysis.py` suite was executed using the command:
`cd /llm_models_python_code_src/ARGOS_POS && source .venv/bin/activate && PYTHONPATH=$PYTHONPATH:./src python3 -m unittest discover -s tests -p "test_*.py"`
Initially, the tests failed due to `AttributeError: 'NoneType' object has no attribute 'time'` in `AnalysisAgent.assess_feasibility`. This was identified as a bug where the method was incorrectly referencing a global `redis_client` instead of `self.redis`. The bug was fixed by changing `redis_client.client.time()[0]` to `self.redis.client.time()[0]` in `src/agents/analysis.py`. After this correction, all 16 tests across the project, including the newly added `test_analysis.py` tests, passed successfully.

## 3. Remaining Local Unit Tests

The following is a plan for the remaining unit tests required to achieve comprehensive local test coverage.

### 3.1. FastAPI Server (`tests/test_main.py`)

-   **[ ] Test Status Endpoint**: Create a test for the `/` endpoint to ensure it returns the expected status message.
-   **[ ] Test WebSocket Connection**: Write a test to verify that a WebSocket client can successfully connect to the `/ws` endpoint. This will involve mocking the ADK `voice_handler` logic that the endpoint calls.

### 3.2. Utilities

-   **[ ] `paper_parser.py`**:
    -   Create tests that mock the responses from `requests.get` and `pdfplumber.open`.
    -   Test with sample HTML and PDF content (as mocked byte streams) to ensure the text extraction logic works as expected.
    -   Test edge cases, such as non-PDF URLs or failed requests.
-   **[ ] `redis_client.py`**:
    -   While the `MockRedisClient` is used for agent tests, we should also test the *real* `RedisClient`.
    -   This will be more of an integration test and will require a running Redis instance (which can be managed via Docker for the test environment).
    -   Test the connection logic and error handling if Redis is unavailable.
-   **[ ] `mcp_client.py`**:
    -   Test the `_parse_tavily_text` method with various string formats to ensure it is robust.
    -   Test the client's connection/disconnection logic and error handling if the subprocess fails to start.
