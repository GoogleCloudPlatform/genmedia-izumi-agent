import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from google.adk.sessions.session import Session
from google.adk.events.event import Event

from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_firestore_client():
    client = MagicMock()
    return client


@pytest.fixture
def mock_asset_service():
    return AsyncMock()


@pytest.fixture
def mock_config():
    return MagicMock(spec=MediagentKitConfig)


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_create_session_success(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    # Setup mock firestore client
    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock doc.get() to simulate non-existing session
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_document.get.return_value = mock_doc_snapshot

    # Mock doc.to_dict() for the get() after set()
    mock_created_snapshot = MagicMock()
    mock_created_snapshot.exists = True
    mock_created_snapshot.to_dict.return_value = {"last_update_time": datetime.utcnow()}

    # Mock app state and user state (non-existent in this test)
    mock_app_snapshot = MagicMock()
    mock_app_snapshot.exists = False
    mock_user_snapshot = MagicMock()
    mock_user_snapshot.exists = False

    # Chain get() calls:
    # 1. session check exists
    # 2. session get after set
    # 3. app state get
    # 4. user state get
    mock_document.get.side_effect = [
        mock_doc_snapshot,
        mock_created_snapshot,
        mock_app_snapshot,
        mock_user_snapshot,
    ]

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    session = await service.create_session(
        app_name="test_app", user_id="user_123", state={"key": "value"}
    )

    assert session.id is not None
    assert session.app_name == "test_app"
    assert session.user_id == "user_123"
    assert session.state == {"key": "value"}
    mock_document.set.assert_called_once()


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_get_session_not_found(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_document.get.return_value = mock_doc_snapshot

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    session = await service.get_session(
        app_name="test_app", user_id="user_123", session_id="session_123"
    )

    assert session is None


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_get_session_success_no_events(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock session doc
    mock_session_snapshot = MagicMock()
    mock_session_snapshot.exists = True
    session_data = {
        "user_id": "user_123",
        "state": {"session_key": "session_val"},
        "last_update_time": datetime.utcnow(),
    }
    mock_session_snapshot.to_dict.return_value = session_data

    # Mock app state and user state docs
    mock_app_snapshot = MagicMock()
    mock_app_snapshot.exists = False
    mock_user_snapshot = MagicMock()
    mock_user_snapshot.exists = False

    # document.get side effects: 1. session_doc, 2. app_state_doc, 3. user_state_doc
    mock_document.get.side_effect = [
        mock_session_snapshot,
        mock_app_snapshot,
        mock_user_snapshot,
    ]

    # Mock events stream (empty)
    mock_events_collection = MagicMock()
    mock_document.collection.return_value = mock_events_collection
    mock_events_collection.order_by.return_value = mock_events_collection
    mock_events_collection.stream.return_value = []

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    session = await service.get_session(
        app_name="test_app", user_id="user_123", session_id="session_123"
    )

    assert session is not None
    assert session.id == "session_123"
    assert session.state == {"session_key": "session_val"}
    assert session.events == []


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_append_event_success(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    # Bypass the transactional decorator
    mock_firestore_module.transactional.side_effect = lambda x: x

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock session snapshot inside transaction
    mock_session_snapshot = MagicMock()
    mock_session_snapshot.exists = True
    from datetime import datetime

    fixed_time = datetime(2026, 1, 1)
    mock_session_snapshot.to_dict.return_value = {"last_update_time": fixed_time}

    # Mock transaction.get to return a generator/iterator
    mock_transaction = MagicMock()
    mock_firestore_client.transaction.return_value = mock_transaction
    mock_transaction.get.return_value = iter([mock_session_snapshot])

    mock_events_collection = MagicMock()
    mock_document.collection.return_value = mock_events_collection
    mock_event_doc = MagicMock()
    mock_events_collection.document.return_value = mock_event_doc

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    mock_session = MagicMock()
    mock_session.app_name = "test_app"
    mock_session.user_id = "user_123"
    mock_session.id = "session_123"
    mock_session.last_update_time = fixed_time.timestamp()

    mock_event = MagicMock()
    mock_event.partial = False
    mock_event.author = "bot"
    mock_event.content = None
    mock_event.timestamp = fixed_time.timestamp()

    # model_dump should return a dict that can be validated back to Event
    mock_event.model_dump.return_value = {
        "author": "bot",
        "timestamp": fixed_time.timestamp(),
        "id": "event_1",
        "partial": False,
    }
    mock_event.id = "event_1"
    mock_event.actions.state_delta = {"session.key": "value"}

    await service.append_event(session=mock_session, event=mock_event)

    # In Firestore transactional updates, we call transaction.set(ref, data)
    # We should verify it was set on the transaction.
    mock_transaction.set.assert_called()


@pytest.mark.asyncio
async def test_list_sessions_success(
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    mock_collection = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection

    mock_query = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_query.where.return_value = mock_query
    mock_query.order_by.return_value = mock_query

    mock_doc = MagicMock()
    from datetime import datetime

    fixed_time = datetime(2026, 1, 1)
    mock_doc.to_dict.return_value = {
        "session_id": "session_123",
        "app_name": "test_app",
        "user_id": "user_123",
        "state": {"key": "value"},
        "last_update_time": fixed_time,
    }
    mock_query.stream.return_value = [mock_doc]

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    response = await service.list_sessions(app_name="test_app", user_id="user_123")

    assert len(response.sessions) == 1
    assert response.sessions[0].id == "session_123"
    assert response.sessions[0].app_name == "test_app"
    assert response.sessions[0].user_id == "user_123"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_create_session_success_with_state_deltas(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock doc.get() to simulate non-existing session
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False

    # Mock doc.to_dict() for the get() after set()
    mock_created_snapshot = MagicMock()
    mock_created_snapshot.exists = True
    from datetime import datetime

    mock_created_snapshot.to_dict.return_value = {"last_update_time": datetime.utcnow()}

    # Mock app state and user state (existent in this test to verify merge)
    mock_app_snapshot = MagicMock()
    mock_app_snapshot.exists = True
    mock_app_snapshot.to_dict.return_value = {"state": {"app_key": "app_val"}}

    mock_user_snapshot = MagicMock()
    mock_user_snapshot.exists = True
    mock_user_snapshot.to_dict.return_value = {"state": {"user_key": "user_val"}}

    # Chain get() calls
    mock_document.get.side_effect = [
        mock_doc_snapshot,
        mock_created_snapshot,
        mock_app_snapshot,
        mock_user_snapshot,
    ]

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    session = await service.create_session(
        app_name="test_app",
        user_id="user_123",
        state={
            "app.new_app_key": "new_app_val",
            "user.new_user_key": "new_user_val",
            "session_key": "session_val",
        },
    )

    assert session.id is not None
    assert session.app_name == "test_app"
    assert session.user_id == "user_123"
    # Merged state should contain session_state, plus app. and user. from existing docs (wait, the code merges existing state from get, not just deltas? Let's check code)
    # The code says:
    # merged_state.update(session_state)
    # merged_state.update({f"app.{k}": v for k, v in app_state.items()})
    # merged_state.update({f"user.{k}": v for k, v in user_state.items()})
    # So it merges what it FETCHES from DB (which I mocked as app_val and user_val).
    assert session.state == {
        "session_key": "session_val",
        "app.app_key": "app_val",
        "user.user_key": "user_val",
    }

    assert mock_document.set.call_count == 3


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_append_event_with_inline_data(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )
    from google.genai import types as genai_types
    import uuid

    # Bypass the transactional decorator
    mock_firestore_module.transactional.side_effect = lambda x: x

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock session snapshot inside transaction
    mock_session_snapshot = MagicMock()
    mock_session_snapshot.exists = True
    fixed_time = datetime(2026, 1, 1)
    mock_session_snapshot.to_dict.return_value = {"last_update_time": fixed_time}

    mock_transaction = MagicMock()
    mock_firestore_client.transaction.return_value = mock_transaction
    mock_transaction.get.return_value = iter([mock_session_snapshot])

    mock_events_collection = MagicMock()
    mock_document.collection.return_value = mock_events_collection
    mock_event_doc = MagicMock()
    mock_events_collection.document.return_value = mock_event_doc

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    mock_session = MagicMock()
    mock_session.app_name = "test_app"
    mock_session.user_id = "user_123"
    mock_session.id = "session_123"
    mock_session.last_update_time = fixed_time.timestamp()

    # Create an event with inline data
    mock_blob = MagicMock()
    mock_blob.mime_type = "image/png"
    mock_blob.data = b"image_bytes"
    # Set display_name to ensure a predictable filename
    setattr(mock_blob, "display_name", "test_file.png")

    mock_part = MagicMock()
    mock_part.inline_data = mock_blob

    mock_content = MagicMock()
    mock_content.parts = [mock_part]
    mock_content.role = "user"

    mock_event = MagicMock()
    mock_event.partial = False
    mock_event.author = "user"
    mock_event.content = mock_content
    mock_event.timestamp = fixed_time.timestamp()
    mock_event.actions.state_delta = {}
    mock_event.id = "event_1"

    # model_dump side effect to simulate the serialization with modified content
    def mock_model_dump(**kwargs):
        # By the time model_dump is called, event.content should have been modified
        return {
            "author": "user",
            "timestamp": fixed_time.timestamp(),
            "id": "event_1",
            "partial": False,
            "content": {
                "role": "user",
                "parts": [{"text": f"<asset://test_file.png>"}],
            },
        }

    mock_event.model_dump.side_effect = mock_model_dump

    await service.append_event(session=mock_session, event=mock_event)

    # Verify save_asset was called with the correct parameters
    mock_asset_service.save_asset.assert_called_once_with(
        user_id="user_123",
        mime_type="image/png",
        file_name="test_file.png",
        blob=b"image_bytes",
    )

    # Verify transaction.set was called to save the event (event_ref, serializable_dict)
    mock_transaction.set.assert_called()


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.firestore_session_service.firestore")
async def test_get_session_with_asset_references(
    mock_firestore_module,
    mock_firestore_client,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.aio.firestore_session_service import (
        FirestoreSessionService,
    )
    from google.genai import types as genai_types

    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_firestore_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    # Mock session doc
    mock_session_snapshot = MagicMock()
    mock_session_snapshot.exists = True
    session_data = {
        "user_id": "user_123",
        "state": {},
        "last_update_time": datetime.utcnow(),
    }
    mock_session_snapshot.to_dict.return_value = session_data

    # Mock app state and user state docs
    mock_app_snapshot = MagicMock()
    mock_app_snapshot.exists = False
    mock_user_snapshot = MagicMock()
    mock_user_snapshot.exists = False

    mock_document.get.side_effect = [
        mock_session_snapshot,
        mock_app_snapshot,
        mock_user_snapshot,
    ]

    # Mock events stream with one event containing <asset://...>
    mock_events_collection = MagicMock()
    mock_document.collection.return_value = mock_events_collection
    mock_events_collection.order_by.return_value = mock_events_collection

    mock_event_snapshot = MagicMock()
    mock_event_snapshot.id = "event_1"

    event_data = {
        "author": "user",
        "timestamp": datetime.utcnow().timestamp(),
        "partial": False,
        "content": {"role": "user", "parts": [{"text": "<asset://image.png>"}]},
    }
    mock_event_snapshot.to_dict.return_value = event_data
    mock_events_collection.stream.return_value = [mock_event_snapshot]

    # Mock asset service to return asset and blob
    mock_asset = MagicMock()
    mock_asset.id = "asset_456"
    mock_asset_service.get_asset_by_file_name.return_value = mock_asset

    mock_blob = MagicMock()
    mock_blob.content = b"image_bytes"
    mock_blob.mime_type = "image/png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    service = FirestoreSessionService(
        db=mock_firestore_client, asset_service=mock_asset_service, config=mock_config
    )

    session = await service.get_session(
        app_name="test_app", user_id="user_123", session_id="session_123"
    )

    assert session is not None
    assert len(session.events) == 1

    mock_asset_service.get_asset_by_file_name.assert_called_once_with(
        user_id="user_123", file_name="image.png"
    )
    mock_asset_service.get_asset_blob.assert_called_once_with(asset_id="asset_456")
