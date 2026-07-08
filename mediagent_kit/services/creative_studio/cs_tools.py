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

"""ADK Tools for Creative Studio integration."""

import logging
import os

import httpx
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from mediagent_kit.utils.auth import get_google_id_token

logger = logging.getLogger(__name__)


def _get_config():
    from mediagent_kit.services import _get_service_factory

    return _get_service_factory().get_config()


async def list_workspaces(tool_context: ToolContext) -> str:
    """Fetches the available workspaces for the user from the Creative Studio backend.

    Returns:
        A Markdown-formatted string containing the list of available workspaces,
        including their IDs, names, and scopes.
    """
    config = _get_config()
    if not config.use_creative_studio:
        return "Creative Studio is not enabled. No workspaces are available."

    state = tool_context.state
    token_key = config.cs_user_auth_token_key or os.getenv(
        "CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token"
    )
    auth_token = state.get(token_key)

    backend_base_url = config.cs_backend_url or "http://backend:8080"
    workspaces_url = f"{backend_base_url}/api/workspaces"

    headers = {
        "X-User-Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    id_token_str = get_google_id_token(workspaces_url)
    if id_token_str:
        headers["Authorization"] = f"Bearer {id_token_str}"

    try:
        logger.info(f"Fetching workspaces from {workspaces_url}...")
        async with httpx.AsyncClient() as client:
            resp = await client.get(workspaces_url, headers=headers)
            resp.raise_for_status()
            workspaces = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch workspaces: {e}")
        return f"Error: Failed to fetch workspaces from the backend. Details: {e}"

    if not workspaces:
        return "No workspaces are available for this user on the backend."

    # Format the workspaces list as a clean markdown list
    result_lines = ["Here are the available workspaces:"]
    for ws in workspaces:
        ws_id = ws.get("id")
        name = ws.get("name")
        scope = ws.get("scope", "private")
        result_lines.append(f"- **ID**: {ws_id} | **Name**: {name} ({scope})")

    return "\n".join(result_lines)


async def select_workspace(workspace_id: int, tool_context: ToolContext) -> str:
    """Sets the selected workspace ID as the active workspace for the session.

    Args:
        workspace_id: The integer ID of the workspace to select.
    """
    tool_context.state["workspace_id"] = workspace_id
    logger.info(f"Successfully set workspace_id to {workspace_id} in session state.")
    return f"Workspace with ID {workspace_id} has been successfully selected and set as the active workspace."


def get_cs_tools() -> list[FunctionTool]:
    """Returns the list of Creative Studio ADK tools if Creative Studio is enabled, else empty list."""
    config = _get_config()
    if config.use_creative_studio:
        return [
            FunctionTool(list_workspaces),
            FunctionTool(select_workspace),
        ]
    return []
