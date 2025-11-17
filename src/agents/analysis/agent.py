import json
from typing import List

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from redis_client import redis_client

def assess_feasibility(synthesis_keys: List[str]) -> dict:
    """Produce feasibility analysis for the synthesis results."""
    aggregated = {"sources": [], "score": 0.0}
    scores = []
    for key in synthesis_keys:
        raw = redis_client.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        aggregated["sources"].append({"key": key, "overlap": data.get("overlap", [])})
        scores.append(data.get("feasibility", 0.0))

    if scores:
        aggregated["score"] = round(sum(scores) / len(scores), 2)

    analysis_key = f"analysis:{int(redis_client.client.time()[0])}"
    redis_client.set_with_ttl(analysis_key, json.dumps(aggregated), 3600)
    redis_client.publish_message("agent:activity", json.dumps({"agent": "analysis", "status": "completed", "key": analysis_key}))
    return aggregated

root_agent = LlmAgent(
    name="analysis",
    instruction="You are an analysis agent. You can assess the feasibility of a synthesis.",
    tools=[
        # Assesses the feasibility of a synthesis.
        FunctionTool(
            func=assess_feasibility,
        )
    ]
)
