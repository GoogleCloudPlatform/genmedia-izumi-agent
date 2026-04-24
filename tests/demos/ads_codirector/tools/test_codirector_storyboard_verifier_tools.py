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

"""Unit tests for storyboard verifier tools."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.tools import storyboard_verifier_tools
from ads_codirector.utils import common_utils


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext for testing flow."""
    context = MagicMock()
    context.state = {
        "mab_iteration": 0,
        common_utils.STORYBOARD_KEY: {
            "scenes": [
                {
                    "first_frame_prompt": {
                        "assets": ["logo.png", "ghost.png"],
                        "description": "Scene 0",
                    },
                    "video_prompt": {"assets": [], "description": "Scene 0 Video"},
                },
                {
                    "first_frame_prompt": {
                        "assets": [],
                        "description": "Scene 1 (Final)",
                    },
                    "video_prompt": {"assets": [], "description": "Scene 1 Video"},
                },
            ]
        },
        common_utils.STORYLINE_KEY: {
            "scenes": [
                {"topic": "Intro", "action": "Establishment"},
                {"topic": "Outro", "action": "Logo Reveal"},
            ]
        },
        common_utils.USER_ASSETS_KEY: {"logo.png": "caption"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "logo.png": {"semantic_role": "logo", "caption": "caption"}
        },
        common_utils.PARAMETERS_KEY: {"campaign_brief": "test"},
    }
    return context


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("utils.adk.get_user_id_from_context", return_value="user")
async def test_verify_storyboard_assets_cleaning(
    _mock_user, mock_asset, mock_mediagen, mock_tool_context
):
    """Verify that invalid filenames are scrubbed and missing assets are injected."""
    mock_mediagen_instance = MagicMock()
    mock_mediagen_instance.generate_text_with_gemini = AsyncMock(
        return_value=MagicMock(id="id")
    )
    mock_mediagen.return_value = mock_mediagen_instance
    mock_asset_instance = MagicMock()
    mock_asset_instance.get_asset_blob = AsyncMock(
        return_value=MagicMock(
            content=b'{"corrections": [{"scene_index": 0, "missing_assets": ["prod.png"], "invalid_filenames": ["ghost.png"], "assets_to_remove": ["logo.png"], "reasoning": "fix"}], "overall_score": 70}'
        )
    )
    mock_asset.return_value = mock_asset_instance
    mock_tool_context.state[common_utils.USER_ASSETS_KEY]["prod.png"] = "Prod"
    mock_tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY][
        "prod.png"
    ] = {"semantic_role": "product", "caption": "Prod"}
    await storyboard_verifier_tools.verify_storyboard_assets(mock_tool_context)
    scene0 = mock_tool_context.state[common_utils.STORYBOARD_KEY]["scenes"][0]
    ff_assets0 = scene0["first_frame_prompt"]["assets"]
    assert "logo.png" not in ff_assets0
    assert "ghost.png" not in ff_assets0
    assert "prod.png" in ff_assets0
