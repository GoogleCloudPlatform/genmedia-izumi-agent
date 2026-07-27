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

from utils.adk import get_user_id_from_context, resolve_workspace_id
import mediagent_kit

from ...utils.common import common_utils
from ...utils.storyboard import template_library
from ...instructions.user_assets import user_assets_instruction
from ..storyboard import production_tools

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def ingest_assets(tool_context: ToolContext) -> ToolResult:
    """Ingests user-provided assets."""
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `ingest_assets` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    workspace_id, ws_error = resolve_workspace_id(tool_context)
    if ws_error:
        return tool_failure(ws_error)
    logger.info(f"Ingesting assets for workspace_id: {workspace_id}")

    asset_service = mediagent_kit.services.aio.get_asset_service()
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    # 1. Skip querying DB for descriptions or hallucinating them without images.
    # We fully rely on the state provided by the interceptor which contains the true image ID and actual image description.
    user_assets: dict[str, str] = {}

    # --- VIRTUAL CREATOR GENERATION ---
    params_dict = tool_context.state.get(common_utils.PARAMETERS_KEY)
    if not params_dict:
        logger.warning("No parameters found in state. Skipping virtual creator logic.")
        existing_user_assets = dict(
            tool_context.state.get(common_utils.USER_ASSETS_KEY) or {}
        )
        existing_user_assets.update(user_assets)
        tool_context.state[common_utils.USER_ASSETS_KEY] = existing_user_assets
        return tool_success(
            f"Ingested {len(existing_user_assets)} user assets (Fallback)."
        )

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
        user_creator_desc = (params.creator_description or "").strip()
        campaign_name = params.campaign_name or ""
        campaign_tone = params.campaign_tone or ""

        # Select (or reuse) the campaign's coherent Look so the cast headshot
        # reflects the SAME styling later injected into every scene (cached in
        # state, so the storyboard binding reuses this exact Look).
        #
        # We pull only WARDROBE + GROOMING as tasteful styling -- NOT the Look's
        # persona ("actor_vibe"). Injecting the persona would turn every creator
        # into that Look's single archetype (e.g. a "Creative Radical") no matter
        # the brand; identity should instead come from the brand/product/audience.
        look_style = ""
        try:
            recipe = await production_tools.select_recipe_for_campaign(
                tool_context,
                params.vertical,
                params.campaign_theme,
                params.campaign_tone,
            )
            look_char = (recipe or {}).get("character", {}) or {}
            look_style = "; ".join(
                b for b in (look_char.get("attire"), look_char.get("grooming")) if b
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Could not resolve Look for casting styling: {e}")

        # STEP 0: Casting (Deduce Demographics).
        # Precedence: the user's explicit description is AUTHORITATIVE. With no
        # description we cast a CREDIBLE, BRAND-APPROPRIATE spokesperson (which
        # varies naturally by product) rather than defaulting to the Look's
        # archetype. The Look only contributes understated wardrobe/grooming.
        if user_creator_desc:
            identity_line = (
                "PRIMARY IDENTITY (authoritative — preserve age, gender, and "
                f"physical features EXACTLY): {user_creator_desc}"
            )
        else:
            identity_line = (
                "PRIMARY IDENTITY: not specified by the user. Cast a credible, "
                "brand-appropriate spokesperson for THIS specific brand, product, "
                "and audience — a believable real person, NOT a fashion model and "
                "NOT an extreme stylized archetype. Fit the brand's positioning "
                "and tone (e.g. premium/gourmet -> refined and understated).\n"
                f"Brand / product: {campaign_name} — {campaign_brief}\n"
                f"Brand tone: {campaign_tone}\n"
                f"Target audience: {target_persona}"
            )
        styling_line = (
            "WARDROBE & GROOMING (tasteful, understated styling that fits the "
            "identity above; must NOT override it or turn the person into a "
            f"costume): {look_style}"
            if look_style
            else ""
        )

        casting_prompt = (
            "You are casting the on-screen creator for an ad.\n"
            f"{identity_line}\n"
            f"{styling_line}\n\n"
            "Provide a concise, one-sentence description containing ONLY:\n"
            "- Age Range and specific Gender (Must be either Male or Female)\n"
            "- Physical Look (hair, style, distinguishing features)\n"
            "- Personality Vibe (e.g., approachable, chatty, enthusiastic, trustworthy)\n\n"
            "Rules:\n"
            "1. If a PRIMARY IDENTITY is given, keep its age, gender, and physical "
            "features EXACTLY; do NOT replace them with the styling.\n"
            "2. The creator must be a believable, brand-appropriate real person — "
            "NOT a stylized fashion archetype or costume.\n"
            "3. DO NOT provide reasoning or explanations.\n"
            "4. DO NOT describe any action, pose, or background.\n"
            "5. Always specify Male or Female (no gender-neutral terms).\n"
            "6. DO NOT generate children or celebrities.\n"
            "7. DO NOT include glasses, rings, or jewelry unless explicitly required."
        )
        try:
            logger.info("Starting Casting for virtual creator...")
            demographics = await mediagen_service.generate_text(
                workspace_id=workspace_id,
                prompt=casting_prompt,
            )
            demographics = demographics.strip()
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
            # NOTE: Unified MediaGenerationServiceInterface adaptation.
            # This would break legacy version due to function signature and method name mismatch.
            workspace_id = str(tool_context.state.get("workspace_id") or "")
            creator_asset = await mediagen_service.generate_image(
                workspace_id=workspace_id,
                prompt=creator_prompt,
                generation_model="gemini-3.1-flash-image",
                aspect_ratio="9:16",
                resolution="1K",
                file_name=creator_filename,
            )

            logger.info(
                f"Successfully generated virtual creator. Asset ID: {creator_asset.id}"
            )

            # Safety delay to ensure GCS consistency before next agent/tool looks for it.
            await asyncio.sleep(5)

            # Define creator filename key using its database ID
            creator_key = f"virtual_creator_{creator_asset.id}.png"

            # Add to the assets list exposed to the Storyboard Agent
            # ONLY if successful.
            user_assets[creator_key] = (
                f"A generated virtual creator character ({demographics}). "
                "Use this asset for scenes requiring the 'Creator' or 'Reviewer'."
            )

            # SAVE METADATA FOR HITL/STUDIO
            tool_context.state[common_utils.VIRTUAL_CREATOR_KEY] = {
                "asset_ref": {
                    "id": creator_asset.id,
                    "asset_type": "generated",
                    "workspace_id": workspace_id,
                },
                "prompt": creator_prompt,
                "demographics": demographics,
                "generated_at": (
                    str(getattr(creator_asset, "created_at", None))
                    if getattr(creator_asset, "created_at", None)
                    else None
                ),
            }

            # Register in state asset_refs map under the identical creator_key
            asset_refs = dict(tool_context.state.get("asset_refs") or {})
            asset_refs[creator_key] = {
                "id": creator_asset.id,
                "asset_type": "generated",
                "workspace_id": workspace_id,
            }
            tool_context.state["asset_refs"] = asset_refs

        except Exception as e:
            logger.error(f"CRITICAL: Failed to generate virtual creator: {e}")
            return tool_failure(f"Mandatory virtual creator generation failed: {e}")

    existing_user_assets = dict(
        tool_context.state.get(common_utils.USER_ASSETS_KEY) or {}
    )
    existing_user_assets.update(user_assets)
    tool_context.state[common_utils.USER_ASSETS_KEY] = existing_user_assets
    return tool_success(f"Ingested {len(existing_user_assets)} user assets.")
