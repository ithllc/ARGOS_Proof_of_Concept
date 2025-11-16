import unittest
from unittest.mock import MagicMock, patch
import asyncio
import json

from ARGOS_POS.src.voice_handler import VoiceHandler

class TestVoiceHandler(unittest.TestCase):

    def setUp(self):
        self.mock_websocket = MagicMock()
        self.mock_coordinator_agent = MagicMock()
        self.voice_handler = VoiceHandler(self.mock_websocket, self.mock_coordinator_agent)

    @patch('google.cloud.speech_v1p1beta1.SpeechClient')
    @patch('google.cloud.texttospeech_v1.TextToSpeechClient')
    async def test_audio_stream_forwarding(self, MockTextToSpeechClient, MockSpeechClient):
        mock_stt_client_instance = MockSpeechClient.return_value
        mock_stt_stream = MagicMock()
        mock_stt_client_instance.streaming_recognize.return_value = mock_stt_stream

        audio_chunk = b"test_audio_data"
        self.mock_websocket.receive_bytes.side_effect = [audio_chunk, asyncio.CancelledError]

        with self.assertRaises(asyncio.CancelledError):
            await self.voice_handler.handle_audio_stream()

        mock_stt_client_instance.streaming_recognize.assert_called_once()
        mock_stt_stream.write.assert_called_once_with(audio_chunk)

    @patch('google.cloud.speech_v1p1beta1.SpeechClient')
    @patch('google.cloud.texttospeech_v1.TextToSpeechClient')
    async def test_transcription_handling(self, MockTextToSpeechClient, MockSpeechClient):
        mock_stt_client_instance = MockSpeechClient.return_value
        mock_stt_stream = MagicMock()
        mock_stt_client_instance.streaming_recognize.return_value = mock_stt_stream

        mock_stt_stream.read.return_value = [
            MagicMock(results=[MagicMock(alternatives=[MagicMock(transcript="hello world")])])
        ]
        self.mock_websocket.receive_bytes.side_effect = [asyncio.CancelledError]

        with self.assertRaises(asyncio.CancelledError):
            await self.voice_handler.handle_audio_stream()

        self.mock_coordinator_agent.process_text.assert_called_once_with("hello world")

    @patch('google.cloud.speech_v1p1beta1.SpeechClient')
    @patch('google.cloud.texttospeech_v1.TextToSpeechClient')
    async def test_tts_streaming(self, MockTextToSpeechClient, MockSpeechClient):
        mock_tts_client_instance = MockTextToSpeechClient.return_value
        mock_tts_response = MagicMock()
        mock_tts_response.audio_content = b"synthesized_audio"
        mock_tts_client_instance.synthesize_speech.return_value = mock_tts_response

        self.mock_coordinator_agent.get_response_text.return_value = "response text"

        await self.voice_handler.send_text_to_speech("test input")

        mock_tts_client_instance.synthesize_speech.assert_called_once()
        self.mock_websocket.send_bytes.assert_called_once_with(b"synthesized_audio")

    @patch('google.cloud.speech_v1p1beta1.SpeechClient')
    @patch('google.cloud.texttospeech_v1.TextToSpeechClient')
    async def test_connection_cleanup(self, MockTextToSpeechClient, MockSpeechClient):
        self.mock_websocket.receive_bytes.side_effect = asyncio.CancelledError
        self.mock_websocket.close.return_value = None

        with self.assertRaises(asyncio.CancelledError):
            await self.voice_handler.handle_audio_stream()

        self.mock_websocket.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
