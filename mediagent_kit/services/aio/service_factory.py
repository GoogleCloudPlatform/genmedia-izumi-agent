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

import functools

from mediagent_kit.services import service_factory as sync_service_factory
from mediagent_kit.services.aio import async_services as services
from mediagent_kit.services.aio.firestore_session_service import FirestoreSessionService


class AsyncServiceFactory:
    def __init__(self, sync_factory: sync_service_factory.ServiceFactory):
        self._sync_factory = sync_factory

    @functools.cache
    def get_asset_service(self) -> services.AsyncAssetService:
        return services.AsyncAssetService(self._sync_factory.get_asset_service())

    @functools.cache
    def get_canvas_service(self) -> services.AsyncCanvasService:
        return services.AsyncCanvasService(self._sync_factory.get_canvas_service())

    @functools.cache
    def get_job_service(self) -> services.AsyncJobService:
        return services.AsyncJobService(self._sync_factory.get_job_service())

    @functools.cache
    def get_media_generation_service(self) -> services.AsyncMediaGenerationService:
        return services.AsyncMediaGenerationService(
            self._sync_factory.get_media_generation_service()
        )

    @functools.cache
    def get_video_stitching_service(self) -> services.AsyncVideoStitchingService:
        return services.AsyncVideoStitchingService(
            self._sync_factory.get_video_stitching_service()
        )

    @functools.cache
    def get_firestore_session_service(self) -> FirestoreSessionService:
        return FirestoreSessionService(
            db=self._sync_factory._get_db(),
            asset_service=self.get_asset_service(),
            config=self._sync_factory.get_config(),
        )
