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

"""Asynchronous service wrappers around MediagentKit services."""

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

from mediagent_kit.services.interfaces import (
    AssetServiceInterface,
    HtmlCanvasServiceInterface,
    MediaGenerationServiceInterface,
)

from mediagent_kit.services import types as asset_types
from mediagent_kit.services.creative_studio.cs_storyboard_service import (
    CSStoryboardService,
)
from mediagent_kit.services.creative_studio.cs_timeline_service import (
    CSTimelineService,
)
from mediagent_kit.services.types.common import (
    AssetRef,
    AssetType,
    GeneratedAsset,
    UploadedAsset,
)
from mediagent_kit.services.types.timeline import VideoTimeline

if TYPE_CHECKING:
    from mediagent_kit.services import (
        AssetService,
        CanvasService,
        JobService,
        MediaGenerationService,
        VideoStitchingService,
    )


class AsyncAssetService:
    def __init__(self, sync_service: Any):
        self._sync_service = sync_service
        self._interface: AssetServiceInterface | None = None

    def _require_interface(self) -> AssetServiceInterface:
        """Resolves the unified asset interface.

        Creative Studio's ``CSAssetService`` already implements the interface
        and is used directly. The native legacy ``AssetService`` does not, so
        it is adapted via ``IzumiAssetService``. The legacy passthrough methods
        below intentionally keep calling ``self._sync_service`` directly, so
        this wrapper still serves legacy callers (REST API, session service)
        unchanged.
        """
        if isinstance(self._sync_service, AssetServiceInterface):
            return self._sync_service
        if self._interface is None:
            from mediagent_kit.services.izumi.asset_service import IzumiAssetService

            self._interface = IzumiAssetService(self._sync_service)
        return self._interface

    async def upload_asset(
        self,
        workspace_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str,
        scope: str = "private",
        idempotency_key: str | None = None,
    ) -> UploadedAsset:
        return await self._require_interface().upload_asset(
            workspace_id=workspace_id,
            file_name=file_name,
            blob=blob,
            mime_type=mime_type,
            scope=scope,
            idempotency_key=idempotency_key,
        )

    async def get_asset(self, ref: AssetRef) -> UploadedAsset | GeneratedAsset | None:
        return await self._require_interface().get_asset(ref)

    async def search_assets(
        self,
        workspace_id: str,
        query: str | None = None,
        asset_type: AssetType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UploadedAsset | GeneratedAsset]:
        return await self._require_interface().search_assets(
            workspace_id=workspace_id,
            query=query,
            asset_type=asset_type,
            limit=limit,
            offset=offset,
        )

    async def download_asset_bytes(self, ref: AssetRef) -> bytes:
        return await self._require_interface().download_asset_bytes(ref)

    async def delete_asset(self, ref: AssetRef) -> None:
        return await self._require_interface().delete_asset(ref)

    async def save_asset(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(self._sync_service.save_asset, **kwargs)

    async def save_asset_from_file(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.save_asset_from_file, **kwargs
        )

    async def get_asset_by_id(
        self, asset_id: str, **kwargs: Any
    ) -> asset_types.Asset | None:
        return await asyncio.to_thread(
            self._sync_service.get_asset_by_id, asset_id, **kwargs
        )

    async def get_asset_by_file_name(
        self, user_id: str, file_name: str
    ) -> asset_types.Asset | None:
        return await asyncio.to_thread(
            self._sync_service.get_asset_by_file_name, user_id, file_name
        )

    async def get_asset_blob(
        self, asset_id: str, version: int | None = None
    ) -> asset_types.AssetBlob:
        return await asyncio.to_thread(
            self._sync_service.get_asset_blob, asset_id, version
        )

    async def list_assets(self, user_id: str) -> list[asset_types.Asset]:
        return await asyncio.to_thread(self._sync_service.list_assets, user_id)

    async def update_asset(
        self, asset_id: str, **kwargs: Any
    ) -> asset_types.Asset | None:
        return await asyncio.to_thread(
            self._sync_service.update_asset, asset_id, **kwargs
        )


class AsyncCanvasService:
    def __init__(self, sync_service: Any):
        self._sync_service = sync_service

    async def create_canvas(self, **kwargs: Any) -> asset_types.Canvas:
        if isinstance(
            self._sync_service, HtmlCanvasServiceInterface
        ) or inspect.iscoroutinefunction(
            getattr(self._sync_service, "create_canvas", None)
        ):
            cs_kwargs = {}
            if "workspace_id" in kwargs:
                cs_kwargs["workspace_id"] = kwargs["workspace_id"]
            elif "user_id" in kwargs:
                cs_kwargs["workspace_id"] = kwargs["user_id"]

            if "title" in kwargs:
                cs_kwargs["title"] = kwargs["title"]

            if "html" in kwargs and kwargs["html"]:
                cs_kwargs["html_content"] = kwargs["html"].content
                cs_kwargs["asset_references"] = kwargs["html"].asset_ids

            if "session_id" in kwargs:
                cs_kwargs["session_id"] = kwargs["session_id"]

            return await self._sync_service.create_canvas(**cs_kwargs)

        # Native path: map unified kwargs to the legacy CanvasService signature
        # create_canvas(user_id, title, video_timeline=None, html=None). The
        # unified callers may pass workspace_id/session_id, which legacy rejects.
        legacy_kwargs: dict[str, Any] = {}
        if "user_id" in kwargs:
            legacy_kwargs["user_id"] = kwargs["user_id"]
        elif "workspace_id" in kwargs:
            legacy_kwargs["user_id"] = kwargs["workspace_id"]

        if "title" in kwargs:
            legacy_kwargs["title"] = kwargs["title"]
        if kwargs.get("video_timeline") is not None:
            legacy_kwargs["video_timeline"] = kwargs["video_timeline"]
        if kwargs.get("html") is not None:
            legacy_kwargs["html"] = kwargs["html"]

        return await asyncio.to_thread(
            self._sync_service.create_canvas, **legacy_kwargs
        )

    async def get_canvas(self, canvas_id: str) -> asset_types.Canvas | None:
        return await asyncio.to_thread(self._sync_service.get_canvas, canvas_id)

    async def list_canvases(self, user_id: str) -> list[asset_types.Canvas]:
        return await asyncio.to_thread(self._sync_service.list_canvases, user_id)

    async def delete_canvas(self, canvas_id: str) -> None:
        return await asyncio.to_thread(self._sync_service.delete_canvas, canvas_id)

    async def update_canvas(
        self, canvas_id: str, **kwargs: Any
    ) -> asset_types.Canvas | None:
        return await asyncio.to_thread(
            self._sync_service.update_canvas, canvas_id, **kwargs
        )


class AsyncJobService:
    def __init__(self, sync_service: "JobService"):
        self._sync_service = sync_service

    async def create_job(
        self,
        user_id: str,
        job_type: asset_types.JobType,
        job_input: dict[str, Any] | None = None,
    ) -> asset_types.Job:
        return await asyncio.to_thread(
            self._sync_service.create_job, user_id, job_type, job_input
        )

    async def get_job(self, job_id: str) -> asset_types.Job | None:
        return await asyncio.to_thread(self._sync_service.get_job, job_id)

    async def get_jobs(self, user_id: str, **kwargs: Any) -> list[asset_types.Job]:
        return await asyncio.to_thread(self._sync_service.get_jobs, user_id, **kwargs)

    async def update_job_status(
        self, job_id: str, status: asset_types.JobStatus
    ) -> None:
        return await asyncio.to_thread(
            self._sync_service.update_job_status, job_id, status
        )

    async def update_job_result(self, job_id: str, **kwargs: Any) -> None:
        return await asyncio.to_thread(
            self._sync_service.update_job_result, job_id, **kwargs
        )


class AsyncMediaGenerationService:
    def __init__(self, sync_service: Any):
        self._sync_service = sync_service
        self._interface: MediaGenerationServiceInterface | None = None

    def _require_interface(self) -> MediaGenerationServiceInterface:
        """Resolves the unified media-generation interface.

        Creative Studio's ``CSMediaGenerationService`` already implements the
        interface and is used directly. The native legacy
        ``MediaGenerationService`` does not, so it is adapted via
        ``IzumiMediaGenerationService`` (reusing the media service's own asset
        service). The legacy passthrough methods below intentionally keep
        calling ``self._sync_service`` directly, so this wrapper still serves
        legacy callers unchanged.
        """
        if isinstance(self._sync_service, MediaGenerationServiceInterface):
            return self._sync_service
        if self._interface is None:
            from mediagent_kit.services.izumi.media_generation_service import (
                IzumiMediaGenerationService,
            )

            self._interface = IzumiMediaGenerationService(
                self._sync_service, self._sync_service._asset_service
            )
        return self._interface

    async def generate_text(self, **kwargs: Any) -> str:
        """Generates text via the unified interface (CS or native Izumi)."""
        return await self._require_interface().generate_text(**kwargs)

    async def generate_image(self, **kwargs: Any) -> Any:
        """Generates an image via the unified interface (CS or native Izumi)."""
        return await self._require_interface().generate_image(**kwargs)

    async def generate_video(self, **kwargs: Any) -> Any:
        """Generates a video via the unified interface (CS or native Izumi)."""
        return await self._require_interface().generate_video(**kwargs)

    async def generate_speech(self, **kwargs: Any) -> Any:
        """Generates speech via the unified interface (CS or native Izumi)."""
        return await self._require_interface().generate_speech(**kwargs)

    async def generate_music(self, **kwargs: Any) -> Any:
        """Generates music via the unified interface (CS or native Izumi)."""
        return await self._require_interface().generate_music(**kwargs)

    # Legacy method compatibility
    async def generate_music_with_lyria(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_music_with_lyria, **kwargs
        )

    async def generate_image_with_imagen(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_image_with_imagen, **kwargs
        )

    async def generate_text_with_gemini(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_text_with_gemini, **kwargs
        )

    async def generate_image_with_gemini(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_image_with_gemini, **kwargs
        )

    async def generate_speech_single_speaker(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_speech_single_speaker, **kwargs
        )

    async def generate_speech_multiple_speaker(
        self, **kwargs: Any
    ) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_speech_multiple_speaker, **kwargs
        )

    async def generate_video_with_veo(self, **kwargs: Any) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.generate_video_with_veo, **kwargs
        )


