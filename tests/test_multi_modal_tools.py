import unittest
from unittest.mock import MagicMock, patch
import asyncio

from ARGOS_POS.src.multi_modal_tools import generate_architecture_image, generate_example_video
from google.adk.tools import FunctionTool

class TestMultiModalTools(unittest.TestCase):

    @patch('google.cloud.aiplatform_v1.PredictionServiceClient')
    async def test_generate_architecture_image_tool(self, MockPredictionServiceClient):
        mock_client_instance = MockPredictionServiceClient.return_value
        mock_response = MagicMock()
        mock_response.predictions = [MagicMock(struct_value=MagicMock(fields={'bytesBase64Encoded': MagicMock(string_value='base64image'), 'mimeType': MagicMock(string_value='image/png')}))]
        mock_client_instance.predict.return_value = mock_response

        description = "a microservice architecture diagram"
        result = await generate_architecture_image(description)

        MockPredictionServiceClient.assert_called_once()
        mock_client_instance.predict.assert_called_once()
        self.assertIn("data:image/png;base64,base64image", result)

    @patch('google.cloud.aiplatform_v1.PredictionServiceClient')
    async def test_generate_example_video_tool(self, MockPredictionServiceClient):
        mock_client_instance = MockPredictionServiceClient.return_value
        mock_response = MagicMock()
        mock_response.predictions = [MagicMock(struct_value=MagicMock(fields={'videoUri': MagicMock(string_value='gs://mock-video-bucket/video.mp4')}))]
        mock_client_instance.predict.return_value = mock_response

        description = "a short video of a cat playing with a ball"
        result = await generate_example_video(description)

        MockPredictionServiceClient.assert_called_once()
        mock_client_instance.predict.assert_called_once()
        self.assertEqual(result, "gs://mock-video-bucket/video.mp4")

    @patch('google.cloud.aiplatform_v1.PredictionServiceClient')
    @patch('ARGOS_POS.src.agents.coordinator.agent.LlmAgent')
    async def test_agent_tool_invocation(self, MockLlmAgent, MockPredictionServiceClient):
        # Mock the LlmAgent and its tools
        mock_coordinator_agent_instance = MockLlmAgent.return_value
        mock_coordinator_agent_instance.tools = [
            FunctionTool(
                func=generate_architecture_image,
                description="Generates a software architecture image based on a textual description using Imagen 3.",
            ),
            FunctionTool(
                func=generate_example_video,
                description="Generates a short video based on a textual description of a real-world scenario using Veo.",
            ),
        ]

        # Simulate the agent calling the tool
        # In a real scenario, the LlmAgent's internal logic would decide to call the tool.
        # Here, we directly call the tool function to test its integration.
        mock_prediction_client_instance = MockPredictionServiceClient.return_value
        mock_response = MagicMock()
        mock_response.predictions = [MagicMock(struct_value=MagicMock(fields={'bytesBase64Encoded': MagicMock(string_value='base64image'), 'mimeType': MagicMock(string_value='image/png')}))]
        mock_prediction_client_instance.predict.return_value = mock_response

        # Simulate a prompt that would trigger the image generation tool
        prompt = "show me a diagram of the system architecture"
        
        # This part is more about how the LlmAgent *would* use the tool,
        # not directly testing the LlmAgent's decision-making here.
        # We're testing that if the tool is called, it works as expected.
        result = await generate_architecture_image(prompt)

        self.assertIn("data:image/png;base64,base64image", result)
        MockPredictionServiceClient.assert_called_once()


if __name__ == '__main__':
    unittest.main()
