import unittest
import json
from unittest.mock import MagicMock, patch, ANY

# Ensure config is loaded before other project imports
import config

from agents.coordinator import CoordinatorAgent

class TestCoordinatorAgent(unittest.TestCase):

    def setUp(self):
        """Set up a mock Redis client before each test."""
        self.mock_redis_client = MagicMock()
        # To instantiate the agent, we pass the mocked client.
        self.agent = CoordinatorAgent(redis_client=self.mock_redis_client)

    def test_decompose_and_dispatch_fallback(self):
        """
        Tests the fallback heuristic decomposition when DSPy is disabled.
        """
        # Force agent into a state where DSPy is disabled
        self.agent.dspy_enabled = False
        
        query = "test query"
        session_id = "test_session_123"

        task_ids = self.agent.decompose_and_dispatch(query, session_id)

        # 1. Check that 5 tasks were created by the fallback heuristic
        self.assertEqual(len(task_ids), 5)
        
        # 2. Check that tasks were pushed to the correct Redis queue
        self.mock_redis_client.push_task.assert_called_with("tasks:research", ANY)
        self.assertEqual(self.mock_redis_client.push_task.call_count, 5)

        # 3. Check that the session-to-task mapping was saved in Redis
        self.mock_redis_client.set_hash_field.assert_called_once_with(
            f"session:{session_id}", "tasks", json.dumps(task_ids)
        )

        # 4. Check that a notification was published
        self.mock_redis_client.publish_message.assert_called_once_with(
            "agent:activity",
            json.dumps(
                {"agent": "coordinator", "status": "dispatched", "tasks": task_ids}
            ),
        )

    @patch('dspy.Predict')
    def test_decompose_and_dispatch_dspy(self, MockPredict):
        """
        Tests the DSPy-powered decomposition.
        """
        # Force agent into a state where DSPy is enabled
        self.agent.dspy_enabled = True

        # Mock the DSPy predictor and its return value
        mock_dspy_output = ["dspy task 1", "dspy task 2"]
        mock_predictor_instance = MockPredict.return_value
        mock_predictor_instance.return_value.tasks = json.dumps(mock_dspy_output)

        query = "dspy test query"
        session_id = "dspy_session_456"

        task_ids = self.agent.decompose_and_dispatch(query, session_id)

        # 1. Check that the DSPy predictor was called with the query
        mock_predictor_instance.assert_called_once_with(query=query)

        # 2. Check that the correct number of tasks were created based on mock output
        self.assertEqual(len(task_ids), 2)

        # 3. Check that tasks were pushed to Redis
        self.assertEqual(self.mock_redis_client.push_task.call_count, 2)

        # 4. Check that the session-to-task mapping was saved
        self.mock_redis_client.set_hash_field.assert_called_once_with(
            f"session:{session_id}", "tasks", json.dumps(task_ids)
        )

        # 5. Check that a notification was published
        self.mock_redis_client.publish_message.assert_called_once()

if __name__ == '__main__':
    unittest.main()
