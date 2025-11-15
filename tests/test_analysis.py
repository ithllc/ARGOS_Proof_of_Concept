import unittest
import json
from unittest.mock import MagicMock, patch

from agents.analysis import AnalysisAgent
from tests.mocks import MockRedisClient

class TestAnalysisAgent(unittest.TestCase):

    def setUp(self):
        """Set up a new analysis agent and a mock redis client for each test."""
        self.redis_client = MockRedisClient()
        self.agent = AnalysisAgent(redis_client=self.redis_client)

    def test_assess_feasibility_success(self):
        """
        Test the successful execution of assess_feasibility with valid synthesis data.
        """
        # 1. Populate mock Redis with synthesis data
        synthesis_1 = {"overlap": ["quantum", "ai"], "feasibility": 8.0}
        synthesis_2 = {"overlap": ["quantum", "cryptography"], "feasibility": 6.0}
        self.redis_client.set_with_ttl("synthesis:1", json.dumps(synthesis_1), 3600)
        self.redis_client.set_with_ttl("synthesis:2", json.dumps(synthesis_2), 3600)

        # 2. Run the assessment
        synthesis_keys = ["synthesis:1", "synthesis:2"]
        result = self.agent.assess_feasibility(synthesis_keys)

        # 3. Verify the aggregated result
        self.assertIn("sources", result)
        self.assertIn("score", result)
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["score"], 7.0) # (8.0 + 6.0) / 2
        self.assertEqual(result["sources"][0]["key"], "synthesis:1")
        self.assertEqual(result["sources"][1]["key"], "synthesis:2")

        # 4. Verify Redis interactions
        # Check that the analysis result was saved
        expected_analysis_key = "analysis:1731642000"
        stored_analysis_raw = self.redis_client.get(expected_analysis_key)
        self.assertIsNotNone(stored_analysis_raw)
        stored_analysis = json.loads(stored_analysis_raw)
        self.assertEqual(stored_analysis["score"], 7.0)

        # Check that a message was published
        published_message_raw = self.redis_client.get_published_message("agent:activity")
        self.assertIsNotNone(published_message_raw)
        published_message = json.loads(published_message_raw)
        self.assertEqual(published_message["agent"], "analysis")
        self.assertEqual(published_message["status"], "completed")
        self.assertEqual(published_message["key"], expected_analysis_key)

    def test_assess_feasibility_no_keys(self):
        """
        Test assess_feasibility with an empty list of keys.
        """
        result = self.agent.assess_feasibility([])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["score"], 0.0)

        # Verify it still saves the empty result
        expected_analysis_key = "analysis:1731642000"
        stored_analysis_raw = self.redis_client.get(expected_analysis_key)
        self.assertIsNotNone(stored_analysis_raw)
        stored_analysis = json.loads(stored_analysis_raw)
        self.assertEqual(stored_analysis["score"], 0.0)

    def test_assess_feasibility_key_not_found(self):
        """
        Test assess_feasibility with keys that do not exist in Redis.
        """
        result = self.agent.assess_feasibility(["synthesis:nonexistent"])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["score"], 0.0)

    def test_assess_feasibility_malformed_json(self):
        """
        Test assess_feasibility when a key contains malformed JSON.
        """
        self.redis_client.set_with_ttl("synthesis:good", json.dumps({"feasibility": 9.0}), 3600)
        self.redis_client.set_with_ttl("synthesis:bad", "this is not json", 3600)

        result = self.agent.assess_feasibility(["synthesis:good", "synthesis:bad"])
        
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["key"], "synthesis:good")
        self.assertEqual(result["score"], 9.0)

    @patch('google.adk.agents.LlmAgent')
    def test_create_adk_agent_success(self, MockLlmAgent):
        """
        Test the successful creation of an ADK LlmAgent.
        """
        mock_agent_instance = MockLlmAgent.return_value
        agent = self.agent.create_adk_agent()

        self.assertIsNotNone(agent)
        self.assertEqual(agent, mock_agent_instance)
        MockLlmAgent.assert_called_once_with(
            name="analysis_agent",
            model="gemini-2.5-flash",
            instruction="Evaluate the synthesis results and provide a feasibility score (0-10) and a short rationale."
        )

    @patch.dict('sys.modules', {'google.adk.agents': None})
    def test_create_adk_agent_failure(self):
        """
        Test that creating an ADK agent returns None if the module is not found.
        """
        agent = self.agent.create_adk_agent()
        self.assertIsNone(agent)

if __name__ == '__main__':
    unittest.main()
