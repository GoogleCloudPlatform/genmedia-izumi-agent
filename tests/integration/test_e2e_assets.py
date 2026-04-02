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
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_e2e_asset_lifecycle(client: TestClient):
    """
    Verifies the full lifecycle of an asset:
    1. Upload via POST /users/{user_id}/assets
    2. Verification via GET /users/{user_id}/assets/{asset_id}
    3. Cleanup via DELETE /users/{user_id}/assets/{asset_id}
    """
    user_id = "test_user_e2e_lifecycle"
    file_name = "test_e2e_text_asset.txt"
    file_content = b"Hello from E2E automated test!"
    mime_type = "text/plain"

    # --- 1. Upload Asset ---
    files = {"file": (file_name, file_content, mime_type)}
    data = {"file_name": file_name, "mime_type": mime_type}

    response = client.post(f"/users/{user_id}/assets", files=files, data=data)
    assert response.status_code == 200, f"Upload failed: {response.text}"

    asset_data = response.json()
    asset_id = asset_data["id"]
    assert asset_id is not None
    assert asset_data["file_name"] == file_name

    # --- 2. Get Asset ---
    response = client.get(f"/users/{user_id}/assets/{asset_id}")
    assert response.status_code == 200
    get_data = response.json()
    assert get_data["id"] == asset_id
    assert get_data["file_name"] == file_name

    # --- 3. Delete Asset ---
    response = client.delete(f"/users/{user_id}/assets/{asset_id}")
    assert response.status_code == 204

    # --- 4. Verify Deletion ---
    response = client.get(f"/users/{user_id}/assets/{asset_id}")
    assert response.status_code == 404
