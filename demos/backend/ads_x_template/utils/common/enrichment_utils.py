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

"""Utility functions for prompt enrichment and script handling."""

import logging
import uuid
from typing import Any, Dict, Tuple

import mediagent_kit.services.aio
from ...instructions.generation import generation_prompts

logger = logging.getLogger(__name__)

async def enrich_prompt_with_llm(
    user_id: str,
    description: str,
    prompt_data: Dict[str, Any],
    scene_index: int,
    prompt_type: str,
    context: str = "",
    is_ugc: bool = False,
    reference_image_filenames: list[str] = [],
) -> Tuple[str, str | None]:
    """
    Uses Gemini to rewrite the prompt. Returns (enriched_text, asset_id).
    """
    # SANITIZATION: Strip internal logic tags from description before building prompt
    for tag in ["[PRODUCT REQUIRED]", "[CHARACTER REQUIRED]", "[PERSON REQUIRED]"]:
        description = description.replace(tag, "").replace(tag.lower(), "")
    description = description.strip()

    cinematography = prompt_data.get("cinematography", {})
    audio = prompt_data.get("audio", {})

    # Construct Raw Input string following Veo Formula
    parts = []
    if val := cinematography.get("camera_description"):
        parts.append(f"Camera: {val}")
    if val := cinematography.get("lens_specification"):
        parts.append(f"Lens: {val}")
    parts.append(f"Action: {description}")
    if val := cinematography.get("lighting_description"):
        parts.append(f"Lighting: {val}")
    if val := cinematography.get("velocity_hint"):
        parts.append(f"Velocity: {val}")
    if val := cinematography.get("mood"):
        parts.append(f"Mood: {', '.join(val)}")
    
    # Re-inject Dialogue into Video Prompts for better synchronization.
    # ONLY for UGC cases where we use the UGC instruction set that supports Dialogue.
    if is_ugc:
        if val := audio.get("dialogue_hint"):
            parts.append(f"Dialogue: {val}")
    
    # Inject Text Overlay Hint for both Image and Video Prompts
    if val := prompt_data.get("on_screen_text_hint"):
        parts.append(f"Text Overlay: {val}")

    raw_input = " | ".join(parts)

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    # Select the correct base instruction
    if prompt_type == "image":
        role_instruction = (
            generation_prompts.UGC_IMAGE_ENRICHMENT_INSTRUCTION
            if is_ugc
            else generation_prompts.BASE_IMAGE_ENRICHMENT_INSTRUCTION
        )
    else:
        role_instruction = (
            generation_prompts.UGC_VIDEO_ENRICHMENT_INSTRUCTION
            if is_ugc
            else generation_prompts.BASE_VIDEO_ENRICHMENT_INSTRUCTION
        )

    # Assemble a structured "Rich Prompt Packet"
    prompt_packet = []

    # 1. THE SYSTEM ROLE & METHODOLOGY
    prompt_packet.append(f"### [METHODOLOGY & ROLE]\n{role_instruction}")

    # 2. THE CREATIVE BRIEF (HIGH PRIORITY STRATEGY)
    if context:
        if "**STARTING IMAGE DESCRIPTION" in context:
            parts = context.split("**STARTING IMAGE DESCRIPTION")
            strategy_part = parts[0].strip()
            anchor_part = parts[1].strip().lstrip("(VISUAL ANCHOR):").strip()
            
            prompt_packet.append(f"### [CREATIVE BRIEF: STRATEGIC ALIGNMENT]\n{strategy_part}")
            prompt_packet.append(f"### [VISUAL ANCHOR: FRAME 0 STATE]\n{anchor_part}")
        else:
            prompt_packet.append(f"### [CREATIVE BRIEF: STRATEGIC ALIGNMENT]\n{context}")

    # 3. TECHNICAL SPECIFICATIONS (CINEMATOGRAPHY)
    tech_specs = f"Camera: {cinematography.get('camera_description', 'Natural')}\n"
    tech_specs += f"Lens: {cinematography.get('lens_specification', '35mm')}\n"
    tech_specs += f"Lighting: {cinematography.get('lighting_description', 'Studio')}\n"
    tech_specs += f"Mood: {', '.join(cinematography.get('mood', ['Commercial']))}"
    prompt_packet.append(f"### [TECHNICAL SPECIFICATIONS]\n{tech_specs}")

    # 4. REFERENCE ASSETS (IF ANY)
    if reference_image_filenames:
        if prompt_type == "image":
            prompt_packet.append("### [PRODUCT VISUAL CONTEXT]\nUse the attached reference images as the GROUND TRUTH for colors, materials, and logos.")
        else:
            prompt_packet.append("### [VISUAL CONTINUITY REFERENCE]\nUse the attached image as the literal starting frame. Do NOT deviate from its established look.")

    # 5. AUDIO & PERFORMANCE CONTEXT
    if prompt_type == "video":
        audio_guidance = (
            "The character is a relatable persona recording a message for a social audience. "
            "Prioritize natural talking-to-camera movements and handheld-style micro-expressions."
            if is_ugc else
            "The character is a professional visual presence. While expressive and alive, "
            "prioritize natural model-like micro-expressions and elegant movements. Avoid exaggerated "
            "talking-head mouth movements unless the narrative strictly requires it."
        )
        prompt_packet.append(
            f"### [AUDIO & PERFORMANCE GUIDANCE]\n"
            f"NOTE: A separate professional voiceover track will be added in post-production. {audio_guidance}"
        )

    # 6. THE NARRATIVE MISSION (THE INPUT)
    prompt_packet.append(f"### [PRIMARY NARRATIVE ACTION TO ENRICH]\n{description}")

    # 7. THE FINAL COMMAND
    mission_commands = [
        "**MISSION:** Synthesize the sections above into a single, high-fidelity cinematic prompt.",
        "Your output must be a single cohesive paragraph description (Veo/Imagen Formula)."
    ]
    
    if context:
        mission_commands.append("You MUST prioritize the [CREATIVE BRIEF] for the overarching visual tone and brand mood.")
    
    mission_commands.append("You MUST prioritize the [TECHNICAL SPECIFICATIONS] for camera movement and lighting details.")
    
    if "**STARTING IMAGE DESCRIPTION" in context:
         mission_commands.append("You MUST strictly honor the [VISUAL ANCHOR] state to ensure seamless continuity.")

    prompt_packet.append(f"### [FINAL MISSION]\n" + "\n".join(mission_commands))

    final_prompt = "\n\n".join(prompt_packet)

    try:
        short_hash = uuid.uuid4().hex[:6]
        temp_filename = (
            f"prompt_enrich_scene_{scene_index}_{prompt_type}_{short_hash}.txt"
        )

        asset = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            file_name=temp_filename,
            prompt=final_prompt,
            reference_image_filenames=reference_image_filenames,
            model="gemini-3-flash-preview",
        )

        # Read content
        blob = await asset_service.get_asset_blob(asset.id)
        enriched_text = blob.content.decode("utf-8").strip()
        return enriched_text, asset.id

    except Exception as e:
        logger.warning(f"Prompt enrichment failed ({e}). Falling back to raw formula.")
        return raw_input.replace("|", "."), None

async def shorten_script(text: str, target_duration: float, user_id: str) -> str:
    """Uses an LLM to shorten a script to a target duration."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    prompt = (
        "You are a professional script editor. Your task is to shorten the following"
        f" text to fit within a {target_duration:.1f} second time limit, while"
        " preserving the original meaning and tone. Respond only with the revised,"
        f" shortened script.\n\nORIGINAL SCRIPT:\n{text}"
    )
    try:
        unique_id = uuid.uuid4().hex[:8]
        response_asset = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            prompt=prompt,
            file_name=f"shortened_script_{unique_id}.txt",
            reference_image_filenames=[],
            model="gemini-2.5-flash",
        )
        asset_service = mediagent_kit.services.aio.get_asset_service()
        blob = await asset_service.get_asset_blob(response_asset.id)
        shortened_text = blob.content.decode().strip()
        logger.info(
            f"Successfully shortened script from '{text}' to '{shortened_text}'"
        )
        return shortened_text
    except Exception as e:
        logger.error(f"Failed to shorten script: {e}")
        return text  # Return original text on failure
