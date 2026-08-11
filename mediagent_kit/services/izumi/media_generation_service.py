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

"""Native (Izumi) implementation of MediaGenerationServiceInterface.

This is the non-Creative-Studio implementation of the unified media
generation interface. It adapts the legacy, synchronous
``MediaGenerationService`` (which returns ``Asset`` objects) to the unified
async contract (which returns ``str`` for text and ``GeneratedAsset`` for
media).

Why this exists: ads_x (and other agents) were migrated to call the unified
``MediaGenerationServiceInterface`` (``generate_text``/``generate_image``/
``generate_video``/``generate_speech``/``generate_music``). The Creative
Studio backend has ``CSMediaGenerationService``; this is the native
counterpart so the open-source, non-CS path works too.

Mapping notes:
  * Unified ``workspace_id`` maps onto the legacy ``user_id`` (native Izumi
    is single-tenant; the workspace scope is the user scope).
  * Unified ``reference_assets: list[AssetRef]`` / ``start_image: AssetRef``
    are resolved to legacy filenames via the asset service (the legacy
    generators take ``reference_image_filenames`` / ``first_frame_filename``).
  * Legacy generators are blocking (Veo polls internally), so every returned
    ``GeneratedAsset`` is already terminal (``status="completed"``), honoring
    the interface contract.
"""

import asyncio
import logging
import uuid
from typing import Any, Optional

from mediagent_kit.services.interfaces import MediaGenerationServiceInterface
from mediagent_kit.services.types.common import (
    AssetRef,
    GeneratedAsset,
    GenerationMetadata,
)

logger = logging.getLogger(__name__)


class IzumiMediaGenerationService(MediaGenerationServiceInterface):
    """Adapts the legacy ``MediaGenerationService`` to the unified interface."""

    def __init__(self, sync_media_service: Any, asset_service: Any):
        """
        Args:
            sync_media_service: the legacy ``MediaGenerationService`` instance.
            asset_service: the legacy ``AssetService`` instance, used to
                resolve ``AssetRef`` inputs to filenames and to read generated
                text back out.
        """
        self._media = sync_media_service
        self._assets = asset_service

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _resolve_ref_to_filename(self, ref: Optional[AssetRef]) -> Optional[str]:
        """Resolves an AssetRef to the legacy filename the generators expect."""
        if ref is None:
            return None
        asset = self._assets.get_asset_by_id(ref.id)
        if asset is None:
            logger.warning(
                "IzumiMediaGenerationService: could not resolve AssetRef id=%s "
                "to a filename; ignoring it.",
                ref.id,
            )
            return None
        return asset.file_name

    def _resolve_refs_to_filenames(self, refs: Optional[list[AssetRef]]) -> list[str]:
        if not refs:
            return []
        names = [self._resolve_ref_to_filename(r) for r in refs]
        return [n for n in names if n]

    @staticmethod
    def _to_generated_asset(
        asset: Any,
        *,
        workspace_id: str,
        mime_type_fallback: str,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> GeneratedAsset:
        """Maps a legacy ``Asset`` to a terminal ``GeneratedAsset``."""
        current = getattr(asset, "current", None)
        gcs_uri = getattr(current, "gcs_uri", "") if current else ""
        created_at = getattr(current, "create_time", None) if current else None
        duration = getattr(current, "duration_seconds", None) if current else None
        if created_at is None:
            from datetime import datetime, timezone

            created_at = datetime.now(timezone.utc)
        return GeneratedAsset(
            id=str(asset.id),
            workspace_id=workspace_id,
            file_name=asset.file_name,
            gcs_uri=gcs_uri,
            mime_type=getattr(asset, "mime_type", None) or mime_type_fallback,
            created_at=created_at,
            status="completed",
            duration_seconds=float(duration) if duration is not None else None,
            error_message=None,
            generation_metadata=GenerationMetadata(
                source="izumi", model=model, prompt=prompt
            ),
        )

    # ------------------------------------------------------------------ #
    # Interface methods
    # ------------------------------------------------------------------ #

    async def generate_text(
        self,
        workspace_id: str,
        prompt: str,
        reference_assets: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Generates text and returns it inline as a ``str``.

        The legacy ``generate_text_with_gemini`` persists the text as an
        asset and returns an ``Asset``; we read the blob back out to satisfy
        the unified contract (text is not persisted at the interface level).
        """
        reference_image_filenames = self._resolve_refs_to_filenames(reference_assets)
        # Synthetic file name: the legacy method persists a text asset; the
        # unified contract discards it, so the name is internal-only.
        file_name = f"gen_text_{uuid.uuid4().hex[:12]}.txt"

        asset = await asyncio.to_thread(
            self._media.generate_text_with_gemini,
            user_id=workspace_id,
            file_name=file_name,
            prompt=prompt,
            reference_image_filenames=reference_image_filenames,
        )
        blob = await asyncio.to_thread(self._assets.get_asset_blob, asset.id)
        if blob is None or blob.content is None:
            return ""
        return blob.content.decode("utf-8")

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
        """Generates a still image via the native Gemini image model.

        ``resolution`` is accepted for interface parity; the Gemini image
        generator does not take an explicit resolution, so it is ignored
        here (Imagen would use it, but ads_x uses the Gemini image model).
        """
        reference_image_filenames = self._resolve_refs_to_filenames(reference_assets)
        asset = await asyncio.to_thread(
            self._media.generate_image_with_gemini,
            user_id=workspace_id,
            file_name=file_name,
            prompt=prompt,
            reference_image_filenames=reference_image_filenames,
            aspect_ratio=aspect_ratio,
            model=generation_model,
        )
        return self._to_generated_asset(
            asset,
            workspace_id=workspace_id,
            mime_type_fallback="image/png",
            model=generation_model,
            prompt=prompt,
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
        """Generates a video via native Veo (image-to-video when a start
        frame is provided)."""
        first_frame = self._resolve_ref_to_filename(start_image)
        last_frame = self._resolve_ref_to_filename(end_image)
        asset = await asyncio.to_thread(
            self._media.generate_video_with_veo,
            user_id=workspace_id,
            file_name=file_name,
            prompt=prompt,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            first_frame_filename=first_frame,
            last_frame_filename=last_frame,
            method="image_to_video",
            model=generation_model,
        )
        return self._to_generated_asset(
            asset,
            workspace_id=workspace_id,
            mime_type_fallback="video/mp4",
            model=generation_model,
            prompt=prompt,
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
        """Generates single-speaker TTS via the native speech generator."""
        asset = await asyncio.to_thread(
            self._media.generate_speech_single_speaker,
            user_id=workspace_id,
            file_name=file_name,
            text=text,
            voice_name=voice_name,
            language_code=language_code,
        )
        return self._to_generated_asset(
            asset,
            workspace_id=workspace_id,
            mime_type_fallback="audio/wav",
            prompt=text,
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
        """Generates background music via native Lyria.

        Note: the legacy Lyria generator does not take a duration; it is
        accepted here for interface parity and ignored by the native model.
        """
        asset = await asyncio.to_thread(
            self._media.generate_music_with_lyria,
            user_id=workspace_id,
            file_name=file_name,
            prompt=prompt,
            model=model,
        )
        return self._to_generated_asset(
            asset,
            workspace_id=workspace_id,
            mime_type_fallback="audio/mpeg",
            model=model,
            prompt=prompt,
        )
