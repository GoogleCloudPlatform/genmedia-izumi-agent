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

"""
Centralized service factory for creating and managing service instances.
"""

import functools
from typing import Any

import firebase_admin
from firebase_admin import firestore
from google.cloud import storage  # type: ignore

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.canvas_service import CanvasService
from mediagent_kit.services.interfaces import (
    AssetServiceInterface,
    HtmlCanvasServiceInterface,
    MediaGenerationServiceInterface,
    StoryboardServiceInterface,
    VideoTimelineServiceInterface,
)
from mediagent_kit.services.job_orchestrator_service import JobOrchestratorService
from mediagent_kit.services.job_service import JobService
from mediagent_kit.services.media_generation_service import MediaGenerationService
from mediagent_kit.services.video_stitching_service import VideoStitchingService
from mediagent_kit.utils.background_job_runner import (
    AbstractBackgroundJobRunner,
)


class ServiceFactory:
    """
    Centralized service factory for creating and managing service instances.
    """

    def __init__(self, config: MediagentKitConfig):
        """Initializes the ServiceFactory."""
        self._config = config

    def get_config(self) -> MediagentKitConfig:
        """Returns the configuration for the application."""
        return self._config

    @functools.cache
    def _get_db(self) -> Any:
        """Returns a singleton instance of the Firestore client."""
        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                options={"projectId": self.get_config().google_cloud_project}
            )
        if self.get_config().firestore_database_id:
            return firestore.client(database_id=self.get_config().firestore_database_id)
        else:
            return firestore.client()

    @functools.cache
    def _get_gcs_bucket(self) -> Any:
        """Returns a singleton instance of the GCS bucket."""
        if self.get_config().asset_service_gcs_bucket:
            storage_client = storage.Client(
                project=self.get_config().google_cloud_project
            )
            return storage_client.bucket(self.get_config().asset_service_gcs_bucket)
        return None

    def _extract_context_credentials(
        self, workspace_id: str | None, user_auth_token: str | None
    ) -> tuple[str | None, str | None]:
        """Extracts workspace_id and user_auth_token from explicit parameters or request context,

        honoring config.cs_user_auth_token_key.
        """
        from mediagent_kit.utils.context import get_request_context

        ctx = get_request_context() or {}
        token_key = self.get_config().cs_user_auth_token_key or "user_auth_token"

        ws_id = workspace_id or ctx.get("workspace_id")
        token = user_auth_token or ctx.get("user_auth_token") or ctx.get(token_key)
        return ws_id, token

    def _get_standard_asset_service(self) -> AssetService:
        """Returns a new instance of the standard AssetService."""
        return AssetService(
            db=self._get_db(),
            gcs_bucket=self._get_gcs_bucket(),
            config=self.get_config(),
        )

    def get_asset_service(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
    ) -> AssetServiceInterface | AssetService:
        """Returns AssetService instance (CSAssetService if CS active, else standard AssetService)."""
        if self.get_config().use_creative_studio:
            from mediagent_kit.services.creative_studio.cs_asset_service import (
                CSAssetService,
            )

            ws_id, token = self._extract_context_credentials(
                workspace_id, user_auth_token
            )
            return CSAssetService(
                workspace_id=ws_id,
                user_auth_token=token,
                config=self.get_config(),
            )
        return self._get_standard_asset_service()

    def _get_standard_canvas_service(self) -> CanvasService:
        """Returns a new instance of the standard CanvasService."""
        return CanvasService(
            db=self._get_db(),
            asset_service=self._get_standard_asset_service(),
            config=self.get_config(),
        )

    def get_canvas_service(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
    ) -> HtmlCanvasServiceInterface | CanvasService:
        """Returns CanvasService instance (CSCanvasService if CS active, else standard CanvasService)."""
        if self.get_config().use_creative_studio:
            from mediagent_kit.services.creative_studio.cs_canvas_service import (
                CSCanvasService,
            )

            ws_id, token = self._extract_context_credentials(
                workspace_id, user_auth_token
            )
            return CSCanvasService(
                workspace_id=ws_id,
                user_auth_token=token,
                config=self.get_config(),
            )
        return self._get_standard_canvas_service()

    def get_job_service(self) -> JobService:
        """Returns a new instance of the JobService."""
        return JobService(db=self._get_db(), config=self.get_config())

    def _get_standard_media_generation_service(self) -> MediaGenerationService:
        """Returns a new instance of the standard MediaGenerationService."""
        return MediaGenerationService(
            asset_service=self._get_standard_asset_service(), config=self.get_config()
        )

    def get_media_generation_service(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
    ) -> MediaGenerationServiceInterface | MediaGenerationService:
        """Returns MediaGenerationService instance."""
        if self.get_config().use_creative_studio:
            from mediagent_kit.services.creative_studio.cs_media_generation_service import (
                CSMediaGenerationService,
            )

            ws_id, token = self._extract_context_credentials(
                workspace_id, user_auth_token
            )
            return CSMediaGenerationService(
                workspace_id=ws_id,
                user_auth_token=token,
                config=self.get_config(),
            )
        return self._get_standard_media_generation_service()

    def get_timeline_service(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
    ) -> VideoTimelineServiceInterface:
        """Returns VideoTimelineService instance."""
        if self.get_config().use_creative_studio:
            from mediagent_kit.services.creative_studio.cs_timeline_service import (
                CSTimelineService,
            )

            ws_id, token = self._extract_context_credentials(
                workspace_id, user_auth_token
            )
            return CSTimelineService(
                workspace_id=ws_id,
                user_auth_token=token,
                config=self.get_config(),
            )
        raise NotImplementedError(
            "Izumi native timeline service implementation pending"
        )

    def get_storyboard_service(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
    ) -> StoryboardServiceInterface:
        """Returns StoryboardService instance."""
        if self.get_config().use_creative_studio:
            from mediagent_kit.services.creative_studio.cs_storyboard_service import (
                CSStoryboardService,
            )

            ws_id, token = self._extract_context_credentials(
                workspace_id, user_auth_token
            )
            return CSStoryboardService(
                workspace_id=ws_id,
                user_auth_token=token,
                config=self.get_config(),
            )
        raise NotImplementedError(
            "Izumi native storyboard service implementation pending"
        )

    def get_video_stitching_service(self) -> VideoStitchingService:
        """Returns a new instance of the VideoStitchingService."""
        return VideoStitchingService(
            asset_service=self.get_asset_service(), config=self.get_config()
        )

    def get_job_orchestrator_service(
        self, background_runner: AbstractBackgroundJobRunner
    ) -> JobOrchestratorService:
        """Creates and returns a new instance of the JobOrchestratorService.

        Note: This service is not a singleton and must be created per-request
        with a request-specific background runner.
        """
        return JobOrchestratorService(
            background_job_runner=background_runner,
            job_service=self.get_job_service(),
            canvas_service=self.get_canvas_service(),
            media_generation_service=self.get_media_generation_service(),
            video_stitching_service=self.get_video_stitching_service(),
            config=self.get_config(),
        )
