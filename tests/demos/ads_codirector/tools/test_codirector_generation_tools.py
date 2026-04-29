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

"""Comprehensive unit tests for media generation tools."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ads_codirector.tools import generation_tools
from ads_codirector.utils import common_utils
from mediagent_kit.services.types import Asset, AssetVersion


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


@pytest.fixture
def mock_gen_service():
    with patch("mediagent_kit.services.aio.get_media_generation_service") as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_asset_service():
    with patch("mediagent_kit.services.aio.get_asset_service") as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service


def create_mock_asset(asset_id, file_name):
    return Asset(
        id=asset_id,
        user_id="u1",
        mime_type="image/png",
        file_name=file_name,
        current_version=1,
        versions=[
            AssetVersion(
                asset_id=asset_id,
                version_number=1,
                gcs_uri=f"gs://bucket/{file_name}",
                create_time=MagicMock(),
                duration_seconds=5.0,
            )
        ],
    )


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


@pytest.mark.asyncio
async def test_produce_refined_keyframes_champion_logic(
    mock_gen_service, mock_asset_service
):
    """Verify that the highest scoring sequence is selected as champion."""
    ctx = MagicMock()
    ctx.state = {
        common_utils.STORYBOARD_KEY: {
            "scenes": [{"first_frame_prompt": {"description": "d1"}}]
        },
        "mab_iteration": 0,
        common_utils.PARAMETERS_KEY: {"target_orientation": "portrait"},
        common_utils.CREATIVE_DIRECTION_KEY: {},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }

    asset1 = create_mock_asset("a1", "f1.png")
    asset2 = create_mock_asset("a2", "f2.png")
    mock_gen_service.generate_image_with_gemini.side_effect = [asset1, asset2]

    mock_gen_service.generate_text_with_gemini.return_value = create_mock_asset(
        "v1", "v1.txt"
    )
    mock_asset_service.get_asset_blob.side_effect = [
        MagicMock(
            content=b'{"score": 70, "feedback": "ok", "problematic_scenes": [0]}'
        ),
        MagicMock(content=b'{"score": 95, "feedback": "great"}'),
    ]

    with (
        patch("ads_codirector.tools.generation_tools.MAX_REFINEMENT_ATTEMPTS", 2),
        patch(
            "ads_codirector.tools.generation_tools.get_user_id_from_context",
            return_value="u1",
        ),
        patch("utils.adk.display_asset"),
    ):

        result = await generation_tools.produce_refined_keyframes(ctx)
        assert result["status"] == "succeeded"
        assert (
            ctx.state[common_utils.STORYBOARD_KEY]["scenes"][0]["first_frame_prompt"][
                "asset_id"
            ]
            == "a2"
        )


@pytest.mark.asyncio
async def test_generate_production_videos_neutralized_retry(
    mock_gen_service, mock_asset_service
):
    """Verify that a safety error triggers a softened prompt retry."""
    ctx = MagicMock()
    ctx.state = {
        common_utils.STORYBOARD_KEY: {
            "scenes": [
                {
                    "first_frame_prompt": {"asset_id": "frame1"},
                    "video_prompt": {
                        "description": "risky prompt",
                        "duration_seconds": 6,
                    },
                }
            ]
        },
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }

    mock_asset_service.get_asset_by_id.return_value = create_mock_asset(
        "frame1", "f1.png"
    )

    mock_gen_service.generate_video_with_veo.side_effect = [
        Exception("High safety risk!"),
        create_mock_asset("vid_final", "v.mp4"),
    ]
    mock_gen_service.generate_text_with_gemini.return_value = create_mock_asset(
        "soft_txt", "s.txt"
    )
    mock_asset_service.get_asset_blob.return_value = MagicMock(
        content=b"neutral prompt"
    )

    with (
        patch(
            "ads_codirector.tools.generation_tools.get_user_id_from_context",
            return_value="u1",
        ),
        patch("utils.adk.display_asset"),
    ):

        await generation_tools.generate_production_videos(ctx)

        assert mock_gen_service.generate_video_with_veo.call_count == 2
        args = mock_gen_service.generate_video_with_veo.call_args[1]
        assert "neutral prompt" in args["prompt"]


@pytest.mark.asyncio
async def test_generate_production_audio_full(mock_gen_service):
    """Verify VO and BGM generation."""
    ctx = MagicMock()
    ctx.state = {
        common_utils.STORYBOARD_KEY: {
            "voiceover_prompt": {"text": "Hello", "gender": "female"},
            "background_music_prompt": {"description": "Music"},
        }
    }

    mock_gen_service.generate_speech_single_speaker.return_value = create_mock_asset(
        "vo1", "vo.mp3"
    )
    mock_gen_service.generate_music_with_lyria.return_value = create_mock_asset(
        "bg1", "bg.mp3"
    )

    with (
        patch(
            "ads_codirector.tools.generation_tools.get_user_id_from_context",
            return_value="u1",
        ),
        patch("utils.adk.display_asset"),
    ):

        await generation_tools.generate_production_audio(ctx)

        storyboard = ctx.state[common_utils.STORYBOARD_KEY]
        assert storyboard["voiceover_prompt"]["asset_id"] == "vo1"
        assert storyboard["background_music_prompt"]["asset_id"] == "bg1"
        assert len(storyboard["voiceover_generation_history"]) == 1
