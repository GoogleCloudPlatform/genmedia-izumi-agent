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

"""Tests for Creative Studio ADK tools and conditional tool helper get_cs_tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.creative_studio.cs_tools import (
    get_cs_tools,
    list_workspaces,
    select_workspace,
)


@pytest.fixture
def mock_tool_context():
    tc = MagicMock(spec=ToolContext)
    tc.state = {"user_auth_token": "mock_user_token_123"}
    return tc


def test_get_cs_tools_disabled():
    """Verify get_cs_tools returns empty list when CS is disabled."""
    with patch(
        "mediagent_kit.services.creative_studio.cs_tools._get_config"
    ) as mock_config_getter:
        mock_config_getter.return_value = MediagentKitConfig(use_creative_studio=False)

        tools = get_cs_tools()
        assert tools == []


def test_get_cs_tools_enabled():
    """Verify get_cs_tools returns workspace FunctionTools when CS is enabled."""
    with patch(
        "mediagent_kit.services.creative_studio.cs_tools._get_config"
    ) as mock_config_getter:
        mock_config_getter.return_value = MediagentKitConfig(use_creative_studio=True)

        tools = get_cs_tools()
        assert len(tools) == 2
        assert all(isinstance(t, FunctionTool) for t in tools)


@pytest.mark.asyncio
async def test_list_workspaces_cs_disabled(mock_tool_context):
    with patch(
        "mediagent_kit.services.creative_studio.cs_tools._get_config"
    ) as mock_config_getter:
        mock_config_getter.return_value = MediagentKitConfig(use_creative_studio=False)

        res = await list_workspaces(mock_tool_context)
        assert "Creative Studio is not enabled" in res


@pytest.mark.asyncio
async def test_list_workspaces_success(mock_tool_context):
    with (
        patch(
            "mediagent_kit.services.creative_studio.cs_tools._get_config"
        ) as mock_config_getter,
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_config_getter.return_value = MediagentKitConfig(
            use_creative_studio=True, cs_backend_url="http://mock-backend:8080"
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 101, "name": "Cymbal Workspace", "scope": "system"},
            {"id": 102, "name": "Private Sandbox", "scope": "private"},
        ]
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await list_workspaces(mock_tool_context)
        assert "ID**: 101" in res
        assert "Cymbal Workspace" in res
        assert "ID**: 102" in res


@pytest.mark.asyncio
async def test_select_workspace(mock_tool_context):
    res = await select_workspace(101, mock_tool_context)
    assert mock_tool_context.state["workspace_id"] == 101
    assert "successfully selected" in res
