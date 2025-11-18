# Technical Plan: DSPy-Powered Redis Streaming and RAG Agents

**Document Version:** 1.0
**Date:** November 16, 2025

## 1. Overview

This document outlines the technical implementation plan for two new agents within the Mini-ARGOS POC ecosystem. These agents will leverage the **DSPy** framework to process and analyze real-time event streams from Redis.

1.  **Event Generalizer Agent**: Subscribes to the Redis `agent:activity` stream, uses DSPy to generate user-friendly summaries of agent actions, and publishes them for the client-facing UI.
2.  **Admin RAG Agent**: Provides a Retrieval-Augmented Generation (RAG) interface for administrators. It uses the history of agent activity stored in Redis as its knowledge base to answer queries about the system's behavior.

## 2. Feasibility Analysis

The existing architecture is highly conducive to these additions:
-   **Redis Backbone**: The system's reliance on Redis for messaging (`Pub/Sub`) and state management is ideal. We will use the existing `agent:activity` channel and introduce a new Redis `List` for persistent event logging.
-   **ADK Framework**: The Google Agent Development Kit (ADK) structure in `src/agents/` allows for modular, discoverable agents. The new agents will be implemented following the existing pattern.
-   **DSPy Integration**: DSPy is already used by the `CoordinatorAgent` and `AnalysisAgent`, establishing a clear precedent for configuring and using DSPy programs within an agent.

## 3. Core Architectural Changes

### 3.1. Persistent Event Logging

To enable the Admin RAG agent, we need to persist events. A new component will be introduced to listen to the `agent:activity` channel and log every event to a Redis `List`.

-   **Redis Key**: `events:log` (A capped list to prevent infinite growth)
-   **Implementation**: A new background process or a modification to an existing agent (like the `CoordinatorAgent`) to perform this logging.

### 3.2. New Redis Channels

-   **`frontend:ui_events` (Pub/Sub)**: The `EventGeneralizerAgent` will publish its user-friendly summaries to this channel for the frontend to consume.

## 4. Technical Implementation Plan

This plan is broken down into steps with prompts suitable for a coding agent.

### Step 1: Create the Persistent Event Logger

**Task:** Modify the `CoordinatorAgent` to log all events from the `agent:activity` channel to a persistent Redis list.

**File to Edit:** `/llm_models_python_code_src/ARGOS_POC/src/agents/coordinator.py`

**Prompt for Coding Agent:**

"Update the `CoordinatorAgent` in `/llm_models_python_code_src/ARGOS_POC/src/agents/coordinator.py`. Add a new method that runs in a background thread. This method should subscribe to the Redis `agent:activity` Pub/Sub channel. For each message received, it should push the message data onto a Redis list named `events:log`. To prevent this list from growing indefinitely, use the `LTRIM` command to cap its size at 1000 entries after each push."

### Step 2: Implement the Event Generalizer Agent

**Task:** Create a new ADK agent that listens to `agent:activity`, filters for `CoordinatorAgent` events, generalizes them using DSPy, and publishes them to a user-session-specific channel.

**File to Create:** `/llm_models_python_code_src/ARGOS_POC/src/agents/event_generalizer_agent.py`

**Prompt for Coding Agent:**

"Create a new file for an ADK agent at `/llm_models_python_code_src/ARGOS_POC/src/agents/event_generalizer_agent.py`.

The agent should be named `EventGeneralizerAgent`.

**Assumption**: Events on the `agent:activity` channel are JSON strings containing `agent_name` and `session_id` fields.

1.  **DSPy Signature**: Define a DSPy signature `GenerateSummary(event_json) -> user_summary` that takes a JSON string representing an agent's activity and outputs a concise, human-readable summary sentence.
2.  **DSPy Program**: Create a simple DSPy program (e.g., `dspy.Predict`) that uses this signature. Configure it to use a Gemini model.
3.  **Agent Implementation**:
    *   The agent should initialize the Redis client and the DSPy program.
    *   It must have a method that runs in a background thread to subscribe to the `agent:activity` Redis channel.
    *   In the subscription handler, for each event message, it should:
        a. Parse the JSON message data.
        b. **Check if the `agent_name` field is `'CoordinatorAgent'`. If not, ignore the message and continue.**
        c. If it is a Coordinator event, extract the `session_id`.
        d. Call the DSPy program to generate a summary from the event data.
        e. **Publish the summary to a dynamic channel using the session ID, e.g., `f'frontend:ui_events:{session_id}'`.**
    *   Ensure the agent is correctly loaded by the ADK by following the patterns in other agent files."

### Step 3: Implement the Admin RAG Agent

**Task:** Create a new ADK agent that can answer questions about agent activity by using the Redis event log as a retrieval source.

**File to Create:** `/llm_models_python_code_src/ARGOS_POC/src/agents/admin_rag_agent.py`

**Prompt for Coding Agent:**

"Create a new file for an ADK agent at `/llm_models_python_code_src/ARGOS_POC/src/agents/admin_rag_agent.py`.

The agent should be named `AdminRAGAgent`.

1.  **Custom DSPy Retrieval Module**:
    *   Create a class `RedisEventRetriever` that inherits from `dspy.Retrieve`.
    *   The `__call__` method of this class should accept a `query` string.
    *   Inside `__call__`, it should:
        a. Fetch the last 1000 events from the `events:log` Redis list using `LRANGE`.
        b. Use a simple keyword search or a more advanced semantic search (if a library is available) to find the top 5-10 most relevant event logs from the list that match the query.
        c. Return these logs as a list of `dspy.Prediction` objects or simple strings.

2.  **DSPy RAG Program**:
    *   Define a standard `dspy.Signature` for question-answering: `AnswerWithContext(context, question) -> answer`.
    *   Create a `dspy.Program` that implements the RAG pattern: `dspy.RAG()`.
    *   This program will use your custom `RedisEventRetriever` for the retrieval step.

3.  **Agent Implementation**:
    *   The agent should initialize the DSPy RAG program.
    *   It should expose a tool/method, e.g., `answer_question(question: str) -> str`.
    *   This method will take a question from an admin user, execute the RAG program with the question, and return the generated answer.
    *   This agent will be used by the Admin UI, so it should be interactive rather than running in a background thread."

### Step 4: Update Documentation

**Task:** Add a section to the architecture document describing the new agents.

**File to Edit:** `/llm_models_python_code_src/ARGOS_POC/docs/Architecture.md`

**Prompt for Coding Agent:**

"Update the architecture document at `/llm_models_python_code_src/ARGOS_POC/docs/Architecture.md`. Add a new subsection under `3.6. Agents` for the two new agents.

-   **e. Event Generalizer Agent**: Describe its trigger (`agent:activity` channel), its function (summarizing events with DSPy), and its output (publishing to `frontend:ui_events`).
-   **f. Admin RAG Agent**: Describe its trigger (direct invocation via an admin tool), its function (answering questions about system activity), and its tooling (a DSPy RAG program with a custom Redis retriever that reads from the `events:log`).
"
