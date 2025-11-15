from google.adk.cli.fast_api import get_fast_api_app
import os

# The agents are in the 'agents' subdirectory of the 'src' directory.
# The get_fast_api_app expects the path to be relative to the current working directory.
# When running with uvicorn from the root of the project, the path should be 'ARGOS_POS/src/agents'.
agents_dir = os.path.join(os.path.dirname(__file__), "agents")

app = get_fast_api_app(
    agents_dir=agents_dir,
    web=True,
)
