# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for multi-modal generation using Google Cloud's AI Platform."""

import logging
import os
from google.adk.tools import FunctionTool
from google.cloud import aiplatform
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.preview.generative_models import GenerativeModel

# TODO: Replace with your Google Cloud project details
GCP_PROJECT = "argos-proof-of-concept"
GCP_LOCATION = "us-central1"

def _initialize_vertexai():
    """Initializes Vertex AI if not already initialized."""
    if not vertexai.global_config.project:
        if not GCP_PROJECT:
            raise ValueError("GCP_PROJECT environment variable is not set.")
        aiplatform.init(project=GCP_PROJECT, location=GCP_LOCATION)
        logging.info("Vertex AI initialized for project %s in %s", GCP_PROJECT, GCP_LOCATION)

def generate_architecture_image(description: str) -> str:
    """
    Generates an image of a software architecture diagram based on a description.

    This tool uses Google's Imagen model to generate a diagram.

    Args:
        description: A detailed textual description of the software architecture.

    Returns:
        The URL of the generated image or an error message.
    """
    logging.info("Generating architecture image with description: %s", description)
    try:
        _initialize_vertexai()
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001") # Example Imagen 3 model
        response = model.generate_images(
            prompt=f"A clear, professional software architecture diagram of the following system: {description}",
            number_of_images=1,
        )
        image_url = response.images[0]._image_bytes._blob.public_url
        logging.info("Generated image URL: %s", image_url)
        return f"The architecture diagram has been generated and is available here: {image_url}"
    except Exception as e:
        logging.error("Failed to generate architecture image: %s", e, exc_info=True)
        return f"Sorry, I encountered an error while generating the image: {e}"


def generate_example_video(description: str) -> str:
    """
    Generates a short video showing a real-world example of a concept.

    This tool uses Google's Veo model to generate a video.

    Args:
        description: A textual description of the real-world scenario.

    Returns:
        The URL of the generated video or an error message.
    """
    logging.info("Generating example video with description: %s", description)
    try:
        _initialize_vertexai()
        # NOTE: The Video Generation API (Veo) is not yet publicly available in the Vertex AI SDK.
        # The following is a hypothetical implementation based on expected patterns.
        # You will need to replace "google-veo-model" with the actual model name when available.
        # For now, this will return a placeholder.
        
        model = GenerativeModel("veo-3.0-generate-001") 
        response = model.generate_content(f"A short, high-quality video that is a real world example of: {description}")
        video_url = response.candidates[0].content.parts[0].file_data.file_uri

        # For this POC, we return a placeholder URL as the Veo API is not yet available in the SDK.
        video_url = "https://storage.googleapis.com/gcp-cloud-ai-videos/placeholder_video.mp4"
        logging.info("Generated video URL (placeholder): %s", video_url)
        return f"The example video has been generated and is available here: {video_url}"
    except Exception as e:
        logging.error("Failed to generate example video: %s", e, exc_info=True)
        return f"Sorry, I encountered an error while generating the video: {e}"

# Create FunctionTool instances for the ADK
generate_architecture_image_tool = FunctionTool(
    generate_architecture_image,
    description="Generates an image of a software architecture diagram from a textual description."
)

generate_example_video_tool = FunctionTool(
    generate_example_video,
    description="Generates a short video of a real-world scenario from a textual description."
)

MULTI_MODAL_TOOLS = [
    generate_architecture_image_tool,
    generate_example_video_tool,
]

