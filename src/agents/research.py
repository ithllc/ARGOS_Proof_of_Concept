import json
import os
import time
from typing import Optional

from tavily import TavilyClient
from mocks.tavily_mock import MockTavilyClient
from redis_client import redis_client
from paper_parser import extract_text_from_url


class ResearchAgent:
	def __init__(self, redis_client=redis_client, tavily_api_key=None):
		self.redis = redis_client
		self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
		if self.tavily_api_key and self.tavily_api_key != "mock":
			self.tavily = TavilyClient(api_key=self.tavily_api_key)
		else:
			# If TAVILY_API_KEY is not set or is 'mock', use a local stub for development
			self.tavily = MockTavilyClient()

	def listen_and_process(self, queue_name: str = "tasks:research"):
		"""A synchronous loop that pops tasks from Redis and processes them.

		For the POC, this continues until the queue is empty. In production this would be a long-running worker.
		"""
		while True:
			raw = self.redis.pop_task(queue_name)
			if not raw:
				break
			try:
				task = json.loads(raw)
			except Exception:
				continue
			ttype = task.get("type")
			payload = task.get("payload", {})
			if ttype == "search_and_parse":
				self._execute_search_and_parse(payload)

	def _execute_search_and_parse(self, payload: dict):
		query = payload.get("query")
		session_id = payload.get("session_id")
		if not self.tavily:
			# publish a warning
			self.redis.publish_message("agent:activity", json.dumps({"agent": "research", "status": "no_tavily_key", "query": query}))
			return

		# 1. Run Tavily search
		try:
			result = self.tavily.search(query)
		except Exception as e:
			self.redis.publish_message("agent:activity", json.dumps({"agent": "research", "status": "search_failed", "meta": str(e)}))
			return

		# 2. Extract candidate PDFs and metadata
		found = []
		for hit in result.get("results", [])[:5]:
			url = hit.get("url") or hit.get("link")
			title = hit.get("title") or hit.get("heading")
			if not url:
				continue
			text = extract_text_from_url(url)
			paper_id = None
			if text:
				paper_id = payload.get("query", "")[:32] + ":" + str(int(time.time()))
				# Save results in Redis
				self.redis.set_hash_field(f"paper:{paper_id}", "title", title or "")
				self.redis.set_hash_field(f"paper:{paper_id}", "url", url)
				self.redis.set_hash_field(f"paper:{paper_id}", "text", text[:4000])  # truncate for storage
				found.append(paper_id)

		# Save found list and notify
		if found:
			self.redis.set_hash_field("last_search", query, json.dumps(found))
			self.redis.publish_message("agent:activity", json.dumps({"agent": "research", "status": "completed", "found": found}))
		else:
			self.redis.publish_message("agent:activity", json.dumps({"agent": "research", "status": "no_pdfs_found", "query": query}))

