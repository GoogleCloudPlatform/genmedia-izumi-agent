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

import json
import logging

from google.adk.tools import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context

# Initialize the Google Cloud Logging client
logger = logging.getLogger(__name__)


async def generate_video_with_veo(
    tool_context: ToolContext,
    *,
    prompt: str,
    file_name: str,
    model: str = "veo-3.1-generate-001",
    first_frame_filename: str = "",
    last_frame_filename: str = "",
    aspect_ratio: str,
    duration_seconds: int,
    resolution: str,
    generate_audio: bool,
) -> str:
    """Generates a video using Veo and saves it as a user-scoped asset.

    Args:
        tool_context: The tool context, used to save assets.
        prompt: The text prompt to generate the video from.
        file_name: The name of the file to save the video as. It will be stored in the user's scope. The file name should include extension (.mp4 by default).
        model: The model to use for video generation. Defaults to 'veo-3.1-generate-001'.
            Supported models: 'veo-3.0-fast-generate-001', 'veo-3.0-generate-001', 'veo-3.1-generate-001'.
        first_frame_filename: Optional file name for a first frame image asset. Defaults to "" to pass no asset.
        last_frame_filename: Optional file name for a last frame image asset for interpolation. Defaults to "". If a last frame image is provided, a first frame must also be provided.
        aspect_ratio: The aspect ratio of the generated video. Supported values are "16:9", "9:16". Defaults to "16:9".
        duration_seconds: The duration of the video in seconds. Supported values are 4, 6, or 8.
        resolution: The resolution of the video. Can be "1080p" or "720p". Defaults to "720p".
        generate_audio: Whether to generate audio for the video.

    Returns:
        A message indicating the video has been saved.
    """
    logger.info(
        json.dumps(
            {
                "message": "Starting generate_video_with_veo",
                "prompt": prompt,
                "file_name": file_name,
                "model": model,
            }
        )
    )

    warning_message = ""
    if first_frame_filename is None:
        first_frame_filename = ""
    if last_frame_filename is None:
        last_frame_filename = ""
    if generate_audio is None:
        generate_audio = True

    if last_frame_filename and not first_frame_filename:
        raise ValueError(
            "A first frame (first_frame_filename) is required when providing a last frame for interpolation."
        )

    supported_models = [
        "veo-3.0-fast-generate-001",
        "veo-3.0-generate-001",
        "veo-3.1-generate-001",
    ]
    if model not in supported_models:
        model_warning = f"Warning: Unsupported model '{model}'. Fell back to default model 'veo-3.1-generate-001'."
        logger.warning(model_warning)
        model = "veo-3.1-generate-001"
        if warning_message:
            warning_message += f" {model_warning}"
        else:
            warning_message = model_warning

    if last_frame_filename:
        if model != "veo-3.1-generate-001":
            model_warning = f"Warning: For frame interpolation, 'veo-3.1-generate-001' is the required model. Using it instead of '{model}'."
            logger.warning(model_warning)
            model = "veo-3.1-generate-001"
            if warning_message:
                warning_message += f" {model_warning}"
            else:
                warning_message = model_warning

    supported_resolutions = ["720p", "1080p"]
    if resolution not in supported_resolutions:
        if resolution is not None and resolution != "":
            resolution_warning = f"Warning: Unsupported resolution '{resolution}'. Fell back to default resolution '720p'."
            logger.warning(resolution_warning)
            if warning_message:
                warning_message += f" {resolution_warning}"
            else:
                warning_message = resolution_warning
        resolution = "720p"

    supported_aspect_ratios = ["16:9", "9:16"]
    if aspect_ratio not in supported_aspect_ratios:
        if aspect_ratio is not None and aspect_ratio != "":
            aspect_ratio_warning = f"Warning: Unsupported aspect ratio '{aspect_ratio}'. Fell back to default aspect ratio '16:9'."
            logger.warning(aspect_ratio_warning)
            if warning_message:
                warning_message += f" {aspect_ratio_warning}"
            else:
                warning_message = aspect_ratio_warning
        aspect_ratio = "16:9"

    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_video_with_veo(
            user_id=user_id,
            prompt=prompt,
            file_name=file_name,
            model=model,
            first_frame_filename=first_frame_filename,
            last_frame_filename=last_frame_filename,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            resolution=resolution,
            generate_audio=generate_audio,
        )

        if asset:
            base_message = f"Video saved as asset with file name: {asset.file_name}"
            logger.info(f"Successfully generated video: {file_name}")
            if warning_message:
                return f"{base_message}. {warning_message}"
            return base_message
        else:
            logger.warning("No video was generated.")
            if warning_message:
                return f"No video was generated. {warning_message}"
            return "No video was generated."

    except ValueError as e:
        logger.error(f"Error generating video with Veo: {e}")
        return f"Error generating video with Veo: {e}"
