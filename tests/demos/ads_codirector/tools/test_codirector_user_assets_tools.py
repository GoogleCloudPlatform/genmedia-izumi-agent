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

"""Unit tests for user asset tools."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.tools import user_assets_tools
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
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
async def test_ingest_assets_classification(
    _mock_user, mock_mediagen, mock_asset, mock_tool_context
):
    """Verify that assets are correctly classified into semantic roles."""
    # Setup mock assets
    mock_asset_instance = MagicMock()
    mock_asset_instance.list_assets = AsyncMock(
        return_value=[MagicMock(file_name="logo.png"), MagicMock(file_name="prod.jpg")]
    )
    mock_asset_instance.get_asset_blob = AsyncMock(
        side_effect=[
            MagicMock(content=b'{"caption": "A logo", "semantic_role": "logo"}'),
            MagicMock(content=b'{"caption": "A product", "semantic_role": "product"}'),
        ]
    )
    mock_asset_instance.update_asset = AsyncMock()
    mock_asset.return_value = mock_asset_instance
    # Mock Gemini response
    mock_mediagen_instance = MagicMock()
    mock_mediagen_instance.generate_text_with_gemini = AsyncMock(
        return_value=MagicMock(id="id")
    )
    mock_mediagen.return_value = mock_mediagen_instance

    await user_assets_tools.ingest_assets(mock_tool_context)
    # Verify state
    annotated = mock_tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY]
    assert annotated["logo.png"]["semantic_role"] == "logo"
    assert annotated["prod.jpg"]["semantic_role"] == "product"
