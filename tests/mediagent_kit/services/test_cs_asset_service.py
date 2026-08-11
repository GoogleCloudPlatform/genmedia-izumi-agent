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

"""Unit tests for CSAssetService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import datetime

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.creative_studio.cs_asset_service import CSAssetService
from mediagent_kit.services.errors import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from mediagent_kit.services.types.common import (
    AssetRef,
    GeneratedAsset,
    UploadedAsset,
)


@pytest.fixture
def cs_config():
    return MediagentKitConfig(
        cs_backend_url="http://backend:8080",
        google_cloud_project="test-project",
    )


@pytest.fixture
def cs_asset_service(cs_config):
    return CSAssetService(
        workspace_id="123",
        user_auth_token="user_token_abc",
        config=cs_config,
    )


@pytest.mark.asyncio
async def test_upload_asset_success(cs_asset_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 101,
            "workspaceId": 123,
            "userId": 456,
            "fileName": "logo.png",
            "gcsUri": "gs://bucket/logo.png",
            "mimeType": "image/png",
            "createdAt": "2026-07-02T12:00:00Z",
            "itemType": "source_asset",
        }
        mock_resp.raise_for_status.return_value = None
        mock_client.post.return_value = mock_resp

        uploaded = await cs_asset_service.upload_asset(
            workspace_id="123",
            file_name="logo.png",
            blob=b"fake-png-bytes",
            mime_type="image/png",
        )

        assert isinstance(uploaded, UploadedAsset)
        assert uploaded.id == "101"
        assert uploaded.workspace_id == "123"
        assert uploaded.file_name == "logo.png"
        assert uploaded.gcs_uri == "gs://bucket/logo.png"


@pytest.mark.asyncio
async def test_get_asset_uploaded_and_generated(cs_asset_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # 1. Uploaded source asset response
        resp_source = MagicMock()
        resp_source.status_code = 200
        resp_source.json.return_value = {
            "id": 201,
            "workspaceId": 123,
            "fileName": "ref.jpg",
            "gcsUri": "gs://bucket/ref.jpg",
            "mimeType": "image/jpeg",
            "itemType": "source_asset",
        }
        resp_source.raise_for_status.return_value = None

        mock_client.get.return_value = resp_source
        ref_uploaded = AssetRef(id="201", asset_type="uploaded", workspace_id="123")
        asset1 = await cs_asset_service.get_asset(ref_uploaded)

        assert isinstance(asset1, UploadedAsset)
        assert asset1.id == "201"
        assert asset1.file_name == "ref.jpg"

        # 2. Generated media item response
        resp_media = MagicMock()
        resp_media.status_code = 200
        resp_media.json.return_value = {
            "id": 301,
            "workspaceId": 123,
            "fileName": "gen_image.png",
            "gcsUris": ["gs://bucket/gen_image.png"],
            "mimeType": "image/png",
            "status": "completed",
            "durationSeconds": 5.0,
            "itemType": "media_item",
            "generationModel": "imagen-3.0-generate-002",
            "prompt": "A beautiful sunset",
        }
        resp_media.raise_for_status.return_value = None

        mock_client.get.return_value = resp_media
        ref_generated = AssetRef(id="301", asset_type="generated", workspace_id="123")
        asset2 = await cs_asset_service.get_asset(ref_generated)

        assert isinstance(asset2, GeneratedAsset)
        assert asset2.id == "301"
        assert asset2.duration_seconds == 5.0
        assert asset2.generation_metadata.model == "imagen-3.0-generate-002"

        # 3. Missing asset returns None (404)
        resp_404 = MagicMock()
        resp_404.status_code = 404
        mock_client.get.return_value = resp_404

        ref_missing = AssetRef(id="999", asset_type="generated", workspace_id="123")
        asset3 = await cs_asset_service.get_asset(ref_missing)
        assert asset3 is None


@pytest.mark.asyncio
async def test_search_assets(cs_asset_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        resp_search = MagicMock()
        resp_search.status_code = 200
        resp_search.json.return_value = [
            {
                "id": 1,
                "workspaceId": 123,
                "fileName": "a1.png",
                "gcsUri": "gs://b/a1.png",
                "itemType": "source_asset",
            },
            {
                "id": 2,
                "workspaceId": 123,
                "fileName": "a2.png",
                "gcsUris": ["gs://b/a2.png"],
                "itemType": "media_item",
            },
        ]
        resp_search.raise_for_status.return_value = None
        mock_client.post.return_value = resp_search

        results = await cs_asset_service.search_assets(
            workspace_id="123",
            query="logo",
            asset_type="uploaded",
            limit=10,
        )

        assert len(results) == 2
        assert isinstance(results[0], UploadedAsset)
        assert isinstance(results[1], GeneratedAsset)


@pytest.mark.asyncio
async def test_delete_asset(cs_asset_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        resp_delete = MagicMock()
        resp_delete.status_code = 200
        resp_delete.raise_for_status.return_value = None
        mock_client.delete.return_value = resp_delete
        mock_client.post.return_value = resp_delete

        # 1. Delete uploaded asset
        await cs_asset_service.delete_asset(
            AssetRef(id="201", asset_type="uploaded", workspace_id="123")
        )

        # 2. Delete generated asset
        await cs_asset_service.delete_asset(
            AssetRef(id="301", asset_type="generated", workspace_id="123")
        )

        # 3. Delete missing asset raises NotFoundError
        resp_404 = MagicMock()
        resp_404.status_code = 404
        mock_client.delete.return_value = resp_404

        with pytest.raises(NotFoundError):
            await cs_asset_service.delete_asset(
                AssetRef(id="999", asset_type="uploaded", workspace_id="123")
            )


@pytest.mark.asyncio
async def test_download_asset_bytes_success(cs_asset_service):
    ref = AssetRef(id="101", asset_type="uploaded", workspace_id="123")

    mock_asset = UploadedAsset(
        id="101",
        workspace_id="123",
        user_id="456",
        file_name="logo.png",
        gcs_uri="gs://bucket/logo.png",
        mime_type="image/png",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )

    with patch.object(
        cs_asset_service, "get_asset", AsyncMock(return_value=mock_asset)
    ):
        with patch("google.cloud.storage.Client") as mock_storage_client_cls:
            mock_storage_client = MagicMock()
            mock_storage_client_cls.return_value = mock_storage_client
            mock_bucket = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_blob = MagicMock()
            mock_bucket.blob.return_value = mock_blob
            mock_blob.download_as_bytes.return_value = b"test-file-bytes"

            data = await cs_asset_service.download_asset_bytes(ref)

            assert data == b"test-file-bytes"
            mock_storage_client_cls.assert_called_once_with(project="test-project")
            mock_storage_client.bucket.assert_called_once_with("bucket")
            mock_bucket.blob.assert_called_once_with("logo.png")
            mock_blob.download_as_bytes.assert_called_once()


@pytest.mark.asyncio
async def test_download_asset_bytes_not_found(cs_asset_service):
    ref = AssetRef(id="999", asset_type="uploaded", workspace_id="123")

    with patch.object(cs_asset_service, "get_asset", AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError) as exc_info:
            await cs_asset_service.download_asset_bytes(ref)
        assert "Asset not found for download" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_asset_bytes_missing_gcs_uri(cs_asset_service):
    ref = AssetRef(id="101", asset_type="uploaded", workspace_id="123")

    mock_asset = UploadedAsset(
        id="101",
        workspace_id="123",
        user_id="456",
        file_name="logo.png",
        gcs_uri="",
        mime_type="image/png",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )

    with patch.object(
        cs_asset_service, "get_asset", AsyncMock(return_value=mock_asset)
    ):
        with pytest.raises(ValidationError) as exc_info:
            await cs_asset_service.download_asset_bytes(ref)
        assert "missing gcs_uri for download" in str(exc_info.value)
