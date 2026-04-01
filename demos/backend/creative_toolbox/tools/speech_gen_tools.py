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


async def generate_speech_single_speaker(
    tool_context: ToolContext,
    *,
    prompt: str,
    text: str,
    model_name: str,
    voice_name: str,
    file_name: str,
) -> str:
    """Generates speech from text with a single speaker and saves it as a user-scoped asset.

    Args:
        tool_context: The tool context, used to save assets.
        prompt: Stylistic instructions on how to synthesize the content in the text field.
        text: The text to synthesize.
        model_name: The Gemini model to use. Currently, the available models are gemini-2.5-flash-tts and gemini-2.5-pro-preview-tts.
        voice_name: The voice to use for the speech generation. e.g. "Charon" for male voice, "Aoede" for female voice.
        file_name: The name of the file to save the audio as. It will be stored in the user's scope. The file name should include extension (.mp3 by default)

    Returns:
        A message indicating the audio has been saved.
    """
    logger.info(
        json.dumps(
            {
                "message": "Starting generate_speech_single_speaker",
                "model_name": model_name,
                "voice_name": voice_name,
                "file_name": file_name,
            }
        )
    )

    supported_models = [
        "gemini-2.5-flash-tts",
        "gemini-2.5-pro-tts",
    ]
    warning_message = ""
    if model_name not in supported_models:
        model_warning = f"Warning: Unsupported model '{model_name}' was provided. Fell back to default model 'gemini-2.5-flash-tts'."
        logger.warning(model_warning)
        if warning_message:
            warning_message += f" {model_warning}"
        else:
            warning_message = model_warning
        model_name = "gemini-2.5-flash-tts"

    supported_voices = [
        "Achernar",
        "Achird",
        "Algenib",
        "Algieba",
        "Alnilam",
        "Aoede",
        "Autonoe",
        "Callirrhoe",
        "Charon",
        "Despina",
        "Enceladus",
        "Erinome",
        "Fenrir",
        "Gacrux",
        "Iapetus",
        "Kore",
        "Laomedeia",
        "Leda",
        "Orus",
        "Pulcherrima",
        "Puck",
        "Rasalgethi",
        "Sadachbia",
        "Sadaltager",
        "Schedar",
        "Sulafat",
        "Umbriel",
        "Vindemiatrix",
        "Zephyr",
        "Zubenelgenubi",
    ]

    if voice_name not in supported_voices:
        voice_warning = f"Warning: Unsupported voice '{voice_name}' was provided. Fell back to default voice 'Aoede'."
        logger.warning(voice_warning)
        if warning_message:
            warning_message += f" {voice_warning}"
        else:
            warning_message = voice_warning
    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_speech_single_speaker(
            user_id=user_id,
            prompt=prompt,
            text=text,
            model=model_name,
            voice_name=voice_name,
            file_name=file_name,
        )
        base_message = f"Speech audio saved as asset with file name: {asset.file_name}"
        logger.info(f"Successfully generated single-speaker speech: {file_name}")
        if warning_message:
            return f"{base_message}. {warning_message}"
        return base_message
    except Exception as e:
        logger.error(f"Error generating single-speaker speech: {e}")
        return f"Error generating single-speaker speech: {e}"


async def generate_speech_multiple_speaker(
    tool_context: ToolContext,
    *,
    multi_speaker_markup: str,
    file_name: str,
) -> str:
    """Generates speech for multiple speakers from a markup and saves it as a user-scoped asset.

    Args:
        tool_context: The tool context, used to save assets.
        multi_speaker_markup: A JSON string representing the multi-speaker markup.
            It should be a list of dictionaries, where each dictionary has "text" and "speaker" keys.
            Example: '''[{"text": "Hello", "speaker": "A"}, {"text": "Hi", "speaker": "B"}]'''
        file_name: The name of the file to save the audio as. It will be stored in the user's scope. The file name should include extension (.mp3 by default)

    Returns:
        A message indicating the audio has been saved.
    """
    user_id = get_user_id_from_context(tool_context)
    media_generation_service = mediagent_kit.services.aio.get_media_generation_service()

    try:
        asset = await media_generation_service.generate_speech_multiple_speaker(
            user_id=user_id,
            multi_speaker_markup=multi_speaker_markup,
            file_name=file_name,
        )
        success_message = (
            f"Speech audio saved as asset with file name: {asset.file_name}"
        )
        logger.info(success_message)
        return success_message
    except Exception as e:
        logger.error(f"Error generating multi-speaker speech: {e}")
        return f"Error generating multi-speaker speech: {e}"
