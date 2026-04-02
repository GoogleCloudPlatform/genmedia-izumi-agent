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
from unittest.mock import AsyncMock, MagicMock

from mediagent_kit.api.sessions import router, get_session_service
from mediagent_kit.services.aio import FirestoreSessionService

app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_session_service():
    return AsyncMock(spec=FirestoreSessionService)


@pytest.fixture
def client(mock_session_service):
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_sessions_success(client, mock_session_service):
    # We mock the response of list_sessions which should have a .sessions attribute
    # Since we don't know the exact structure of Session, we use a MagicMock
    # and hope FastAPI can serialize it or we might need to adjust based on failures.
    
    mock_session = MagicMock()
    mock_session.id = "session_1"
    mock_session.appName = "test_app"
    mock_session.userId = "user_1"
    mock_session.state = {}
    
    mock_eval_session = MagicMock()
    mock_eval_session.id = "___eval___session___1"
    mock_eval_session.appName = "test_app"
    mock_eval_session.userId = "user_1"
    mock_eval_session.state = {}

    mock_response = MagicMock()
    mock_response.sessions = [mock_session, mock_eval_session]
    mock_session_service.list_sessions.return_value = mock_response

    response = client.get("/users/user_1/sessions")
    assert response.status_code == 200
    data = response.json()
    # It should filter out the eval session
    assert len(data) == 1
    assert data[0]["id"] == "session_1"
