import asyncio
import os
from contextlib import asynccontextmanager
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolRequest

class TavilyMCPClient:
    """
    An asynchronous client for interacting with the Tavily MCP server.
    """
    def __init__(self):
        self.server_params = StdioServerParameters(
            command="node",
            args=[os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "TavilyMCP", "build", "index.js"))],
            env=os.environ.copy(),
        )
        self._session = None
        self._client_context = None

    async def connect(self):
        """Initializes the connection to the MCP server."""
        if not self._session:
            self._client_context = stdio_client(self.server_params)
            read, write = await self._client_context.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.initialize()

    async def close(self):
        """Closes the connection to the MCP server."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None

    async def search(self, query: str, **kwargs) -> dict:
        """
        Calls the 'tavily-search' tool on the MCP server.

        Args:
            query: The search query string.
            **kwargs: Additional arguments for the tavily-search tool.

        Returns:
            The result from the tool call.
        """
        if not self._session:
            await self.connect()

        request = CallToolRequest(
            params={
                "name": "tavily-search",
                "arguments": {"query": query, **kwargs},
            }
        )
        result = await self._session.call_tool(request)
        
        # The result from the MCP server is a list of content blocks.
        # We need to parse the text content to get the search results.
        if result.content and hasattr(result.content[0], 'text'):
            # This is a simplified parser. A more robust implementation
            # would handle different content types and structures.
            return {"results": self._parse_tavily_text(result.content[0].text)}
        return {"results": []}

    def _parse_tavily_text(self, text: str) -> list:
        """
        Parses the text output from the tavily-search tool into a list of results.
        This is a simple parser and might need to be adjusted based on the exact
        format from the TavilyMCP server.
        """
        results = []
        current_result = {}
        for line in text.split('\\n'):
            if line.startswith('Title: '):
                if current_result:
                    results.append(current_result)
                current_result = {'title': line[7:]}
            elif line.startswith('URL: '):
                current_result['url'] = line[5:]
            elif line.startswith('Content: '):
                current_result['content'] = line[9:]
        if current_result:
            results.append(current_result)
        return results

@asynccontextmanager
async def get_tavily_mcp_client():
    """Asynchronous context manager for the TavilyMCPClient."""
    client = TavilyMCPClient()
    try:
        await client.connect()
        yield client
    finally:
        await client.close()
