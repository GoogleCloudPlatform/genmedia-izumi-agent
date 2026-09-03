import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {"workspace_id": "1"}
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
    from demos.backend.ads_x.tools.generation.generation_tools import (
        generate_all_media,
    )
    from demos.backend.ads_x.utils.common.common_utils import (
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

    # Mock helpers to avoid real API calls. generate_all_media now runs a fast
    # lane (first frames + audio) then a slow lane (videos); it no longer calls
    # generate_scene, so mock the first-frame step and the video step directly.
    with (
        patch(
            "demos.backend.ads_x.utils.generation.generation_helpers.generate_background_music",
            new_callable=AsyncMock,
        ) as mock_gen_music,
        patch(
            "demos.backend.ads_x.utils.generation.generation_helpers.generate_scene_voiceover",
            new_callable=AsyncMock,
        ) as mock_scene_vo,
        patch(
            "demos.backend.ads_x.tools.generation.voiceover_tools.generate_group_voiceover",
            new_callable=AsyncMock,
        ) as mock_group_vo,
        patch(
            "demos.backend.ads_x.tools.generation.generation_tools.generate_scene_first_frame_step",
            new_callable=AsyncMock,
        ) as mock_first_frame,
        patch(
            "demos.backend.ads_x.tools.generation.generation_tools.generate_scene_video",
            new_callable=AsyncMock,
        ) as mock_gen_video,
    ):
        mock_gen_music.return_value = MagicMock()
        mock_scene_vo.return_value = MagicMock()
        mock_group_vo.return_value = MagicMock()
        mock_first_frame.return_value = (MagicMock(), "desc")
        mock_gen_video.return_value = [MagicMock()]

        import asyncio

        result = asyncio.run(generate_all_media(mock_tool_context))

        assert result["status"] == "succeeded"
        mock_gen_music.assert_called_once()
        mock_first_frame.assert_called_once()
        mock_gen_video.assert_called_once()


def test_generate_all_media_missing_storyboard(mock_tool_context):
    from demos.backend.ads_x.tools.generation.generation_tools import (
        generate_all_media,
    )
    from demos.backend.ads_x.utils.common.common_utils import PARAMETERS_KEY

    mock_tool_context.state[PARAMETERS_KEY] = {}

    import asyncio

    result = asyncio.run(generate_all_media(mock_tool_context))

    assert result["status"] == "failed"
    assert "Missing storyboard" in result["error_message"]


def test_generate_single_scene_success(mock_tool_context):
    from demos.backend.ads_x.tools.generation.generation_tools import (
        generate_single_scene,
    )
    from demos.backend.ads_x.utils.common.common_utils import (
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
        "demos.backend.ads_x.tools.generation.generation_tools.generate_scene",
        new_callable=AsyncMock,
    ) as mock_gen_scene:
        mock_gen_scene.return_value = [MagicMock()]

        import asyncio

        result = asyncio.run(generate_single_scene(mock_tool_context, scene_index=0))

        assert result["status"] == "succeeded"
        mock_gen_scene.assert_called_once()


@pytest.mark.asyncio
@patch(
    "demos.backend.ads_x.tools.generation.generation_tools.scene_generation_utils.generate_scene_video"
)
@patch(
    "demos.backend.ads_x.tools.generation.generation_tools.enrichment_utils.enrich_prompt_with_llm"
)
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_scene_video_success_internal(
    mock_get_media_gen_service,
    mock_get_asset_service,
    mock_enrich,
    mock_generate_scene_video,
):
    from demos.backend.ads_x.tools.generation.generation_tools import (
        generate_scene_video,
    )

    mock_asset_service_inst = AsyncMock()
    mock_get_asset_service.return_value = mock_asset_service_inst

    mock_media_gen_inst = AsyncMock()
    mock_get_media_gen_service.return_value = mock_media_gen_inst
    # Reconciliation runs against this before enrichment; left unset the mock
    # answers with an AsyncMock and the action is silently discarded.
    mock_media_gen_inst.generate_text.return_value = "A video, reconciled"

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
        workspace_id="workspace_1",
        scene=scene,
        index=0,
        aspect_ratio="16:9",
        first_frame_asset=first_frame_asset,
    )

    assert len(result) == 2
    assert result[1].id == "vid_123"
    assert scene["video_prompt"]["asset_id"] == "vid_123"


@pytest.mark.asyncio
@patch("demos.backend.ads_x.tools.generation.generation_tools.generate_scene_video")
@patch(
    "demos.backend.ads_x.tools.generation.generation_tools.generation_helpers.generate_scene_voiceover"
)
@patch(
    "demos.backend.ads_x.tools.generation.generation_tools.scene_generation_utils.generate_scene_first_frame"
)
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_scene_success_internal(
    mock_get_asset_service,
    mock_generate_scene_first_frame,
    mock_generate_scene_voiceover,
    mock_generate_scene_video,
):
    from demos.backend.ads_x.tools.generation.generation_tools import (
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
        workspace_id="workspace_1",
        scene=scene,
        index=0,
        aspect_ratio="16:9",
    )

    assert len(result) == 2  # gather results
    mock_generate_scene_first_frame.assert_called_once()
    mock_generate_scene_video.assert_called_once()
    mock_generate_scene_voiceover.assert_called_once()


# --------------------------------------------------------------------------
# The two phases
#
# Frames are cheap and videos are not, so the two halves can be run by
# separate calls with a review checkpoint between them.
# --------------------------------------------------------------------------


def test_the_three_entry_points_select_a_phase():
    from demos.backend.ads_x.tools.generation import generation_tools as gt

    assert (gt.FRAMES_PHASE, gt.VIDEOS_PHASE, gt.ALL_PHASES) == (
        "frames",
        "videos",
        "all",
    )
    for name in (
        "generate_scene_frames",
        "generate_scene_videos",
        "generate_all_media",
    ):
        assert callable(getattr(gt, name))


@pytest.mark.asyncio
async def test_each_entry_point_asks_for_its_own_phase():
    from unittest.mock import patch as _patch

    from demos.backend.ads_x.tools.generation import generation_tools as gt

    with _patch.object(gt, "_generate_media", new=AsyncMock(return_value="ok")) as run:
        await gt.generate_scene_frames("ctx")
        await gt.generate_scene_videos("ctx")
        await gt.generate_all_media("ctx")

    assert [c.args[1] for c in run.await_args_list] == ["frames", "videos", "all"]


def test_the_visual_anchor_survives_between_the_phases():
    """The videos may be rendered by a later request than the frames.

    generate_scene_first_frame_step returns the anchor description only when
    it renders; on the reuse path it reads it back from the scene, so the
    video is still anchored to the frame it starts from.
    """
    import inspect

    from demos.backend.ads_x.tools.generation import generation_tools as gt

    source = inspect.getsource(gt.generate_scene_first_frame_step)
    assert '["visual_anchor"] = first_frame_desc' in source
    assert 'first_frame_prompt.get("visual_anchor"' in source


def test_the_videos_phase_does_not_replan_the_narration():
    import inspect

    from demos.backend.ads_x.tools.generation import generation_tools as gt

    source = inspect.getsource(gt._generate_media)
    guard = source.index("if phase == VIDEOS_PHASE:")
    replan = source.index("grouping_utils.create_voiceover_groups")
    assert guard < replan, "the phase check must short-circuit the planning"

    # The tail writes voiceover_groups back onto the storyboard. It must only
    # do so when it holds some, or the videos phase erases the rendered audio.
    assert "if voiceover_groups:" in source