class AsyncVideoStitchingService:
    def __init__(self, sync_service: "VideoStitchingService"):
        self._sync_service = sync_service

    async def stitch_video(
        self, user_id: str, timeline: VideoTimeline, output_filename: str
    ) -> asset_types.Asset:
        return await asyncio.to_thread(
            self._sync_service.stitch_video, user_id, timeline, output_filename
        )


class AsyncStoryboardService:
    def __init__(self, sync_service: Any):
        self._sync_service = sync_service

    async def save_storyboard(
        self,
        storyboard: Any,
        idempotency_key: str | None = None,
    ) -> Any:
        if isinstance(self._sync_service, CSStoryboardService):
            return await self._sync_service.save_storyboard(storyboard, idempotency_key)
        return await asyncio.to_thread(
            self._sync_service.save_storyboard, storyboard, idempotency_key
        )

    async def get_storyboard(self, storyboard_id: str) -> Any:
        if isinstance(self._sync_service, CSStoryboardService):
            return await self._sync_service.get_storyboard(storyboard_id)
        return await asyncio.to_thread(self._sync_service.get_storyboard, storyboard_id)

    async def list_storyboards(
        self,
        workspace_id: str,
        session_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Any]:
        if isinstance(self._sync_service, CSStoryboardService):
            return await self._sync_service.list_storyboards(
                workspace_id, session_id, limit, offset
            )
        return await asyncio.to_thread(
            self._sync_service.list_storyboards,
            workspace_id,
            session_id,
            limit,
            offset,
        )

    async def delete_storyboard(self, storyboard_id: str) -> None:
        if isinstance(self._sync_service, CSStoryboardService):
            return await self._sync_service.delete_storyboard(storyboard_id)
        return await asyncio.to_thread(
            self._sync_service.delete_storyboard, storyboard_id
        )


