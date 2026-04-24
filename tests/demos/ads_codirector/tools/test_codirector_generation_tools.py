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

"""Unit tests for media generation tools."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.tools import generation_tools
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
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("utils.adk.display_asset", new_callable=AsyncMock)
async def test_generate_production_videos_r2v(
    _mock_display, _mock_user, mock_mediagen, mock_asset, mock_tool_context
):
    """Verify that R2V mode is triggered and constraints are injected."""
    with patch(
        "ads_codirector.mab.utils.get_mab_config",
        return_value={"mab": {"logo_scene_mode": "r2v"}},
    ):
        mock_asset_instance = MagicMock()
        mock_asset_instance.get_asset_by_id = AsyncMock(
            return_value=MagicMock(file_name="frame.png")
        )
        mock_asset.return_value = mock_asset_instance
        mock_mediagen_instance = MagicMock()
        mock_mediagen_instance.generate_video_with_veo = AsyncMock(
            return_value=MagicMock(id="v_id")
        )
        mock_mediagen.return_value = mock_mediagen_instance

        await generation_tools.generate_production_videos(mock_tool_context)
        call_args = mock_mediagen_instance.generate_video_with_veo.call_args.kwargs
        assert call_args["method"] == "reference_to_video"
        assert call_args["duration_seconds"] == 8


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("utils.adk.display_asset", new_callable=AsyncMock)
async def test_r2v_rapid_fallback(
    _mock_display, _mock_user, mock_mediagen, mock_asset, mock_tool_context
):
    """Verify the 2-stage rapid fallback: R2V -> Softened Extrap + Hold."""
    mock_asset_instance = MagicMock()
    mock_asset_instance.get_asset_by_id = AsyncMock(
        return_value=MagicMock(file_name="frame.png")
    )
    mock_blob = MagicMock()
    mock_blob.content = b"softened prompt text"
    mock_asset_instance.get_asset_blob = AsyncMock(return_value=mock_blob)
    logo_asset = MagicMock(id="logo_id", file_name="logo.png")
    mock_asset_instance.get_asset_by_file_name = AsyncMock(return_value=logo_asset)
    mock_asset.return_value = mock_asset_instance
    mock_mediagen_instance = MagicMock()
    mock_mediagen_instance.generate_video_with_veo = AsyncMock(
        side_effect=[Exception("R2V blocked by safety"), MagicMock(id="v_extrap_id")]
    )
    mock_softened_resp = MagicMock(id="soft_id")
    mock_mediagen_instance.generate_text_with_gemini = AsyncMock(
        return_value=mock_softened_resp
    )
    mock_mediagen.return_value = mock_mediagen_instance

    with patch(
        "ads_codirector.mab.utils.get_mab_config",
        return_value={"mab": {"logo_scene_mode": "r2v"}},
    ):
        mock_tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY] = {
            "logo.png": {"semantic_role": "logo"}
        }
        await generation_tools.generate_production_videos(mock_tool_context)
    assert mock_mediagen_instance.generate_video_with_veo.call_count == 2
    assert (
        mock_mediagen_instance.generate_video_with_veo.call_args_list[0].kwargs[
            "method"
        ]
        == "reference_to_video"
    )
    second_call = mock_mediagen_instance.generate_video_with_veo.call_args_list[1]
    assert second_call.kwargs["method"] == "image_to_video"
    assert second_call.kwargs["duration_seconds"] == 6
    assert "softened prompt text" in second_call.kwargs["prompt"]
    scn_data = mock_tool_context.state[common_utils.STORYBOARD_KEY]["scenes"][0]
    assert scn_data["video_prompt"]["asset_id"] == "v_extrap_id"
    assert scn_data["last_frame_hold_asset_id"] == "logo_id"
    assert scn_data["last_frame_hold_duration"] == 2.0
