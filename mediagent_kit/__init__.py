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

"""Top-level package for Mediagent Kit."""

import os
import threading

from . import config, server, services
from .config import MediagentKitConfig
from .services.service_factory import ServiceFactory

_initialization_lock = threading.Lock()


def is_initialized() -> bool:
    """Returns True if the Mediagent Kit has been initialized."""
    return services._service_factory is not None


def initialize(config: MediagentKitConfig) -> None:
    """Initializes the Mediagent Kit with the given configuration."""
    with _initialization_lock:
        if services._service_factory is not None:
            raise ValueError("mediagent_kit is already initialized.")
        print(f"[mediagent_kit] Initializing with config: {config}")
        services._service_factory = ServiceFactory(config)
        print("[mediagent_kit] Service factory initialized.")


def initialize_from_env() -> None:
    """Initializes the Mediagent Kit from environment variables."""
    if is_initialized():
        return

    project_id = (
        os.getenv("IZUMI_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("PROJECT_ID")
    )
    location = (
        os.getenv("IZUMI_LOCATION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or "us-central1"
    )
    bucket = os.getenv("ASSET_SERVICE_GCS_BUCKET")
    db_id = os.getenv("FIRESTORE_DATABASE_ID", "(default)")

    print(
        f"[mediagent_kit] Attempting auto-initialization with project_id={project_id}, location={location}, bucket={bucket}"
    )

    if not project_id:
        print(
            "[mediagent_kit] Auto-initialization skipped: project_id not found in environment."
        )
        return

    try:
        initialize(
            MediagentKitConfig(
                google_cloud_project=project_id,
                google_cloud_location=location,
                asset_service_gcs_bucket=bucket,
                firestore_database_id=db_id,
            )
        )
        print("[mediagent_kit] Auto-initialization successful.")
    except Exception as e:
        print(f"[mediagent_kit] Auto-initialization failed: {e}")


__all__ = [
    "config",
    "initialize",
    "initialize_from_env",
    "is_initialized",
    "server",
    "services",
]
