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

    @functools.cache
    def get_asset_service(self) -> AssetService:
        """Returns a singleton instance of the AssetService."""
        return AssetService(
            db=self._get_db(),
            gcs_bucket=self._get_gcs_bucket(),
            config=self.get_config(),
        )

    @functools.cache
    def get_canvas_service(self) -> CanvasService:
        """Returns a singleton instance of the CanvasService."""
        return CanvasService(
            db=self._get_db(),
            asset_service=self.get_asset_service(),
            config=self.get_config(),
        )

    @functools.cache
    def get_job_service(self) -> JobService:
        """Returns a singleton instance of the JobService."""
        return JobService(db=self._get_db(), config=self.get_config())

    @functools.cache
    def get_media_generation_service(self) -> MediaGenerationService:
        """Returns a singleton instance of the MediaGenerationService."""
        return MediaGenerationService(
            asset_service=self.get_asset_service(), config=self.get_config()
        )

    @functools.cache
    def get_video_stitching_service(self) -> VideoStitchingService:
        """Returns a singleton instance of the VideoStitchingService."""
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
            media_generation_service=self.get_media_generation_service(),
            video_stitching_service=self.get_video_stitching_service(),
            config=self.get_config(),
        )
