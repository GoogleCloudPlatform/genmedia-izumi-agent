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
"""mediagent_kit services package.

Two layers coexist here (both are exported):

  * **Legacy concrete services**: ``AssetService``, ``CanvasService``,
    ``JobService``, ``JobOrchestratorService``,
    ``MediaGenerationService``, ``VideoStitchingService``. These are
    the existing process-singleton services used by current agents.
    Accessed via top-level helpers ``get_asset_service()``,
    ``get_canvas_service()``, etc.

  * **Unified abstract interfaces and the request-scoped session
    pattern**: ``AssetServiceInterface``,
    ``HtmlCanvasServiceInterface``, ``VideoTimelineServiceInterface``,
    ``StoryboardServiceInterface``,
    ``MediaGenerationServiceInterface``, plus ``AgentSession``. These
    define the cross-backend contract (Izumi Native + Creative Studio
    + future backends) per
    ``unified_media_agent_interface_spec_v1.md``. Concrete
    implementations land in follow-up CLs as ``izumi/*Service`` and
    ``creative_studio/*Service`` submodules.

  * **Typed error taxonomy**: see ``errors.MediagentError`` and its
    subclasses. Concrete backends translate their backend-specific
    failures into these so callers can write backend-agnostic error
    handling.

The legacy and unified layers coexist by design; the unified layer
is the forward path and the legacy layer is incrementally retired.
"""

from mediagent_kit.services import aio, creative_studio, errors, interfaces
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.base_service import BaseService
from mediagent_kit.services.canvas_service import CanvasService
from mediagent_kit.services.creative_studio import (
    CSAssetService,
    CSCanvasService,
    CSMediaGenerationService,
    CSStoryboardService,
    CSTimelineService,
)
from mediagent_kit.services.interfaces import (
    AgentSession,
    AssetServiceInterface,
    HtmlCanvasServiceInterface,
    MediaGenerationServiceInterface,
    StoryboardServiceInterface,
    VideoTimelineServiceInterface,
)
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


def get_asset_service() -> AssetServiceInterface | AssetService:
    """Returns the AssetService."""
    return _get_service_factory().get_asset_service()


def get_canvas_service() -> HtmlCanvasServiceInterface | CanvasService:
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


def get_media_generation_service() -> (
    MediaGenerationServiceInterface | MediaGenerationService
):
    """Returns the MediaGenerationService."""
    return _get_service_factory().get_media_generation_service()


def get_video_stitching_service() -> VideoStitchingService:
    """Returns the VideoStitchingService."""
    return _get_service_factory().get_video_stitching_service()


__all__ = [
    # Legacy concrete services
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
    # Creative Studio implementations
    "CSAssetService",
    "CSCanvasService",
    "CSMediaGenerationService",
    "CSStoryboardService",
    "CSTimelineService",
    "creative_studio",
    # Unified abstract interfaces
    "AgentSession",
    "AssetServiceInterface",
    "HtmlCanvasServiceInterface",
    "MediaGenerationServiceInterface",
    "StoryboardServiceInterface",
    "VideoTimelineServiceInterface",
    "errors",
    "interfaces",
]
