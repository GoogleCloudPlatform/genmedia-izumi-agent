# Copyright 2026 Google LLC
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

"""Unit tests for video stitching tools."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.tools import stitching_tools
from ads_codirector.utils import common_utils


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext."""
    context = MagicMock()
    context.state = {
        "mab_iteration": 0,
        common_utils.STORYBOARD_KEY: {
            "scenes": [
                {
                    "first_frame_prompt": {
                        "description": "scene1",
                        "assets": [],
                        "asset_id": "f1",
                    },
                    "video_prompt": {
                        "description": "v1",
                        "duration_seconds": 4,
                        "asset_id": "v1",
                    },
                }
            ],
            "voiceover_prompt": {"text": "Hello", "asset_id": "vo1"},
            "background_music_prompt": {"asset_id": "bgm1"},
        },
        common_utils.PARAMETERS_KEY: {"target_orientation": "landscape"},
        common_utils.CREATIVE_DIRECTION_KEY: {"audio_instruction": "fast"},
        common_utils.USER_ASSETS_KEY: {"logo.png": "Logo"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "logo.png": {"semantic_role": "logo"}
        },
    }
    return context


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_video_stitching_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("utils.adk.display_asset", new_callable=AsyncMock)
async def test_stitch_final_video_audio_sync(
    _mock_display, _mock_user, mock_stitch, mock_asset, mock_tool_context
):
    """Verify that audio speed is calculated to fit video duration."""
    mock_asset_instance = MagicMock()
    # Mock VO asset with 10s duration
    vo_asset = MagicMock()
    vo_asset.versions = [MagicMock(duration_seconds=10.0)]
    mock_asset_instance.get_asset_by_id = AsyncMock(
        side_effect=[
            MagicMock(file_name="f1.png"),  # Scene 1 Frame
            MagicMock(file_name="v1.mp4"),  # Scene 1 Video
            vo_asset,  # VO
            MagicMock(file_name="bgm.mp3"),  # BGM
        ]
    )
    mock_asset.return_value = mock_asset_instance
    mock_stitch_instance = MagicMock()
    mock_stitch_instance.stitch_video = AsyncMock(
        return_value=MagicMock(id="stitched_id", current_version=1)
    )
    mock_stitch.return_value = mock_stitch_instance

    await stitching_tools.stitch_final_video(mock_tool_context)
    # Scene is 4s, VO is 10s. Speed should be clamped to 2.0x (max)
    timeline = mock_stitch_instance.stitch_video.call_args.kwargs["timeline"]
    vo_clip = timeline.audio_clips[0]
    assert vo_clip.speed == 2.0
