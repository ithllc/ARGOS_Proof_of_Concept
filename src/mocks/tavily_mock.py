import os
from typing import Dict, Any

# A small TavilyClient stub that returns local sample paper file paths
# Used when TAVILY_API_KEY is unset or set to 'mock' in .env for local dev/testing

class MockTavilyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.base = os.path.join(os.path.dirname(__file__), "..", "docs", "sample_papers")

    def search(self, query: str) -> Dict[str, Any]:
        # Return a structured response similar to real TavilyClient.search
        results = []
        sample_dir = os.path.abspath(os.path.join(self.base))
        # Find up to 5 PDF files in sample dir
        try:
            for fname in os.listdir(sample_dir)[:5]:
                if not fname.lower().endswith(".pdf"):
                    continue
                results.append({
                    "title": fname.replace("_", " ").replace(".pdf", ""),
                    "url": f"file://{os.path.join(sample_dir, fname)}",
                    "snippet": "Local sample paper provided for offline testing",
                })
        except FileNotFoundError:
            # If sample dir does not exist, create sample response
            results.append({
                "title": "Mock Paper",
                "url": "file:///tmp/mock-paper.pdf",
                "snippet": "A mock paper used for local testing",
            })

        return {"results": results, "query": query}
