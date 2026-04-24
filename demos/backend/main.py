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
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pydantic.json_schema as pjs
from fastapi.openapi.utils import get_openapi
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.evaluation.local_eval_set_results_manager import (
    LocalEvalSetResultsManager,
)
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

import mediagent_kit
from config import settings
from mediagent_kit import MediagentKitConfig
from mediagent_kit.server import mount_to_fastapi_app

# Define the path to the agents directory
agents_dir = os.path.dirname(os.path.abspath(__file__))


# Configure logging with Pacific Time timestamps (Safe Implementation)
class PTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("America/Los_Angeles"))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(sep=" ", timespec="milliseconds")


# Force initialization of basic logging if no handlers exist
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO)

# Update all existing handlers to use the PTFormatter
pt_formatter = PTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
for handler in logging.root.handlers:
    handler.setFormatter(pt_formatter)
logging.root.setLevel(logging.INFO)

# Create the config
kit_config = MediagentKitConfig(
    google_cloud_project=settings.GOOGLE_CLOUD_PROJECT,
    google_cloud_location=settings.GOOGLE_CLOUD_LOCATION,
    asset_service_gcs_bucket=settings.ASSET_SERVICE_GCS_BUCKET,
    firestore_database_id=settings.FIRESTORE_DATABASE_ID,
)

# Initialize the kit
mediagent_kit.initialize(kit_config)

# Instantiate your custom FirestoreSessionService
session_service = mediagent_kit.services.aio.get_firestore_session_service()

# Instantiate the ArtifactService
if settings.ASSET_SERVICE_GCS_BUCKET:
    artifact_service = GcsArtifactService(bucket_name=settings.ASSET_SERVICE_GCS_BUCKET)
else:
    artifact_service = InMemoryArtifactService()

# Instantiate local eval managers as per the provided logic
eval_sets_manager = LocalEvalSetsManager(agents_dir=agents_dir)
eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=agents_dir)


class FilteredAgentLoader(AgentLoader):
    """Subclass of AgentLoader that ignores non-agent directories like 'utils'."""

    def list_agents(self) -> list[str]:
        agents = super().list_agents()
        return [a for a in agents if a not in ["utils"]]


# Instantiate the other default services
agent_loader = FilteredAgentLoader(agents_dir)
memory_service = InMemoryMemoryService()
credential_service = InMemoryCredentialService()

# Create the AdkWebServer with all required services
adk_server = AdkWebServer(
    agent_loader=agent_loader,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
    credential_service=credential_service,
    eval_sets_manager=eval_sets_manager,
    eval_set_results_manager=eval_set_results_manager,
    agents_dir=agents_dir,
)

# Get the FastAPI app from the web server
app = adk_server.get_fast_api_app(
    allow_origins=["*"],
)


# Fix FastAPI docs issue as per https://github.com/google/adk-python/issues/3316
def make_openapi(app):
    def new_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        original_is_instance_schema = pjs.GenerateJsonSchema.is_instance_schema

        def patched_is_instance_schema(self, schema):
            if isinstance(schema, dict) and schema.get("cls") in (
                httpx.Client,
                httpx.AsyncClient,
            ):
                return {}
            return original_is_instance_schema(self, schema)

        pjs.GenerateJsonSchema.is_instance_schema = patched_is_instance_schema
        try:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                summary=app.summary,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=app.routes,
                webhooks=app.webhooks.routes,
                tags=app.openapi_tags,
                servers=app.servers,
                separate_input_output_schemas=False,
            )
        finally:
            pjs.GenerateJsonSchema.is_instance_schema = original_is_instance_schema

        return app.openapi_schema

    return new_openapi


app.openapi = make_openapi(app)


# Initialize the non-agent API
# This mounts the API endpoints and the default kit UIs (ADK Web, Debug UI)
mount_to_fastapi_app(app)

# Frontend is served independently.
