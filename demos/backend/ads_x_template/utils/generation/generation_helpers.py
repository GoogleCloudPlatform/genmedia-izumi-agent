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

"""Helper functions for media generation (voiceover, music, and context)."""

import logging
from typing import Any

import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset

from ..common import enrichment_utils

logger = logging.getLogger(__name__)

MAX_VOICEOVER_ATTEMPTS = 3

async def generate_background_music(
    user_id: str, background_music_prompt: dict[str, Any], uid: str = ""
) -> Asset | None:
    """Generates the background music for the campaign."""
    # Idempotency: Skip if already generated
    if background_music_prompt.get("asset_id"):
        logger.info("Background music already exists. Skipping generation.")
        asset_service = mediagent_kit.services.aio.get_asset_service()
        return await asset_service.get_asset(background_music_prompt["asset_id"])

    logger.info(f"Generating background music for user {user_id}")
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    music_prompt = background_music_prompt["description"]
    filename = f"background_music_{uid}.mp3" if uid else "background_music.mp3"
    
    try:
        music_asset = await mediagen_service.generate_music_with_lyria(
            user_id=user_id, file_name=filename, prompt=music_prompt
        )
        background_music_prompt["asset_id"] = music_asset.id
        return music_asset
    except Exception as e:
        logger.error(f"Background music generation failed: {e}. Proceeding without music.")
        background_music_prompt["asset_id"] = None
        return None

async def generate_scene_voiceover(
    user_id: str,
    voiceover_prompt: dict[str, Any],
    index: int,
    uid: str = "",
    target_duration: float = 4.0,
) -> Asset | None:
    """Generates voiceover for one scene."""
    # Idempotency: Skip if already generated
    if voiceover_prompt.get("asset_id"):
        logger.info(f"Voiceover for scene {index} already exists. Skipping generation.")
        asset_service = mediagent_kit.services.aio.get_asset_service()
        return await asset_service.get_asset(voiceover_prompt["asset_id"])

    logger.info(f"Generating voiceover for scene {index}")
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    # Safely extract text
    original_text = voiceover_prompt.get("text", "").strip()
    if not original_text:
        return None

    current_text = original_text
    voice_name = "Enceladus" if voiceover_prompt.get("gender") == "male" else "Aoede"
    
    best_asset_so_far = None
    
    for attempt in range(MAX_VOICEOVER_ATTEMPTS):
        filename = f"scene_{index}_voiceover_{uid}_att{attempt}.mp3" if uid else f"scene_{index}_voiceover_att{attempt}.mp3"
        try:
            voiceover_asset = await mediagen_service.generate_speech_single_speaker(
                user_id=user_id,
                file_name=filename,
                text=current_text,
                voice_name=voice_name
            )
            best_asset_so_far = voiceover_asset
            
            actual_duration = voiceover_asset.versions[-1].duration_seconds
            
            if actual_duration <= target_duration:
                logger.info(f"Voiceover for scene {index} accepted. Duration: {actual_duration:.2f}s (Target: {target_duration}s)")
                voiceover_prompt["asset_id"] = voiceover_asset.id
                voiceover_prompt["text"] = current_text
                return voiceover_asset
            
            # Too long, shorten text
            logger.warning(f"Voiceover too long ({actual_duration}s > {target_duration}s). Shortening text...")
            current_text = await enrichment_utils.shorten_script(current_text, target_duration * 0.9, user_id)
            
        except Exception as e:
            logger.error(f"Voiceover generation attempt {attempt} failed: {e}")
            break
            
    # Fallback to best effort
    if best_asset_so_far:
        logger.warning(f"Using best effort voiceover for scene {index} despite duration mismatch.")
        voiceover_prompt["asset_id"] = best_asset_so_far.id
        return best_asset_so_far

    return None

def build_global_context_string(storyboard: dict, scene: dict) -> str:
    """Builds a structured context string from global campaign fields."""
    global_fields = {
        "Theme": storyboard.get("campaign_theme"),
        "Tone": storyboard.get("campaign_tone"),
        "Concept": storyboard.get("concept_description"),
        "Key Message": storyboard.get("key_message"),
        "Visual Style": storyboard.get("global_visual_style"),
        "Setting": storyboard.get("global_setting"),
        "Target Audience": storyboard.get("target_audience_profile"),
        "Brand Voice": ", ".join(storyboard.get("brand_voice_keywords", [])) if storyboard.get("brand_voice_keywords") else storyboard.get("campaign_tone")
    }
    
    active_globals = {k: v for k, v in global_fields.items() if v}
    context_string = ""

    if active_globals:
        context_string += "--- GLOBAL CAMPAIGN CONTEXT ---\n"
        for key, value in active_globals.items():
            context_string += f"{key}: {value}\n"
        context_string += "-------------------------------\n"

    # Add scene-specific Narrative Action or Establishment Shot to the context
    if (est := scene.get("establishment_shot")):
        context_string += f"Establishment Shot: {est}\n"
    if (act := scene.get("narrative_action")):
        context_string += f"Character Action: {act}\n"
        
    return context_string

def clamp_duration(seconds: int | float) -> int:
    """Clamps duration to the next HIGHER Veo-supported value to avoid static frames."""
    if seconds <= 4:
        return 4
    elif seconds <= 6:
        return 6
    else:
        return 8
