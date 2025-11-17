"""
ADK Debug Web UI
This is a development-only tool for testing and debugging ADK agents.
Run this alongside the main application on a different port.
"""

from google.adk.cli.fast_api import get_fast_api_app
import os

# Load environment variables
import config

# The agents are in the 'agents' subdirectory of the 'src' directory
agents_dir = os.path.join(os.path.dirname(__file__), "agents")

# Create the ADK debug app with the built-in web UI
debug_app = get_fast_api_app(
    agents_dir=agents_dir,
    web=True,
)

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("Starting ADK Debug Web UI")
    print("This is for DEVELOPMENT ONLY - use for agent debugging")
    print("Access at: http://localhost:8001")
    print("="*60)
    uvicorn.run(debug_app, host="0.0.0.0", port=8001)
