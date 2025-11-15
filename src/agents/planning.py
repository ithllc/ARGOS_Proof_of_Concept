import json
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer

from redis_client import redis_client


class PlanningAgent:
	def __init__(self, redis_client=redis_client):
		self.redis = redis_client

	def synthesize(self, paper_ids: List[str], synthesis_key: str | None = None):
		"""Synthesize concepts from a list of parsed papers (paper:ID stored in redis).

		For the POC we do a simple TF-IDF to find overlapping important tokens.
		Saves synthesis result to Redis with a TTL.
		"""
		texts = []
		metadata = {}
		for pid in paper_ids:
			paper = self.redis.get_all_hash_fields(f"paper:{pid}") or {}
			text = paper.get("text", "")
			title = paper.get("title", "")
			texts.append(text[:5000])
			metadata[pid] = {"title": title}

		synth = {"overlap": [], "feasibility": 0.0, "applications": []}
		if len(texts) > 0:
			# TF-IDF approach to find top correlated tokens between documents
			vec = TfidfVectorizer(stop_words="english", max_features=1000)
			X = vec.fit_transform(texts)
			tfidf = X.toarray()
			# Overlap: tokens that have high average tfidf across docs
			avg_tfidf = tfidf.mean(axis=0)
			tokens = vec.get_feature_names_out()
			top_indices = avg_tfidf.argsort()[::-1][:20]
			top_terms = [tokens[i] for i in top_indices if avg_tfidf[i] > 0.01][:10]
			synth["overlap"] = top_terms
			# crude feasibility: proportion of docs >= 1000 chars
			doc_lengths = [len(t) for t in texts]
			synth["feasibility"] = round(min(10.0, sum(1 for dl in doc_lengths if dl > 1000) / max(1, len(doc_lengths)) * 10), 2)
			# applications: create example list using top_terms
			if top_terms:
				synth["applications"] = [f"Use {top_terms[:3]} for optimization workflows"]

		result_key = synthesis_key or f"synthesis:{','.join(paper_ids)}"
		self.redis.set_with_ttl(result_key, json.dumps(synth), 3600)
		self.redis.publish_message("agent:activity", json.dumps({"agent": "planning", "status": "synthesized", "key": result_key}))
		return synth

	def create_adk_agent(self):
		try:
			from google.adk.agents import LlmAgent

			agent = LlmAgent(
				name="planning_agent",
				model="gemini-2.5-pro",
				instruction="Take the research outputs in session.state and generate a concise synthesis with overlap, feasibility, and 3 example applications."
			)
			return agent
		except Exception:
			return None

