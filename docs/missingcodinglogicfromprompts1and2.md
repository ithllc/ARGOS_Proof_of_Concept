# Missing Coding Logic from Prompts 1 & 2 — Mini-ARGOS POC

This document captures missing logic from Prompt 1 (scaffolding) and Prompt 2 (backend: FastAPI & Redis), and records the actions taken to address them. It references `POC Idea #5` in `/llm_models_python_code_src/ARGOS_POS/docs/scaled_down_ideas_claude.md` and includes next steps.

## What's already implemented

- Project skeleton created under `ARGOS_POS/` including `src/`, `agents/`, `frontend/` and `docs/`
- `pyproject.toml` and `.gitignore` created
- Virtual environment set up and dependencies installed
- `FastAPI` server in `src/main.py` with WebSocket endpoint
- `RedisClient` in `src/redis_client.py` with helpers for Lists/Hashes/TLL/Publish
- Simple `CoordinatorAgent` implemented (task decomposition + push to Redis)
- `ResearchAgent` implemented to use Tavily for searches and `paper_parser.py` to extract text
- `PlanningAgent` implemented to synthesize concepts via TF-IDF
- `AnalysisAgent` implemented to generate feasibility score
- Frontend React components created for a basic dashboard, agent status, voice interface, and paper visualizer

## Missing or incomplete pieces (required by POC #5)

1. ADK agent integration
   - TODO: Agents were implemented as local classes (CoordinatorAgent, ResearchAgent, etc.). ADK `LlmAgent` usage is not complete and should be integrated for:
     - Coordinator: use ADK `LlmAgent` for task decomposition, with `dspy` fallback
     - Planning: use adk LlmAgent with `output_schema` to produce structured syntheses
     - Analysis: use adk `LlmAgent` or `ChainOfThought` via DSPy to generate feasibility and application suggestions
   - Rationale: ADK `output_schema` and `Runner` will make agent communication consistent with `POC Idea #5`.

2. ADK Live (voice) end-to-end integration
   - TODO: `voice_handler.py` currently empty; must implement WebSocket handling for audio frames, integration with ADK Live `Runner.run_live` and Google TTS/STT.
   - Note: Since `REDIS` is available locally in a container but not installed permanently, ADK Live will be best tested on Google Cloud with Memorystore.

3. DSPy decomposition
   - TODO: The pipeline should be replaced with a robust `dspy` pipeline (using `dspy.Module` or `dspy.ReAct`) that decomposes complex requests into structured tasks when available; fallback code has been added.

4. Tavily integration robustness
   - TODO: The `ResearchAgent` uses `TavilyClient.search` and `PaperParser` for parsing. Missing: stable error handling, support for credentials refresh and rate-limiting.

5. Agent-to-agent communication via ADK `session.state`
   - TODO: Replace Redis key/value usage with ADK Session state where applicable – i.e., `state['paper:ID']` and `output_key` integration. For the POC this is optional, but it aligns with ADK patterns.

6. Frontend interactive features
   - TODO: Add CopilotKit `useCopilotChat` integration and ADK Live client for voice. The React components are scaffolds and call simple API endpoints.

7. End-to-end tests and `adk eval` configuration
   - TODO: Create minimal evalset for POC to validate one user flow: decomposition, research find papers, synthesize applications, TTS.

## Actions applied to fix issues found

- Implemented `CoordinatorAgent.decompose_and_dispatch()` to push tasks to `tasks:research` Redis list
- Implemented `ResearchAgent.listen_and_process()` that calls `TavilyClient.search`, downloads and parses PDFs with `paper_parser` and saves `paper:<id>` hashes to Redis
- Implemented `PlanningAgent.synthesize()` to produce a TF-IDF-based concept overlap list and a crude feasibility score saved to Redis
- Implemented `AnalysisAgent.assess_feasibility()` to aggregate syntheses and produce an analysis summary
- Added FastAPI endpoints: `/api/decompose` to kick off the coordinator and `/api/papers` to list parsed papers for front-end
- Added front-end components: `Dashboard.jsx`, `AgentStatus.jsx`, `VoiceInterface.jsx`, and `PaperVisualizer.jsx`

### Recent updates (Tavily fallback & local developer flow)

- Added `src/mocks/tavily_mock.py`: a `MockTavilyClient` that returns sample results from `docs/sample_papers` for local/offline testing when `TAVILY_API_KEY` is not set or set to `mock`.
- Implemented `paper_parser.extract_text_from_url()` to parse local `file://` PDFs and remote PDFs (basic fallback) using `pypdf`.
- Added `docker-compose.yml`, `Dockerfile`, and `requirements.txt` so you can bring up a local Redis service with `docker-compose up` and run the FastAPI app with a resumed environment. This makes local testing frictionless.

These changes let you test the entire POC locally without an actual Tavily API key. If you prefer to run against Tavily's real API, set `TAVILY_API_KEY` in your `.env` file.

## Next steps (recommended)

1. Integrate `LlmAgent` and `Runner` from ADK for coordinating agents and producing structural outputs using `output_schema`.
2. Implement `voice_handler.py` using ADK Live following the `adk_live` sample in `GCP-agent-starter-pack`.
3. Harden Tavily and Redis workflows with retries and exponential backoff.
4. Create a demo script to run the coordinator, research and planning agents locally using the `InMemorySessionService` from ADK.
5. Create a simple `docker-compose.yml` to run Redis and the FastAPI local server together for local testing.

---

Document prepared automatically by the coding agent.