class AsyncVideoTimelineService:
    def __init__(self, sync_service: Any):
        self._sync_service = sync_service

    async def create_timeline(
        self,
        workspace_id: str,
        session_id: str | None = None,
        storyboard_id: str | None = None,
        title: str | None = None,
        timeline: Any = None,
    ) -> Any:
        if isinstance(self._sync_service, CSTimelineService):
            return await self._sync_service.create_timeline(
                workspace_id=workspace_id,
                session_id=session_id,
                storyboard_id=storyboard_id,
                title=title,
                timeline=timeline,
            )
        return await asyncio.to_thread(
            self._sync_service.create_timeline,
            workspace_id=workspace_id,
            session_id=session_id,
            storyboard_id=storyboard_id,
            title=title,
            timeline=timeline,
        )

    async def get_timeline(self, timeline_id: str) -> Any:
        if isinstance(self._sync_service, CSTimelineService):
            return await self._sync_service.get_timeline(timeline_id)
        return await asyncio.to_thread(self._sync_service.get_timeline, timeline_id)

    async def update_timeline(self, timeline_id: str, timeline: Any) -> None:
        if isinstance(self._sync_service, CSTimelineService):
            return await self._sync_service.update_timeline(timeline_id, timeline)
        return await asyncio.to_thread(
            self._sync_service.update_timeline, timeline_id, timeline
        )

    async def stitch_timeline(
        self,
        timeline_id: str,
        output_filename: str,
        idempotency_key: str | None = None,
    ) -> Any:
        if isinstance(self._sync_service, CSTimelineService):
            return await self._sync_service.stitch_timeline(
                timeline_id, output_filename, idempotency_key
            )
        return await asyncio.to_thread(
            self._sync_service.stitch_timeline,
            timeline_id,
            output_filename,
            idempotency_key,
        )

    async def delete_timeline(self, timeline_id: str) -> None:
        if isinstance(self._sync_service, CSTimelineService):
            return await self._sync_service.delete_timeline(timeline_id)
        return await asyncio.to_thread(self._sync_service.delete_timeline, timeline_id)
