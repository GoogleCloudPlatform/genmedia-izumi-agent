# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


def test_initialize_project(mock_tool_context):
    from elements_to_video.tools.storyboard_tool import _initialize_project

    _initialize_project(mock_tool_context, "A cat in space", "16:9")

    assert mock_tool_context.state["user_idea"] == "A cat in space"
    assert mock_tool_context.state["aspect_ratio"] == "16:9"
    assert mock_tool_context.state["generation_stage"] == "WRITING_STORYBOARD"


def test_format_storyboard_for_display():
    from elements_to_video.tools.storyboard_tool import _format_storyboard_for_display

    storyboard_json = {
        "voice_name": "Aoede",
        "voice_gender": "Female",
        "video_clips": [
            {
                "clip_number": 1,
                "duration_seconds": 5.0,
                "description": "A cat",
                "narration": "Hello cat",
            }
        ],
    }

    result = _format_storyboard_for_display(storyboard_json)
    assert "**Narration Voice:** Aoede (Female)" in result
    assert "Clip 1:" in result
    assert '"Hello cat"' in result


def test_format_storyboard_for_display_rich():
    from elements_to_video.tools.storyboard_tool import _format_storyboard_for_display

    storyboard_json = {
        "voice_name": "Aoede",
        "voice_gender": "Female",
        "consistent_elements": [
            {
                "id": "char_1",
                "name": "Cat",
                "description": "A space cat",
                "file_name": "cat.png",
            }
        ],
        "video_clips": [
            {
                "clip_number": 1,
                "duration_seconds": 5.0,
                "description": "A cat",
                "narration": "Hello cat",
                "elements": ["char_1"],
            }
        ],
        "transitions": [{"type": "fade", "duration_seconds": 1.0}],
        "background_music_clips": [
            {
                "start_at": {"video_clip_index": 0, "offset_seconds": 0.0},
                "duration_seconds": 10.0,
                "prompt": "Space music",
                "fade_in_seconds": 1.0,
                "fade_out_seconds": 1.0,
            }
        ],
    }

    result = _format_storyboard_for_display(storyboard_json)
    assert "**Consistent Elements:**" in result
    assert "Cat" in result
    assert "Space music" in result
    assert "fade" in result


@pytest.mark.asyncio
@patch("elements_to_video.tools.storyboard_tool.genai.Client")
@patch("elements_to_video.tools.storyboard_tool.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_create_storyboard_success(
    mock_get_asset_service,
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    # Mock GenAI Client
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    # Mock response
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "title": "Title",
            "voice_gender": "Female",
            "voice_name": "Aoede",
            "aspect_ratio": "16:9",
            "video_clips": [
                {
                    "clip_number": 1,
                    "description": "Clip 1",
                    "duration_seconds": 5.0,
                    "image_prompt": "Image prompt",
                    "video_prompt": "Video prompt",
                    "image_file_name": "img1.png",
                    "video_file_name": "vid1.mp4",
                    "elements": [],
                }
            ],
            "consistent_elements": [],
            "transitions": [],
            "background_music_clips": [],
        }
    )

    # asyncio.to_thread is used, so we mock the blocking call
    mock_client.models.generate_content.return_value = mock_response

    from elements_to_video.tools.storyboard_tool import create_storyboard

    result_str = await create_storyboard(
        mock_tool_context, user_idea="A user idea", aspect_ratio="16:9"
    )
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert "storyboard_plan" in mock_tool_context.state
    assert mock_tool_context.state["generation_stage"] == "STORYBOARD_REVIEW"


def test_adjust_music_duration():
    from elements_to_video.tools.storyboard_tool import _adjust_music_duration
    from elements_to_video.types import StoryboardPlan, BackgroundMusicClipPlan

    mock_plan = MagicMock(spec=StoryboardPlan)
    mock_plan.calculate_total_duration.return_value = 20.0
    mock_plan.get_clip_start_times.return_value = [0.0, 10.0]

    mock_music_clip = MagicMock()
    mock_music_clip.start_at.video_clip_index = 1
    mock_music_clip.start_at.offset_seconds = 2.0
    mock_music_clip.duration_seconds = 5.0

    mock_plan.background_music_clips = [mock_music_clip]

    result = _adjust_music_duration(mock_plan)

    # total_duration (20) - latest_start_time (10 + 2 = 12) = 8
    assert result.background_music_clips[0].duration_seconds == 8.0


@pytest.mark.asyncio
@patch("elements_to_video.tools.storyboard_tool.genai.Client")
@patch("elements_to_video.tools.storyboard_tool.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_create_storyboard_with_asset_references(
    mock_get_asset_service_factory,
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    mock_asset_service = AsyncMock()
    mock_get_asset_service_factory.return_value = mock_asset_service

    # Mock asset found
    mock_asset = MagicMock()
    mock_asset.id = "asset_456"
    mock_asset_service.get_asset_by_file_name.return_value = mock_asset

    mock_blob = MagicMock()
    mock_blob.content = b"image_data"
    mock_blob.mime_type = "image/png"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    # Mock GenAI Client
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "title": "Title",
            "voice_gender": "Female",
            "voice_name": "Aoede",
            "aspect_ratio": "16:9",
            "video_clips": [],
            "consistent_elements": [],
            "transitions": [],
            "background_music_clips": [],
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    from elements_to_video.tools.storyboard_tool import create_storyboard

    result_str = await create_storyboard(
        mock_tool_context, user_idea="A user idea with image.png", aspect_ratio="16:9"
    )
    result = json.loads(result_str)

    assert result["status"] == "success"
    mock_asset_service.get_asset_by_file_name.assert_called_once_with(
        user_id="user_123", file_name="image.png"
    )
    mock_asset_service.get_asset_blob.assert_called_once_with(asset_id="asset_456")
