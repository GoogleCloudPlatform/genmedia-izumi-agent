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

"""Tools for ingesting user assets."""

import asyncio
import os

from google.adk.tools.tool_context import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context

from ..utils import common_utils

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


_DESCRIPTION_PROMPT = """
Provide a concise (1-2 sentence) summary of this image for an advertising campaign, focusing on its key visual elements.
If visible in the image, include the product's name and price.
The description should be brief but contain essential product details.
"""


async def ingest_assets(tool_context: ToolContext) -> ToolResult:
    """Ingests user-provided assets."""
    user_id = get_user_id_from_context(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    # Run description generation concurrently for all assets.
    asset_tasks = []
    assets = await asset_service.list_assets(user_id=user_id)
    for asset in assets:
        # Safe filename generation for descriptions
        base_name = os.path.basename(asset.file_name)
        file_name = os.path.splitext(base_name)[0] + "_description.txt"
        description_task = mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            file_name=file_name,
            model="gemini-2.5-flash",
            prompt=_DESCRIPTION_PROMPT,
            reference_image_filenames=[asset.file_name],
        )
        asset_tasks.append(description_task)
    descriptions = await asyncio.gather(*asset_tasks, return_exceptions=True)
    user_assets: dict[str, str] = {}
    for asset, description in zip(assets, descriptions, strict=True):
        if isinstance(description, BaseException):
            return tool_failure(f"Failed to describe {asset.file_name}: {description}")
        blob = await asset_service.get_asset_blob(description.id)
        user_assets[asset.file_name] = blob.content.decode()
    tool_context.state[common_utils.USER_ASSETS_KEY] = user_assets

    return tool_success(f"Ingested {len(user_assets)} user assets.")
