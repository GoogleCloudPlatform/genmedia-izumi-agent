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

import datetime
import os
import importlib.metadata
import json
import logging
import random
import time
import uuid

import httpx

from typing import Final, Literal, Any

from google import genai
from google.cloud import texttospeech, texttospeech_v1beta1
from google.genai import types

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types as asset_types
from mediagent_kit.services.creative_studio_asset_service import CreativeStudioAssetService
from mediagent_kit.utils.retry import ImmediateRetriableAPIError, retry_on_error
from mediagent_kit.utils.auth import get_google_id_token

from mediagent_kit.services.media_generation_service import MediaGenerationService

"""This module provides a service for generating media using various Google Cloud APIs."""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


GEMINI_TEXT_MODEL: Final = "gemini-2.5-flash"


GEMINI_IMAGE_MODEL: Final = "gemini-3.1-flash-image-preview"
GEMINI_IMAGE_ASPECT_RATIOS = Literal[
    "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"
]
GEMINI_IMAGE_ASPECT_RATIO: Final = "16:9"
GEMINI_SIZES = Literal["1K", "2K", "4K"]
GEMINI_SIZE: Final = "1K"


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
VEO_DURATIONS = Literal[4, 6, 8]
VEO_DURATION: Final = 4
VEO_ASPECT_RATIOS = Literal["16:9", "9:16"]
VEO_ASPECT_RATIO: Final = "16:9"
VEO_RESOLUTIONS = Literal["720p", "1080p"]
VEO_RESOLUTION: Final = "720p"

try:
    VERSION = importlib.metadata.version("genmedia-izumi-agent")
except importlib.metadata.PackageNotFoundError:
    try:
        VERSION = importlib.metadata.version("mediagent-kit")
    except importlib.metadata.PackageNotFoundError:
        VERSION = "0.1.0"

_USER_AGENT = f"mediagent-kit/{VERSION} (+https://github.com/GoogleCloudPlatform/genmedia-izumi-agent)"


