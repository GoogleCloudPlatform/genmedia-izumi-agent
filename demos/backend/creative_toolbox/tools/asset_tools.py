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

from google.adk.tools import ToolContext
from google.genai import types

import mediagent_kit
from utils.adk import get_user_id_from_context


async def load_asset_and_save_as_artifact(
    tool_context: ToolContext,
    *,
    filename: str = "",
    asset_id: str = "",
    version: int = 0,
) -> str:
    """Loads an asset and makes it available as a session artifact.

    Args:
        tool_context: The tool context.
        filename: The filename of the asset to load.
        asset_id: The ID of the asset to load.
        version: The version of the asset to load.

    Returns:
        A message indicating the artifact ID of the loaded asset.
    """
    asset_service = mediagent_kit.services.aio.get_asset_service()
    user_id = get_user_id_from_context(tool_context)

    load_asset_id = asset_id
    if not load_asset_id and filename:
        user_assets = await asset_service.list_assets(user_id=user_id)
        found_asset = None
        for asset in user_assets:
            if asset.file_name == filename:
                found_asset = asset
                break
        if found_asset:
            load_asset_id = found_asset.id
        else:
            return f"Error: Asset with filename '{filename}' not found."

    if not load_asset_id:
        return "Error: Either asset_id or filename must be provided."

    try:
        if version:
            asset_blob = await asset_service.get_asset_blob(
                asset_id=load_asset_id, version=version
            )
        else:
            asset_blob = await asset_service.get_asset_blob(asset_id=load_asset_id)

        # Make it available as a session artifact for the LLM
        temp_artifact_id = asset_blob.file_name
        part = types.Part.from_bytes(
            data=asset_blob.content, mime_type=asset_blob.mime_type
        )
        await tool_context.save_artifact(filename=temp_artifact_id, artifact=part)

        return f"Asset loaded as session artifact: {temp_artifact_id}"
    except Exception as e:
        return f"Error loading asset: {e}"


async def list_assets(tool_context: ToolContext) -> str:
    """Lists all assets for the current user.

    Args:
        tool_context: The tool context.

    Returns:
        A JSON string representing the list of assets.
    """
    asset_service = mediagent_kit.services.aio.get_asset_service()
    user_id = get_user_id_from_context(tool_context)
    user_assets = await asset_service.list_assets(user_id=user_id)

    if not user_assets:
        return "No assets found for the current user."

    asset_list = []
    for asset in user_assets:
        asset_info = {
            "file_name": asset.file_name,
            "asset_id": asset.id,
            "mime_type": asset.mime_type,
            "current_version": asset.current_version,
        }
        asset_list.append(asset_info)

    return json.dumps(asset_list, indent=2)
