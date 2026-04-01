# Copyright 2024 Google LLC
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
"""
This package contains the services used by the application.
"""

from mediagent_kit.services import aio
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.base_service import BaseService
from mediagent_kit.services.canvas_service import CanvasService
from mediagent_kit.services.job_orchestrator_service import JobOrchestratorService
from mediagent_kit.services.job_service import JobService
from mediagent_kit.services.media_generation_service import MediaGenerationService
from mediagent_kit.services.service_factory import ServiceFactory
from mediagent_kit.services.video_stitching_service import VideoStitchingService
from mediagent_kit.utils.background_job_runner import AbstractBackgroundJobRunner

_service_factory: ServiceFactory | None = None


def _get_service_factory() -> ServiceFactory:
    """Returns the singleton instance of the ServiceFactory."""
    global _service_factory
    if _service_factory is None:
        import mediagent_kit

        mediagent_kit.initialize_from_env()

    if _service_factory is None:
        raise ValueError(
            "mediagent_kit has not been initialized. Call initialize() first."
        )
    return _service_factory


def get_asset_service() -> AssetService:
    """Returns the AssetService."""
    return _get_service_factory().get_asset_service()


def get_canvas_service() -> CanvasService:
    """Returns the CanvasService."""
    return _get_service_factory().get_canvas_service()


def get_job_service() -> JobService:
    """Returns the JobService."""
    return _get_service_factory().get_job_service()


def _get_job_orchestrator_service(
    background_runner: AbstractBackgroundJobRunner,
) -> JobOrchestratorService:
    """Returns the JobOrchestratorService."""
    return _get_service_factory().get_job_orchestrator_service(background_runner)


def get_media_generation_service() -> MediaGenerationService:
    """Returns the MediaGenerationService."""
    return _get_service_factory().get_media_generation_service()


def get_video_stitching_service() -> VideoStitchingService:
    """Returns the VideoStitchingService."""
    return _get_service_factory().get_video_stitching_service()


__all__ = [
    "AssetService",
    "BaseService",
    "CanvasService",
    "JobOrchestratorService",
    "JobService",
    "MediaGenerationService",
    "ServiceFactory",
    "VideoStitchingService",
    "_get_job_orchestrator_service",
    "_get_service_factory",
    "aio",
    "get_asset_service",
    "get_canvas_service",
    "get_job_service",
    "get_media_generation_service",
    "get_video_stitching_service",
]
