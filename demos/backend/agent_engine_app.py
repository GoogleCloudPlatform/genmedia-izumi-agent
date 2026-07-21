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

import logging
from vertexai.agent_engines import AdkApp
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export

import mediagent_kit
from mediagent_kit import MediagentKitConfig
from config import settings
from utils.tracing import CloudTraceLoggingSpanExporter


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Set up logging, tracing, and global configurations for the agent engine app."""
        super().set_up()
        self.logger = logging.getLogger(__name__)

        # 1. Tracing Initialization
        provider = TracerProvider()
        processor = export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(project_id=settings.GOOGLE_CLOUD_PROJECT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # 2. MediagentKit Initialization
        if not mediagent_kit.is_initialized():
            kit_config = MediagentKitConfig(
                google_cloud_project=settings.GOOGLE_CLOUD_PROJECT,
                google_cloud_location=settings.GOOGLE_CLOUD_LOCATION,
                model_target_location=settings.MODEL_TARGET_LOCATION,
                asset_service_gcs_bucket=settings.ASSET_SERVICE_GCS_BUCKET,
                firestore_database_id=settings.FIRESTORE_DATABASE_ID,
                use_creative_studio=settings.USE_CREATIVE_STUDIO,
                cs_backend_url=settings.CREATIVE_STUDIO_BACKEND_URL,
                cs_frontend_url=settings.CREATIVE_STUDIO_FRONTEND_URL,
                cs_user_auth_token_key=settings.CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY,
            )
            mediagent_kit.initialize(kit_config)
            self.logger.info("MediagentKit explicitly initialized in Agent Engine.")
