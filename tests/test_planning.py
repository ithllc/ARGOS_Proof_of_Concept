import unittest
import json
from unittest.mock import MagicMock, patch

from agents.planning import PlanningAgent
from tests.mocks import MockRedisClient

class TestPlanningAgent(unittest.TestCase):

    def setUp(self):
        """Set up a new planning agent and a mock redis client for each test."""
        self.redis_client = MockRedisClient()
        self.agent = PlanningAgent(redis_client=self.redis_client)

    def test_synthesize_with_valid_papers(self):
        """
        Test the synthesis process with a list of valid paper IDs.
        """
        # 1. Populate mock Redis with paper data
        paper_1_id = "paper:1"
        paper_2_id = "paper:2"
        self.redis_client.set_hash_field(paper_1_id, "title", "Quantum Computing and Cryptography")
        self.redis_client.set_hash_field(paper_1_id, "text", "This scientific paper explores the intersection of quantum computing and modern cryptography. We analyze the potential threats that quantum algorithms, such as Shor's algorithm, pose to existing cryptographic standards. The quantum realm offers new paradigms for secure communication.")
        self.redis_client.set_hash_field(paper_2_id, "title", "Neural Network Architectures for Quantum Systems")
        self.redis_client.set_hash_field(paper_2_id, "text", "We propose novel neural network architectures designed to simulate and analyze quantum systems. These models leverage principles of quantum mechanics to create more efficient simulations. The intersection of AI and quantum physics is a promising field.")

        paper_ids = [paper_1_id, paper_2_id]
        synthesis_key = "synthesis:test_key"

        # 2. Run the synthesis
        result = self.agent.synthesize(paper_ids, synthesis_key)

        # 3. Verify the results
        self.assertIn("overlap", result)
        self.assertIn("feasibility", result)
        self.assertIn("applications", result)

        # Check that the top overlapping terms are relevant
        self.assertIn("quantum", result["overlap"])
        self.assertIn("intersection", result["overlap"])
        self.assertNotIn("cryptography", result["overlap"]) # Only in one doc
        self.assertNotIn("shors", result["overlap"]) # Only in one doc

        # 4. Verify Redis interactions
        # Check that the synthesis result was saved
        stored_synthesis_raw = self.redis_client.get_value(synthesis_key)
        self.assertIsNotNone(stored_synthesis_raw)
        stored_synthesis = json.loads(stored_synthesis_raw)
        self.assertEqual(stored_synthesis["overlap"], result["overlap"])

        # Check that a message was published
        published_message_raw = self.redis_client.get_published_message("agent:activity")
        self.assertIsNotNone(published_message_raw)
        published_message = json.loads(published_message_raw)
        self.assertEqual(published_message["agent"], "planning")
        self.assertEqual(published_message["status"], "synthesized")
        self.assertEqual(published_message["key"], synthesis_key)

    def test_synthesize_with_no_papers(self):
        """
        Test the synthesis process with an empty list of paper IDs.
        """
        result = self.agent.synthesize([], "synthesis:empty_key")

        self.assertEqual(result["overlap"], [])
        self.assertEqual(result["feasibility"], 0.0)
        self.assertEqual(result["applications"], [])

        # Verify it still saves the empty result
        stored_synthesis_raw = self.redis_client.get_value("synthesis:empty_key")
        self.assertIsNotNone(stored_synthesis_raw)

    def test_synthesize_with_short_text(self):
        """
        Test the feasibility score with short texts.
        """
        paper_1_id = "paper:short"
        self.redis_client.set_hash_field(paper_1_id, "text", "a b c") # very short text
        paper_2_id = "paper:short2"
        self.redis_client.set_hash_field(paper_2_id, "text", "d e f")

        result = self.agent.synthesize([paper_1_id, paper_2_id])
        # Feasibility should be 0 because the text length is < 1000
        self.assertEqual(result["feasibility"], 0.0)
        # Overlap should be empty due to the ValueError being handled
        self.assertEqual(result["overlap"], [])

    @patch('google.adk.agents.LlmAgent')
    def test_create_adk_agent_success(self, MockLlmAgent):
        """
        Test the successful creation of an ADK LlmAgent.
        """
        # Because LlmAgent is imported inside the method, we must patch it in the 'google.adk.agents' namespace
        mock_agent_instance = MockLlmAgent.return_value
        agent = self.agent.create_adk_agent()

        self.assertIsNotNone(agent)
        self.assertEqual(agent, mock_agent_instance)
        MockLlmAgent.assert_called_once_with(
            name="planning_agent",
            model="gemini-2.5-pro",
            instruction="Take the research outputs in session.state and generate a concise synthesis with overlap, feasibility, and 3 example applications."
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
