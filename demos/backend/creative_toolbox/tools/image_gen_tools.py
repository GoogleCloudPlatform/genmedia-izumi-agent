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


async def generate_image_with_imagen(
    tool_context: ToolContext,
    *,
    prompt: str,
    aspect_ratio: str,
    model: str,
    file_name: str,
) -> str:
    """Generates an image using Imagen and saves it as a user-scoped asset.
    Imagen can only generate images from text prompt and cannot do image editing (e.g. take a reference image as input)

    Args:
        tool_context: The tool context, used to save assets.
        prompt: The text prompt to generate the image from.
        aspect_ratio: The aspect ratio of the generated image. Supported values are "1:1", "3:4", "4:3", "16:9", "9:16".
        model: The model to use for image generation. Can be one of:
            - Imagen 4 Fast: imagen-4.0-fast-generate-001
            - Imagen 4 Standard: imagen-4.0-generate-001 (recommended)
            - Imagen 4 Ultra: imagen-4.0-ultra-generate-001
        file_name: The name of the file to save the image as. It will be stored in the user's scope. The file name should include extension (.png by default)

    Returns:
        A message indicating the image has been saved.
    """
    logger.info(
        json.dumps(
            {
                "message": "Starting generate_image_with_imagen",
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "file_name": file_name,
            }
        )
    )
    supported_models = [
        "imagen-4.0-fast-generate-001",
        "imagen-4.0-generate-001",
        "imagen-4.0-ultra-generate-001",
    ]
    warning_message = ""
    if model not in supported_models:
        warning_message = f"Warning: Unsupported model '{model}' was provided. Fell back to default model 'imagen-4.0-generate-001'."
        logger.warning(warning_message)
        model = "imagen-4.0-generate-001"

    supported_aspect_ratios = ["1:1", "3:4", "4:3", "16:9", "9:16"]
    if aspect_ratio not in supported_aspect_ratios:
        aspect_ratio_warning = f"Unsupported aspect ratio '{aspect_ratio}' was provided. Fell back to default aspect ratio '1:1'."
        logger.warning(aspect_ratio_warning)
        if warning_message:
            warning_message += f" {aspect_ratio_warning}"
        else:
            warning_message = f"Warning: {aspect_ratio_warning}"
        aspect_ratio = "1:1"

    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_image_with_imagen(
            user_id=user_id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            model=model,
            file_name=file_name,
        )
        base_message = f"Image saved as asset with file name: {asset.file_name}"
        logger.info(f"Successfully generated image with Imagen: {file_name}")
        if warning_message:
            return f"{base_message}. {warning_message}"
        return base_message
    except Exception as e:
        logger.error(f"Error generating image with Imagen: {e}")
        return f"Error generating image with Imagen: {e}"


async def generate_image_with_gemini(
    tool_context: ToolContext,
    *,
    prompt: str,
    aspect_ratio: str,
    file_name: str,
    reference_image_1_filename: str = "",
    reference_image_2_filename: str = "",
    reference_image_3_filename: str = "",
    reference_image_4_filename: str = "",
) -> str:
    """Generates an image using Gemini Image, with an optional set of reference images.
    Gemini Image supports both generating images from a text prompt and using reference images.

    Args:
        tool_context: The tool context, used to save and load assets.
        prompt: The text prompt to generate the image from.
        aspect_ratio: The aspect ratio of the generated image. Supported values are "1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9".
        file_name: The name of the file to save the image as. It will be stored in the user's scope. The file name should include extension (.png by default)
        reference_image_1_filename: Optional file name for a reference image asset. Defaults to "" to pass no asset.
        reference_image_2_filename: Optional file name for a reference image asset. Defaults to "" to pass no asset.
        reference_image_3_filename: Optional file name for a reference image asset. Defaults to "" to pass no asset.
        reference_image_4_filename: Optional file name for a reference image asset. Defaults to "" to pass no asset.

    Returns:
        A message indicating the image has been saved, or an error message.
    """
    reference_image_filenames = [
        reference_image_1_filename,
        reference_image_2_filename,
        reference_image_3_filename,
        reference_image_4_filename,
    ]

    logger.info(
        json.dumps(
            {
                "message": "Starting generate_image_with_gemini",
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "file_name": file_name,
                "reference_files": reference_image_filenames,
            }
        )
    )
    warning_message = ""
    supported_aspect_ratios = [
        "1:1",
        "3:2",
        "2:3",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "9:16",
        "16:9",
        "21:9",
    ]
    if aspect_ratio not in supported_aspect_ratios:
        aspect_ratio_warning = f"Unsupported aspect ratio '{aspect_ratio}' was provided. Fell back to default aspect ratio '1:1'."
        logger.warning(aspect_ratio_warning)
        warning_message = f"Warning: {aspect_ratio_warning}"
        aspect_ratio = "1:1"

    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_image_with_gemini(
            user_id=user_id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            file_name=file_name,
            reference_image_filenames=reference_image_filenames,
        )

        if asset:
            base_message = f"Image saved as asset with file name: {asset.file_name}"
            logger.info(f"Successfully generated image with Gemini: {file_name}")
            if warning_message:
                return f"{base_message}. {warning_message}"
            return base_message
        else:
            logger.warning("No image was generated by Gemini.")
            if warning_message:
                return f"No image was generated. {warning_message}"
            return "No image was generated."
    except ValueError as e:
        logger.error(f"Error generating image with Gemini: {e}")
        return f"Error generating image with Gemini: {e}"
