# Copyright 2026 Google LLC
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

"""Creative Studio implementation of MediaGenerationServiceInterface."""

import asyncio
import datetime
import json
import logging
import random
import time
from typing import Any, Optional

import httpx
from google import genai

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.errors import (
    AuthenticationError,
    BackendError,
    TimeoutError,
    ValidationError,
)
from mediagent_kit.services.interfaces import MediaGenerationServiceInterface
from mediagent_kit.services.types.common import (
    AssetRef,
    GeneratedAsset,
    GenerationMetadata,
)
from mediagent_kit.utils.auth import get_google_id_token

logger = logging.getLogger(__name__)


class CSMediaGenerationService(MediaGenerationServiceInterface):
    """Creative Studio implementation of MediaGenerationServiceInterface."""

    def __init__(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
        config: MediagentKitConfig | None = None,
    ):
        self._workspace_id = workspace_id
        self._user_auth_token = user_auth_token
        self._config = config or MediagentKitConfig()

    def _get_workspace_id(self, explicit: str | None = None) -> str:
        from mediagent_kit.utils.context import get_request_context

        ctx = get_request_context() or {}
        ws_id = explicit or ctx.get("workspace_id") or self._workspace_id
        if not ws_id or not str(ws_id).isdigit():
            raise ValidationError(
                f"Invalid workspace_id: '{ws_id}'. Workspace ID must be a non-empty numeric string."
            )
        return str(ws_id)

    def _get_user_auth_token(self, explicit: str | None = None) -> str:
        if explicit:
            return str(explicit)
        from mediagent_kit.utils.context import get_request_context

        ctx = get_request_context() or {}
        token_key = self._config.cs_user_auth_token_key or "user_auth_token"
        token = (
            ctx.get(token_key) or ctx.get("user_auth_token") or self._user_auth_token
        )
        if not token:
            raise AuthenticationError(
                "user_auth_token is required for Creative Studio media generation."
            )
        return str(token)

    def _get_headers(self, user_auth_token: str, url: str) -> dict[str, str]:
        headers = {
            "X-User-Authorization": f"Bearer {user_auth_token}",
            "Content-Type": "application/json",
        }
        id_token_str = get_google_id_token(url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"
        return headers

    async def _wait_for_media_completion(
        self,
        client: httpx.AsyncClient,
        item_id: str | int,
        headers: dict[str, str],
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """Async polling loop awaiting CS gallery item completion."""
        backend_url = self._config.cs_backend_url or "http://backend:8080"
        poll_url = f"{backend_url}/api/gallery/item/{item_id}"

        start_time = time.time()
        curr_interval = poll_interval

        while time.time() - start_time < timeout:
            resp = await client.get(poll_url, headers=headers, timeout=30.0)
            if resp.status_code == 401:
                raise AuthenticationError(
                    f"Unauthorized polling CS gallery item {item_id}"
                )
            if resp.status_code >= 500:
                raise BackendError(
                    f"Backend error polling item {item_id}: {resp.status_code}"
                )
            resp.raise_for_status()

            item_data = resp.json()
            status = item_data.get("status")
            if status in ("completed", "failed"):
                return item_data

            await asyncio.sleep(curr_interval)
            curr_interval = min(curr_interval * 1.5, 10.0)

        raise TimeoutError(
            f"Media generation timed out for item {item_id} after {timeout}s"
        )

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """Extracts the visible response text from a Gemini response.

        Mirrors the legacy MediaGenerationService behavior: iterate the
        candidate parts and keep only NON-thought parts. Relying on the
        SDK's ``response.text`` convenience accessor is fragile for
        thinking models (2.5+/3.x) because thought parts can pollute the
        output and break downstream JSON parsing (this is what caused
        parameter extraction to fail in Creative Studio mode and silently
        route campaigns into templated instead of creative mode).
        """
        candidates = getattr(response, "candidates", None)
        if candidates:
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) if content else None
            if parts:
                texts = [
                    p.text
                    for p in parts
                    if getattr(p, "text", None) and not getattr(p, "thought", False)
                ]
                if texts:
                    return "".join(texts)
        # Fall back to the convenience accessor (may raise on blocked
        # responses; callers treat that as a generation failure).
        return getattr(response, "text", "") or ""

    async def generate_text(
        self,
        workspace_id: str,
        prompt: str,
        reference_assets: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Generates text inline using Gemini model (Vertex AI).

        Retries a few times on transient failures and empty responses.
        Without this, a single flaky/empty Vertex response would bubble up
        to the caller as a hard failure -- e.g. parameter extraction would
        fall through to its "intelligent fallback" and silently pick a
        template, routing a creative brief into templated mode.
        """
        model = self._config.models.get("text", {}).get("default", "gemini-2.5-flash")
        logger.info(f"CSMediaGenerationService: Generating text with model {model}...")

        client = genai.Client(
            vertexai=True,
            project=self._config.google_cloud_project,
            location=self._config.google_cloud_location or "us-central1",
        )

        max_attempts = 3
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=prompt,
                )
                text = self._extract_response_text(response)
                if text.strip():
                    return text
                logger.warning(
                    "CSMediaGenerationService.generate_text: empty response on "
                    "attempt %d/%d; retrying.",
                    attempt + 1,
                    max_attempts,
                )
            except Exception as e:  # noqa: BLE001 - retry any transient error
                last_error = e
                logger.warning(
                    "CSMediaGenerationService.generate_text: error on attempt "
                    "%d/%d: %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
            if attempt < max_attempts - 1:
                await asyncio.sleep(1.0 * (2**attempt))

        if last_error is not None:
            raise BackendError(
                f"Text generation failed after {max_attempts} attempts: {last_error}"
            ) from last_error
        # All attempts returned empty text.
        return ""

    async def generate_image(
        self,
        workspace_id: str,
        prompt: str,
        generation_model: str,
        aspect_ratio: str,
        resolution: str,
        file_name: str,
        reference_assets: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates an image via CS POST /api/images/generate-images and polls for completion."""
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/images/generate-images"
        headers = self._get_headers(token, url)

        source_asset_ids = []
        source_media_items = []
        if reference_assets:
            for ref in reference_assets:
                if ref.asset_type == "uploaded":
                    source_asset_ids.append(int(ref.id))
                elif ref.asset_type == "generated":
                    source_media_items.append(
                        {"mediaItemId": int(ref.id), "mediaIndex": 0, "role": "input"}
                    )

        payload: dict[str, Any] = {
            "workspaceId": int(ws_id),
            "prompt": prompt,
            "generationModel": generation_model,
            "aspectRatio": aspect_ratio,
            "resolution": resolution,
            "fileName": file_name,
            "numberOfMedia": 1,
        }
        if source_asset_ids:
            payload["sourceAssetIds"] = source_asset_ids
        if source_media_items:
            payload["sourceMediaItems"] = source_media_items

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized calling CS image generation")
            if resp.status_code == 422:
                raise ValidationError(
                    f"CS image generation validation error: {resp.text}"
                )
            resp.raise_for_status()

            item_id = resp.json().get("id")
            if not item_id:
                raise BackendError("No item ID returned from CS image generation")

            final_item = await self._wait_for_media_completion(
                client, item_id, headers, timeout=300
            )

            status = final_item.get("status", "completed")
            gcs_uris = final_item.get("gcsUris", [])
            gcs_uri = gcs_uris[0] if gcs_uris else ""
            error_msg = final_item.get("errorMessage") if status == "failed" else None

            return GeneratedAsset(
                id=str(item_id),
                workspace_id=str(ws_id),
                file_name=file_name,
                gcs_uri=gcs_uri,
                mime_type="image/png",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                status=status,
                error_message=error_msg,
                generation_metadata=GenerationMetadata(
                    source="creative_studio",
                    model=generation_model,
                    prompt=prompt,
                    raw=final_item,
                ),
            )

    async def generate_video(
        self,
        workspace_id: str,
        prompt: str,
        generation_model: str,
        aspect_ratio: str,
        duration_seconds: int,
        file_name: str,
        start_image: Optional[AssetRef] = None,
        end_image: Optional[AssetRef] = None,
        reference_videos: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates a video via CS POST /api/videos/generate-videos and polls for completion."""
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/videos/generate-videos"
        headers = self._get_headers(token, url)

        payload: dict[str, Any] = {
            "workspaceId": int(ws_id),
            "prompt": prompt,
            "generationModel": generation_model,
            "aspectRatio": aspect_ratio,
            "durationSeconds": duration_seconds,
            "fileName": file_name,
            "numberOfMedia": 1,
        }
        if start_image:
            payload["startImageAssetId"] = {
                "id": int(start_image.id),
                "type": (
                    "source_asset"
                    if start_image.asset_type == "uploaded"
                    else "media_item"
                ),
            }
        if end_image:
            payload["endImageAssetId"] = {
                "id": int(end_image.id),
                "type": (
                    "source_asset"
                    if end_image.asset_type == "uploaded"
                    else "media_item"
                ),
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized calling CS video generation")
            if resp.status_code == 422:
                raise ValidationError(
                    f"CS video generation validation error: {resp.text}"
                )
            resp.raise_for_status()

            item_id = resp.json().get("id")
            if not item_id:
                raise BackendError("No item ID returned from CS video generation")

            final_item = await self._wait_for_media_completion(
                client, item_id, headers, timeout=600, poll_interval=3.0
            )

            status = final_item.get("status", "completed")
            gcs_uris = final_item.get("gcsUris", [])
            gcs_uri = gcs_uris[0] if gcs_uris else ""
            error_msg = final_item.get("errorMessage") if status == "failed" else None

            return GeneratedAsset(
                id=str(item_id),
                workspace_id=str(ws_id),
                file_name=file_name,
                gcs_uri=gcs_uri,
                mime_type="video/mp4",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                status=status,
                duration_seconds=float(
                    final_item.get("durationSeconds") or duration_seconds
                ),
                error_message=error_msg,
                generation_metadata=GenerationMetadata(
                    source="creative_studio",
                    model=generation_model,
                    prompt=prompt,
                    raw=final_item,
                ),
            )

    async def generate_speech(
        self,
        workspace_id: str,
        text: str,
        voice_name: str,
        language_code: str,
        file_name: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates TTS speech via CS POST /api/audios/generate and polls for completion."""
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/audios/generate"
        headers = self._get_headers(token, url)

        model = self._config.models.get("tts", {}).get("default", "gemini-2.5-pro-tts")
        payload = {
            "workspaceId": int(ws_id),
            "prompt": text,
            "model": model,
            "fileName": file_name,
            "voiceName": voice_name,
            "languageCode": language_code,
            "sampleCount": 1,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized calling CS speech generation")
            if resp.status_code == 422:
                raise ValidationError(
                    f"CS speech generation validation error: {resp.text}"
                )
            resp.raise_for_status()

            item_id = resp.json().get("id")
            if not item_id:
                raise BackendError("No item ID returned from CS speech generation")

            final_item = await self._wait_for_media_completion(
                client, item_id, headers, timeout=300
            )

            status = final_item.get("status", "completed")
            gcs_uris = final_item.get("gcsUris", [])
            gcs_uri = gcs_uris[0] if gcs_uris else ""
            error_msg = final_item.get("errorMessage") if status == "failed" else None

            return GeneratedAsset(
                id=str(item_id),
                workspace_id=str(ws_id),
                file_name=file_name,
                gcs_uri=gcs_uri,
                mime_type="audio/mp3",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                status=status,
                duration_seconds=float(final_item.get("durationSeconds") or 0.0),
                error_message=error_msg,
                generation_metadata=GenerationMetadata(
                    source="creative_studio",
                    model=model,
                    prompt=text,
                    raw=final_item,
                ),
            )

    async def generate_music(
        self,
        workspace_id: str,
        prompt: str,
        model: str,
        duration_seconds: int,
        file_name: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates music via CS POST /api/audios/generate and polls for completion."""
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/audios/generate"
        headers = self._get_headers(token, url)

        music_model = model or "lyria-002"
        if music_model == "lyria":
            music_model = "lyria-002"
        payload = {
            "workspaceId": int(ws_id),
            "prompt": prompt,
            "model": music_model,
            "fileName": file_name,
            "sampleCount": 1,
            "seed": random.randint(0, 2**32 - 1),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized calling CS music generation")
            if resp.status_code == 422:
                raise ValidationError(
                    f"CS music generation validation error: {resp.text}"
                )
            resp.raise_for_status()

            item_id = resp.json().get("id")
            if not item_id:
                raise BackendError("No item ID returned from CS music generation")

            final_item = await self._wait_for_media_completion(
                client, item_id, headers, timeout=300
            )

            status = final_item.get("status", "completed")
            gcs_uris = final_item.get("gcsUris", [])
            gcs_uri = gcs_uris[0] if gcs_uris else ""
            error_msg = final_item.get("errorMessage") if status == "failed" else None

            return GeneratedAsset(
                id=str(item_id),
                workspace_id=str(ws_id),
                file_name=file_name,
                gcs_uri=gcs_uri,
                mime_type="audio/mp3",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                status=status,
                duration_seconds=float(
                    final_item.get("durationSeconds") or duration_seconds
                ),
                error_message=error_msg,
                generation_metadata=GenerationMetadata(
                    source="creative_studio",
                    model=music_model,
                    prompt=prompt,
                    raw=final_item,
                ),
            )
