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
import logging
from html.parser import HTMLParser

from google.adk.tools import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context
from mediagent_kit.services import types
from mediagent_kit.services.asset_service import AssetService

logger = logging.getLogger(__name__)


class AssetUriExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.asset_filenames = set()

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if (
                attr in ("src", "srcset", "data")
                and value
                and value.startswith("asset://")
            ):
                uri = value[len("asset://") :]
                file_name = uri.split("/")[0]
                self.asset_filenames.add(file_name)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


async def _process_html_assets(
    user_id: str, html_content: str, asset_service: AssetService
) -> tuple[types.Html, list[str]]:
    """Processes HTML content to find and resolve asset URIs."""
    parser = AssetUriExtractor()
    parser.feed(html_content)
    asset_filenames = parser.asset_filenames

    asset_ids = []
    not_found_assets = []
    if asset_filenames:
        user_assets = {
            asset.file_name: asset
            for asset in await asset_service.list_assets(user_id=user_id)
        }
        for filename in asset_filenames:
            asset = user_assets.get(filename)
            if asset:
                asset_ids.append(asset.id)
            else:
                logger.warning(
                    f"Asset with filename '{filename}' not found for user '{user_id}'"
                )
                not_found_assets.append(filename)
    return types.Html(content=html_content, asset_ids=asset_ids), not_found_assets


async def create_html_canvas(
    tool_context: ToolContext,
    *,
    title: str,
    html_content: str,
) -> str:
    """Creates a new HTML canvas.

    Args:
        tool_context: The tool context.
        title: The title of the canvas.
        html_content: The HTML content to save.

    Returns:
        A message indicating the result of the operation.
    """
    user_id = get_user_id_from_context(tool_context)
    canvas_service = mediagent_kit.services.aio.get_canvas_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    logger.info(f"Creating new canvas with title: {title}")
    html, not_found_assets = await _process_html_assets(
        user_id, html_content, asset_service
    )

    try:
        canvas = await canvas_service.create_canvas(
            user_id=user_id, title=title, html=html
        )
        success_message = f"HTML canvas '{canvas.title}' saved with ID: {canvas.id}."
        if not_found_assets:
            success_message += f" Warning: The following assets were not found: {', '.join(not_found_assets)}."
        logger.info(success_message)
        return success_message
    except Exception as e:
        error_message = f"Error creating canvas: {e}"
        logger.error(error_message)
        return error_message


async def update_canvas_title(
    tool_context: ToolContext,
    *,
    canvas_id: str,
    title: str,
) -> str:
    """Updates the title of an existing canvas.

    Args:
        tool_context: The tool context.
        canvas_id: The ID of the canvas to update.
        title: The new title for the canvas.

    Returns:
        A message indicating the result of the operation.
    """
    user_id = get_user_id_from_context(tool_context)
    canvas_service = mediagent_kit.services.aio.get_canvas_service()

    logger.info(f"Updating title for canvas with ID: {canvas_id}")
    try:
        canvas = await canvas_service.get_canvas(canvas_id)
        if not canvas or canvas.user_id != user_id:
            return f"Error: Canvas with ID '{canvas_id}' not found."

        updated_canvas = await canvas_service.update_canvas(canvas_id, title=title)
        return f"Canvas '{updated_canvas.title}' (ID: {canvas_id}) title updated."
    except Exception as e:
        error_message = f"Error updating canvas title: {e}"
        logger.error(error_message)
        return error_message


async def update_canvas_html(
    tool_context: ToolContext,
    *,
    canvas_id: str,
    html_content: str,
) -> str:
    """Updates the HTML content of an existing canvas.

    Args:
        tool_context: The tool context.
        canvas_id: The ID of the canvas to update.
        html_content: The new HTML content for the canvas.

    Returns:
        A message indicating the result of the operation.
    """
    user_id = get_user_id_from_context(tool_context)
    canvas_service = mediagent_kit.services.aio.get_canvas_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    logger.info(f"Updating HTML for canvas with ID: {canvas_id}")
    html, not_found_assets = await _process_html_assets(
        user_id, html_content, asset_service
    )

    try:
        canvas = await canvas_service.get_canvas(canvas_id)
        if not canvas or canvas.user_id != user_id:
            return f"Error: Canvas with ID '{canvas_id}' not found."

        updated_canvas = await canvas_service.update_canvas(canvas_id, html=html)
        success_message = (
            f"Canvas '{updated_canvas.title}' (ID: {canvas_id}) HTML content updated."
        )
        if not_found_assets:
            success_message += f" Warning: The following assets were not found: {', '.join(not_found_assets)}."
        logger.info(success_message)
        return success_message
    except Exception as e:
        error_message = f"Error updating canvas HTML: {e}"
        logger.error(error_message)
        return error_message


async def list_canvases(tool_context: ToolContext) -> str:
    """Lists all canvases for the current user.

    Args:
        tool_context: The tool context.

    Returns:
        A JSON string representing the list of canvases.
    """
    canvas_service = mediagent_kit.services.aio.get_canvas_service()
    user_id = get_user_id_from_context(tool_context)
    user_canvases = await canvas_service.list_canvases(user_id=user_id)

    if not user_canvases:
        return "No canvases found for the current user."

    canvas_list = [{"id": canvas.id, "title": canvas.title} for canvas in user_canvases]

    return json.dumps(canvas_list, indent=2)
