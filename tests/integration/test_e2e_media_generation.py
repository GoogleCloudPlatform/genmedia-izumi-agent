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

import time
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_e2e_media_generation_polling(client: TestClient):
    """
    Verifies full lifecycle of long-running job generation:
    1. Request image generation via POST /users/{user_id}/media:generate-image-with-gemini
    2. Long-poll GET /users/{user_id}/jobs/{job_id} until COMPLETED
    3. Verify result_asset_id is returned
    """
    user_id = "test_user_e2e_media_polling"
    file_name = "test_gemini_image_e2e.png"

    # --- 1. Submit Generation Job ---
    payload = {
        "prompt": "A beautiful sunset over a cyberpunk city.",
        "aspect_ratio": "1:1",
        "file_name": file_name,
        "model": "gemini-2.5-flash-image",
    }

    response = client.post(
        f"/users/{user_id}/media:generate-image-with-gemini", json=payload
    )
    assert response.status_code == 202, f"Submission failed: {response.text}"

    job_data = response.json()
    job_id = job_data["id"]
    assert job_id is not None
    assert job_data["status"] == "PENDING" or job_data["status"] == "RUNNING"

    # --- 2. Poll Job Status ---
    max_retries = 30
    delay = 2
    completed = False

    for _ in range(max_retries):
        response = client.get(f"/users/{user_id}/jobs/{job_id}")
        assert response.status_code == 200
        job_state = response.json()

        if job_state["status"] == "COMPLETED":
            completed = True
            break
        elif job_state["status"] == "FAILED":
            pytest.fail(f"Job failed with error: {job_state.get('error_message')}")

        time.sleep(delay)

    assert completed, f"Job timed out after {max_retries * delay} seconds"

    # --- 3. Verify Final Result ---
    job_state = response.json()
    assert job_state["result_asset_id"] is not None
