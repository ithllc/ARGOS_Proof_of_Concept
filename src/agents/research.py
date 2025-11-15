import json
import os
import time
from typing import Optional
import asyncio

# Load environment variables before other imports
import config

from mcp_client import get_tavily_mcp_client
from redis_client import redis_client
from paper_parser import extract_text_from_url


class ResearchAgent:
	def __init__(self, redis_client=redis_client):
		self.redis = redis_client
		# The Tavily API key is now managed by the MCP server,
		# so we don't need it here directly.
		# The client will connect to the local MCP server.

	async def listen_and_process(self, queue_name: str = "tasks:research"):
		"""An asynchronous loop that pops tasks from Redis and processes them."""
		while True:
			raw = self.redis.pop_task(queue_name)
			if not raw:
				# In a real async worker, we might wait here instead of breaking.
				await asyncio.sleep(1) # prevent busy-looping
				continue # check again
			try:
				task = json.loads(raw)
			except Exception:
				continue
			ttype = task.get("type")
			payload = task.get("payload", {})
			if ttype == "search_and_parse":
				await self._execute_search_and_parse(payload)

	async def _execute_search_and_parse(self, payload: dict):
		query = payload.get("query")
		session_id = payload.get("session_id")

		try:
			async with get_tavily_mcp_client() as tavily_mcp:
				result = await tavily_mcp.search(query)
		except Exception as e:
			self.redis.publish_message("agent:activity", json.dumps({"agent": "research", "status": "search_failed", "meta": str(e)}))
			return

		# 2. Extract candidate PDFs and metadata
		found = []
		for hit in result.get("results", [])[:5]:
			url = hit.get("url")
			title = hit.get("title")
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


