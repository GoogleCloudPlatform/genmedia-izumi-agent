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

"""Unit tests for casting tools."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.tools import casting_tools
from ads_codirector.utils import common_utils


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext."""
    context = MagicMock()
    context.state = {
        "mab_iteration": 0,
        common_utils.USER_ASSETS_KEY: {},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }
    return context


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("utils.adk.display_asset", new_callable=AsyncMock)
async def test_generate_character_collage(
    _mock_display, _mock_user, mock_mediagen, mock_tool_context
):
    """Verify character reference image generation."""
    mock_tool_context.state[common_utils.CASTING_KEY] = {
        "collage_prompt": "3-view collage prompt",
        "character_profile": "test profile",
    }
    mock_mediagen_instance = MagicMock()
    mock_mediagen_instance.generate_image_with_gemini = AsyncMock(
        return_value=MagicMock(id="coll_id", file_name="iter_0_character_collage.png")
    )
    mock_mediagen.return_value = mock_mediagen_instance

    await casting_tools.generate_character_collage(mock_tool_context)
    # Verify the new collage was added to user_assets for storyboard access
    assert (
        "iter_0_character_collage.png"
        in mock_tool_context.state[common_utils.USER_ASSETS_KEY]
    )
    assert mock_tool_context.state[common_utils.CHARACTER_COLLAGE_ID_KEY] == "coll_id"
