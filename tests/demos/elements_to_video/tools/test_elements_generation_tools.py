import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
    return context


@pytest.fixture
def mock_media_generation_service():
    return AsyncMock()


@pytest.fixture
def mock_canvas_service():
    return AsyncMock()


@pytest.fixture
def mock_asset_service():
    return AsyncMock()


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_images_for_storyboard_success(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1 description",
                "duration_seconds": 5.0,
                "image_prompt": "Prompt 1",
                "video_prompt": "Video Prompt 1",
                "image_file_name": "img1.png",
                "video_file_name": "vid1.mp4",
                "elements": [],
            },
            {
                "clip_number": 2,
                "description": "Clip 2 description",
                "duration_seconds": 5.0,
                "image_prompt": "Prompt 2",
                "video_prompt": "Video Prompt 2",
                "image_file_name": "img2.png",
                "video_file_name": "vid2.mp4",
                "elements": [],
            },
        ],
        "transitions": [{"type": "fade", "duration_seconds": 1.0}],
        "background_music_clips": [],
    }
    mock_tool_context.state["consistent_elements"] = []

    # Mock media generation service
    mock_image_asset = MagicMock()
    mock_image_asset.file_name = "generated.png"
    mock_media_generation_service.generate_image_with_gemini.return_value = (
        mock_image_asset
    )

    # Mock canvas service
    mock_canvas = MagicMock()
    mock_canvas.id = "new_canvas_id"
    mock_canvas_service.create_canvas.return_value = mock_canvas

    from elements_to_video.tools.generation_tools import generate_images_for_storyboard

    result_str = await generate_images_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert mock_tool_context.state["video_timeline_canvas_id"] == "new_canvas_id"
    assert mock_tool_context.state["generation_stage"] == "IMAGES_REVIEW"
    assert mock_media_generation_service.generate_image_with_gemini.call_count == 2


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_generate_videos_and_speech_for_storyboard_success(
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_123"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1 description",
                "duration_seconds": 5.0,
                "image_prompt": "Image Prompt 1",
                "video_prompt": "Video Prompt 1",
                "image_file_name": "img1.png",
                "video_file_name": "vid1.mp4",
                "speech_file_name": "speech1.mp3",
                "narration": "Hello",
            },
            {
                "clip_number": 2,
                "description": "Clip 2 description",
                "duration_seconds": 5.0,
                "image_prompt": "Image Prompt 2",
                "video_prompt": "Video Prompt 2",
                "image_file_name": "img2.png",
                "video_file_name": "vid2.mp4",
                "speech_file_name": "speech2.mp3",
                "narration": "World",
            },
        ],
        "transitions": [{"type": "fade", "duration_seconds": 1.0}],
        "background_music_clips": [],
    }

    # Mock canvas service to return existing canvas with timeline
    mock_canvas = MagicMock()
    mock_timeline = MagicMock()

    mock_clip1 = MagicMock()
    mock_clip1.first_frame_asset = MagicMock(file_name="img1.png")

    mock_clip2 = MagicMock()
    mock_clip2.first_frame_asset = MagicMock(file_name="img2.png")

    mock_timeline.video_clips = [mock_clip1, mock_clip2]
    mock_timeline.audio_clips = []
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    # Mock media generation service
    mock_video_asset = MagicMock()
    mock_video_asset.file_name = "vid1.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = (
        mock_video_asset
    )

    mock_speech_asset = MagicMock()
    mock_speech_asset.file_name = "speech1.mp3"
    mock_media_generation_service.generate_speech_single_speaker.return_value = (
        mock_speech_asset
    )

    from elements_to_video.tools.generation_tools import (
        generate_videos_and_speech_for_storyboard,
    )

    result_str = await generate_videos_and_speech_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert mock_tool_context.state["generation_stage"] == "VIDEO_SPEECH_REVIEW"
    assert mock_media_generation_service.generate_video_with_veo.call_count == 2
    assert mock_media_generation_service.generate_speech_single_speaker.call_count == 2


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_regenerate_assets_success(
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Setup state
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_123"
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1 description",
                "duration_seconds": 5.0,
                "video_file_name": "vid1.mp4",
                "video_prompt": "Vid Prompt 1",
                "image_file_name": "img1.png",
                "image_prompt": "Img Prompt 1",
            }
        ],
        "transitions": [],
        "background_music_clips": [],
    }

    # Mock canvas and timeline
    mock_canvas = MagicMock()
    mock_timeline = MagicMock()
    mock_clip = MagicMock()
    mock_clip.first_frame_asset = MagicMock(file_name="img1.png")
    mock_timeline.video_clips = [mock_clip]
    mock_timeline.audio_clips = []
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    # Mock generation
    mock_video_asset = MagicMock()
    mock_video_asset.file_name = "vid1_new.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = (
        mock_video_asset
    )

    from elements_to_video.tools.generation_tools import regenerate_assets

    result_str = await regenerate_assets(
        mock_tool_context, clip_numbers=[1], asset_types=["video"]
    )
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert mock_media_generation_service.generate_video_with_veo.call_count == 1


