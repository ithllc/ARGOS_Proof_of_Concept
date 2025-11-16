# Unit Test Plan for ADK Live and Multi-Modal Features

**Document Version:** 1.0
**Date:** November 15, 2025

## 1. Overview

This document outlines the unit testing strategy for the new ADK Live voice interaction and multi-modal generation features. The goal is to ensure these components are reliable, handle errors gracefully, and function as expected without requiring real hardware (microphones, speakers) or making actual API calls to Google Cloud services during testing.

## 2. Testing Strategy

The core of the strategy is **comprehensive mocking**. All external dependencies will be replaced with mock objects using Python's `unittest.mock` library.

-   **WebSocket:** The WebSocket connection will be mocked to simulate a client connection, allowing us to send and receive data without a real network connection.
-   **Google Cloud APIs:** The clients for Speech-to-Text, Text-to-Speech, and AI Platform (for Imagen/Veo) will be mocked to return predefined responses. This allows us to test the application's logic in isolation.
-   **Audio Streams:** We will simulate audio streams by sending byte strings to the mocked WebSocket, and we will verify that the TTS output is correctly formatted.

## 3. New Test Files

New test files will be created to mirror the new source files:

-   `tests/test_voice_handler.py`
-   `tests/test_multi_modal_tools.py`
-   `tests/test_main_live.py` (To test the WebSocket endpoint in `main.py`)

## 4. Test Cases

### 4.1. `test_voice_handler.py`

-   **`test_audio_stream_forwarding`**: Verify that audio chunks received from the (mocked) WebSocket are correctly streamed to the (mocked) Speech-to-Text API.
-   **`test_transcription_handling`**: Verify that transcribed text from the STT API is correctly passed to the `CoordinatorAgent`.
-   **`test_tts_streaming`**: Verify that text received from the `CoordinatorAgent` is correctly sent to the TTS API and that the resulting audio is streamed back to the WebSocket client.
-   **`test_connection_cleanup`**: Ensure that all resources are properly closed when the WebSocket connection is terminated.

### 4.2. `test_multi_modal_tools.py`

-   **`test_generate_architecture_image_tool`**:
    -   Verify that the `generate_architecture_image` tool correctly calls the (mocked) AI Platform client for Imagen 3.
    -   Check that the prompt passed to the model is correctly formatted.
    -   Ensure the tool returns the mocked image URL as expected.
-   **`test_generate_example_video_tool`**:
    -   Verify that the `generate_example_video` tool correctly calls the (mocked) AI Platform client for Veo.
    -   Check that the prompt passed to the model is correctly formatted.
    -   Ensure the tool returns the mocked video URL as expected.
-   **`test_agent_tool_invocation`**:
    -   In a test for the `CoordinatorAgent`, provide a user prompt like "show me a diagram of the system."
    -   Verify that the agent's logic correctly decides to call the `generate_architecture_image` tool.

### 4.3. `test_main_live.py`

-   **`test_websocket_connection`**: Use a test client to verify that a WebSocket connection to the `/ws/live` endpoint can be established successfully.
-   **`test_websocket_rejection`**: Verify that the endpoint handles invalid or unauthorized connection attempts gracefully.

## 5. Frontend Testing Considerations

The logic for rendering images and auto-playing videos resides entirely on the client-side. While the backend Python tests ensure the correct data (URLs and audio streams) is sent, testing the visual behavior itself requires a frontend testing framework (e.g., Jest with React Testing Library).

The following test cases should be implemented in the frontend test suite for the `VoiceInterface.tsx` component:

-   **`test_renders_image_on_message`**:
    -   Simulate receiving a text message from the agent containing an image URL.
    -   Verify that an `<img>` tag is rendered in the document.
    -   Verify that the `src` attribute of the `<img>` tag matches the URL from the message.

-   **`test_renders_video_on_message`**:
    -   Simulate receiving a text message from the agent containing a video URL.
    -   Verify that a `<video>` tag is rendered in the document.
    -   Verify that the `src` attribute of the `<video>` tag matches the URL from the message.

-   **`test_video_plays_after_tts_ends`**:
    -   Simulate receiving a message with a video URL and a corresponding TTS audio stream.
    -   Mock the `HTMLAudioElement` used for TTS playback to allow manual triggering of the `onended` event.
    -   Mock the `.play()` method on the `HTMLVideoElement`.
    -   Trigger the `onended` event for the audio element and verify that the `.play()` method on the video element was called exactly once.

-   **`test_no_media_is_rendered`**:
    -   Simulate receiving a standard text message without a media URL.
    -   Verify that no `<img>` or `<video>` tags are rendered in the media display area.
