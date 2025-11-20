import asyncio
import json
import os
import uuid
import logging

from fastapi import WebSocket, WebSocketDisconnect
from google.cloud.speech_v1p1beta1 import SpeechAsyncClient
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech_v1 as tts

from redis_client import redis_client

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.speech_client = SpeechAsyncClient()
        self.tts_client = tts.TextToSpeechClient()
        self.audio_stream = None
        self.stt_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000, # Assuming 16kHz audio from frontend
            language_code="en-US",
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.stt_config,
            interim_results=True,
        )
        self.session_id = str(uuid.uuid4()) # Unique session ID for Redis pub/sub
        self.pubsub_channel = f"session:{self.session_id}:response"
        self.redis_pubsub = redis_client.pubsub()
        self.redis_pubsub.subscribe(self.pubsub_channel)
        self.tts_task = None
        logger.info(f"VoiceHandler initialized for session {self.session_id}")

    async def _listen_for_redis_responses(self):
        logger.info(f"Listening for Redis responses on {self.pubsub_channel}")
        for message in self.redis_pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                logger.info(f"Received Redis message: {data}")
                if data.get("type") == "agent_response":
                    response_text = data.get("text")
                    media_url = data.get("media_url")
                    media_type = data.get("media_type")

                    if media_url and media_type:
                        logger.info(f"Sending media URL: {media_url}")
                        await self.websocket.send_text(json.dumps({
                            "type": "media_url",
                            "url": media_url,
                            "media_type": media_type
                        }))
                    
                    if response_text:
                        logger.info(f"Sending text response: {response_text}")
                        await self.send_text_to_speech(response_text)
                        await self.websocket.send_text(json.dumps({
                            "type": "text_response",
                            "text": response_text
                        }))

    async def _request_generator(self):
        try:
            while True: # Keep receiving until WebSocketDisconnect
                audio_chunk = await self.websocket.receive_bytes()
                # logger.debug(f"Received audio chunk of size {len(audio_chunk)}") # Too verbose for info
                yield speech.StreamingRecognizeRequest(audio_content=audio_chunk)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected in request generator.")
            return

    async def handle_audio_stream(self):
        self.tts_task = asyncio.create_task(self._listen_for_redis_responses())

        try:
            logger.info("Starting Google Cloud Speech streaming recognition")
            streaming_call = self.speech_client.streaming_recognize(
                requests=self._request_generator(),
                config=self.streaming_config,
            )

            async for response in streaming_call:
                for result in response.results:
                    if result.is_final:
                        transcript = result.alternatives[0].transcript
                        logger.info(f"Final transcript: {transcript}")
                        # Publish transcript to Redis for CoordinatorAgent
                        redis_client.publish_message(
                            "agent:activity",
                            json.dumps({
                                "agent": "voice_handler",
                                "status": "transcribed",
                                "text": transcript,
                                "session_id": self.session_id
                            })
                        )
                        # Also send to a specific queue for the CoordinatorAgent to pick up
                        task_payload = json.dumps({
                            "task_id": str(uuid.uuid4()),
                            "type": "voice_input",
                            "payload": {
                                "query": transcript,
                                "session_id": self.session_id,
                                "response_channel": self.pubsub_channel
                            }
                        })
                        logger.info(f"Pushing task to tasks:coordinator_voice_input: {task_payload}")
                        redis_client.push_task("tasks:coordinator_voice_input", task_payload)
        except Exception as e:
            logger.error(f"Error in handle_audio_stream: {e}")
            raise

    async def send_text_to_speech(self, text: str):
        logger.info(f"Synthesizing speech for: {text}")
        synthesis_input = tts.SynthesisInput(text=text)
        voice = tts.VoiceSelectionParams(
            language_code="en-US", ssml_gender=tts.SsmlVoiceGender.NEUTRAL
        )
        audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

        response = self.tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        logger.info("Sending synthesized audio bytes")
        await self.websocket.send_bytes(response.audio_content)

    async def close(self):
        logger.info("Closing VoiceHandler")
        if self.audio_stream:
            self.audio_stream.cancel()
        if self.tts_task:
            self.tts_task.cancel()
        self.redis_pubsub.unsubscribe(self.pubsub_channel)
        await self.websocket.close()