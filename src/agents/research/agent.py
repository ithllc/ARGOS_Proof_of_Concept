import json
import time
from typing import List
import asyncio

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from mcp_client import get_tavily_mcp_client
from redis_client import redis_client
from paper_parser import extract_text_from_url

def search_and_parse(query: str) -> List[str]:
    """Searches for a query and parses the results, storing them in Redis."""
    try:
        async def _search():
            async with get_tavily_mcp_client() as tavily_mcp:
                return await tavily_mcp.search(query)

        result = asyncio.run(_search())

    except Exception as e:
        redis_client.publish_message("agent:activity", json.dumps({"agent": "research", "status": "search_failed", "meta": str(e)}))
        return []

    found = []
    for hit in result.get("results", [])[:5]:
        url = hit.get("url")
        title = hit.get("title")
        if not url:
            continue
        text = extract_text_from_url(url)
        if text:
            paper_id = query[:32] + ":" + str(int(time.time()))
            redis_client.set_hash_field(f"paper:{paper_id}", "title", title or "")
            redis_client.set_hash_field(f"paper:{paper_id}", "url", url)
            redis_client.set_hash_field(f"paper:{paper_id}", "text", text[:4000])
            found.append(paper_id)

    if found:
        redis_client.set_hash_field("last_search", query, json.dumps(found))
        redis_client.publish_message("agent:activity", json.dumps({"agent": "research", "status": "completed", "found": found}))
    else:
        redis_client.publish_message("agent:activity", json.dumps({"agent": "research", "status": "no_pdfs_found", "query": query}))
    
    return found

root_agent = LlmAgent(
    name="research",
    model="gemini-2.5-flash",
    instruction="You are a research agent. You can search for papers and parse them.",
    tools=[
        # Searches for a query and parses the results.
        FunctionTool(
            func=search_and_parse,
        )
    ]
)
