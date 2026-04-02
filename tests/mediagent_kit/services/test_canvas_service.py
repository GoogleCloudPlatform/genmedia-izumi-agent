import pytest
from unittest.mock import MagicMock, patch
from firebase_admin import firestore
from mediagent_kit.services.canvas_service import CanvasService
from mediagent_kit.services.types import Canvas, VideoTimeline, Html
from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_db():
    return MagicMock(spec=firestore.Client)


@pytest.fixture
def mock_asset_service():
    return MagicMock()


@pytest.fixture
def mock_config():
    return MagicMock(spec=MediagentKitConfig)


@pytest.fixture
def service(mock_db, mock_asset_service, mock_config):
    # Patch self._get_collection to return a mock collection
    with patch.object(CanvasService, "_get_collection") as mock_get_col:
        mock_col = MagicMock()
        mock_get_col.return_value = mock_col
        svc = CanvasService(mock_db, mock_asset_service, mock_config)
        svc.canvases_collection = mock_col  # Ensure it's set
        return svc


def test_create_canvas(service):
    user_id = "user1"
    title = "Test Canvas"
    mock_html = Html(content="<p>Test</p>")

    mock_doc = MagicMock()
    service.canvases_collection.document.return_value = mock_doc

    canvas = service.create_canvas(user_id, title, html=mock_html)

    assert canvas.user_id == user_id
    assert canvas.title == title
    assert canvas.id is not None

    service.canvases_collection.document.assert_called_once_with(canvas.id)
    mock_doc.set.assert_called_once()


def test_get_canvas_exists(service):
    canvas_id = "canvas1"

    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = True
    # types.Canvas.from_firestore expects a dict with 'id' if 'id' is not in data, but Canvas model has id.
    # types.Canvas.from_firestore implementation detail:
    # it might expect 'id' in data or it might set it from doc_id. Let's assume it sets it or expects it.
    mock_doc_snapshot.to_dict.return_value = {
        "id": canvas_id,
        "user_id": "user1",
        "title": "Test Canvas",
        "html": {"content": "<p>Test</p>"},
    }
    mock_doc_ref.get.return_value = mock_doc_snapshot
    service.canvases_collection.document.return_value = mock_doc_ref

    canvas = service.get_canvas(canvas_id)

    assert canvas is not None
    assert canvas.id == canvas_id
    service.canvases_collection.document.assert_called_once_with(canvas_id)


def test_get_canvas_not_found(service):
    canvas_id = "canvas1"

    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_doc_ref.get.return_value = mock_doc_snapshot
    service.canvases_collection.document.return_value = mock_doc_ref

    canvas = service.get_canvas(canvas_id)

    assert canvas is None


def test_list_canvases(service):
    user_id = "user1"

    mock_query = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.to_dict.return_value = {
        "id": "canvas1",
        "user_id": user_id,
        "title": "Test Canvas",
        "html": {"content": "<p>Test</p>"},
    }
    mock_query.stream.return_value = [mock_doc_snapshot]
    service.canvases_collection.where.return_value = mock_query

    canvases = service.list_canvases(user_id)

    assert len(canvases) == 1
    assert canvases[0].id == "canvas1"
    service.canvases_collection.where.assert_called_once()


def test_update_canvas(service):
    canvas_id = "canvas1"

    mock_doc_ref = MagicMock()
    service.canvases_collection.document.return_value = mock_doc_ref

    # Mock get_canvas to return the updated canvas
    updated_canvas = Canvas(
        id=canvas_id,
        user_id="user1",
        title="Updated Title",
        html=Html(content="<p>Updated</p>"),
    )
    with patch.object(service, "get_canvas", return_value=updated_canvas):
        result = service.update_canvas(canvas_id, title="Updated Title")

        assert result.title == "Updated Title"
        mock_doc_ref.update.assert_called_once_with({"title": "Updated Title"})


def test_delete_canvas(service):
    canvas_id = "canvas1"

    mock_doc_ref = MagicMock()
    service.canvases_collection.document.return_value = mock_doc_ref

    service.delete_canvas(canvas_id)

    mock_doc_ref.delete.assert_called_once()
