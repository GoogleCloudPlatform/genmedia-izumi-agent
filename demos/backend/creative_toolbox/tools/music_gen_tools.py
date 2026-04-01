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

logger = logging.getLogger(__name__)


async def generate_music_with_lyria(
    tool_context: ToolContext,
    *,
    prompt: str,
    file_name: str,
    model: str,
    negative_prompt: str = "",
) -> str:
    """Generates music using Lyria and saves it as a user-scoped asset.

    Args:
        tool_context: The tool context, used to save assets.
        prompt: The text prompt to generate the music from.
        file_name: The name of the file to save the music as. It will be stored in the user's scope. The file name should include extension (.wav by default)
        model: The model to use for music generation. The only supported model is 'lyria-002'.
        negative_prompt: An optional prompt to specify what to avoid in the generated music. Defaults to an empty string.

    Returns:
        A message indicating the music has been saved.
    """
    logger.info(
        json.dumps(
            {
                "message": "Starting generate_music_with_lyria",
                "prompt": prompt,
                "model": model,
                "file_name": file_name,
            }
        )
    )
    supported_models = [
        "lyria-002",
    ]
    warning_message = ""
    if model not in supported_models:
        warning_message = f"Warning: Unsupported model '{model}' was provided. Fell back to default model 'lyria-002'."
        logger.warning(warning_message)
        model = "lyria-002"

    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_music_with_lyria(
            user_id=user_id,
            prompt=prompt,
            file_name=file_name,
            model=model,
            negative_prompt=negative_prompt,
        )
        base_message = f"Music saved as asset with file name: {asset.file_name}"
        logger.info(f"Successfully generated music with Lyria: {file_name}")
        if warning_message:
            return f"{base_message}. {warning_message}"
        return base_message
    except Exception as e:
        logger.error(f"Error generating music with Lyria: {e}")
        return f"Error generating music with Lyria: {e}"
