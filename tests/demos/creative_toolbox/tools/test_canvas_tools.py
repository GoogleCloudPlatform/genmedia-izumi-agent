import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext

# We use patch.dict to mock sys.modules if needed, or just patch the imports.
# Since we are in Execution mode, we can just write the tests.


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    # Mock any needed attributes on ToolContext if necessary
    return context


@pytest.fixture
def mock_canvas_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_asset_service():
    service = AsyncMock()
    return service


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_create_html_canvas_success(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Mock asset service to return empty list (no assets to resolve)
    mock_asset_service.list_assets.return_value = []

    # Mock canvas service to return a created canvas
    created_canvas = MagicMock()
    created_canvas.id = "canvas_789"
    created_canvas.title = "My Canvas"
    mock_canvas_service.create_canvas.return_value = created_canvas

    from creative_toolbox.tools.canvas_tools import create_html_canvas

    result = await create_html_canvas(
        mock_tool_context, title="My Canvas", html_content="<div>Hello</div>"
    )

    assert "HTML canvas 'My Canvas' saved with ID: canvas_789" in result
    mock_canvas_service.create_canvas.assert_called_once()


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_create_html_canvas_with_assets(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Mock asset service to return some assets
    asset1 = MagicMock()
    asset1.file_name = "image1.png"
    asset1.id = "asset_1"
    mock_asset_service.list_assets.return_value = [asset1]

    created_canvas = MagicMock()
    created_canvas.id = "canvas_789"
    created_canvas.title = "My Canvas"
    mock_canvas_service.create_canvas.return_value = created_canvas

    from creative_toolbox.tools.canvas_tools import create_html_canvas

    html_content = '<img src="asset://image1.png"> <img src="asset://image2.png">'
    result = await create_html_canvas(
        mock_tool_context, title="My Canvas", html_content=html_content
    )

    assert "HTML canvas 'My Canvas' saved with ID: canvas_789" in result
    assert "Warning: The following assets were not found: image2.png" in result

    # Verify create_canvas was called with resolved asset_ids
    called_args, called_kwargs = mock_canvas_service.create_canvas.call_args
    assert "html" in called_kwargs
    assert called_kwargs["html"].asset_ids == ["asset_1"]


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_update_canvas_title_success(
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service

    existing_canvas = MagicMock()
    existing_canvas.user_id = "user_123"
    mock_canvas_service.get_canvas.return_value = existing_canvas

    updated_canvas = MagicMock()
    updated_canvas.title = "New Title"
    mock_canvas_service.update_canvas.return_value = updated_canvas

    from creative_toolbox.tools.canvas_tools import update_canvas_title

    result = await update_canvas_title(
        mock_tool_context, canvas_id="canvas_123", title="New Title"
    )

    assert "Canvas 'New Title' (ID: canvas_123) title updated." in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_list_canvases_success(
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service

    canvas1 = MagicMock()
    canvas1.id = "c1"
    canvas1.title = "Canvas 1"
    canvas2 = MagicMock()
    canvas2.id = "c2"
    canvas2.title = "Canvas 2"
    mock_canvas_service.list_canvases.return_value = [canvas1, canvas2]

    from creative_toolbox.tools.canvas_tools import list_canvases

    result = await list_canvases(mock_tool_context)

    canvases = json.loads(result)
    assert len(canvases) == 2
    assert canvases[0]["id"] == "c1"
    assert canvases[1]["title"] == "Canvas 2"


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_update_canvas_html_success(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    existing_canvas = MagicMock()
    existing_canvas.user_id = "user_123"
    mock_canvas_service.get_canvas.return_value = existing_canvas

    updated_canvas = MagicMock()
    updated_canvas.title = "My Canvas"
    mock_canvas_service.update_canvas.return_value = updated_canvas

    mock_asset_service.list_assets.return_value = []

    from creative_toolbox.tools.canvas_tools import update_canvas_html

    result = await update_canvas_html(
        mock_tool_context, canvas_id="canvas_123", html_content="<div>New Content</div>"
    )

    assert "Canvas 'My Canvas' (ID: canvas_123) HTML content updated." in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_update_canvas_title_not_found(
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service

    mock_canvas_service.get_canvas.return_value = None

    from creative_toolbox.tools.canvas_tools import update_canvas_title

    result = await update_canvas_title(
        mock_tool_context, canvas_id="canvas_123", title="New Title"
    )

    assert "Error: Canvas with ID 'canvas_123' not found." in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.canvas_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_update_canvas_html_not_found(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    mock_canvas_service.get_canvas.return_value = None
    mock_asset_service.list_assets.return_value = []

    from creative_toolbox.tools.canvas_tools import update_canvas_html

    result = await update_canvas_html(
        mock_tool_context, canvas_id="canvas_123", html_content="<div>New Content</div>"
    )

    assert "Error: Canvas with ID 'canvas_123' not found." in result
