import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {
        "workspace_id": "1",
        "storyboard": {
            "template_name": "Custom",
            "scenes": [
                {
                    "topic": "Scene 1",
                    "video_prompt": {
                        "asset_ref": {
                            "id": "asset_vid_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        },
                        "description": "Vid desc",
                    },
                    "first_frame_prompt": {
                        "asset_ref": {
                            "id": "asset_img_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        },
                        "description": "Img desc",
                    },
                    "voiceover_prompt": {
                        "asset_ref": {
                            "id": "asset_vo_1",
                            "asset_type": "generated",
                            "workspace_id": "user_123",
                        },
                        "text": "Hello",
                    },
                }
            ],
            "background_music_prompt": {
                "description": "Music desc",
                "asset_ref": {
                    "id": "asset_bgm_1",
                    "asset_type": "generated",
                    "workspace_id": "user_123",
                },
            },
        },
        "parameters": {"campaign_brief": "A test campaign"},
    }
    return context


@pytest.fixture
def mock_asset_service():
    service = AsyncMock()
    mock_asset = MagicMock()
    mock_asset.file_name = "mock_file.mp4"
    service.get_asset.return_value = mock_asset
    service.download_asset_bytes.return_value = b"Enriched prompt text"
    return service


@pytest.fixture
def mock_canvas_service():
    service = AsyncMock()
    mock_canvas = MagicMock()
    mock_canvas.id = "canvas_summary_123"
    service.create_canvas.return_value = mock_canvas
    return service


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch(
    "ads_x.tools.generation.summary_canvas_tool.template_library.get_template_by_name"
)
async def test_create_campaign_summary_success(
    mock_get_template,
    mock_get_canvas_service,
    mock_get_asset_service,
    mock_tool_context,
    mock_asset_service,
    mock_canvas_service,
):
    mock_get_asset_service.return_value = mock_asset_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Mock template
    mock_template = MagicMock()
    mock_template.description = "Test Template"
    mock_template.brand_personality = ["Playful"]
    mock_template.music_keywords = ["Upbeat"]
    mock_template.scene_structure = []
    mock_get_template.return_value = mock_template

    from ads_x.tools.generation.summary_canvas_tool import (
        create_campaign_summary,
    )

    result = await create_campaign_summary(mock_tool_context)

    assert result["status"] == "succeeded"
    assert "View Campaign Summary in Izumi Studio" in result["result"]
    mock_canvas_service.create_canvas.assert_called_once()


@pytest.mark.asyncio
async def test_create_campaign_summary_missing_storyboard(
    mock_tool_context,
):
    mock_tool_context.state = {}  # Empty state

    from ads_x.tools.generation.summary_canvas_tool import (
        create_campaign_summary,
    )

    result = await create_campaign_summary(mock_tool_context)

    assert result["status"] == "failed"
    assert "No storyboard found" in result["error_message"]
