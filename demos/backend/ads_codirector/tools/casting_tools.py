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

"""Tools for generating character reference collages."""

import logging

from google.adk.tools.tool_context import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context

from ..utils import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def generate_character_collage(tool_context: ToolContext) -> ToolResult:
    """Generates a 3-view character collage reference image."""
    user_id = get_user_id_from_context(tool_context)
    state = tool_context.state

    casting_data = state.get(common_utils.CASTING_KEY)
    if not casting_data:
        return tool_failure("No casting data found in state.")

    collage_prompt = casting_data.get("collage_prompt")
    if not collage_prompt:
        return tool_failure("Missing collage_prompt for character generation.")

    # Identify character references using structured roles OR keyword fallback
    annotated_visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})
    user_assets = state.get(common_utils.USER_ASSETS_KEY, {})
    character_references = []

    # 1. Try structured roles first
    for filename, metadata in annotated_visuals.items():
        if isinstance(metadata, dict) and metadata.get("semantic_role") == "character":
            character_references.append(filename)

    # 2. Fallback to keyword matching if none found via role
    if not character_references:
        for filename, caption in user_assets.items():
            caption_lower = caption.lower()
            if any(kw in caption_lower for kw in ["character", "person", "human", "man", "woman", "actor"]):
                character_references.append(filename)

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    iteration_num = state.get("mab_iteration", 0)
    collage_filename = f"iter_{iteration_num}_character_collage.png"

    logger.info(
        f"Generating character collage {collage_filename} with {len(character_references)} references..."
    )

    try:
        # Generate the collage using Gemini 3.1 Flash Image
        asset = await mediagen_service.generate_image_with_gemini(
            user_id=user_id,
            file_name=collage_filename,
            model="gemini-3.1-flash-image-preview",
            prompt=collage_prompt,
            reference_image_filenames=character_references,
        )

        # Add this new collage to user_assets so storyboard agent can find it
        new_caption = f"Primary character reference collage (Iteration {iteration_num}): {casting_data.get('character_profile')}. Wearing: {casting_data.get('wardrobe_description')}"
        user_assets[collage_filename] = new_caption
        state[common_utils.USER_ASSETS_KEY] = user_assets

        # Also update structured annotated_reference_visuals for MAB logging/reporting
        annotated_visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})
        annotated_visuals[collage_filename] = {
            "file_name": collage_filename,
            "caption": new_caption,
            "semantic_role": "character",
        }
        state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY] = annotated_visuals

        state[common_utils.CHARACTER_COLLAGE_ID_KEY] = asset.id

        # UI Sync Trigger
        from utils.adk import display_asset

        await display_asset(tool_context=tool_context, asset_id=asset.id)

        return tool_success(f"Generated character collage: {asset.file_name}")

    except Exception as e:
        logger.error(f"Failed to generate character collage: {e}")
        return tool_failure(f"Failed to generate character collage: {e}")
