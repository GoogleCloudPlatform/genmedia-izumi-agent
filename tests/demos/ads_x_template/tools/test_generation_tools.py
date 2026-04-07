import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
    return context


@pytest.fixture
def mock_mediagen_service():
    service = MagicMock()
    service.generate_text_with_gemini = AsyncMock()
    return service


@pytest.fixture
def mock_asset_service():
    service = MagicMock()
    service.get_asset_blob = AsyncMock()
    service.get_asset = AsyncMock()
    return service


def test_generate_all_media_success(mock_tool_context):
    from demos.backend.ads_x_template.tools.generation.generation_tools import (
        generate_all_media,
    )
    from demos.backend.ads_x_template.utils.common.common_utils import (
        STORYBOARD_KEY,
        PARAMETERS_KEY,
    )

    mock_tool_context.state[STORYBOARD_KEY] = {
        "campaign_title": "Test Campaign",
        "background_music_prompt": {"description": "Music"},
        "scenes": [
            {
                "topic": "Scene 1",
                "first_frame_prompt": {"description": "F1"},
                "video_prompt": {"description": "V1", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Hello",
                    "gender": "female",
                    "description": "Happy",
                },
            }
        ],
    }
    mock_tool_context.state[PARAMETERS_KEY] = {
        "campaign_name": "Test Campaign",
        "campaign_brief": "Brief",
        "target_orientation": "landscape",
        "template_name": "Custom",
    }

    # Mock helpers to avoid real API calls
    with patch(
        "demos.backend.ads_x_template.utils.generation.generation_helpers.generate_background_music",
        new_callable=AsyncMock,
    ) as mock_gen_music:
        with patch(
            "demos.backend.ads_x_template.tools.generation.generation_tools.generate_scene",
            new_callable=AsyncMock,
        ) as mock_gen_scene:

            mock_gen_music.return_value = MagicMock()
            mock_gen_scene.return_value = [MagicMock()]

            import asyncio

            result = asyncio.run(generate_all_media(mock_tool_context))

            assert result["status"] == "succeeded"
            mock_gen_music.assert_called_once()
            mock_gen_scene.assert_called_once()


def test_generate_all_media_missing_storyboard(mock_tool_context):
    from demos.backend.ads_x_template.tools.generation.generation_tools import (
        generate_all_media,
    )
    from demos.backend.ads_x_template.utils.common.common_utils import PARAMETERS_KEY

    mock_tool_context.state[PARAMETERS_KEY] = {}

    import asyncio

    result = asyncio.run(generate_all_media(mock_tool_context))

    assert result["status"] == "failed"
    assert "Missing storyboard" in result["error_message"]


def test_generate_single_scene_success(mock_tool_context):
    from demos.backend.ads_x_template.tools.generation.generation_tools import (
        generate_single_scene,
    )
    from demos.backend.ads_x_template.utils.common.common_utils import (
        STORYBOARD_KEY,
        PARAMETERS_KEY,
    )

    mock_tool_context.state[STORYBOARD_KEY] = {
        "scenes": [
            {
                "topic": "Scene 1",
                "first_frame_prompt": {"description": "F1"},
                "video_prompt": {"description": "V1", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Hello",
                    "gender": "female",
                    "description": "Happy",
                },
            }
        ]
    }
    mock_tool_context.state[PARAMETERS_KEY] = {"template_name": "Custom"}

    with patch(
        "demos.backend.ads_x_template.tools.generation.generation_tools.generate_scene",
        new_callable=AsyncMock,
    ) as mock_gen_scene:
        mock_gen_scene.return_value = [MagicMock()]

        import asyncio

        result = asyncio.run(generate_single_scene(mock_tool_context, scene_index=0))

        assert result["status"] == "succeeded"
        mock_gen_scene.assert_called_once()


@pytest.mark.asyncio
@patch(
    "demos.backend.ads_x_template.tools.generation.generation_tools.scene_generation_utils.generate_scene_video"
)
@patch(
    "demos.backend.ads_x_template.tools.generation.generation_tools.enrichment_utils.enrich_prompt_with_llm"
)
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_scene_video_success_internal(
    mock_get_media_gen_service,
    mock_get_asset_service,
    mock_enrich,
    mock_generate_scene_video,
):
    from demos.backend.ads_x_template.tools.generation.generation_tools import (
        generate_scene_video,
    )

    mock_asset_service_inst = AsyncMock()
    mock_get_asset_service.return_value = mock_asset_service_inst

    mock_media_gen_inst = AsyncMock()
    mock_get_media_gen_service.return_value = mock_media_gen_inst

    mock_enrich.return_value = ("Final prompt", "enrich_id")

    mock_video_asset = MagicMock()
    mock_video_asset.id = "vid_123"
    mock_generate_scene_video.return_value = mock_video_asset

    scene = {
        "video_prompt": {"description": "A video"},
        "voiceover_prompt": {"text": "Hello"},
    }

    first_frame_asset = MagicMock()
    first_frame_asset.file_name = "frame.png"
    first_frame_asset.id = "frame_id"

    result = await generate_scene_video(
        user_id="user_123",
        scene=scene,
        index=0,
        aspect_ratio="16:9",
        first_frame_asset=first_frame_asset,
    )

    assert len(result) == 2
    assert result[1].id == "vid_123"
    assert scene["video_prompt"]["asset_id"] == "vid_123"


@pytest.mark.asyncio
@patch(
    "demos.backend.ads_x_template.tools.generation.generation_tools.generate_scene_video"
)
@patch(
    "demos.backend.ads_x_template.tools.generation.generation_tools.generation_helpers.generate_scene_voiceover"
)
@patch(
    "demos.backend.ads_x_template.tools.generation.generation_tools.scene_generation_utils.generate_scene_first_frame"
)
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_scene_success_internal(
    mock_get_asset_service,
    mock_generate_scene_first_frame,
    mock_generate_scene_voiceover,
    mock_generate_scene_video,
):
    from demos.backend.ads_x_template.tools.generation.generation_tools import (
        generate_scene,
    )

    mock_asset_service_inst = AsyncMock()
    mock_get_asset_service.return_value = mock_asset_service_inst

    mock_first_frame_asset = MagicMock()
    mock_first_frame_asset.id = "frame_id"
    mock_generate_scene_first_frame.return_value = (
        mock_first_frame_asset,
        "Description",
    )

    mock_generate_scene_voiceover.return_value = MagicMock()
    mock_video_asset = MagicMock()
    mock_generate_scene_video.return_value = [mock_first_frame_asset, mock_video_asset]

    scene = {
        "first_frame_prompt": {"description": "First frame"},
        "video_prompt": {"description": "Video"},
        "voiceover_prompt": {"text": "Hello"},
    }

    result = await generate_scene(
        user_id="user_123",
        scene=scene,
        index=0,
        aspect_ratio="16:9",
    )

    assert len(result) == 2  # gather results
    mock_generate_scene_first_frame.assert_called_once()
    mock_generate_scene_video.assert_called_once()
    mock_generate_scene_voiceover.assert_called_once()
