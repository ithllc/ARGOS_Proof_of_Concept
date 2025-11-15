import json
from typing import List

from redis_client import redis_client


class AnalysisAgent:
	def __init__(self, redis_client=redis_client):
		self.redis = redis_client

	def assess_feasibility(self, synthesis_keys: List[str]):
		"""Produce feasibility analysis for the synthesis results.

		This POC creates a simple summary and a score between 0-10 stored in Redis.
		"""
		aggregated = {"sources": [], "score": 0.0}
		scores = []
		for key in synthesis_keys:
			raw = self.redis.get(key)
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

		# Save analysis
		analysis_key = f"analysis:{int(self.redis.client.time()[0])}"
		self.redis.set_with_ttl(analysis_key, json.dumps(aggregated), 3600)
		self.redis.publish_message("agent:activity", json.dumps({"agent": "analysis", "status": "completed", "key": analysis_key}))
		return aggregated

	def create_adk_agent(self):
		try:
			from google.adk.agents import LlmAgent

			agent = LlmAgent(
				name="analysis_agent",
				model="gemini-2.5-flash",
				instruction=(
					"Evaluate the synthesis results and provide a feasibility score (0-10) and a short rationale."
				),
			)
			return agent
		except Exception:
			return None

