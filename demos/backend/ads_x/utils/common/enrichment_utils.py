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

from . import common_utils
from ...instructions.generation import generation_prompts

logger = logging.getLogger(__name__)


async def enrich_prompt_with_llm(
    workspace_id: str,
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
    description = common_utils.tidy_spacing(description)

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

            prompt_packet.append(
                f"### [CREATIVE BRIEF: STRATEGIC ALIGNMENT]\n{strategy_part}"
            )
            prompt_packet.append(f"### [VISUAL ANCHOR: FRAME 0 STATE]\n{anchor_part}")
        else:
            prompt_packet.append(
                f"### [CREATIVE BRIEF: STRATEGIC ALIGNMENT]\n{context}"
            )

    # 3. TECHNICAL SPECIFICATIONS (CINEMATOGRAPHY)
    tech_specs = f"Camera: {cinematography.get('camera_description', 'Natural')}\n"
    tech_specs += f"Lens: {cinematography.get('lens_specification', '35mm')}\n"
    tech_specs += f"Lighting: {cinematography.get('lighting_description', 'Studio')}\n"
    tech_specs += f"Mood: {', '.join(cinematography.get('mood', ['Commercial']))}"
    prompt_packet.append(f"### [TECHNICAL SPECIFICATIONS]\n{tech_specs}")

    # 4. REFERENCE ASSETS (IF ANY)
    if reference_image_filenames:
        if prompt_type == "image":
            prompt_packet.append(
                "### [PRODUCT VISUAL CONTEXT]\nUse the attached reference images as the GROUND TRUTH for colors, materials, and logos."
            )
        else:
            prompt_packet.append(
                "### [WHAT THE SHOT ALREADY CONTAINS]\n"
                "The action below has already been checked against this shot's "
                "rendered first frame, so it is a true account of what is "
                "there at the start. You are not shown that frame; the action "
                "is your only sight of it. Read every object it names as "
                "present, and every object it does not name as absent.\n"
                "Movement is unconstrained. Invent freely in time within the "
                "world the action establishes."
            )

    # 5. AUDIO & PERFORMANCE CONTEXT
    if prompt_type == "video":
        audio_guidance = (
            "The character is a relatable persona recording a message for a social audience. "
            "Prioritize natural talking-to-camera movements and handheld-style micro-expressions."
            if is_ugc
            else "The character is a professional visual presence. While expressive and alive, "
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
        "Your output must be a single cohesive paragraph description (Veo/Imagen Formula).",
        (
            "CRITICAL ART DIRECTION: If the action contains an "
            "[ART DIRECTION (NON-NEGOTIABLE)] block, you MUST faithfully weave EVERY "
            "one of its anchors (Mode, Aesthetic, Cast, Wardrobe, Grooming, Lighting, "
            "Key Light, Optics, Texture) into your description. Do NOT substitute, "
            "soften, or omit them. Express them in natural cinematic language and do "
            "NOT print the literal bracket tag."
        ),
        (
            "BRAND MARK FIDELITY: a supplied logo or wordmark is reproduced "
            "exactly as provided, in its own colours and proportions. The art "
            "direction governs the scene around it - the surface it rests on, "
            "the light falling across it, the depth of field - never the mark "
            "itself. Do NOT recolour, tint, plate, or re-finish it to match "
            "the palette, and do NOT describe it in the palette's materials."
        ),
    ]

    # A video call is handed a frame that has already settled what is in the
    # shot, so it is asked for time rather than composition.
    if prompt_type == "video":
        mission_commands.append(
            "WHAT EXISTS IS SETTLED BY THE FRAME. Invent freely in time: "
            "movement, shifting light, a rack of focus, rising steam, drifting "
            "dust, a travelling reflection, the way the camera breathes. Those "
            "are the frame's own contents behaving over the seconds that "
            "follow, and richer is better. What you must not do is add matter: "
            "no object or substance the frame does not already hold, and no "
            "person or hand entering a shot they were never in. If it would "
            "have to be painted into the picture before the clip could start, "
            "it does not belong in the action."
        )
        mission_commands.append(
            "TEXT DOES NOT VANISH. Readable text in the frame - a logo "
            "lockup, a product name, a label, a sign - is still accounted for "
            "when the shot ends. It may hold, drift out of frame with the "
            "camera, or fade. It may not be present in one moment and gone "
            "the next. This is one continuous shot: do not change framing "
            "part way through."
        )

    # Composition rules for a still frame. A video call is anchored by the
    # first frame it is handed, so sending these there would spend the
    # model's attention on decisions the image has already made.
    if prompt_type == "image":
        mission_commands += [
            (
                "SPELL THE WORDS THE FRAME MUST SHOW. Where the packet carries a "
                "Text Overlay, or the action names text the frame displays, write "
                "those words into your description inside quotation marks, spelled "
                "character for character, and name the brand in full every time "
                "you refer to the product or its logo. Naming a mark instead of "
                "spelling it - 'the brand logo lockup', 'the product name', 'the "
                "bottled water product' - leaves the renderer to copy the letters "
                "out of the reference image, and it misspells them."
            ),
            (
                "BRAND MARK PLACEMENT: a supplied logo occupies its own space in the "
                "frame - an overlay, a card, a plate, a wall, or clear ground beside "
                "the product. Do NOT print, emboss, engrave, etch, stitch or "
                "otherwise apply it to the product. A supplied logo is a separate "
                "brand asset and the marking it carries is frequently not the "
                "marking the product carries, so applying it invents branding the "
                "product reference does not show. The product wears exactly what "
                "its own reference image shows, no more and no less. Count the "
                "marks in that image and reproduce those: a wordmark, a product "
                "name or printed text on the reference must appear on the "
                "product, in the same place and proportion. If it carries an icon "
                "and no words, NO words appear on the product anywhere in the "
                "frame. If it carries no mark at all, the product surface stays "
                "bare. A branded product rendered blank is as wrong as an "
                "unbranded one covered in text."
            ),
            (
                "PRODUCT FIDELITY: a supplied product image is the authority on how "
                "that product looks. Refer to it by its brand and product name and "
                "let the reference carry its appearance. Naming it is required; "
                "describing it is not. Do "
                "NOT restate or elaborate its form, proportions, surface finish, "
                "engraving, embossing, pattern, texture or markings, and do NOT "
                "enrich them with adjectives such as ornate, intricate, filigreed, "
                "finely detailed or hand-tooled. Decoration the reference does not "
                "show must not appear, and branding it does show must not be "
                "dropped. The art direction governs the scene around "
                "the product - the surface it rests on, the light, the lens, the "
                "depth of field - never the product itself."
            ),
            (
                "THE FRAME IS A SCENE, NOT A CUTOUT. A reference image supplies the "
                "product's appearance, never the shot. The described environment is "
                "built around the product: its surfaces, depth, light sources and "
                "background all appear. NEVER place the product on a plain white, "
                "grey or empty studio sweep, and NEVER reproduce the framing or "
                "backdrop of the reference photograph. A frame that could be "
                "mistaken for the supplied product shot is wrong, and cutting from "
                "it into a dressed scene reads as a jump cut."
            ),
        ]

    if context:
        mission_commands.append(
            "You MUST prioritize the [CREATIVE BRIEF] for the overarching visual tone and brand mood."
        )

    mission_commands.append(
        "You MUST prioritize the [TECHNICAL SPECIFICATIONS] for camera movement and lighting details."
    )

    if "**STARTING IMAGE DESCRIPTION" in context:
        mission_commands.append(
            "You MUST strictly honor the [VISUAL ANCHOR] state to ensure seamless continuity."
        )

    prompt_packet.append(f"### [FINAL MISSION]\n" + "\n".join(mission_commands))

    final_prompt = "\n\n".join(prompt_packet)

    try:
        enriched_text = await mediagen_service.generate_text(
            workspace_id=workspace_id,
            prompt=final_prompt,
            purpose=f"enriched_{prompt_type}_scene_{scene_index}",
        )
        return common_utils.tidy_spacing(enriched_text), None

    except Exception as e:
        logger.warning(f"Prompt enrichment failed ({e}). Falling back to raw formula.")
        return raw_input.replace("|", "."), None


async def shorten_script(text: str, target_duration: float, workspace_id: str) -> str:
    """Uses an LLM to shorten a script to a target duration."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    prompt = (
        "You are a professional script editor. Your task is to shorten the following"
        f" text to fit within a {target_duration:.1f} second time limit, while"
        " preserving the original meaning and tone. Respond only with the revised,"
        f" shortened script.\n\nORIGINAL SCRIPT:\n{text}"
    )
    try:
        shortened_text = await mediagen_service.generate_text(
            purpose="script_shorten",
            workspace_id=workspace_id,
            prompt=prompt,
        )
        shortened_text = shortened_text.strip()
        logger.info(
            f"Successfully shortened script from '{text}' to '{shortened_text}'"
        )
        return shortened_text
    except Exception as e:
        logger.error(f"Failed to shorten script: {e}")
        return text  # Return original text on failure
