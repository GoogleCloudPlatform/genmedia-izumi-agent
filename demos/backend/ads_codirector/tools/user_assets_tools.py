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

"""Tools for ingesting and annotating user-provided assets."""

import asyncio
import logging
import os

from google.adk.tools.tool_context import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context

from ..instructions import user_assets_instruction
from ..utils import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def ingest_assets(tool_context: ToolContext) -> ToolResult:
    """Ingests and annotates image assets provided by the user."""
    user_id = get_user_id_from_context(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    all_assets = await asset_service.list_assets(user_id=user_id)
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    # Filter for images and EXCLUDE generated artifacts (Asset Pollution)
    assets_to_process = []
    for a in all_assets:
        ext = os.path.splitext(a.file_name)[1].lower()
        if ext in image_extensions:
            if a.file_name.startswith("iter_") or a.file_name.startswith("scene_"):
                continue
            if "_description.txt" in a.file_name:
                continue
            assets_to_process.append(a)

    if not assets_to_process:
        logger.warning("No image assets found to process.")
        tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY] = {}
        tool_context.state[common_utils.USER_ASSETS_KEY] = {}
        return tool_success("No image assets to process.")

    logger.info(f"Annotating {len(assets_to_process)} image assets...")

    asset_tasks = []
    for asset in assets_to_process:
        description_filename = f"{os.path.splitext(asset.file_name)[0]}_description.txt"

        # Resolve filename placeholder for the LLM
        prompt = user_assets_instruction.INSTRUCTION.replace("{file_name}", asset.file_name)

        annotation_task = mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            file_name=description_filename,
            model="gemini-2.5-flash",
            prompt=prompt,
            reference_image_filenames=[asset.file_name],
        )
        asset_tasks.append(annotation_task)

    annotations_results = await asyncio.gather(*asset_tasks, return_exceptions=True)
    annotated_reference_visuals: dict[str, dict] = {}
    legacy_user_assets: dict[str, str] = {}

    for asset, result in zip(assets_to_process, annotations_results, strict=False):
        if isinstance(result, BaseException):
            logger.error(f"Failed to process {asset.file_name}: {result}")
            continue

        blob = await asset_service.get_asset_blob(result.id)
        raw_text = blob.content.decode()

        try:
            # Extract structured data
            annotation_data = await common_utils.parse_json_from_text(
                raw_text, user_id=user_id
            )
            annotation_data["file_name"] = asset.file_name
            annotated_reference_visuals[asset.file_name] = annotation_data

            # ALIGNMENT with ads_x: Store clean caption text in legacy key.
            # This allows proven storyboard prompts to work without JSON noise.
            caption = annotation_data.get("caption", raw_text)
            legacy_user_assets[asset.file_name] = caption

            # Force metadata update for UI side-pane sync
            await asset_service.update_asset(asset_id=asset.id, caption=caption)

        except Exception as e:
            logger.error(
                f"Failed to parse JSON for {asset.file_name}: {e}. Raw text: {raw_text}"
            )
            legacy_user_assets[asset.file_name] = raw_text

    # Populate BOTH keys to ensure both legacy and new agents are satisfied.
    tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY] = (
        annotated_reference_visuals
    )
    tool_context.state[common_utils.USER_ASSETS_KEY] = legacy_user_assets

    return tool_success(
        f"Successfully processed {len(legacy_user_assets)} reference visuals."
    )
