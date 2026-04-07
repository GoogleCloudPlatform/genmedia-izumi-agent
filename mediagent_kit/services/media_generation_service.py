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

import base64
import json
import logging
import random
import time
from typing import Final, Literal

import google.auth
import google.auth.transport.requests
import requests
from google import genai
from google.cloud import texttospeech, texttospeech_v1beta1
from google.genai import types

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types as asset_types
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.utils.media_tools import (
    convert_wav_blob_to_mp3_blob,
    trim_last_frames_from_video_blob,
)
from mediagent_kit.utils.retry import ImmediateRetriableAPIError, retry_on_error

"""This module provides a service for generating media using various Google Cloud APIs."""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


GEMINI_TEXT_MODEL: Final = "gemini-2.5-flash"


GEMINI_IMAGE_MODEL: Final = "gemini-3.1-flash-image-preview"
GEMINI_IMAGE_ASPECT_RATIOS = Literal[
    "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"
]
GEMINI_IMAGE_ASPECT_RATIO: Final = "16:9"


LYRIA_MODEL: Final = "lyria-002"


TTS_MODEL: Final = "gemini-2.5-pro-tts"
TTS_VOICES = Literal[
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


IMAGEN_MODEL: Final = "imagen-4.0-generate-001"
IMAGEN_ASPECT_RATIOS = Literal["1:1", "3:4", "4:3", "9:16", "16:9"]
IMAGEN_ASPECT_RATIO: Final = "16:9"
IMAGEN_SIZES = Literal["1K", "2K"]
IMAGEN_SIZE: Final = "1K"


VEO_MODEL: Final = "veo-3.1-generate-001"
VEO_R2V_MODEL: Final = "veo-3.1-generate-preview"
VEO_DURATIONS = Literal[4, 6, 8]
VEO_DURATION: Final = 4
VEO_ASPECT_RATIOS = Literal["16:9", "9:16"]
VEO_ASPECT_RATIO: Final = "16:9"
VEO_RESOLUTIONS = Literal["720p", "1080p"]
VEO_RESOLUTION: Final = "720p"

_USER_AGENT = "Izumi-GenMedia-Agent/0.1.0"


class MediaGenerationService:
    def __init__(self, asset_service: AssetService, config: MediagentKitConfig):
        self._asset_service = asset_service
        self._config = config

    def _get_genai_client(self, region: str | None = None) -> genai.Client:
        project = self._config.google_cloud_project
        if not region:
            region = self._config.google_cloud_location

        if not project or not region:
            raise ValueError(
                "Missing required environment variables: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION"
            )
        return genai.Client(
            vertexai=True,
            project=project,
            location=region,
            http_options={"headers": {"user-agent": _USER_AGENT}},
        )

    @retry_on_error()
    def _call_lyria_api(
        self,
        model: str,
        prompt: str,
        negative_prompt: str | None = None,
    ) -> bytes:
        """Calls the Lyria API and returns the generated music as bytes."""
        project = self._config.google_cloud_project
        region = self._config.google_cloud_location

        if not project or not region:
            raise ValueError(
                "Missing required environment variables: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION"
            )

        music_model_endpoint = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:predict"

        request_body: dict[str, str | int] = {"prompt": prompt}
        if negative_prompt:
            request_body["negative_prompt"] = negative_prompt

        # Add a random seed for deterministic generation.
        # Note: 'seed' and 'sample_count' cannot be set in the same request.
        seed = random.randint(0, 2**32 - 1)
        request_body["seed"] = seed

        req = {"instances": [request_body], "parameters": {}}

        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        access_token = creds.token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        }

        response = requests.post(music_model_endpoint, headers=headers, json=req)

        if response.status_code == 400 and "recitation" in response.text:
            logger.warning(
                f"Lyria API returned recitation error (400). Retrying...: {response.text}"
            )
            raise ImmediateRetriableAPIError(
                "Lyria recitation error detected, triggering retry."
            )
        elif response.status_code != 200:
            logger.error(
                f"Lyria API request failed with status {response.status_code}. "
                f"status_code={response.status_code}, response_text={response.text}, "
                f"prompt={prompt}, negative_prompt={negative_prompt}"
            )

        response.raise_for_status()
        resp = response.json()

        predictions = resp.get("predictions", [])
        if not predictions:
            logger.error(
                f"No music was generated by Lyria. prompt={prompt}, "
                f"negative_prompt={negative_prompt}"
            )
            raise Exception("No music was generated by Lyria")

        music_bytes_b64 = predictions[0]["bytesBase64Encoded"]
        return base64.b64decode(music_bytes_b64)

    def generate_music_with_lyria(
        self,
        *,
        user_id: str,
        file_name: str,
        prompt: str,
        negative_prompt: str | None = None,
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates music using Lyria and saves it as a user-scoped asset."""
        if model is None:
            config = self._config.models.get("music", {})
            if purpose and purpose in config:
                model = config[purpose]
            else:
                model = config.get("default", LYRIA_MODEL)

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_music_with_lyria",
                    "prompt": prompt,
                    "model": model,
                    "file_name": file_name,
                    "purpose": purpose,
                }
            )
        )

        music_bytes = self._call_lyria_api(
            model=model, prompt=prompt, negative_prompt=negative_prompt
        )

        # Lyria currently returns WAV, convert to MP3 for wider compatibility
        music_bytes = convert_wav_blob_to_mp3_blob(music_bytes)
        mime_type = "audio/mpeg"

        music_generate_config = asset_types.MusicGenerateConfig(
            model=model,
            prompt=prompt,
            negative_prompt=negative_prompt,
        )

        asset = self._asset_service.save_asset(
            user_id=user_id,
            mime_type=mime_type,
            file_name=file_name,
            blob=music_bytes,
            music_generate_config=music_generate_config,
        )
        logger.info(f"Successfully generated music: {file_name}")
        return asset

    @retry_on_error()
    def generate_image_with_imagen(
        self,
        *,
        user_id: str,
        file_name: str,
        prompt: str,
        aspect_ratio: IMAGEN_ASPECT_RATIOS = IMAGEN_ASPECT_RATIO,
        image_size: IMAGEN_SIZES = IMAGEN_SIZE,
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates an image using Imagen and saves it as a user-scoped asset."""
        if model is None:
            config = self._config.models.get("image_imagen", {})
            if purpose and purpose in config:
                model = config[purpose]
            else:
                model = config.get("default", IMAGEN_MODEL)

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_image_with_imagen",
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "model": model,
                    "file_name": file_name,
                    "purpose": purpose,
                }
            )
        )

        client = self._get_genai_client()
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                aspect_ratio=aspect_ratio,
                number_of_images=1,
                image_size=image_size,
                safety_filter_level=types.SafetyFilterLevel.BLOCK_ONLY_HIGH,
                person_generation=types.PersonGeneration.ALLOW_ALL,
            ),
        )

        if response.generated_images:
            generated_image = response.generated_images[0]
            if generated_image.image is None:
                raise ValueError("Generated image is None")
            img_bytes = generated_image.image.image_bytes
            mime_type = generated_image.image.mime_type

            if not mime_type:
                raise ValueError(
                    "Could not determine mime type of the generated image."
                )

            image_generate_config = asset_types.ImageGenerateConfig(
                model=model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

            asset = self._asset_service.save_asset(
                user_id=user_id,
                mime_type=mime_type,
                file_name=file_name,
                blob=img_bytes,
                image_generate_config=image_generate_config,
            )
            logger.info(f"Successfully generated Imagen image: {file_name}")
            return asset
        else:
            logger.error(
                f"No image was generated by Imagen. prompt={prompt}, "
                f"aspect_ratio={aspect_ratio}, model={model}, file_name={file_name}"
            )
            raise Exception("No image was generated by Imagen")

    # We extract this out as a helper so that we can patch it in test.
    # We don't want to patch generate_content since we want to use real LLM for testing,
    # but just dont want to generate real images (both use the same generate_content endpoint).
    def _generate_gemini_image_content(
        self,
        client: genai.Client,
        model: str,
        contents: list,
        aspect_ratio: str,
    ) -> types.GenerateContentResponse:
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                candidate_count=1,
            ),
        )

    def _generate_gemini_text_content(
        self,
        client: genai.Client,
        model: str,
        contents: list,
    ) -> types.GenerateContentResponse:
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
                candidate_count=1,
            ),
        )

    def _get_asset(self, user_id: str, file_name: str) -> asset_types.Asset:
        """Returns an asset by its file name for a given user."""
        asset = self._asset_service.get_asset_by_file_name(
            user_id=user_id, file_name=file_name
        )
        if not asset:
            raise ValueError(f"Could not find asset with file name: {file_name}")
        return asset

    @retry_on_error()
    def generate_text_with_gemini(
        self,
        *,
        user_id: str,
        file_name: str,
        prompt: str,
        reference_image_filenames: list[str] = [],
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates text using Gemini, with an optional set of reference images."""
        if model is None:
            text_config = self._config.models.get("text", {})
            if purpose and purpose in text_config:
                model = text_config[purpose]
            else:
                model = text_config.get("default", GEMINI_TEXT_MODEL)

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_text_with_gemini",
                    "file_name": file_name,
                    "model": model,
                    "prompt": prompt,
                    "reference_files": reference_image_filenames,
                    "purpose": purpose,
                }
            )
        )

        reference_images = [
            self._get_asset(user_id, reference_image_filename)
            for reference_image_filename in reference_image_filenames
        ]
        contents = [
            types.Part.from_uri(
                file_uri=asset.current.gcs_uri, mime_type=asset.mime_type
            )
            for asset in reference_images
        ]
        contents.append(types.Part.from_text(text=prompt))

        client = self._get_genai_client()
        response = self._generate_gemini_text_content(
            client=client, model=model, contents=contents
        )

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            error_message = f"Text generation failed. The prompt was blocked for reason: {response.prompt_feedback.block_reason.name}"
            logger.warning(
                json.dumps(
                    {
                        "message": error_message,
                        "reason": response.prompt_feedback.block_reason.name,
                    }
                )
            )
            raise ValueError(error_message)

        if (
            response.candidates
            and response.candidates[0].content
            and (parts := response.candidates[0].content.parts)
        ):
            generated_text = "".join(part.text for part in parts if part.text)
            if generated_text:
                text_generate_config = asset_types.TextGenerateConfig(
                    model=model,
                    prompt=prompt,
                    reference_images=reference_images,
                )
                asset = self._asset_service.save_asset(
                    user_id=user_id,
                    file_name=file_name,
                    blob=generated_text.encode(),
                    mime_type="text/plain",
                    text_generate_config=text_generate_config,
                )
                logger.info(f"Successfully generated text: {file_name}")
                return asset

        logger.error(f"No text was generated by Gemini. prompt={prompt}")
        raise ImmediateRetriableAPIError("No text was generated by Gemini.")

    @retry_on_error()
    def generate_image_with_gemini(
        self,
        *,
        user_id: str,
        file_name: str,
        prompt: str,
        reference_image_filenames: list[str] = [],
        aspect_ratio: GEMINI_IMAGE_ASPECT_RATIOS = GEMINI_IMAGE_ASPECT_RATIO,
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates an image using Gemini Image, with an optional set of reference images."""
        if model is None:
            config = self._config.models.get("image_gemini", {})
            if purpose and purpose in config:
                model = config[purpose]
            else:
                model = config.get("default", GEMINI_IMAGE_MODEL)

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_image_with_gemini",
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "file_name": file_name,
                    "reference_files": reference_image_filenames,
                    "purpose": purpose,
                    "model": model,
                }
            )
        )

        reference_images = [
            self._get_asset(user_id, file_name)
            for file_name in reference_image_filenames
        ]
        contents = [
            types.Part.from_uri(
                file_uri=asset.current.gcs_uri, mime_type=asset.mime_type
            )
            for asset in reference_images
        ]
        contents.append(types.Part.from_text(text=prompt))

        region = None
        if "preview" in model:
            region = "global"

        client = self._get_genai_client(region=region)
        response = self._generate_gemini_image_content(
            client=client,
            model=model,
            contents=contents,
            aspect_ratio=aspect_ratio,
        )

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            error_message = f"Image generation failed. The prompt was blocked for reason: {response.prompt_feedback.block_reason.name}"
            logger.warning(
                json.dumps(
                    {
                        "message": error_message,
                        "reason": response.prompt_feedback.block_reason.name,
                    }
                )
            )
            raise ValueError(error_message)

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_generate_config = asset_types.ImageGenerateConfig(
                        model=model,
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        reference_images=reference_images,
                    )
                    asset = self._asset_service.save_asset(
                        user_id=user_id,
                        mime_type=part.inline_data.mime_type,
                        file_name=file_name,
                        blob=part.inline_data.data,
                        image_generate_config=image_generate_config,
                    )
                    logger.info(f"Successfully generated Gemini image: {file_name}")
                    return asset

        logger.error(f"No image was generated by Gemini Image. Prompt: {prompt}")
        raise ImmediateRetriableAPIError("No image was generated by Gemini Image.")

    @retry_on_error()
    def generate_speech_single_speaker(
        self,
        *,
        user_id: str,
        file_name: str,
        text: str,
        voice_name: TTS_VOICES,
        language_code: str = "en-US",
        prompt: str = "",
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates speech from text with a single speaker and saves it as a user-scoped asset."""
        if model is None:
            config = self._config.models.get("tts", {})
            if purpose and purpose in config:
                model = config[purpose]
            else:
                model = config.get("default", TTS_MODEL)

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_speech_single_speaker",
                    "model": model,
                    "voice_name": voice_name,
                    "language_code": language_code,
                    "file_name": file_name,
                    "purpose": purpose,
                }
            )
        )

        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code, name=voice_name, model_name=model
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        speech_generate_config = asset_types.SpeechGenerateConfig(
            model=model,
            prompt=prompt,
            voice=voice_name,
            spoken_text=text,
        )

        asset = self._asset_service.save_asset(
            user_id=user_id,
            mime_type="audio/mpeg",
            file_name=file_name,
            blob=response.audio_content,
            speech_generate_config=speech_generate_config,
        )

        logger.info(f"Successfully generated speech: {file_name}")
        return asset

    @retry_on_error()
    def generate_speech_multiple_speaker(
        self,
        *,
        user_id: str,
        file_name: str,
        multi_speaker_markup: str,
    ) -> asset_types.Asset:
        """Generates speech for multiple speakers from a markup and saves it as a user-scoped asset."""
        logger.info(f"Starting generate_speech_multiple_speaker for file: {file_name}")
        project = self._config.google_cloud_project
        if not project:
            raise ValueError(
                "Missing required environment variable: GOOGLE_CLOUD_PROJECT"
            )

        client = texttospeech_v1beta1.TextToSpeechClient()

        try:
            turns_data = json.loads(multi_speaker_markup)
            turns = [
                texttospeech_v1beta1.MultiSpeakerMarkup.Turn(
                    text=turn["text"], speaker=turn["speaker"]
                )
                for turn in turns_data
            ]
        except (json.JSONDecodeError, KeyError) as e:
            error_message = f"Error: Invalid multi_speaker_markup format. {e}"
            logger.error(f"{error_message}: {e}")
            raise ValueError(error_message) from e

        multi_speaker_markup_object = texttospeech_v1beta1.MultiSpeakerMarkup(
            turns=turns
        )

        synthesis_input = texttospeech_v1beta1.SynthesisInput(
            multi_speaker_markup=multi_speaker_markup_object
        )

        voice = texttospeech_v1beta1.VoiceSelectionParams(
            language_code="en-US", name="en-US-Studio-MultiSpeaker"
        )

        audio_config = texttospeech_v1beta1.AudioConfig(
            audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        speech_generate_config = asset_types.SpeechGenerateConfig(
            spoken_text=multi_speaker_markup,
        )

        asset = self._asset_service.save_asset(
            user_id=user_id,
            mime_type="audio/mpeg",
            file_name=file_name,
            blob=response.audio_content,
            speech_generate_config=speech_generate_config,
        )

        return asset

    @retry_on_error()
    def generate_video_with_veo(
        self,
        *,
        user_id: str,
        file_name: str,
        prompt: str,
        duration_seconds: VEO_DURATIONS = VEO_DURATION,
        aspect_ratio: VEO_ASPECT_RATIOS = VEO_ASPECT_RATIO,
        resolution: VEO_RESOLUTIONS = VEO_RESOLUTION,
        generate_audio: bool = False,
        first_frame_filename: str | None = None,
        last_frame_filename: str | None = None,
        reference_image_filenames: list[str] | None = None,
        method: Literal["image_to_video", "reference_to_video"] = "image_to_video",
        purpose: str | None = None,
        model: str | None = None,
    ) -> asset_types.Asset:
        """Generates a video using Veo and saves it as a user-scoped asset."""
        if model is None:
            config = self._config.models.get("video", {})
            if purpose and purpose in config:
                model = config[purpose]
            else:
                model = config.get("default", VEO_MODEL)

        # Use preview model for reference-based generation
        if method == "reference_to_video" and model == VEO_MODEL:
            model = VEO_R2V_MODEL

        logger.info(
            json.dumps(
                {
                    "message": "Starting generate_video_with_veo",
                    "prompt": prompt,
                    "file_name": file_name,
                    "model": model,
                    "method": method,
                }
            )
        )
        client = self._get_genai_client()

        image_to_pass = None
        first_frame_asset = None

        if first_frame_filename:
            try:
                first_frame_asset = self._get_asset(user_id, first_frame_filename)
                image_to_pass = types.Image(
                    gcs_uri=first_frame_asset.current.gcs_uri,
                    mime_type=first_frame_asset.mime_type,
                )
            except Exception as e:
                error_message = (
                    f"Error loading reference image asset {first_frame_filename}: {e}"
                )
                logger.error(
                    json.dumps(
                        {
                            "message": error_message,
                            "file_name": first_frame_filename,
                            "error": str(e),
                        }
                    )
                )
                raise ValueError(error_message) from e

        last_frame_to_pass = None
        last_frame_asset = None

        if last_frame_filename:
            try:
                last_frame_asset = self._get_asset(user_id, last_frame_filename)
                last_frame_to_pass = types.Image(
                    gcs_uri=last_frame_asset.current.gcs_uri,
                    mime_type=last_frame_asset.mime_type,
                )
            except Exception as e:
                error_message = (
                    f"Error loading last frame image asset {last_frame_filename}: {e}"
                )
                logger.error(
                    json.dumps(
                        {
                            "message": error_message,
                            "file_name": last_frame_filename,
                            "error": str(e),
                        }
                    )
                )
                raise ValueError(error_message) from e

        reference_images_to_pass = None
        if reference_image_filenames:
            reference_images_to_pass = []
            for ref_filename in reference_image_filenames:
                ref_asset = self._get_asset(user_id, ref_filename)
                reference_images_to_pass.append(
                    types.VideoGenerationReferenceImage(
                        image=types.Image(
                            gcs_uri=ref_asset.current.gcs_uri,
                            mime_type=ref_asset.mime_type,
                        ),
                        reference_type=types.VideoGenerationReferenceType.ASSET,
                    )
                )

        video_config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
            duration_seconds=duration_seconds,
            person_generation=types.PersonGeneration.ALLOW_ALL,
            enhance_prompt=True,
            generate_audio=generate_audio,
            last_frame=last_frame_to_pass,
            reference_images=(
                reference_images_to_pass if method == "reference_to_video" else None
            ),
            resolution=resolution,
        )

        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image_to_pass if method == "image_to_video" else None,
            config=video_config,
        )

        logger.info("Waiting for video generation to complete...")

        while not operation.done:
            logger.info(f"Still waiting for video generation: {file_name}")
            time.sleep(15)
            operation = client.operations.get(operation)

        if operation.error:
            error_message = f"Video generation failed with error: {operation.error}. Prompt: {prompt}. Output file: {file_name}."
            logger.error(error_message)
            raise ValueError(error_message)

        if (
            operation.response
            and operation.result
            and operation.result.generated_videos
            and operation.result.generated_videos[0].video
        ):
            video_bytes = operation.result.generated_videos[0].video.video_bytes

            if first_frame_filename and last_frame_filename and "veo-3.1" in model:
                # This is needed to make the last frame to be exactly what we provide, due to the padding logic of Veo
                video_bytes = trim_last_frames_from_video_blob(video_bytes, "mp4", 7)

            video_generate_config = asset_types.VideoGenerateConfig(
                model=model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                resolution=resolution,
                generate_audio=generate_audio,
                first_frame_asset=first_frame_asset,
                last_frame_asset=last_frame_asset,
            )

            asset = self._asset_service.save_asset(
                user_id=user_id,
                mime_type="video/mp4",
                file_name=file_name,
                blob=video_bytes,
                video_generate_config=video_generate_config,
            )

            logger.info(f"Successfully generated video: {file_name}")
            return asset

        logger.error(f"No video was generated by Veo. Prompt: {prompt}")
        raise ImmediateRetriableAPIError("No video was generated by Veo.")
