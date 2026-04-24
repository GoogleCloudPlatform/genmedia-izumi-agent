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

"""Unit tests for video verifier tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ads_codirector.tools import video_verifier_tools
from ads_codirector.utils import common_utils


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext."""
    context = MagicMock()
    context.state = {
        common_utils.STORYBOARD_KEY: {"final_video_asset_id": "fake_video_id"},
        common_utils.PARAMETERS_KEY: {"brand": "TestBrand"},
        common_utils.USER_ASSETS_KEY: {"img.png": "A test image"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "img.png": {"semantic_role": "product"}
        },
        common_utils.CREATIVE_CONFIG_KEY: {"creative_strategy": "informational"},
        common_utils.THEORETICAL_DEFS_KEY: {"creative_strategy": "Theory text"},
        "mab_iteration": 0,
    }
    return context


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
async def test_evaluate_final_video_success(
    _mock_user, mock_mediagen, mock_asset, mock_tool_context
):
    """Verify that video evaluation succeeds and updates state."""
    asset_service = MagicMock()
    asset_service.get_asset_by_id = AsyncMock(
        return_value=MagicMock(file_name="final_video.mp4")
    )
    asset_service.get_asset_blob = AsyncMock(
        return_value=MagicMock(
            content=b'{"score": 85, "breakdown": {"coherence": 15, "visual_quality": 15, "engagement": 15, "prompt_adherence": 20, "logical_consistency": 20}, "mab_efficacy_scores": {"creative_strategy": 90}, "mab_efficacy_justifications": {"creative_strategy": "good"}, "feedback": "test", "primary_fault": "none", "actionable_feedback": "none"}'
        )
    )
    mock_asset.return_value = asset_service
    mediagen_service = MagicMock()
    mediagen_service.generate_text_with_gemini = AsyncMock(
        return_value=MagicMock(id="response_id")
    )
    mock_mediagen.return_value = mediagen_service

    result = await video_verifier_tools.evaluate_final_video(mock_tool_context)
    assert result["status"] == "succeeded"
    saved_result = mock_tool_context.state[common_utils.VERIFICATION_RESULT_KEY]
    assert saved_result["score"] == 85
    assert saved_result["mab_efficacy_scores"]["creative_strategy"] == 90


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
async def test_evaluate_final_video_missing_asset(
    _mock_user, _mock_mediagen, _mock_asset, mock_tool_context
):
    """Verify evaluation failure when the final video asset is missing."""
    mock_tool_context.state[common_utils.STORYBOARD_KEY]["final_video_asset_id"] = None
    result = await video_verifier_tools.evaluate_final_video(mock_tool_context)
    assert result["status"] == "failed"
    assert mock_tool_context.state[common_utils.VERIFICATION_RESULT_KEY]["score"] == 0
