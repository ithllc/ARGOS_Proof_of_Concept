import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agents.research import ResearchAgent
from tests.mocks import MockRedisClient

class TestResearchAgentAsync(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Set up a new research agent and a mock redis client for each test."""
        self.redis_client = MockRedisClient()
        self.agent = ResearchAgent(redis_client=self.redis_client)

    @patch('agents.research.get_tavily_mcp_client')
    @patch('time.time')
    async def test_execute_search_and_parse_success(self, mock_time, mock_get_tavily_mcp_client):
        """
        Test the successful execution of a search and parse task.
        """
        # Make time.time() return unique values for each call to ensure unique paper_ids
        mock_time.side_effect = [1763244625, 1763244626]

        # Configure the async context manager mock
        mock_tavily_mcp = AsyncMock()
        mock_tavily_mcp.search.return_value = {
            "results": [
                {"title": "Test Paper 1", "url": "http://example.com/paper1.pdf", "content": "..."},
                {"title": "Test Paper 2", "url": "http://example.com/paper2.pdf", "content": "..."}
            ]
        }
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_tavily_mcp
        mock_get_tavily_mcp_client.return_value = mock_context_manager

        payload = {"query": "test query", "session_id": "test_session"}

        # Mock extract_text_from_url to avoid actual network calls
        with patch('agents.research.extract_text_from_url', return_value="Mocked PDF text") as mock_extract:
            await self.agent._execute_search_and_parse(payload)

            # 1. Verify that the search was called
            mock_tavily_mcp.search.assert_called_once_with("test query")

            # 2. Verify that text extraction was attempted for the URLs
            self.assertEqual(mock_extract.call_count, 2)
            mock_extract.assert_any_call("http://example.com/paper1.pdf")
            mock_extract.assert_any_call("http://example.com/paper2.pdf")

            # 3. Verify that results were stored in Redis
            paper_hashes_found = [
                key for key in self.redis_client.hashes
                if key.startswith("paper:")
            ]
            self.assertEqual(len(paper_hashes_found), 2) # Two papers were found

            for paper_hash_key in paper_hashes_found:
                paper_data = self.redis_client.hashes[paper_hash_key]
                self.assertIn("title", paper_data)
                self.assertIn("url", paper_data)
                self.assertIn("text", paper_data)

            
            # Check the 'last_search' record
            last_search_raw = self.redis_client.get_hash_field("last_search", "test query")
            self.assertIsNotNone(last_search_raw)
            found_papers = json.loads(last_search_raw)
            self.assertEqual(len(found_papers), 2)

            # 4. Verify that a completion message was published
            published_message_raw = self.redis_client.get_published_message("agent:activity")
            self.assertIsNotNone(published_message_raw)
            published_message = json.loads(published_message_raw)
            self.assertEqual(published_message["agent"], "research")
            self.assertEqual(published_message["status"], "completed")
            self.assertEqual(len(published_message["found"]), 2)

    @patch('agents.research.get_tavily_mcp_client')
    async def test_execute_search_and_parse_no_results(self, mock_get_tavily_mcp_client):
        """
        Test the case where the search returns no results.
        """
        mock_tavily_mcp = AsyncMock()
        mock_tavily_mcp.search.return_value = {"results": []}
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_tavily_mcp
        mock_get_tavily_mcp_client.return_value = mock_context_manager

        payload = {"query": "obscure topic", "session_id": "test_session"}

        await self.agent._execute_search_and_parse(payload)

        mock_tavily_mcp.search.assert_called_once_with("obscure topic")

        # Verify 'no_pdfs_found' message was published
        published_message_raw = self.redis_client.get_published_message("agent:activity")
        self.assertIsNotNone(published_message_raw)
        published_message = json.loads(published_message_raw)
        self.assertEqual(published_message["status"], "no_pdfs_found")
        self.assertEqual(published_message["query"], "obscure topic")

    @patch('agents.research.get_tavily_mcp_client')
    async def test_execute_search_and_parse_search_fails(self, mock_get_tavily_mcp_client):
        """
        Test the case where the search call itself raises an exception.
        """
        mock_tavily_mcp = AsyncMock()
        mock_tavily_mcp.search.side_effect = Exception("MCP Connection Error")

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_tavily_mcp
        mock_get_tavily_mcp_client.return_value = mock_context_manager

        payload = {"query": "failing query", "session_id": "test_session"}

        await self.agent._execute_search_and_parse(payload)

        mock_tavily_mcp.search.assert_called_once_with("failing query")

        # Verify 'search_failed' message was published
        published_message_raw = self.redis_client.get_published_message("agent:activity")
        self.assertIsNotNone(published_message_raw)
        published_message = json.loads(published_message_raw)
        self.assertEqual(published_message["status"], "search_failed")
        self.assertEqual(published_message["meta"], "MCP Connection Error")

if __name__ == '__main__':
    unittest.main()
