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

from .async_services import (
    AsyncAssetService,
    AsyncCanvasService,
    AsyncJobService,
    AsyncMediaGenerationService,
    AsyncVideoStitchingService,
)
from .firestore_session_service import FirestoreSessionService
from .service_factory import AsyncServiceFactory

_async_service_factory: AsyncServiceFactory | None = None


def _get_async_service_factory() -> AsyncServiceFactory:
    global _async_service_factory
    if _async_service_factory is None:
        from mediagent_kit.services import _get_service_factory

        print("[mediagent_kit.aio] Creating AsyncServiceFactory from sync factory...")
        _async_service_factory = AsyncServiceFactory(_get_service_factory())

    return _async_service_factory


def get_asset_service() -> AsyncAssetService:
    return _get_async_service_factory().get_asset_service()


def get_canvas_service() -> AsyncCanvasService:
    return _get_async_service_factory().get_canvas_service()


def get_job_service() -> AsyncJobService:
    return _get_async_service_factory().get_job_service()


def get_media_generation_service() -> AsyncMediaGenerationService:
    return _get_async_service_factory().get_media_generation_service()


def get_video_stitching_service() -> AsyncVideoStitchingService:
    return _get_async_service_factory().get_video_stitching_service()


def get_firestore_session_service() -> FirestoreSessionService:
    return _get_async_service_factory().get_firestore_session_service()


__all__ = [
    "AsyncAssetService",
    "AsyncCanvasService",
    "AsyncJobService",
    "AsyncMediaGenerationService",
    "AsyncVideoStitchingService",
    "FirestoreSessionService",
    "get_asset_service",
    "get_canvas_service",
    "get_firestore_session_service",
    "get_job_service",
    "get_media_generation_service",
    "get_video_stitching_service",
]
