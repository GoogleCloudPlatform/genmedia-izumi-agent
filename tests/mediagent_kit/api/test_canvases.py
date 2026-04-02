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
from unittest.mock import MagicMock

from mediagent_kit.api.canvases import router, get_canvas_service, get_asset_service
from mediagent_kit.services import CanvasService, AssetService
from mediagent_kit.api.types import Canvas

app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_canvas_service():
    return MagicMock(spec=CanvasService)


@pytest.fixture
def mock_asset_service():
    return MagicMock(spec=AssetService)


@pytest.fixture
def client(mock_canvas_service, mock_asset_service):
    app.dependency_overrides[get_canvas_service] = lambda: mock_canvas_service
    app.dependency_overrides[get_asset_service] = lambda: mock_asset_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_canvases_success(client, mock_canvas_service):
    mock_canvas = MagicMock()
    mock_canvas.id = "canvas_1"
    mock_canvas.title = "Test Canvas"
    mock_canvas.user_id = "user_1"
    mock_canvas.video_timeline = None
    mock_canvas_service.list_canvases.return_value = [mock_canvas]

    response = client.get("/users/user_1/canvases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "canvas_1"
    assert data[0]["title"] == "Test Canvas"


def test_get_canvas_success(client, mock_canvas_service):
    mock_canvas = MagicMock()
    mock_canvas.id = "canvas_1"
    mock_canvas.title = "Test Canvas"
    mock_canvas.user_id = "user_1"
    mock_canvas.video_timeline = None
    mock_canvas.html = None
    mock_canvas_service.get_canvas.return_value = mock_canvas

    response = client.get("/users/user_1/canvases/canvas_1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "canvas_1"


def test_get_canvas_not_found(client, mock_canvas_service):
    mock_canvas_service.get_canvas.return_value = None

    response = client.get("/users/user_1/canvases/canvas_1")
    assert response.status_code == 404


def test_get_canvas_wrong_user(client, mock_canvas_service):
    mock_canvas = MagicMock()
    mock_canvas.id = "canvas_1"
    mock_canvas.user_id = "user_2"
    mock_canvas_service.get_canvas.return_value = mock_canvas

    response = client.get("/users/user_1/canvases/canvas_1")
    assert response.status_code == 404


def test_delete_canvas_success(client, mock_canvas_service):
    mock_canvas = MagicMock()
    mock_canvas.user_id = "user_1"
    mock_canvas_service.get_canvas.return_value = mock_canvas

    response = client.delete("/users/user_1/canvases/canvas_1")
    assert response.status_code == 204
    mock_canvas_service.delete_canvas.assert_called_once_with("canvas_1")


def test_update_canvas_success(client, mock_canvas_service):
    mock_canvas = MagicMock()
    mock_canvas.user_id = "user_1"
    mock_canvas_service.get_canvas.return_value = mock_canvas
    
    updated_canvas = MagicMock()
    updated_canvas.id = "canvas_1"
    updated_canvas.title = "Updated Title"
    updated_canvas.user_id = "user_1"
    updated_canvas.video_timeline = None
    updated_canvas.html = None
    mock_canvas_service.update_canvas.return_value = updated_canvas

    response = client.patch(
        "/users/user_1/canvases/canvas_1", json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


def test_view_canvas_success(client, mock_canvas_service, mock_asset_service):
    from mediagent_kit.api.types import Html

    mock_canvas = MagicMock()
    mock_canvas.user_id = "user_1"
    mock_canvas.html = Html(content='<img src="asset://test.png" />', asset_ids=["asset_1"])
    mock_canvas_service.get_canvas.return_value = mock_canvas

    mock_asset = MagicMock()
    mock_asset.id = "asset_1"
    mock_asset.file_name = "test.png"
    mock_asset_service.list_assets.return_value = [mock_asset]

    response = client.get("/users/user_1/canvases/canvas_1/view")
    assert response.status_code == 200
    assert "/users/user_1/assets/asset_1/view" in response.text


def test_view_canvas_not_found(client, mock_canvas_service):
    mock_canvas_service.get_canvas.return_value = None

    response = client.get("/users/user_1/canvases/canvas_1/view")
    assert response.status_code == 404
