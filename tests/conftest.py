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

import os
import sys

# Ensure APP_ENV is set to 'test' BEFORE importing main or config.
# This forces config.py to load .env.test if it exists.
os.environ["APP_ENV"] = "test"

# Add workspace root and demos/backend to path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../demos/backend"))
)

import pytest
from fastapi.testclient import TestClient

# Create dummy credentials file for CI to prevent Firestore init crash
dummy_creds_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "dummy_creds.json")
)
if not os.path.exists(dummy_creds_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate a valid valid RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    import json

    creds_info = {
        "type": "service_account",
        "project_id": "dummy-project",
        "private_key_id": "dummy-key-id",
        "private_key": pem,
        "client_email": "dummy@example.com",
        "client_id": "dummy-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy@example.com",
    }
    with open(dummy_creds_path, "w") as f:
        json.dump(creds_info, f)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = dummy_creds_path
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8083"

# Inject fallback environment variables for CI if missing
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "dummy-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("ASSET_SERVICE_GCS_BUCKET", "dummy-bucket")

from unittest.mock import patch, MagicMock

# Patch GCS client globally for tests to prevent live network calls
mock_storage_patcher = patch("google.cloud.storage.Client")
mock_storage_client = mock_storage_patcher.start()
mock_bucket = MagicMock()
mock_blob = MagicMock()
mock_storage_client.return_value.bucket.return_value = mock_bucket
mock_bucket.blob.return_value = mock_blob
mock_blob.upload_from_string.return_value = True
mock_blob.download_as_bytes.return_value = b"fake media content"

# Patch Gemini image generation globally for tests
mock_gemini_patcher = patch(
    "mediagent_kit.services.media_generation_service.MediaGenerationService._generate_gemini_image_content"
)
mock_gemini_gen = mock_gemini_patcher.start()
mock_gen_response = MagicMock()
mock_candidate = MagicMock()
mock_part = MagicMock()
mock_part.inline_data.data = b"fake image data"
mock_part.inline_data.mime_type = "image/png"
mock_candidate.content.parts = [mock_part]
mock_gen_response.candidates = [mock_candidate]
mock_gen_response.prompt_feedback = None
mock_gemini_gen.return_value = mock_gen_response

from demos.backend.main import app


@pytest.fixture(scope="module")
def client():
    """Returns a FastAPI TestClient for E2E API testing."""
    with TestClient(app) as client:
        yield client
