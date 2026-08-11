import pytest
from fastapi.testclient import TestClient
from mediagent_kit.api.types import Asset
from mediagent_kit.api.assets import get_asset_service, get_async_asset_service


class DummyAssetService:
    def __init__(self):
        self.assets = {}

    async def save_asset(self, user_id, file_name, blob, mime_type, **kwargs):
        asset = Asset(
            id="test_asset_123",
            user_id=user_id,
            mime_type=mime_type,
            file_name=file_name,
            current_version=1,
            versions=[],
        )
        self.assets[asset.id] = asset
        return asset

    def get_asset_by_id(self, asset_id):
        return self.assets.get(asset_id)

    def delete_asset(self, asset_id):
        if asset_id in self.assets:
            del self.assets[asset_id]
            return True
        return False


@pytest.fixture
def dummy_asset_service():
    return DummyAssetService()


@pytest.mark.integration
def test_e2e_asset_lifecycle(client: TestClient, dummy_asset_service):
    from demos.backend.main import app

    app.dependency_overrides[get_asset_service] = lambda: dummy_asset_service
    app.dependency_overrides[get_async_asset_service] = lambda: dummy_asset_service

    workspace_id = "workspace_e2e_lifecycle"
    file_name = "test_e2e_text_asset.txt"
    file_content = b"Hello from E2E automated test!"
    mime_type = "text/plain"

    files = {"file": (file_name, file_content, mime_type)}
    data = {"file_name": file_name, "mime_type": mime_type}

    response = client.post(f"/workspaces/{workspace_id}/assets", files=files, data=data)
    assert response.status_code == 200, f"Upload failed: {response.text}"

    asset_data = response.json()
    asset_id = asset_data["id"]
    assert asset_id is not None
    assert asset_data["file_name"] == file_name

    response = client.get(f"/workspaces/{workspace_id}/assets/{asset_id}")
    assert response.status_code == 200
    get_data = response.json()
    assert get_data["id"] == asset_id
    assert get_data["file_name"] == file_name

    response = client.delete(f"/workspaces/{workspace_id}/assets/{asset_id}")
    assert response.status_code == 204

    response = client.get(f"/workspaces/{workspace_id}/assets/{asset_id}")
    assert response.status_code == 404

    app.dependency_overrides.clear()
