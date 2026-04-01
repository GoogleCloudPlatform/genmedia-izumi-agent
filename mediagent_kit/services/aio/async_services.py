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

import asyncio
from typing import TYPE_CHECKING, Any

from mediagent_kit.services import types as asset_types
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
    def __init__(self, sync_service: "CanvasService"):
        self._sync_service = sync_service

    async def create_canvas(self, **kwargs: Any) -> asset_types.Canvas:
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
    def __init__(self, sync_service: "MediaGenerationService"):
        self._sync_service = sync_service

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