class CreativeStudioMediaGenerationService(MediaGenerationService):
    """Media generation service subclass for integration with a custom Creative Studio media backend."""

    def __init__(
        self,
        asset_service: CreativeStudioAssetService,
        config: MediagentKitConfig,
        workspace_id: str | int | None = None,
        user_auth_token: str | None = None,
        transient_cache: dict[str, Any] | None = None,
    ):
        self._asset_service = asset_service
        self._config = config
        self.__workspace_id = workspace_id
        self.__user_auth_token = user_auth_token
        self.__transient_cache = transient_cache

    @property
    def _workspace_id(self) -> Any:
        if self.__workspace_id is not None:
            return self.__workspace_id
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("workspace_id") if ctx else None

    @property
    def _user_auth_token(self) -> str | None:
        if self.__user_auth_token is not None:
            return self.__user_auth_token
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("user_auth_token") if ctx else None

    @property
    def _transient_cache(self) -> dict[str, Any]:
        if self.__transient_cache is not None:
            return self.__transient_cache
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("transient_cache") if (ctx and ctx.get("transient_cache") is not None) else {}

    def _cache_asset(self, asset: asset_types.Asset):
        """Caches the generated Asset in the transient cache."""
        if asset and hasattr(asset, "id") and self._transient_cache is not None:
            if hasattr(asset, "to_dict"):
                self._transient_cache[asset.id] = asset.to_dict()
            else:
                self._transient_cache[asset.id] = asset

    def _get_headers(self, user_auth_token: str, url: str) -> dict:
        headers = {
            "X-User-Authorization": f"Bearer {user_auth_token}",
            "Content-Type": "application/json",
        }
        id_token_str = get_google_id_token(url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"
        return headers

    def _wait_for_media_completion(
        self,
        item_id: str,
        headers: dict,
        client: httpx.Client,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> dict:
        """Polls the Creative Studio Backend until a media item is completed or failed.

        Args:
            client: The httpx Client to use for requests.
            item_id: The ID of the media item to poll.
            user_id: The user ID for authentication.
            secret: The internal agent secret for authentication.
            timeout: Maximum time to poll in seconds. Defaults to 300 (5 minutes).
            poll_interval: Time between polls in seconds. Defaults to 5.

        Returns:
            The final media item data from the backend.

        Raises:
            TimeoutError: If the media item does not complete/fail within the timeout.
        """
        url = f"{self._config.creative_studio_backend_url}/api/gallery/item/{item_id}"

        start_time = time.time()
        # Using logger for structured runtime logging
        logger.info(f"[POLLING] Starting polling for media item {item_id} at {url}")

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"[POLLING] Timeout after {timeout}s for item {item_id}")
                raise TimeoutError(
                    f"Media generation timed out after {timeout} seconds."
                )

            try:
                logger.info(f"[POLLING] Checking item {item_id} (elapsed: {int(elapsed)}s)...")
                response = client.get(url, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    if status == "completed":
                        logger.info(f"[POLLING] Item {item_id} completed!")
                        return data
                    elif status == "failed":
                        error_msg = data.get("error_message") or "Unknown backend error"
                        logger.error(f"[POLLING] Item {item_id} FAILED: {error_msg}")
                        return data
                    
                    logger.info(f"[POLLING] Item {item_id} status: {status}. Waiting {poll_interval}s...")
                elif response.status_code == 404:
                    logger.error(f"[POLLING] Error: Media item {item_id} not found (404).")
                    return {"status": "failed", "error_message": f"Media item {item_id} not found."}
                else:
                    logger.warning(f"[POLLING] Warning: Unexpected response {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"[POLLING] Exception during poll: {e}")

            time.sleep(poll_interval)

    def _call_creative_studio_audio_generation(
        self,
        model: str,
        prompt: str,
        file_name: str,
        voice_name: TTS_VOICES | None = None,
        language_code: str | None = None,
        negative_prompt: str | None = None,
    ) -> asset_types.Asset:
        """Calls the Lyria API and returns the generated music as bytes."""
        if not self._workspace_id or not self._user_auth_token:
            raise ValueError("workspace_id and user_auth_token must be provided at initialization")
            
        user_auth_header = f"Bearer {self._user_auth_token}"
        
        # API Request variables
        url = f"{self._config.creative_studio_backend_url}/api/audios/generate"

        creative_studio_headers = self._get_headers(self._user_auth_token, url)
        if voice_name:
            creative_studio_audio_dto = {
                "prompt": prompt,
                "workspaceId": self._workspace_id,
                "model": model,
                "fileName": file_name,
                "sampleCount": 1,
                "languageCode": "en-US",
                "voiceName": voice_name,

            }
        else:
            creative_studio_audio_dto = {
                "prompt": prompt,
                "workspaceId": self._workspace_id,
                "model": model,
                "fileName": file_name,
                "negativePrompt": negative_prompt,
                "sampleCount": 1,
                "seed": random.randint(0, 2**32 - 1)
            }

        try:
            with httpx.Client() as client:
                response = client.post(
                    url, json=creative_studio_audio_dto, headers=creative_studio_headers, timeout=60.0
                )

                response.raise_for_status()

                data = response.json()
                logger.info(f"[AUDIO_GEN] Backend response status {response.status_code}: {json.dumps(data)}")

                # The backend returns a MediaItemResponse, which includes an 'id'
                item_id = data.get("id")
                if not item_id:
                    logger.error("No item ID found in backend response.")
                    raise Exception("No item ID found in backend response.")

                final_item = self._wait_for_media_completion(
                    item_id=item_id,
                    headers=creative_studio_headers,
                    client=client,
                    timeout=180,  # 3 minutes for images
                )
                
                status = final_item.get("status")
                if status == "completed":
                    gcs_uris = final_item.get("gcsUris", [])
                    gcs_uri = gcs_uris[0] if len(gcs_uris) > 0 else ""
                    
                    speech_generate_config = None
                    music_generate_config = None
                    if voice_name:
                        speech_generate_config = asset_types.SpeechGenerateConfig(
                            model=model,
                            spoken_text=prompt, # TODO: We use the prompt as the text generation variable for now, we may need to change this
                            voice=voice_name,
                        )
                    else:
                        music_generate_config = asset_types.MusicGenerateConfig(
                            model=model,
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                        )
                    
                    duration_seconds = final_item.get("durationSeconds")
                    if duration_seconds is None and gcs_uri:
                        try:
                            logger.info(f"durationSeconds missing in backend response for audio {item_id}. Probing GCS file: {gcs_uri}")
                            audio_bytes = self._asset_service._download_from_gcs(gcs_uri)
                            from mediagent_kit.utils.media_tools import get_media_metadata_from_blob
                            ext = gcs_uri.split(".")[-1] if "." in gcs_uri else "wav"
                            metadata = get_media_metadata_from_blob(audio_bytes, ext)
                            duration_seconds = metadata.duration
                            logger.info(f"Successfully probed audio duration: {duration_seconds}s")
                        except Exception as probe_err:
                            logger.error(f"Failed to probe audio duration from GCS: {probe_err}")

                    asset = self._asset_service.to_asset(
                        asset_id=item_id,
                        workspace_id=str(self._workspace_id),
                        file_name=file_name,
                        gcs_uri=gcs_uri,
                        created_at=datetime.datetime.now(),
                        mime_type="audio/wav",
                        music_generate_config=music_generate_config,
                        speech_generate_config=speech_generate_config,
                        item_type="media_item",
                        duration_seconds=duration_seconds,
                    )
                    self._cache_asset(asset)
                    return asset
                else:
                    error_msg = final_item.get("errorMessage") or "Unknown error"
                    logger.error(f"Error generating audio: {error_msg}")
                    raise Exception(error_msg)
                
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error occurred while calling Creative Studio: {exc.response.status_code} - {exc.response.text}")
            raise exc
        except Exception as exc:
            logger.error(f"Unexpected error occurred while calling Creative Studio: {exc}")
            raise exc

    def _call_creative_studio_image_generation(
        self,
        *,
        model: str,
        prompt: str,
        file_name: str,
        aspect_ratio: str,
        image_size: str,
        reference_image_filenames: list[str] = [],
    ) -> asset_types.CreativeStudioAsset:
        """Helper to orchestrate Creative Studio image generation API calls and poll for completion."""
        if not self._workspace_id or not self._user_auth_token:
            raise ValueError("workspace_id and user_auth_token must be provided at initialization")


        # 1. Gather reference assets if provided
        reference_assets = []
        source_asset_ids = []
        source_media_items = []
        if reference_image_filenames:
            reference_assets = [
                self._asset_service.get_asset_by_file_name(ref_name)
                for ref_name in reference_image_filenames
            ]
            for asset in reference_assets:
                if not asset:
                    logger.warning("Reference asset not found, skipping...")
                    continue
                if asset.item_type == "source_asset":
                    source_asset_ids.append(asset.id)
                elif asset.item_type == "media_item":
                    source_media_items.append({
                        "mediaItemId": asset.id,
                        "mediaIndex": 0,
                        "role": "input",
                    })
                else:
                    logger.warning(
                        f"Asset {asset.file_name} is not a supported asset type for image generation {asset.item_type}."
                    )

        # 2. Setup endpoint, headers and DTO payload
        url = f"{self._config.creative_studio_backend_url}/api/images/generate-images"
        headers = self._get_headers(self._user_auth_token, url)
        creative_studio_image_dto = {
            "prompt": prompt,
            "workspaceId": self._workspace_id,
            "generationModel": model,
            "aspectRatio": aspect_ratio,
            "numberOfMedia": 1,
            "resolution": image_size,
            "fileName": file_name,
        }

        if source_asset_ids:
            creative_studio_image_dto["sourceAssetIds"] = source_asset_ids
        if source_media_items:
            creative_studio_image_dto["sourceMediaItems"] = source_media_items

        # 3. Call endpoint and await completion
        try:
            with httpx.Client() as client:
                response = client.post(
                    url, json=creative_studio_image_dto, headers=headers, timeout=60.0
                )
                response.raise_for_status()

                data = response.json()
                logger.info(f"[IMAGE_GEN] Backend response status {response.status_code}: {json.dumps(data)}")

                item_id = data.get("id")
                if not item_id:
                    logger.error("No item ID found in backend response.")
                    raise Exception("No item ID found in backend response.")

                final_item = self._wait_for_media_completion(
                    item_id=item_id,
                    headers=headers,
                    client=client,
                    timeout=180,
                )

                status = final_item.get("status")
                if status == "completed":
                    gcs_uris = final_item.get("gcsUris", [])
                    gcs_uri = gcs_uris[0] if len(gcs_uris) > 0 else ""

                    image_generate_config = asset_types.ImageGenerateConfig(
                        model=model,
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        reference_images=reference_assets if reference_assets else None,
                    )

                    asset = self._asset_service.to_asset(
                        asset_id=item_id,
                        workspace_id=str(self._workspace_id),
                        file_name=file_name,
                        gcs_uri=gcs_uri,
                        created_at=datetime.datetime.now(),
                        mime_type="image/png",
                        image_generate_config=image_generate_config,
                        item_type="media_item",
                    )
                    self._cache_asset(asset)
                    return asset
                else:
                    error_msg = final_item.get("errorMessage") or "Unknown error"
                    logger.error(f"Error generating image: {error_msg}")
                    raise Exception(error_msg)

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"HTTP error occurred while calling Creative Studio: {exc.response.status_code} - {exc.response.text}"
            )
            raise exc
        except Exception as exc:
            logger.error(f"Unexpected error occurred while calling Creative Studio: {exc}")
            raise exc

    @retry_on_error()
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
                }
            )
        )
        
        asset = self._call_creative_studio_audio_generation(
            model=model,
            prompt=prompt,
            file_name=file_name,
            negative_prompt=negative_prompt,
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
    ) -> asset_types.CreativeStudioAsset:
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

        return self._call_creative_studio_image_generation(
            model=model,
            prompt=prompt,
            file_name=file_name,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
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

        reference_assets = [
            self._asset_service.get_asset_by_file_name(ref_name)
            for ref_name in reference_image_filenames
        ]
        contents = [
            types.Part.from_uri(
                file_uri=asset.current.gcs_uri, mime_type=asset.mime_type
            )
            for asset in reference_assets
        ]

        contents.append(types.Part.from_text(text=prompt))

        try:
            client = self._get_genai_client()
            response = self._generate_gemini_text_content(
                client=client, model=model, contents=contents
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Gemini generation failed: {e}") from e

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
                    reference_images=reference_assets,
                )
                asset = self._asset_service.to_asset(
                    asset_id=str(uuid.uuid4()),
                    workspace_id=str(self._workspace_id) if self._workspace_id else user_id,
                    file_name=file_name,
                    gcs_uri="",
                    created_at=datetime.datetime.now(),
                    text_generate_config=text_generate_config,
                )
                asset._content = generated_text.encode()
                self._cache_asset(asset)
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
        image_size: GEMINI_SIZES = GEMINI_SIZE,
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

        return self._call_creative_studio_image_generation(
            model=model,
            prompt=prompt,
            file_name=file_name,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            reference_image_filenames=reference_image_filenames,
        )

    # TODO: Check for Creative studio plausability
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

        asset = self._call_creative_studio_audio_generation(
            model=model,
            prompt=text,
            file_name=file_name,
            language_code=language_code,
            voice_name=voice_name,
        )
        
        logger.info(f"Successfully generated music: {file_name}")
        return asset


    # TODO:It's Not available in Creative studio, 
    # After implementing on creative Studio come back to integrate this
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


    # TODO: Make with Creative Studio
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

        # 1. Gather reference assets if provided and build DTO payload
        creative_studio_video_dto = {
            "prompt": prompt,
            "workspaceId": self._workspace_id,
            "generationModel": model,
            "aspectRatio": aspect_ratio,
            "numberOfMedia": 1,
            "durationSeconds": duration_seconds,
            "generateAudio": generate_audio,
            "fileName": file_name,
        }
        first_frame_asset = None
        last_frame_asset = None

        if method == "image_to_video":
            source_media_items = []
            if first_frame_filename:
                first_frame_asset = self._asset_service.get_asset_by_file_name(first_frame_filename)

                if first_frame_asset and first_frame_asset.item_type == "source_asset":
                    creative_studio_video_dto["startImageAssetId"] = first_frame_asset.id
                elif first_frame_asset and first_frame_asset.item_type == "media_item":
                    source_media_items.append({
                        "mediaItemId": first_frame_asset.id,
                        "mediaIndex": 0,
                        "role": "start_frame",
                    })
                else:
                    logger.warning(
                        f"Asset {first_frame_filename} not found or unsupported."
                    )

            if last_frame_filename:
                last_frame_asset = self._asset_service.get_asset_by_file_name(last_frame_filename)

                if last_frame_asset and last_frame_asset.item_type == "source_asset":
                    creative_studio_video_dto["endImageAssetId"] = last_frame_asset.id
                elif last_frame_asset and last_frame_asset.item_type == "media_item":
                    source_media_items.append({
                        "mediaItemId": last_frame_asset.id,
                        "mediaIndex": 0,
                        "role": "end_frame",
                    })
                else:
                    logger.warning(
                        f"Asset {last_frame_filename} not found or unsupported."
                    )

            if source_media_items:
                creative_studio_video_dto["sourceMediaItems"] = source_media_items

        elif method == "reference_to_video":
            source_asset_ids = []
            source_media_items = []
            if reference_image_filenames:
                reference_assets = [
                    self._asset_service.get_asset_by_file_name(ref_name)
                    for ref_name in reference_image_filenames
                ]
                for asset in reference_assets:
                    if not asset:
                        continue
                    if asset.item_type == "source_asset":
                        source_asset_ids.append(asset.id)
                    elif asset.item_type == "media_item":
                        source_media_items.append({
                            "mediaItemId": asset.id,
                            "mediaIndex": 0,
                            "role": "image_reference_asset",
                        })
                    else:
                        logger.warning(
                            f"Asset {asset.file_name} is not a supported asset type for video generation {asset.item_type}."
                        )

            if source_asset_ids:
                creative_studio_video_dto["sourceVideoAssetIds"] = source_asset_ids
            if source_media_items:
                creative_studio_video_dto["sourceMediaItems"] = source_media_items
        
        # 2. Setup endpoint, headers
        url = f"{self._config.creative_studio_backend_url}/api/videos/generate-videos"
        headers = self._get_headers(self._user_auth_token, url)
        
        # 3. Call endpoint and await completion
        try:
            with httpx.Client() as client:
                response = client.post(
                    url, json=creative_studio_video_dto, headers=headers, timeout=60.0
                )
                response.raise_for_status()

                data = response.json()
                logger.info(f"[VIDEO_GEN] Backend response status {response.status_code}: {json.dumps(data)}")

                item_id = data.get("id")
                if not item_id:
                    logger.error("No item ID found in backend response.")
                    raise Exception("No item ID found in backend response.")

                final_item = self._wait_for_media_completion(
                    item_id=item_id,
                    headers=headers,
                    client=client,
                    timeout=600,
                )

                status = final_item.get("status")
                if status == "completed":
                    gcs_uris = final_item.get("gcsUris", [])
                    gcs_uri = gcs_uris[0] if len(gcs_uris) > 0 else ""

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

                    return self._asset_service.to_asset(
                        asset_id=item_id,
                        workspace_id=self._workspace_id,
                        file_name=file_name,
                        gcs_uri=gcs_uri,
                        created_at=datetime.datetime.now(), # We can replace this with createdAt inside the final item
                        mime_type="video/mp4",
                        video_generate_config=video_generate_config,
                        item_type="media_item",
                        duration_seconds=final_item.get("durationSeconds") or duration_seconds,
                    )
                else:
                    error_msg = final_item.get("errorMessage") or "Unknown error"
                    logger.error(f"Error generating video: {error_msg}")
                    raise Exception(error_msg)

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"HTTP error occurred while calling Creative Studio: {exc.response.status_code} - {exc.response.text}"
            )
            raise exc
        except Exception as exc:
            logger.error(f"Unexpected error occurred while calling Creative Studio: {exc}")
            raise exc
