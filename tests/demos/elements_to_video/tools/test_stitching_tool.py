import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext

@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


@pytest.fixture
def mock_canvas_service():
    return AsyncMock()


@pytest.fixture
def mock_stitching_service():
    return AsyncMock()


@pytest.mark.asyncio
@patch("elements_to_video.tools.stitching_tool.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
async def test_stitch_final_video_success(
    mock_get_stitching_service,
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
    mock_stitching_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_stitching_service.return_value = mock_stitching_service

    # Setup state
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_456"

    # Mock canvas
    mock_canvas = MagicMock()
    mock_timeline = MagicMock()
    mock_timeline.title = "My Awesome Video"
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    # Mock stitching result
    mock_asset = MagicMock()
    mock_asset.file_name = "My_Awesome_Video.mp4"
    mock_asset.to_firestore.return_value = {"file_name": "My_Awesome_Video.mp4"}
    mock_stitching_service.stitch_video.return_value = mock_asset

    from elements_to_video.tools.stitching_tool import stitch_final_video

    result_str = await stitch_final_video(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert result["final_asset_name"] == "My_Awesome_Video.mp4"
    assert mock_tool_context.state["final_video_asset"] == {"file_name": "My_Awesome_Video.mp4"}
    assert mock_tool_context.state["generation_stage"] == "STITCHING_VIDEO"


@pytest.mark.asyncio
@patch("elements_to_video.tools.stitching_tool.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_stitch_final_video_missing_state(
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
):
    # Do not set video_timeline_canvas_id in state

    from elements_to_video.tools.stitching_tool import stitch_final_video

    result_str = await stitch_final_video(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "failure"
    assert "video_timeline_canvas_id not found in state" in result["error_message"]


@pytest.mark.asyncio
@patch("elements_to_video.tools.stitching_tool.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_stitch_final_video_canvas_not_found(
    mock_get_canvas_service,
    mock_get_user_id,
    mock_tool_context,
    mock_canvas_service,
):
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_456"
    
    # Mock get_canvas to return None
    mock_canvas_service.get_canvas.return_value = None

    from elements_to_video.tools.stitching_tool import stitch_final_video

    result_str = await stitch_final_video(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "failure"
    assert "Canvas with id canvas_456 not found" in result["error_message"]
