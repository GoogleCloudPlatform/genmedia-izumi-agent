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

from mediagent_kit.services.interfaces import HtmlCanvasServiceInterface

from mediagent_kit.services import types as asset_types
from mediagent_kit.services.creative_studio.cs_asset_service import CSAssetService
from mediagent_kit.services.creative_studio.cs_media_generation_service import (
    CSMediaGenerationService,
)
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
    def __init__(self, sync_service: "AssetService"):
        self._sync_service = sync_service

    async def upload_asset(
        self,
        workspace_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str,
        scope: str = "private",
        idempotency_key: str | None = None,
    ) -> UploadedAsset:
        if isinstance(self._sync_service, CSAssetService):
            return await self._sync_service.upload_asset(
                workspace_id=workspace_id,
                file_name=file_name,
                blob=blob,
                mime_type=mime_type,
                scope=scope,
                idempotency_key=idempotency_key,
            )
        return await asyncio.to_thread(
            self._sync_service.upload_asset,
            workspace_id,
            file_name,
            blob,
            mime_type,
            scope,
            idempotency_key,
        )

    async def get_asset(self, ref: AssetRef) -> UploadedAsset | GeneratedAsset | None:
        if isinstance(self._sync_service, CSAssetService):
            return await self._sync_service.get_asset(ref)
        return await asyncio.to_thread(self._sync_service.get_asset, ref)

    async def search_assets(
        self,
        workspace_id: str,
        query: str | None = None,
        asset_type: AssetType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UploadedAsset | GeneratedAsset]:
        if isinstance(self._sync_service, CSAssetService):
            return await self._sync_service.search_assets(
                workspace_id=workspace_id,
                query=query,
                asset_type=asset_type,
                limit=limit,
                offset=offset,
            )
        return await asyncio.to_thread(
            self._sync_service.search_assets,
            workspace_id,
            query,
            asset_type,
            limit,
            offset,
        )

    async def download_asset_bytes(self, ref: AssetRef) -> bytes:
        if isinstance(self._sync_service, CSAssetService):
            return await self._sync_service.download_asset_bytes(ref)
        return await asyncio.to_thread(self._sync_service.download_asset_bytes, ref)

    async def delete_asset(self, ref: AssetRef) -> None:
        if isinstance(self._sync_service, CSAssetService):
            return await self._sync_service.delete_asset(ref)
        return await asyncio.to_thread(self._sync_service.delete_asset, ref)

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

    async def delete_asset(self, asset_id: str) -> None:
        return await asyncio.to_thread(self._sync_service.delete_asset, asset_id)


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

        return await asyncio.to_thread(self._sync_service.create_canvas, **kwargs)

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

    async def generate_text(self, **kwargs: Any) -> str:
        """Generates text using CS direct async call or native thread pool execution."""
        if isinstance(self._sync_service, CSMediaGenerationService):
            return await self._sync_service.generate_text(**kwargs)
        return await asyncio.to_thread(
            self._sync_service.generate_text_with_gemini, **kwargs
        )

    async def generate_image(self, **kwargs: Any) -> Any:
        """Generates image using CS direct async call or native thread pool execution."""
        if isinstance(self._sync_service, CSMediaGenerationService):
            return await self._sync_service.generate_image(**kwargs)
        return await asyncio.to_thread(
            self._sync_service.generate_image_with_imagen, **kwargs
        )

    async def generate_video(self, **kwargs: Any) -> Any:
        """Generates video using CS direct async call or native thread pool execution."""
        if isinstance(self._sync_service, CSMediaGenerationService):
            return await self._sync_service.generate_video(**kwargs)
        return await asyncio.to_thread(
            self._sync_service.generate_video_with_veo, **kwargs
        )

    async def generate_speech(self, **kwargs: Any) -> Any:
        """Generates speech using CS direct async call or native thread pool execution."""
        if isinstance(self._sync_service, CSMediaGenerationService):
            return await self._sync_service.generate_speech(**kwargs)
        return await asyncio.to_thread(
            self._sync_service.generate_speech_single_speaker, **kwargs
        )

    async def generate_music(self, **kwargs: Any) -> Any:
        """Generates music using CS direct async call or native thread pool execution."""
        if isinstance(self._sync_service, CSMediaGenerationService):
            return await self._sync_service.generate_music(**kwargs)
        return await asyncio.to_thread(
            self._sync_service.generate_music_with_lyria, **kwargs
        )

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
