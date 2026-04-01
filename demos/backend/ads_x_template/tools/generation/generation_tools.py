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

"""Tools for generating all ad campaign media."""

import asyncio
import logging
import json
import uuid
from typing import Any, List

from google.adk.tools.tool_context import ToolContext

from utils.adk import get_user_id_from_context
import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset

from ...utils.common import common_utils, enrichment_utils, scene_generation_utils
from ...utils.storyboard import template_library, storyboard_model
from ...utils.generation import grouping_utils, generation_helpers
from . import voiceover_tools

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Media generation helper logic moved to scene_generation_utils.py


async def generate_scene_video(
    user_id: str,
    scene: dict[str, Any],
    index: int,
    aspect_ratio: str,
    uid: str = "",
    veo_method: str = "image_to_video",
    first_frame_asset: Asset | None = None,
    context: str = "",
    allow_veo_audio: bool = False,
) -> List[Asset]:
    """Generates the video for one scene with verification loop."""
    video_prompt_data = scene["video_prompt"]

    # Idempotency: Skip if already generated
    if video_prompt_data.get("asset_id"):
        logger.info(f"Video for scene {index} already exists. Skipping generation.")
        asset_service = mediagent_kit.services.aio.get_asset_service()
        video_asset = await asset_service.get_asset(video_prompt_data["asset_id"])
        return [first_frame_asset, video_asset] if first_frame_asset else [video_asset]

    logger.info(f"Generating video for scene {index}")
    mediagent_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()
    voiceover_text = scene.get("voiceover_prompt", {}).get("text", "")

    if not first_frame_asset:
        logger.warning(f"Skipping video generation for scene {index} due to missing first frame.")
        scene["video_prompt"]["asset_id"] = None
        return []

    valid_duration = generation_helpers.clamp_duration(video_prompt_data.get("duration_seconds", 6))
    
    # Enrichment Logic
    enrichment_data = video_prompt_data.copy()
    if allow_veo_audio:
        if voiceover_text:
            enrichment_data["audio"] = {"dialogue_hint": voiceover_text}
        elif audio_hints := scene.get("audio_hints"):
            enrichment_data["audio"] = audio_hints

    final_video_prompt, enrichment_asset_id = await enrichment_utils.enrich_prompt_with_llm(
        user_id,
        video_prompt_data["description"],
        enrichment_data,
        scene_index=index,
        prompt_type="video",
        context=context,
        is_ugc=allow_veo_audio,
        reference_image_filenames=[first_frame_asset.file_name], 
    )
    if enrichment_asset_id:
        video_prompt_data["enrichment_asset_id"] = enrichment_asset_id

    try:
        winner_asset = await scene_generation_utils.generate_scene_video(
            user_id=user_id,
            scene=scene,
            index=index,
            valid_duration=valid_duration,
            aspect_ratio=aspect_ratio,
            allow_veo_audio=allow_veo_audio,
            veo_method=veo_method,
            first_frame_asset=first_frame_asset,
            final_video_prompt=final_video_prompt,
            uid=uid,
        )
        
        # Sync back to storyboard for persistence
        video_prompt_data["asset_id"] = winner_asset.id
        return [first_frame_asset, winner_asset]

    except Exception as e:
        logger.error(f"Critical video generation failure for scene {index}: {e}")
        # Critical Fallback
        logger.warning(f"Video generation failed for scene {index}. Using static frame.")
        video_prompt_data["asset_id"] = first_frame_asset.id
        return [first_frame_asset, first_frame_asset]


