import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {
        "workspace_id": "1",
        "storyboard": {
            "scenes": [
                {
                    "first_frame_prompt": {
                        "asset_ref": {
                            "id": "asset_img_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        }
                    },
                    "video_prompt": {
                        "asset_ref": {
                            "id": "asset_vid_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        },
                        "duration_seconds": 5,
                    },
                    "voiceover_prompt": {
                        "asset_ref": {
                            "id": "asset_vo_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        }
                    },
                    "topic": "Scene 1",
                }
            ],
            "background_music_prompt": {
                "asset_ref": {
                    "id": "asset_bgm_1",
                    "asset_type": "generated",
                    "workspace_id": "user_123",
                }
            },
        },
        "parameters": {"template_name": "Custom"},
    }
    return context


@pytest.fixture
def mock_asset_service():
    service = AsyncMock()
    # Mock get_asset to return a mock asset with duration_seconds
    mock_asset = MagicMock()
    mock_asset.id = "mock_asset_id"
    mock_asset.file_name = "mock_file.mp4"
    mock_asset.mime_type = "video/mp4"
    mock_asset.duration_seconds = 5
    service.get_asset.return_value = mock_asset
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
@patch("ads_x.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("ads_x.tools.generation.stitching_tools.display_asset")
@patch("ads_x.tools.generation.stitching_tools.template_library.get_template_by_name")
async def test_stitch_final_video_success(
    mock_get_template,
    mock_display_asset,
    mock_get_canvas_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
    mock_canvas_service,
):
    mock_get_session_id.return_value = "session_123"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Mock template
    mock_template = MagicMock()
    mock_template.industry_type = "Standard"
    mock_get_template.return_value = mock_template

    mock_display_asset.return_value = "Success"

    from ads_x.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    assert "View Video Timeline in Izumi Studio" in result["result"]
    mock_stitching_service.stitch_video.assert_called_once()
    mock_canvas_service.create_canvas.assert_called_once()


@pytest.mark.asyncio
@patch("ads_x.tools.generation.stitching_tools.get_session_id_from_context")
async def test_stitch_final_video_missing_storyboard(
    mock_get_session_id,
    mock_tool_context,
):
    mock_tool_context.state = {}  # Empty state

    from ads_x.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "failed"
    assert "Missing storyboard" in result["error_message"]


@pytest.mark.asyncio
@patch("ads_x.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("ads_x.tools.generation.stitching_tools.display_asset")
@patch("ads_x.tools.generation.stitching_tools.template_library.get_template_by_name")
async def test_stitch_final_video_ugc_logic(
    mock_get_template,
    mock_display_asset,
    mock_get_canvas_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
    mock_canvas_service,
):
    mock_get_session_id.return_value = "session_123"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Mock template as Social Native (UGC)
    mock_template = MagicMock()
    mock_template.industry_type = "Social Native"
    mock_get_template.return_value = mock_template

    mock_display_asset.return_value = "Success"

    from ads_x.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    # Verify that it used Strategy B (per-scene voiceover or video audio)
    # In UGC mode, it should log "Using Per-Scene Voiceover Strategy"
    # We can check if audio clips were added correctly (mock timeline call parameters)
    # The timeline is passed to stitch_video, we can inspect it.
    called_timeline = mock_stitching_service.stitch_video.call_args[1]["timeline"]
    assert len(called_timeline.audio_clips) > 0  # Should have audio clips


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_config")
@patch("ads_x.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_video_timeline_service")
@patch("mediagent_kit.services.aio.get_storyboard_service")
@patch("ads_x.tools.generation.stitching_tools.display_asset")
@patch("ads_x.tools.generation.stitching_tools.template_library.get_template_by_name")
async def test_stitch_final_video_creative_studio_link(
    mock_get_template,
    mock_display_asset,
    mock_get_sb_service,
    mock_get_timeline_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_get_config,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
):
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    mock_get_config.return_value = mock_config
    mock_get_session_id.return_value = "session_camel_test"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service

    mock_tl_service_inst = AsyncMock()
    mock_created_tl = MagicMock()
    mock_created_tl.timeline_id = "tl_camel_789"
    mock_tl_service_inst.create_timeline.return_value = mock_created_tl
    mock_get_timeline_service.return_value = mock_tl_service_inst

    mock_sb_service_inst = AsyncMock()
    mock_sb_service_inst.save_storyboard.return_value = {
        "storyboard_id": "sb_camel_123"
    }
    mock_get_sb_service.return_value = mock_sb_service_inst

    mock_stitched = MagicMock()
    mock_stitched.id = "stitched_camel_456"
    mock_stitching_service.stitch_video.return_value = mock_stitched
    mock_tl_service_inst.stitch_timeline.return_value = mock_stitched

    mock_template = MagicMock()
    mock_template.industry_type = "Standard"
    mock_get_template.return_value = mock_template
    mock_display_asset.return_value = "Success"

    from ads_x.tools.generation.stitching_tools import stitch_final_video

    with patch.dict(
        "os.environ", {"CREATIVE_STUDIO_FRONTEND_URL": "http://cs-test:4200"}
    ):
        result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    expected_link = "http://cs-test:4200/workbench?timelineId=tl_camel_789&storyboardId=sb_camel_123&sessionId=session_camel_test"
    assert expected_link in result["result"]
    mock_tl_service_inst.create_timeline.assert_called_once()
    assert (
        mock_tl_service_inst.create_timeline.call_args.kwargs["storyboard_id"]
        == "sb_camel_123"
    )


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_config")
@patch("ads_x.tools.generation.stitching_tools.get_session_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("mediagent_kit.services.aio.get_storyboard_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("ads_x.tools.generation.stitching_tools.display_asset")
@patch("ads_x.tools.generation.stitching_tools.template_library.get_template_by_name")
async def test_stitch_final_video_custom_object_storyboard(
    mock_get_template,
    mock_display_asset,
    mock_get_canvas_service,
    mock_get_sb_service,
    mock_get_stitching_service,
    mock_get_asset_service,
    mock_get_session_id,
    mock_get_config,
    mock_tool_context,
    mock_asset_service,
    mock_stitching_service,
):
    mock_get_canvas_service.return_value = AsyncMock()
    mock_config = MagicMock()
    mock_config.use_creative_studio = False
    mock_get_config.return_value = mock_config
    mock_get_session_id.return_value = "session_obj_guarantee"
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_stitching_service.return_value = mock_stitching_service

    mock_sb_service_inst = AsyncMock()
    mock_sb_service_inst.save_storyboard.return_value = {"storyboard_id": "sb_obj_999"}
    mock_get_sb_service.return_value = mock_sb_service_inst

    # Create a custom non-dict object without session_id pre-defined
    # We add a .get() method to mimic dict lookups required by stitch_final_video
    # but since it's not a dict, isinstance(storyboard, dict) is False.
    class CustomStoryboard:
        def __init__(self):
            self.storyboard_id = "sb_init_111"
            self.scenes = [
                {
                    "first_frame_prompt": {
                        "asset_ref": {
                            "id": "asset_img_1",
                            "asset_type": "generated",
                            "workspace_id": "1",
                        }
                    },
                    "video_prompt": {
                        "asset_ref": {
                            "id": "asset_vid_1",
                            "asset_type": "generated",
                            "workspace_id": "1",
                        },
                        "duration_seconds": 5,
                    },
                    "voiceover_prompt": {
                        "asset_ref": {
                            "id": "asset_vo_1",
                            "asset_type": "generated",
                            "workspace_id": "1",
                        }
                    },
                }
            ]

        def get(self, key, default=None):
            if key == "scenes":
                return self.scenes
            if key == "storyboard_id" or key == "id":
                return self.storyboard_id
            return default

    custom_sb = CustomStoryboard()
    mock_tool_context.state["storyboard"] = custom_sb

    mock_stitched = MagicMock()
    mock_stitched.id = "stitched_obj_777"
    mock_stitching_service.stitch_video.return_value = mock_stitched

    mock_template = MagicMock()
    mock_template.industry_type = "Standard"
    mock_get_template.return_value = mock_template
    mock_display_asset.return_value = "Success"

    from ads_x.tools.generation.stitching_tools import stitch_final_video

    result = await stitch_final_video(mock_tool_context)

    assert result["status"] == "succeeded"
    assert custom_sb.session_id == "session_obj_guarantee"
    assert custom_sb.workspace_id == "1"
    mock_sb_service_inst.save_storyboard.assert_called_once_with(custom_sb)
