import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext
from google.genai import types

@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    return context


@pytest.fixture
def mock_asset_service():
    service = AsyncMock()
    return service


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_load_asset_and_save_as_artifact_success_by_id(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    # Mock asset service to return a blob
    mock_blob = MagicMock()
    mock_blob.file_name = "image.png"
    mock_blob.content = b"fake content"
    mock_blob.mime_type = "image/png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    from creative_toolbox.tools.asset_tools import load_asset_and_save_as_artifact

    result = await load_asset_and_save_as_artifact(
        mock_tool_context, asset_id="asset_1"
    )

    assert "Asset loaded as session artifact: image.png" in result
    mock_asset_service.get_asset_blob.assert_called_once_with(asset_id="asset_1")
    mock_tool_context.save_artifact.assert_called_once()


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_load_asset_and_save_as_artifact_success_by_filename(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    # Mock list_assets to find the asset by filename
    asset1 = MagicMock()
    asset1.file_name = "image.png"
    asset1.id = "asset_1"
    mock_asset_service.list_assets.return_value = [asset1]

    # Mock get_asset_blob
    mock_blob = MagicMock()
    mock_blob.file_name = "image.png"
    mock_blob.content = b"fake content"
    mock_blob.mime_type = "image/png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    from creative_toolbox.tools.asset_tools import load_asset_and_save_as_artifact

    result = await load_asset_and_save_as_artifact(
        mock_tool_context, filename="image.png"
    )

    assert "Asset loaded as session artifact: image.png" in result
    mock_asset_service.list_assets.assert_called_once_with(user_id="user_123")
    mock_asset_service.get_asset_blob.assert_called_once_with(asset_id="asset_1")


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_load_asset_and_save_as_artifact_with_version(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    mock_blob = MagicMock()
    mock_blob.file_name = "image_v2.png"
    mock_blob.content = b"fake content"
    mock_blob.mime_type = "image/png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    from creative_toolbox.tools.asset_tools import load_asset_and_save_as_artifact

    result = await load_asset_and_save_as_artifact(
        mock_tool_context, asset_id="asset_1", version=2
    )

    assert "Asset loaded as session artifact: image_v2.png" in result
    mock_asset_service.get_asset_blob.assert_called_once_with(asset_id="asset_1", version=2)


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_load_asset_and_save_as_artifact_not_found(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    mock_asset_service.list_assets.return_value = []

    from creative_toolbox.tools.asset_tools import load_asset_and_save_as_artifact

    result = await load_asset_and_save_as_artifact(
        mock_tool_context, filename="missing.png"
    )

    assert "Error: Asset with filename 'missing.png' not found." in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_load_asset_and_save_as_artifact_missing_args(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    from creative_toolbox.tools.asset_tools import load_asset_and_save_as_artifact

    result = await load_asset_and_save_as_artifact(mock_tool_context)

    assert "Error: Either asset_id or filename must be provided." in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_list_assets_success(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    asset1 = MagicMock()
    asset1.file_name = "asset1.mp4"
    asset1.id = "id1"
    asset1.mime_type = "video/mp4"
    asset1.current_version = 1

    asset2 = MagicMock()
    asset2.file_name = "asset2.jpg"
    asset2.id = "id2"
    asset2.mime_type = "image/jpeg"
    asset2.current_version = 2

    mock_asset_service.list_assets.return_value = [asset1, asset2]

    from creative_toolbox.tools.asset_tools import list_assets

    result = await list_assets(mock_tool_context)

    assets = json.loads(result)
    assert len(assets) == 2
    assert assets[0]["file_name"] == "asset1.mp4"
    assert assets[1]["asset_id"] == "id2"


@pytest.mark.asyncio
@patch("creative_toolbox.tools.asset_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_list_assets_empty(
    mock_get_asset_service,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_asset_service.return_value = mock_asset_service

    mock_asset_service.list_assets.return_value = []

    from creative_toolbox.tools.asset_tools import list_assets

    result = await list_assets(mock_tool_context)

    assert "No assets found for the current user." in result