async def generate_scene(
    user_id: str,
    scene: dict[str, Any],
    index: int,
    aspect_ratio: str,
    uid: str = "",
    use_voiceover: bool = True,
    veo_method: str = "image_to_video",
    allow_veo_audio: bool = False,
    global_context: str = "",
) -> List[Asset]:
    """Generates the media for one scene."""
    # Idempotency: Skip if first frame already exists
    first_frame_prompt = scene.get("first_frame_prompt", {})
    first_frame_asset = None
    first_frame_desc = ""

    if first_frame_prompt.get("asset_id"):
        logger.info(f"First frame for scene {index} already exists. Skipping generation.")
        asset_service = mediagent_kit.services.aio.get_asset_service()
        first_frame_asset = await asset_service.get_asset(first_frame_prompt["asset_id"])
    else:
        logger.info(f"Starting generation for scene {index}")
        
        try:
            first_frame_asset, first_frame_desc = await scene_generation_utils.generate_scene_first_frame(
                user_id,
                scene["first_frame_prompt"],
                index,
                aspect_ratio,
                voiceover_text=scene.get("voiceover_prompt", {}).get("text", ""),
                on_screen_text_hint=scene.get("on_screen_text_hint", ""),
                uid=uid,
                is_ugc=allow_veo_audio,
                context=global_context,
            )
            # Persist first frame asset id
            scene["first_frame_prompt"]["asset_id"] = first_frame_asset.id
        except Exception as e:
            logger.error(f"Critical failure generating first frame for scene {index}: {e}")
            return []
    
    # Voiceover handling (idempotent helper will skip if asset_id exists)
    voiceover_task = None
    if use_voiceover:
        target_duration = scene.get("duration_seconds", 4.0)
        voiceover_task = generation_helpers.generate_scene_voiceover(
            user_id, scene["voiceover_prompt"], index, uid, target_duration=target_duration
        )

    blended_video_context = global_context
    if first_frame_desc:
        blended_video_context += f"\n\n**STARTING IMAGE DESCRIPTION (VISUAL ANCHOR):**\n{first_frame_desc}"
    
    video_task = generate_scene_video(
        user_id, 
        scene, 
        index, 
        aspect_ratio, 
        uid, 
        veo_method, 
        first_frame_asset=first_frame_asset, 
        context=blended_video_context,
        allow_veo_audio=allow_veo_audio, 
    )
    
    tasks = [video_task]
    if voiceover_task:
        tasks.append(voiceover_task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


async def generate_all_media(tool_context: ToolContext) -> ToolResult:
    """Generates the media for all scenes in the storyboard."""
    logger.error("⭐⭐⭐ [NATIVE TOOL INVOCATION] `generate_all_media` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐")
    logger.info("Tool 'generate_all_media' invoked.")
    
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure("Missing storyboard.")
    
    if (parameters := tool_context.state.get(common_utils.PARAMETERS_KEY)) is None:
        return tool_failure("Missing parameters.")

    orientation = parameters.get("target_orientation", "landscape").lower()
    aspect_ratio = "9:16" if orientation in ["portrait", "vertical", "9:16"] else "16:9"
    template_name = parameters.get("template_name", "Custom")
    template_obj = template_library.get_template_by_name(template_name)
    
    use_voiceover = template_obj.use_voiceover
    veo_method = template_obj.veo_method
    is_ugc = (template_obj.industry_type == "Social Native") or (storyboard.get("campaign_theme") == "Social Native") or (parameters.get("vertical") in ["Social Native", "UGC"])

    uid = uuid.uuid4().hex[:4]
    user_id = get_user_id_from_context(tool_context)

    # --- VOICE OVER GROUPING LOGIC ---
    voiceover_groups = []
    if not is_ugc:
        try:
            storyboard_obj = storyboard_model.Storyboard(**storyboard)
            voiceover_groups = grouping_utils.create_voiceover_groups(storyboard_obj)
            
            group_tasks = []
            for i, group in enumerate(voiceover_groups):
                first_scene_idx = group.scene_indices[0]
                style_description = storyboard["scenes"][first_scene_idx]["voiceover_prompt"].get("description", "A professional commercial voiceover.")
                group_tasks.append(voiceover_tools.generate_group_voiceover(user_id=user_id, group=group, style_prompt=style_description, group_index=i))
            
            if group_tasks:
                await asyncio.gather(*group_tasks)
                storyboard["voiceover_groups"] = [g.model_dump() for g in voiceover_groups]
        except Exception as e:
            logger.error(f"Voiceover grouping failure: {e}")

    use_per_scene_voiceover = use_voiceover if not voiceover_groups else False

    # --- ASSET BINDING (Hardened & Sanitized) ---
    user_assets = tool_context.state.get(common_utils.USER_ASSETS_KEY, {})
    creator_metadata = tool_context.state.get(common_utils.VIRTUAL_CREATOR_KEY, {})
    creator_id = creator_metadata.get("asset_id") or next((k for k in user_assets.keys() if k.startswith("virtual_creator_")), None)
    primary_product = next((k for k in user_assets.keys() if not k.startswith("virtual_creator_") and "logo" not in k.lower()), None)
    
    scenes = storyboard.get("scenes", [])
    if not scenes:
        return tool_failure("Malformed storyboard: 'scenes' key is missing. Please regenerate the storyboard.")

    for scene in scenes:
        first_frame_prompt = scene.get("first_frame_prompt", {})
        desc = first_frame_prompt.get("description", "").upper()
        guidance = scene.get("asset_guidance", "").upper()
        
        # Sanitization: Filter out tags from the assets list if LLM accidentally included them
        assets = [a for a in first_frame_prompt.get("assets", []) if not (str(a).startswith("[") and str(a).endswith("]"))]
        
        # 1. CHARACTER BINDING (Virtual Creator)
        char_triggers = ["[CHARACTER REQUIRED]", "CREATOR", "[PERSON REQUIRED]", "PERSON", "HUMAN", "TALKING HEAD"]
        if creator_id and (any(t in desc for t in char_triggers) or any(t in guidance for t in char_triggers)):
            if creator_id not in assets: 
                assets.append(creator_id)
                logger.info(f"Bound Creator {creator_id} to scene based on description/guidance.")
        
        # 2. PRODUCT BINDING (Fuzzy/Proactive)
        prod_triggers = ["[PRODUCT REQUIRED]", "PRODUCT", "LOGO", "BRAND", "BOTTLE", "CAN", "DEVICE", "ITEM", "CLOSE-UP", "MACRO", "DETAIL SHOT", "HERO SHOT"]
        is_product_scene = any(t in desc for t in prod_triggers) or any(t in guidance for t in prod_triggers)
        
        if primary_product and is_product_scene:
            if primary_product not in assets: 
                assets.append(primary_product)
                logger.info(f"Bound Product {primary_product} to scene based on triggers.")
        
        # 3. SAFETY FALLBACK: Avoid Empty Assets in Storyboard (Prevents Hallucinations)
        # If the list is STILL empty and it's not a CTA/Text-only scene, 
        # proactive binding of the primary product ensures the model has a visual anchor.
        if not assets and primary_product and "TEXT" not in desc and "CTA" not in desc:
            assets.append(primary_product)
            logger.info(f"Proactive Fallback: Bound {primary_product} to scene to prevent hallucination.")

        # 4. PROMPT SANITIZATION: Strip tags from description before persistence and media generation
        final_desc = first_frame_prompt.get("description", "")
        for tag in ["[PRODUCT REQUIRED]", "[CHARACTER REQUIRED]", "[PERSON REQUIRED]"]:
             final_desc = final_desc.replace(tag, "").replace(tag.lower(), "")
        scene["first_frame_prompt"]["description"] = final_desc.strip()
        
        if "video_prompt" in scene:
            v_desc = scene["video_prompt"].get("description", "")
            for tag in ["[PRODUCT REQUIRED]", "[CHARACTER REQUIRED]", "[PERSON REQUIRED]"]:
                v_desc = v_desc.replace(tag, "").replace(tag.lower(), "")
            scene["video_prompt"]["description"] = v_desc.strip()

        scene["first_frame_prompt"]["assets"] = assets

    # --- CORE GENERATION ---
    if "background_music_prompt" not in storyboard:
        return tool_failure("Malformed storyboard: 'background_music_prompt' key is missing.")

    music_task = generation_helpers.generate_background_music(user_id, storyboard["background_music_prompt"], uid)
    scene_tasks = [
        generate_scene(
            user_id, scene, index, aspect_ratio, uid=uid, use_voiceover=use_per_scene_voiceover, veo_method=veo_method,
            allow_veo_audio=is_ugc, global_context=generation_helpers.build_global_context_string(storyboard, scene),
        )
        for index, scene in enumerate(storyboard["scenes"])
    ]

    results = await asyncio.gather(music_task, *scene_tasks, return_exceptions=True)
    return tool_success("🎬 **Visuals Rendered!** All cinematic scenes successfully generated. Proceeding to stitching...")


async def generate_single_scene(tool_context: ToolContext, scene_index: int) -> ToolResult:
    """Regenerates a single specific scene. (HITL Tool)"""
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None or (parameters := tool_context.state.get(common_utils.PARAMETERS_KEY)) is None:
        return tool_failure("Missing storyboard or parameters.")

    if scene_index < 0 or scene_index >= len(storyboard["scenes"]):
        return tool_failure(f"Invalid scene index: {scene_index}")

    orientation = parameters.get("target_orientation", "landscape").lower()
    aspect_ratio = "9:16" if orientation in ["portrait", "vertical", "9:16"] else "16:9"
    template_name = parameters.get("template_name", "")
    template_obj = template_library.get_template_by_name(template_name)
    is_ugc = (template_obj.industry_type == "Social Native") or (storyboard.get("campaign_theme") == "Social Native") or (parameters.get("vertical") in ["Social Native", "UGC"])
    
    user_id = get_user_id_from_context(tool_context)
    scene = storyboard["scenes"][scene_index]
    
    # Simple Binding refresh
    user_assets = tool_context.state.get(common_utils.USER_ASSETS_KEY, {})
    creator_id = next((k for k in user_assets.keys() if k.startswith("virtual_creator_")), None)
    primary_product = next((k for k in user_assets.keys() if not k.startswith("virtual_creator_") and "logo" not in k.lower()), None)
    
    desc = scene["first_frame_prompt"].get("description", "").upper()
    assets = scene["first_frame_prompt"].get("assets", [])
    if creator_id and ("[CHARACTER REQUIRED]" in desc or "CREATOR" in desc):
        if creator_id not in assets: assets.append(creator_id)
    scene["first_frame_prompt"]["assets"] = assets

    await generate_scene(
        user_id, scene, scene_index, aspect_ratio, uid=uuid.uuid4().hex[:4],
        use_voiceover=template_obj.use_voiceover, veo_method=template_obj.veo_method, allow_veo_audio=is_ugc,
        global_context=generation_helpers.build_global_context_string(storyboard, scene),
    )
    return tool_success(f"🎬 **Visuals Rendered!** Successfully regenerated scene {scene_index}.")
