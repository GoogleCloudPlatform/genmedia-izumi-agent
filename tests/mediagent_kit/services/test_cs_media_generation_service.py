# Copyright 2026 Google LLC
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

"""Tests for CSMediaGenerationService implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.creative_studio.cs_media_generation_service import (
    CSMediaGenerationService,
)
from mediagent_kit.services.errors import (
    AuthenticationError,
    BackendError,
    ValidationError,
)
from mediagent_kit.services.types.common import AssetRef, GeneratedAsset


@pytest.fixture
def cs_config():
    return MediagentKitConfig(
        use_creative_studio=True,
        cs_backend_url="http://mock-cs-backend:8080",
    )


@pytest.fixture
def cs_service(cs_config):
    return CSMediaGenerationService(
        workspace_id="101",
        user_auth_token="test_user_token_abc",
        config=cs_config,
    )


@pytest.mark.asyncio
async def test_generate_text(cs_service):
    with patch("google.genai.Client") as mock_genai_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Generated prompt rewriting text."
        mock_client.models.generate_content.return_value = mock_resp
        mock_genai_cls.return_value = mock_client

        text = await cs_service.generate_text(
            workspace_id="101", prompt="Make a video of a cat"
        )
        assert text == "Generated prompt rewriting text."


@pytest.mark.asyncio
async def test_generate_image_success(cs_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # POST response (ID 501 returned)
        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {"id": 501}
        post_resp.raise_for_status.return_value = None

        # GET poll response (completed)
        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "id": 501,
            "status": "completed",
            "gcsUris": ["gs://bucket/image_501.png"],
        }
        poll_resp.raise_for_status.return_value = None

        mock_client.post.return_value = post_resp
        mock_client.get.return_value = poll_resp

        asset = await cs_service.generate_image(
            workspace_id="101",
            prompt="A sleek red sports car",
            generation_model="imagen-4.0-generate-001",
            aspect_ratio="16:9",
            resolution="1K",
            file_name="car.png",
            reference_assets=[
                AssetRef(id="201", workspace_id="101", asset_type="uploaded"),
                AssetRef(id="301", workspace_id="101", asset_type="generated"),
            ],
        )

        assert isinstance(asset, GeneratedAsset)
        assert asset.id == "501"
        assert asset.status == "completed"
        assert asset.gcs_uri == "gs://bucket/image_501.png"
        assert asset.mime_type == "image/png"
        assert asset.generation_metadata.source == "creative_studio"


@pytest.mark.asyncio
async def test_generate_image_failure_status(cs_service):
    """Verify failed status returns GeneratedAsset with status=failed and error_message populated."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {"id": 502}
        post_resp.raise_for_status.return_value = None

        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "id": 502,
            "status": "failed",
            "errorMessage": "Safety threshold exceeded",
        }
        poll_resp.raise_for_status.return_value = None

        mock_client.post.return_value = post_resp
        mock_client.get.return_value = poll_resp

        asset = await cs_service.generate_image(
            workspace_id="101",
            prompt="Unsafe prompt",
            generation_model="imagen-4.0-generate-001",
            aspect_ratio="16:9",
            resolution="1K",
            file_name="unsafe.png",
        )

        assert isinstance(asset, GeneratedAsset)
        assert asset.id == "502"
        assert asset.status == "failed"
        assert asset.error_message == "Safety threshold exceeded"


@pytest.mark.asyncio
async def test_generate_video_success(cs_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {"id": 601}
        post_resp.raise_for_status.return_value = None

        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "id": 601,
            "status": "completed",
            "durationSeconds": 6.0,
            "gcsUris": ["gs://bucket/video_601.mp4"],
        }
        poll_resp.raise_for_status.return_value = None

        mock_client.post.return_value = post_resp
        mock_client.get.return_value = poll_resp

        asset = await cs_service.generate_video(
            workspace_id="101",
            prompt="Pan across futuristic city",
            generation_model="veo-3.1-generate-001",
            aspect_ratio="16:9",
            duration_seconds=6,
            file_name="city.mp4",
            start_image=AssetRef(id="1001", workspace_id="101", asset_type="uploaded"),
        )

        assert isinstance(asset, GeneratedAsset)
        assert asset.id == "601"
        assert asset.status == "completed"
        assert asset.duration_seconds == 6.0
        assert asset.gcs_uri == "gs://bucket/video_601.mp4"
        assert asset.mime_type == "video/mp4"


@pytest.mark.asyncio
async def test_generate_speech_success(cs_service):
    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("mediagent_kit.services.aio.get_asset_service") as mock_get_asset_service,
    ):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {"id": 701}
        post_resp.raise_for_status.return_value = None

        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "id": 701,
            "status": "completed",
            "durationSeconds": 3.5,
            "gcsUris": ["gs://bucket/speech_701.mp3"],
        }
        poll_resp.raise_for_status.return_value = None

        mock_client.post.return_value = post_resp
        mock_client.get.return_value = poll_resp

        mock_asset_service = AsyncMock()
        mock_get_asset_service.return_value = mock_asset_service
        import datetime

        mock_asset_service.get_asset.return_value = GeneratedAsset(
            id="701",
            workspace_id="101",
            file_name="welcome.mp3",
            gcs_uri="gs://bucket/speech_701.mp3",
            mime_type="audio/mp3",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            status="completed",
            duration_seconds=3.5,
            generation_metadata=None,
        )

        asset = await cs_service.generate_speech(
            workspace_id="101",
            text="Welcome to Cymbal Direct",
            voice_name="Puck",
            language_code="en-US",
            file_name="welcome.mp3",
        )

        assert isinstance(asset, GeneratedAsset)
        assert asset.id == "701"
        assert asset.status == "completed"
        assert asset.duration_seconds == 3.5
        assert asset.mime_type == "audio/mp3"


@pytest.mark.asyncio
async def test_missing_credentials_raises_error(cs_config):
    svc_no_creds = CSMediaGenerationService(
        workspace_id=None, user_auth_token=None, config=cs_config
    )
    with pytest.raises(ValidationError):
        await svc_no_creds.generate_image(
            workspace_id="",
            prompt="test",
            generation_model="imagen-4.0-generate-001",
            aspect_ratio="16:9",
            resolution="1K",
            file_name="test.png",
        )
