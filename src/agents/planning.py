import json
import re
from typing import List
from collections import Counter
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from redis_client import redis_client


class PlanningAgent:
	def __init__(self, redis_client=redis_client):
		self.redis = redis_client

	def synthesize(self, paper_ids: List[str], synthesis_key: str | None = None):
		"""Synthesize concepts from a list of parsed papers (paper:ID stored in redis).

		For the POC, we find the most common non-stop-words that appear across multiple documents.
		Saves synthesis result to Redis with a TTL.
		"""
		texts = []
		metadata = {}
		for pid in paper_ids:
			paper = self.redis.get_all_hash_fields(pid) or {}
			text = paper.get("text", "")
			title = paper.get("title", "")
			texts.append(text[:5000])
			metadata[pid] = {"title": title}

		synth = {"overlap": [], "feasibility": 0.0, "applications": []}
		
		if texts:
			# Clean text by removing punctuation and making it lowercase
			clean_texts = [re.sub(r'[^a-zA-Z\s]', '', doc.lower()) for doc in texts]
			
			# Get word sets for each document, excluding stop words
			doc_word_sets = [
				set(word for word in doc.split() if word not in ENGLISH_STOP_WORDS and word)
				for doc in clean_texts
			]

			# Find the intersection of words that appear in all documents
			overlap_words = set()
			if doc_word_sets:
				# Find words that appear in more than one document
				word_doc_counts = Counter()
				for word_set in doc_word_sets:
					word_doc_counts.update(word_set)
				
				multi_doc_words = {word for word, count in word_doc_counts.items() if count > 1}

				# To get the most relevant terms, sort them by overall frequency
				total_word_counts = Counter(word for doc in clean_texts for word in doc.split())
				
				# Sort the words that appear in multiple docs by their total frequency
				sorted_multi_doc_words = sorted(
					multi_doc_words, 
					key=lambda w: total_word_counts.get(w, 0), 
					reverse=True
				)
				overlap_words.update(sorted_multi_doc_words)

			synth["overlap"] = list(overlap_words)[:10]

			# crude feasibility: proportion of docs >= 1000 chars
			doc_lengths = [len(t) for t in texts]
			synth["feasibility"] = round(min(10.0, sum(1 for dl in doc_lengths if dl > 1000) / max(1, len(doc_lengths)) * 10), 2)
			
			# applications: create example list using top_terms
			if synth["overlap"]:
				synth["applications"] = [f"Use {synth['overlap'][:3]} for optimization workflows"]

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

