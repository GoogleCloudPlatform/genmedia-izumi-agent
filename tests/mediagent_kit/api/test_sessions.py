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
from google.adk.sessions.session import Session
from google.api_core import exceptions as gcp_exceptions
from unittest.mock import AsyncMock, MagicMock

from mediagent_kit.api.sessions import (
    derive_session_title,
    router,
    get_session_service,
)
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

    response = client.get("/workspaces/user_1/sessions")
    assert response.status_code == 200
    data = response.json()
    # It should filter out the eval session
    assert len(data) == 1
    assert data[0]["id"] == "session_1"


def _session(session_id="s-1", state=None):
    return Session(
        id=session_id,
        app_name="ads_x",
        user_id="user_1",
        state=state or {},
        last_update_time=0.0,
    )


def test_title_skips_the_opening_greeting():
    """New chats open with "Hi", which would otherwise name every chat."""
    assert (
        derive_session_title(["Hi", "Make an ad for Dior foundation"])
        == "Make an ad for Dior foundation"
    )


def test_a_long_message_is_cut_at_a_word_boundary():
    title = derive_session_title(
        [
            "Create a 12-second vertical 9:16 video ad for Dior Forever "
            "foundation. Luxurious and radiant."
        ]
    )

    assert title == "Create a 12-second vertical 9:16 video ad for Dior Forever…"


def test_no_title_when_there_is_only_a_greeting():
    assert derive_session_title(["Hi", "hello!"]) is None


def test_markdown_is_not_shown_in_a_title():
    """A brief pasted from the template opens with a bold heading."""
    title = derive_session_title(["**Bespoke Creative (AI Director)** *For an ad*"])

    assert title == "Bespoke Creative (AI Director) For an ad"


def test_an_untitled_session_is_listed_under_its_first_request(
    client, mock_session_service
):
    mock_session_service.list_sessions.return_value = MagicMock(sessions=[_session()])
    mock_session_service.list_opening_user_texts.return_value = [
        "Hi",
        "Make an ad for Dior foundation",
    ]

    data = client.get("/workspaces/user_1/sessions").json()

    assert data[0]["state"]["session_title_derived"] == (
        "Make an ad for Dior foundation"
    )
    mock_session_service.set_session_title.assert_awaited_once_with(
        app_name="ads_x",
        user_id="user_1",
        session_id="s-1",
        title="Make an ad for Dior foundation",
        derived=True,
    )


def test_a_derived_title_is_not_derived_again(client, mock_session_service):
    mock_session_service.list_sessions.return_value = MagicMock(
        sessions=[_session(state={"session_title_derived": "Make an ad"})]
    )

    client.get("/workspaces/user_1/sessions")

    mock_session_service.list_opening_user_texts.assert_not_awaited()


def test_a_titled_session_is_not_derived_again(client, mock_session_service):
    mock_session_service.list_sessions.return_value = MagicMock(
        sessions=[_session(state={"session_title": "Dior launch"})]
    )

    data = client.get("/workspaces/user_1/sessions").json()

    assert data[0]["state"]["session_title"] == "Dior launch"
    mock_session_service.list_opening_user_texts.assert_not_awaited()
    mock_session_service.set_session_title.assert_not_awaited()


def test_a_failed_derivation_still_lists_the_session(client, mock_session_service):
    mock_session_service.list_sessions.return_value = MagicMock(sessions=[_session()])
    mock_session_service.list_opening_user_texts.side_effect = RuntimeError("down")

    response = client.get("/workspaces/user_1/sessions")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "s-1"


def test_rename_stores_the_title(client, mock_session_service):
    response = client.patch(
        "/workspaces/user_1/sessions/s-1",
        json={"appName": "ads_x", "title": "  Dior   launch  "},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "s-1", "title": "Dior launch"}
    mock_session_service.set_session_title.assert_awaited_once_with(
        app_name="ads_x", user_id="user_1", session_id="s-1", title="Dior launch"
    )


def test_rename_refuses_an_empty_title(client, mock_session_service):
    response = client.patch(
        "/workspaces/user_1/sessions/s-1", json={"appName": "ads_x", "title": "   "}
    )

    assert response.status_code == 422
    mock_session_service.set_session_title.assert_not_awaited()


def test_renaming_a_missing_session_is_not_found(client, mock_session_service):
    mock_session_service.set_session_title.side_effect = gcp_exceptions.NotFound(
        "no such document"
    )

    response = client.patch(
        "/workspaces/user_1/sessions/s-1", json={"appName": "ads_x", "title": "X"}
    )

    assert response.status_code == 404


async def test_a_rename_leaves_last_update_time_alone():
    """append_event rejects a session whose stored time is newer than its own.

    A rename that changed last_update_time would fail a run in progress, so it
    writes the title field and nothing else.
    """
    db = MagicMock()
    service = FirestoreSessionService(
        db=db, asset_service=MagicMock(), config=MagicMock()
    )

    await service.set_session_title(
        app_name="ads_x", user_id="user_1", session_id="s-1", title="Dior launch"
    )

    db.collection.assert_called_with("adk_sessions")
    db.collection.return_value.document.assert_called_with("ads_x_user_1_s-1")
    db.collection.return_value.document.return_value.update.assert_called_once_with(
        {"state.session_title": "Dior launch"}
    )


async def test_opening_texts_keep_only_user_messages_with_text():
    def doc(data):
        return MagicMock(to_dict=MagicMock(return_value=data))

    db = MagicMock()
    events = db.collection.return_value.document.return_value.collection.return_value
    events.order_by.return_value.limit.return_value.stream.return_value = [
        doc({"author": "user", "content": {"parts": [{"text": "Hi"}]}}),
        doc({"author": "ads_x_agent", "content": {"parts": [{"text": "Hello!"}]}}),
        doc({"author": "user", "content": {"parts": [{"function_response": {}}]}}),
        doc(
            {
                "author": "user",
                "content": {"parts": [{"inline_data": {}}, {"text": "Make a Dior ad"}]},
            }
        ),
    ]
    service = FirestoreSessionService(
        db=db, asset_service=MagicMock(), config=MagicMock()
    )

    texts = await service.list_opening_user_texts(
        app_name="ads_x", user_id="user_1", session_id="s-1"
    )

    assert texts == ["Hi", "Make a Dior ad"]
    events.order_by.assert_called_once_with("timestamp")
