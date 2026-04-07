import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {
        "storyboard": {
            "scenes": [
                {
                    "first_frame_prompt": {"asset_id": "asset_img_1"},
                    "video_prompt": {"asset_id": "asset_vid_1", "duration_seconds": 5},
                    "voiceover_prompt": {"asset_id": "asset_vo_1"},
                    "topic": "Scene 1",
                }
            ],
            "background_music_prompt": {"asset_id": "asset_bgm_1"},
        },
        "parameters": {"template_name": "Custom"},
    }
    return context


@pytest.fixture
def mock_asset_service():
    service = AsyncMock()
    # Mock get_asset_by_id to return a mock asset with current.duration_seconds
    mock_asset = MagicMock()
    mock_asset.id = "mock_asset_id"
    mock_asset.file_name = "mock_file.mp4"
    mock_asset.current.duration_seconds = 5
    mock_asset.current.video_generate_config.generate_audio = False
    service.get_asset_by_id.return_value = mock_asset
    return service


@pytest.fixture
def mock_stitching_service():
    service = AsyncMock()
    mock_stitched_asset = MagicMock()
    mock_stitched_asset.id = "stitched_vid_1"
    service.stitch_video.return_value = mock_stitched_asset
    return service


@pytest.fixture
def mock_canvas_service():
    service = AsyncMock()
    mock_canvas = MagicMock()
    mock_canvas.id = "canvas_123"
    service.create_canvas.return_value = mock_canvas
    return service


@pytest.mark.asyncio
@patch("ads_x_template.tools.generation.stitching_tools.get_user_id_from_context")
@patch("ads_x_template.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("ads_x_template.tools.generation.stitching_tools.display_asset")
@patch(
    "ads_x_template.tools.generation.stitching_tools.template_library.get_template_by_name"
)
async def test_stitch_final_video_success(
    mock_get_template,
    mock_display_asset,
    mock_get_canvas_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_session_id.return_value = "session_123"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Mock template
    mock_template = MagicMock()
    mock_template.industry_type = "Standard"
    mock_get_template.return_value = mock_template

    mock_display_asset.return_value = "Success"

    from ads_x_template.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    assert "View Video Timeline in Izumi Studio" in result["result"]
    mock_stitching_service.stitch_video.assert_called_once()
    mock_canvas_service.create_canvas.assert_called_once()


@pytest.mark.asyncio
@patch("ads_x_template.tools.generation.stitching_tools.get_user_id_from_context")
@patch("ads_x_template.tools.generation.stitching_tools.get_session_id_from_context")
async def test_stitch_final_video_missing_storyboard(
    mock_get_session_id,
    mock_get_user_id,
    mock_tool_context,
):
    mock_tool_context.state = {}  # Empty state

    from ads_x_template.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "failed"
    assert "Missing storyboard" in result["error_message"]


@pytest.mark.asyncio
@patch("ads_x_template.tools.generation.stitching_tools.get_user_id_from_context")
@patch("ads_x_template.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("ads_x_template.tools.generation.stitching_tools.display_asset")
@patch(
    "ads_x_template.tools.generation.stitching_tools.template_library.get_template_by_name"
)
async def test_stitch_final_video_ugc_logic(
    mock_get_template,
    mock_display_asset,
    mock_get_canvas_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_get_user_id,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_session_id.return_value = "session_123"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Mock template as Social Native (UGC)
    mock_template = MagicMock()
    mock_template.industry_type = "Social Native"
    mock_get_template.return_value = mock_template

    mock_display_asset.return_value = "Success"

    from ads_x_template.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    # Verify that it used Strategy B (per-scene voiceover or video audio)
    # In UGC mode, it should log "Using Per-Scene Voiceover Strategy"
    # We can check if audio clips were added correctly (mock timeline call parameters)
    # The timeline is passed to stitch_video, we can inspect it.
    called_timeline = mock_stitching_service.stitch_video.call_args[1]["timeline"]
    assert len(called_timeline.audio_clips) > 0  # Should have audio clips