@pytest.mark.asyncio
async def test_generate_images_for_storyboard_missing_plan(mock_tool_context):
    from elements_to_video.tools.generation_tools import generate_images_for_storyboard

    mock_tool_context.state = {}  # Missing storyboard_plan

    result_str = await generate_images_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "failure"
    assert "storyboard_plan not found in state" in result["error_message"]


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_images_for_storyboard_with_consistent_elements(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [],
        "transitions": [],
        "background_music_clips": [],
    }
    mock_tool_context.state["consistent_elements"] = [
        {
            "id": "char_1",
            "name": "Character",
            "image_prompt": "Draw a character",
            "file_name": "char1.png",
        }
    ]

    # Mock media generation service
    mock_image_asset = MagicMock()
    mock_image_asset.file_name = "generated_char.png"
    mock_image_asset.id = "asset_char_1"
    mock_media_generation_service.generate_image_with_gemini.return_value = (
        mock_image_asset
    )

    # Mock canvas service
    mock_canvas = MagicMock()
    mock_canvas.id = "new_canvas_id"
    mock_canvas_service.create_canvas.return_value = mock_canvas

    from elements_to_video.tools.generation_tools import generate_images_for_storyboard

    result_str = await generate_images_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    # Verify consistent elements were updated with asset_id
    updated_elements = mock_tool_context.state["consistent_elements"]
    assert len(updated_elements) == 1
    assert updated_elements[0]["asset_id"] == "asset_char_1"


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_images_for_storyboard_partial_failure(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Setup state with 2 clips
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1 description",
                "duration_seconds": 5.0,
                "image_prompt": "Prompt 1",
                "video_prompt": "Video Prompt 1",
                "image_file_name": "img1.png",
                "video_file_name": "vid1.mp4",
                "elements": [],
            },
            {
                "clip_number": 2,
                "description": "Clip 2 description",
                "duration_seconds": 5.0,
                "image_prompt": "Prompt 2",
                "video_prompt": "Video Prompt 2",
                "image_file_name": "img2.png",
                "video_file_name": "vid2.mp4",
                "elements": [],
            },
        ],
        "transitions": [{"type": "fade", "duration_seconds": 1.0}],
        "background_music_clips": [],
    }

    # Mock media generation service to fail for one clip and succeed for another
    mock_media_generation_service.generate_image_with_gemini.side_effect = [
        MagicMock(file_name="success.png"),  # Clip 1
        Exception("Generation failed"),  # Clip 2
    ]

    mock_canvas_service.create_canvas.return_value = MagicMock(id="new_canvas_id")

    from elements_to_video.tools.generation_tools import generate_images_for_storyboard

    result_str = await generate_images_for_storyboard(mock_tool_context)
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert result["failed_clips"] == [2]


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_images_for_storyboard_with_consistent_elements_and_clips(
    mock_get_asset_service,
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
    mock_asset_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service
    mock_get_asset_service.return_value = mock_asset_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1",
                "duration_seconds": 5.0,
                "image_prompt": "Prompt 1",
                "video_prompt": "Vid 1",
                "image_file_name": "img1.png",
                "video_file_name": "vid1.mp4",
                "elements": ["char_1"],
            }
        ],
        "transitions": [],
        "background_music_clips": [],
    }
    mock_tool_context.state["consistent_elements"] = [
        {
            "id": "char_1",
            "name": "Character",
            "asset_id": "asset_char_1",
        }
    ]

    # Mock asset service
    mock_asset = MagicMock()
    mock_asset.file_name = "char1.png"
    mock_asset_service.get_asset_by_id.return_value = mock_asset

    # Mock media generation service
    mock_image_asset = MagicMock()
    mock_image_asset.file_name = "generated_clip.png"
    mock_media_generation_service.generate_image_with_gemini.return_value = (
        mock_image_asset
    )

    mock_canvas_service.create_canvas.return_value = MagicMock(id="new_canvas_id")

    from elements_to_video.tools.generation_tools import generate_images_for_storyboard

    result_str = await generate_images_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert mock_media_generation_service.generate_image_with_gemini.call_count == 1

    called_args = mock_media_generation_service.generate_image_with_gemini.call_args[1]
    assert "char1.png" in called_args["reference_image_filenames"]


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_generate_videos_and_speech_for_storyboard_with_music(
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_123"

    # We need to mock the storyboard plan as a Pydantic model or dict that can be parsed.
    # The code uses Parameters.model_validate or similar if it's from state,
    # but here it seems it just use it as a dict or it parses it.
    # Let's see how it's used in generation_tools.py. It uses it as an object if it's parsed, or dict.
    # In test_generate_images_for_storyboard_success it was a dict.
    # Let's check if generate_videos_and_speech_for_storyboard uses it as dict or object.
    # In generation_tools.py:
    # storyboard_plan_dict = tool_context.state.get("storyboard_plan")
    # storyboard_plan = Parameters.model_validate(storyboard_plan_dict) ... wait, it might use Pydantic.
    # Let's assume it works like previous tests where it was a dict or we mock it.
    # In test_generate_videos_and_speech_for_storyboard_success it was a dict!

    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [],
        "transitions": [],
        "background_music_clips": [
            {
                "prompt": "Happy music",
                "file_name": "music1.mp3",
                "duration_seconds": 5.0,
                "start_at": {"video_clip_index": 0, "offset_seconds": 0.0},
            }
        ],
    }

    mock_canvas = MagicMock()
    mock_timeline = MagicMock()
    mock_timeline.video_clips = []
    mock_timeline.audio_clips = []
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    mock_music_asset = MagicMock()
    mock_music_asset.file_name = "music1.mp3"
    mock_media_generation_service.generate_music_with_lyria.return_value = (
        mock_music_asset
    )

    from elements_to_video.tools.generation_tools import (
        generate_videos_and_speech_for_storyboard,
    )

    result_str = await generate_videos_and_speech_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert mock_media_generation_service.generate_music_with_lyria.call_count == 1


