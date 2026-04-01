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

# config.py
import os
import socket
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    GOOGLE_GENAI_USE_VERTEXAI: bool = True
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "global"
    ARTIFACT_SERVICE_GCS_BUCKET: str = ""
    ASSET_SERVICE_GCS_BUCKET: str = ""
    RETRY_MAX_ATTEMPTS: int = 5
    RETRY_INITIAL_DELAY_SECONDS: float = 30.0
    FIRESTORE_DATABASE_ID: str = ""


def check_firestore_emulator():
    """Checks if the Firestore emulator is running if the host is set."""
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if emulator_host:
        try:
            host, port_str = emulator_host.split(":")
            port = int(port_str)
            with socket.create_connection((host, port), timeout=1):
                pass
        except (OSError, ValueError) as e:
            raise RuntimeError(
                f"FIRESTORE_EMULATOR_HOST is set to '{emulator_host}', but the emulator is not running or not reachable. Please start the Firestore emulator. Error: {e}"
            ) from e


def load_config() -> Config:
    """
    Loads configuration from the correct .env file and returns a Config object.
    """
    app_env = os.environ.get("APP_ENV", "local")
    dotenv_path = f".env.{app_env}"

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True)
    else:
        load_dotenv()

    if "pytest" not in sys.modules:
        check_firestore_emulator()

    return Config(
        GOOGLE_GENAI_USE_VERTEXAI=os.environ.get(
            "GOOGLE_GENAI_USE_VERTEXAI", "True"
        ).lower()
        in ["true", "1"],
        GOOGLE_CLOUD_PROJECT=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        GOOGLE_CLOUD_LOCATION=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        ARTIFACT_SERVICE_GCS_BUCKET=os.environ.get("ARTIFACT_SERVICE_GCS_BUCKET", ""),
        ASSET_SERVICE_GCS_BUCKET=os.environ.get("ASSET_SERVICE_GCS_BUCKET", ""),
        RETRY_MAX_ATTEMPTS=int(os.environ.get("RETRY_MAX_ATTEMPTS", "3")),
        RETRY_INITIAL_DELAY_SECONDS=float(
            os.environ.get("RETRY_INITIAL_DELAY_SECONDS", "30.0")
        ),
        FIRESTORE_DATABASE_ID=os.environ.get("FIRESTORE_DATABASE_ID", ""),
    )


settings = load_config()
