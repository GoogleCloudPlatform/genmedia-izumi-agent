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

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from mediagent_kit.api.assets import router, get_asset_service, get_async_asset_service
from mediagent_kit.services import AssetService
from mediagent_kit.services.aio import AsyncAssetService

app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_asset_service():
    return MagicMock(spec=AssetService)


@pytest.fixture
def mock_async_asset_service():
    return AsyncMock(spec=AsyncAssetService)


@pytest.fixture
def client(mock_asset_service, mock_async_asset_service):
    app.dependency_overrides[get_asset_service] = lambda: mock_asset_service
    app.dependency_overrides[get_async_asset_service] = lambda: mock_async_asset_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_assets_success(client, mock_asset_service):
    # Using a real Asset model for return value
    from mediagent_kit.api.types import Asset
    
    asset = Asset(
        id="asset_1",
        user_id="user_1",
        mime_type="image/png",
        file_name="test.png",
        current_version=1,
        versions=[]
    )
    mock_asset_service.list_assets.return_value = [asset]

    response = client.get("/users/user_1/assets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_update_asset_success(client, mock_asset_service):
    from mediagent_kit.api.types import Asset

    mock_asset = MagicMock()
    mock_asset.user_id = "user_1"
    mock_asset_service.get_asset_by_id.return_value = mock_asset

    updated_mock_asset = Asset(
        id="asset_1",
        user_id="user_1",
        file_name="test.png",
        mime_type="image/png",
        size_bytes=100,
        current_version=1,
        versions=[],
    )
    mock_asset_service.update_asset.return_value = updated_mock_asset

    response = client.patch("/users/user_1/assets/asset_1", json={"file_name": "updated.png"})
    assert response.status_code == 200


def test_download_asset_success(client, mock_asset_service):
    mock_asset = MagicMock()
    mock_asset.user_id = "user_1"
    mock_asset_service.get_asset_by_id.return_value = mock_asset

    mock_blob = MagicMock()
    mock_blob.content = b"fake content"
    mock_blob.mime_type = "image/png"
    mock_blob.file_name = "test.png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    response = client.get("/users/user_1/assets/asset_1/download")
    assert response.status_code == 200
    assert response.content == b"fake content"


def test_view_asset_redirect(client, mock_asset_service):
    mock_asset = MagicMock()
    mock_asset.user_id = "user_1"
    mock_asset.current_version = 1
    mock_asset_service.get_asset_by_id.return_value = mock_asset

    response = client.get("/users/user_1/assets/asset_1/view", follow_redirects=False)
    assert response.status_code == 307
    assert "version=1" in response.headers["location"]


def test_get_asset_success(client, mock_asset_service):
    from mediagent_kit.api.types import Asset
    
    asset = Asset(
        id="asset_1",
        user_id="user_1",
        mime_type="image/png",
        file_name="test.png",
        current_version=1,
        versions=[]
    )
    mock_asset_service.get_asset_by_id.return_value = asset

    response = client.get("/users/user_1/assets/asset_1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "asset_1"


def test_get_asset_not_found(client, mock_asset_service):
    mock_asset_service.get_asset_by_id.return_value = None

    response = client.get("/users/user_1/assets/asset_1")
    assert response.status_code == 404


def test_create_asset_success(client, mock_async_asset_service):
    from mediagent_kit.api.types import Asset
    
    asset = Asset(
        id="asset_1",
        user_id="user_1",
        mime_type="image/png",
        file_name="test.png",
        current_version=1,
        versions=[]
    )
    mock_async_asset_service.save_asset.return_value = asset

    # Test file upload
    files = {"file": ("test.png", b"fake content", "image/png")}
    data = {"file_name": "test.png", "mime_type": "image/png"}
    
    response = client.post("/users/user_1/assets", files=files, data=data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "asset_1"


def test_delete_asset_success(client, mock_asset_service):
    mock_asset = MagicMock()
    mock_asset.user_id = "user_1"
    mock_asset_service.get_asset_by_id.return_value = mock_asset

    response = client.delete("/users/user_1/assets/asset_1")
    assert response.status_code == 204
    mock_asset_service.delete_asset.assert_called_once_with("asset_1")