@pytest.mark.asyncio
@patch("elements_to_video.tools.generation_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_canvas_service")
async def test_generate_videos_and_speech_for_storyboard_partial_failure(
    mock_get_canvas_service,
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
    mock_canvas_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service
    mock_get_canvas_service.return_value = mock_canvas_service

    # Setup state
    mock_tool_context.state["aspect_ratio"] = "16:9"
    mock_tool_context.state["video_timeline_canvas_id"] = "canvas_123"
    mock_tool_context.state["storyboard_plan"] = {
        "title": "Test Video",
        "aspect_ratio": "16:9",
        "voice_gender": "Female",
        "voice_name": "Aoede",
        "video_clips": [
            {
                "clip_number": 1,
                "description": "Clip 1 description",
                "duration_seconds": 5.0,
                "image_prompt": "Image Prompt 1",
                "video_prompt": "Video Prompt 1",
                "image_file_name": "img1.png",
                "video_file_name": "vid1.mp4",
                "speech_file_name": "speech1.mp3",
                "narration": "Hello",
            },
            {
                "clip_number": 2,
                "description": "Clip 2 description",
                "duration_seconds": 5.0,
                "image_prompt": "Image Prompt 2",
                "video_prompt": "Video Prompt 2",
                "image_file_name": "img2.png",
                "video_file_name": "vid2.mp4",
                "speech_file_name": "speech2.mp3",
                "narration": "World",
            },
        ],
        "transitions": [],
        "background_music_clips": [],
    }

    # Mock canvas service to return existing canvas with timeline
    mock_canvas = MagicMock()
    mock_timeline = MagicMock()

    mock_clip1 = MagicMock()
    mock_clip1.first_frame_asset = MagicMock(file_name="img1.png")

    mock_clip2 = MagicMock()
    mock_clip2.first_frame_asset = MagicMock(file_name="img2.png")

    mock_timeline.video_clips = [mock_clip1, mock_clip2]
    mock_timeline.audio_clips = []
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    # Mock media generation service to fail for video 2, succeed for video 1 and speech
    mock_media_generation_service.generate_video_with_veo.side_effect = [
        MagicMock(file_name="vid1.mp4"),
        Exception("Veo failed"),
    ]
    mock_media_generation_service.generate_speech_single_speaker.return_value = (
        MagicMock(file_name="speech.mp3")
    )

    from elements_to_video.tools.generation_tools import (
        generate_videos_and_speech_for_storyboard,
    )

    result_str = await generate_videos_and_speech_for_storyboard(mock_tool_context)
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert result["failed_clips"]["video"] == [2]
    assert result["failed_clips"]["speech"] == []
