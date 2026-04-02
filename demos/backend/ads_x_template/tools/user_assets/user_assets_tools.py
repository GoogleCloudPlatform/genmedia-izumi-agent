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
import logging
import os
from google.adk.tools.tool_context import ToolContext

from utils.adk import get_user_id_from_context
import mediagent_kit

from ...utils.common import common_utils
from ...utils.storyboard import template_library
from ...instructions.user_assets import user_assets_instruction

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def ingest_assets(tool_context: ToolContext) -> ToolResult:
    """Ingests user-provided assets."""
    user_id = get_user_id_from_context(tool_context)
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `ingest_assets` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    logger.info(f"Ingesting assets for user_id: {user_id}")

    asset_service = mediagent_kit.services.aio.get_asset_service()
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    # 1. List all assets for the user
    all_assets = await asset_service.list_assets(user_id=user_id)
    print(f"\n[DEBUG] Total assets found in DB for user {user_id}: {len(all_assets)}")
    for a in all_assets:
        print(f"  - {a.file_name} (ID: {a.id}, MIME: {a.mime_type})")

    # 2. Filter for images and identify existing descriptions
    image_assets = [
        a for a in all_assets if a.mime_type and a.mime_type.startswith("image/")
    ]
    description_assets = {
        a.file_name: a for a in all_assets if a.file_name.endswith("_description.txt")
    }

    user_assets: dict[str, str] = {}
    assets_to_describe = []

    for asset in image_assets:
        desc_file_name = os.path.splitext(asset.file_name)[0] + "_description.txt"
        if desc_file_name in description_assets:
            # Skip generation, just load existing description
            logger.info(f"Loading existing description for {asset.file_name}")
            desc_asset = description_assets[desc_file_name]
            blob = await asset_service.get_asset_blob(desc_asset.id)
            user_assets[asset.file_name] = blob.content.decode()
        else:
            # Need to generate description
            assets_to_describe.append(asset)

    # 3. Generate descriptions for new assets concurrently
    if assets_to_describe:
        logger.info(
            f"Generating descriptions for {len(assets_to_describe)} new assets..."
        )
        asset_tasks = []
        for asset in assets_to_describe:
            # Generate description using multimodal Gemini 3 Pro
            # Note: Now using a real GCS bucket in tests to ensure multimodal stability.
            base_name = os.path.basename(asset.file_name)
            desc_file_name = os.path.splitext(base_name)[0] + "_description.txt"
            description_task = mediagen_service.generate_text_with_gemini(
                user_id=user_id,
                file_name=desc_file_name,
                model="gemini-3.1-pro-preview",  # High-fidelity multimodal description
                prompt=user_assets_instruction.DESCRIPTION_INSTRUCTION,
                reference_image_filenames=[asset.file_name],
            )
            asset_tasks.append(description_task)

        new_descriptions = await asyncio.gather(*asset_tasks, return_exceptions=True)

        for asset, description in zip(assets_to_describe, new_descriptions):
            if isinstance(description, BaseException):
                logger.error(f"Failed to describe {asset.file_name}: {description}")
                continue
            blob = await asset_service.get_asset_blob(description.id)
            user_assets[asset.file_name] = blob.content.decode()

    # --- VIRTUAL CREATOR GENERATION ---
    params_dict = tool_context.state.get(common_utils.PARAMETERS_KEY)
    if not params_dict:
        logger.warning("No parameters found in state. Skipping virtual creator logic.")
        tool_context.state[common_utils.USER_ASSETS_KEY] = user_assets
        return tool_success(f"Ingested {len(user_assets)} user assets (Fallback).")

    from ...utils.parameters.parameters_model import Parameters

    params = Parameters.model_validate(params_dict)

    # Deterministic source of truth: THE PARAMETERS AGENT (Stage 1)
    # This respects both template defaults AND manual user overrides (e.g. from Custom mode)
    should_generate = params.generate_virtual_creator

    if should_generate:
        target_persona = (
            params.brief_results.audience.persona
            if params.brief_results and params.brief_results.audience
            else params.target_audience
        )
        campaign_brief = params.campaign_brief or ""

        # STEP 0: Casting (Deduce Demographics)
        casting_prompt = (
            f"Based on the campaign brief: '{campaign_brief}'\n"
            f"Target Audience Persona: '{target_persona}'\n\n"
            "Identify the ideal social media creator look and personality for this product.\n"
            "Provide a concise, one-sentence description containing ONLY:\n"
            "- Age Range and specific Gender (Must be either Male or Female; choose based on product relevance)\n"
            "- Physical Look (hair, style, distinguishing features)\n"
            "- Personality Vibe (e.g., approachable, chatty, enthusiastic, trustworthy)\n\n"
            "Rules:\n"
            "1. DO NOT provide reasoning or explanations.\n"
            "2. DO NOT describe any action, pose, or background.\n"
            "3. DO NOT use gender-neutral or ambiguous terms; always specify Male or Female.\n"
            "4. DO NOT generate children or celebrities.\n"
            "5. DO NOT include glasses, rings, or jewelry in the look description unless explicitly required by the brief."
        )
        try:
            import uuid

            uid = uuid.uuid4().hex[:4]
            casting_filename = f"creator_casting_{uid}.txt"
            logger.info("Starting Casting for virtual creator...")
            demographic_result = await mediagen_service.generate_text_with_gemini(
                user_id=user_id,
                file_name=casting_filename,
                prompt=casting_prompt,
                reference_image_filenames=[],
                model="gemini-2.5-flash",  # Upgrade to Gemini 2.5 Flash
            )
            casting_blob = await asset_service.get_asset_blob(demographic_result.id)
            demographics = casting_blob.content.decode().strip()
            logger.info(f"Casted Virtual Creator: {demographics}")
            creator_prompt = (
                f"A professional-quality static headshot portrait of a content creator with a clean white background. "
                f"Description: {demographics}. "
                f"Pose: Static, looking directly at the camera, neutral but friendly expression. "
                f"Details: No glasses, no rings, no jewelry. "
                f"Lighting: Even, natural studio lighting. "
                f"Style: Realistic, high-detail, non-model, authentic person vibe."
            )

            import uuid

            uid = uuid.uuid4().hex[:4]
            creator_filename = f"virtual_creator_{uid}.png"

            logger.info(f"Executing Image Generation for: {creator_filename}")
            creator_asset = await mediagen_service.generate_image_with_gemini(
                user_id=user_id,
                file_name=creator_filename,
                prompt=creator_prompt,
                reference_image_filenames=[],
                aspect_ratio="9:16",  # Vertical for Social
                model="gemini-3.1-flash-image-preview",  # Upgrade to Gemini 3.1 Flash Image
            )

            logger.info(
                f"Successfully generated virtual creator. Asset ID: {creator_asset.id}"
            )

            # Safety delay to ensure GCS consistency before next agent/tool looks for it.
            await asyncio.sleep(5)

            # Add to the assets list exposed to the Storyboard Agent
            # ONLY if successful.
            user_assets[creator_filename] = (
                f"A generated virtual creator character ({demographics}). "
                "Use this asset for scenes requiring the 'Creator' or 'Reviewer'."
            )

            # SAVE METADATA FOR HITL/STUDIO
            tool_context.state[common_utils.VIRTUAL_CREATOR_KEY] = {
                "asset_id": creator_filename,
                "prompt": creator_prompt,
                "demographics": demographics,
                "generated_at": (
                    str(creator_asset.versions[-1].create_time)
                    if creator_asset.versions
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"CRITICAL: Failed to generate virtual creator: {e}")
            return tool_failure(f"Mandatory virtual creator generation failed: {e}")

    tool_context.state[common_utils.USER_ASSETS_KEY] = user_assets
    return tool_success(f"Ingested {len(user_assets)} user assets.")
