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

"""Tools for modular production (Phi_prod) with Joint Keyframe Refinement."""

import asyncio
import dataclasses
import json
import logging
import re
from typing import Any

from google.adk.tools.tool_context import ToolContext

import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset
from utils.adk import get_user_id_from_context

from ..instructions.verifier import keyframe_verifier_instruction
from ..mab import utils as mab_utils
from ..utils import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Load refinement config
_mab_config = mab_utils.get_mab_config()
_refine_config = _mab_config.get("self_refinement", {}).get("keyframe", {})
MAX_REFINEMENT_ATTEMPTS = _refine_config.get("max_attempts", 1)
KEYFRAME_PASS_THRESHOLD = _refine_config.get("score_threshold", 85)


async def _generate_single_keyframe(
    user_id: str,
    scene: dict[str, Any],
    index: int,
    aspect_ratio: str,
    iteration_num: int,
    refinement_cycle: int,
    creative_direction: dict[str, str],
    annotated_visuals: dict[str, Any],
) -> Asset:
    """Internal helper to generate one image asset."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    # Propagate creative direction
    style_instr = creative_direction.get("keyframe_instruction", "")
    base_prompt = scene["first_frame_prompt"]["description"]
    full_prompt = f"{base_prompt}\n\nVisual Style: {style_instr}"

    # Use ONLY scene-specific assets from the storyboard
    all_references = scene["first_frame_prompt"].get("assets", [])

    # CRITICAL LAW: The logo image MUST NOT be blended in with the product reference visual.
    # Filter out any assets that are identified as 'logo' from the references list.
    cleaned_references = []
    for ref in all_references:
        if not ref:
            continue
        fname = ref.replace("asset://", "")
        if annotated_visuals.get(fname, {}).get("semantic_role") == "logo":
            logger.info(
                f"Filtering out logo asset '{fname}' from keyframe generation references."
            )
            continue
        cleaned_references.append(fname)

    # Gather reference descriptions to achieve "Consensus Prompting" (Text + Image sync)
    reference_descriptions = []
    for fname in cleaned_references:
        if meta := annotated_visuals.get(fname):
            desc = meta.get("caption") if isinstance(meta, dict) else str(meta)
            if desc:
                reference_descriptions.append(f"- {fname}: {desc}")

    if reference_descriptions:
        ref_context = "\n".join(reference_descriptions)
        full_prompt += f"\n\n### MANDATORY REFERENCE DETAILS (ABSOLUTE 100% FIDELITY REQUIRED):\n{ref_context}"
        full_prompt += (
            "\n\nSTRICT FIDELITY MANDATE: This is a high-precision visual replication task. "
            "You MUST maintain 1:1 visual parity with the SUBJECT of the provided reference images. "
            "DO NOT modernize, simplify, or creatively re-interpret the subject's design, "
            "textures, or branding. "
            "HOWEVER, you MUST COMPLETELY IGNORE the background of the reference images and "
            "instead place the subject into the environment described in the scene prompt above. "
            "The generated subject MUST be indistinguishable from the reference visuals in terms "
            "of structural identity and detail."
        )

    logger.info(
        f"Generating keyframe for scene {index} (Cycle {refinement_cycle}) with {len(cleaned_references)} refs using gemini-3.1-flash..."
    )
    asset = await mediagen_service.generate_image_with_gemini(
        user_id=user_id,
        file_name=f"iter_{iteration_num}_scene_{index}_cycle_{refinement_cycle}.png",
        model="gemini-3.1-flash-image-preview",
        prompt=full_prompt,
        reference_image_filenames=cleaned_references,
        aspect_ratio=aspect_ratio,
    )
    return asset


async def _verify_keyframes_jointly(
    user_id: str,
    storyboard: dict[str, Any],
    keyframe_assets: list[Asset],
    iteration_num: int,
    refinement_cycle: int,
) -> dict[str, Any]:
    """MLLM-based joint verification of the entire keyframe sequence."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    # The first image is the product reference (if any), then the sequence
    # For simplicity, we just pass all generated frames.
    image_filenames = [a.file_name for a in keyframe_assets]

    logger.info(f"Jointly verifying {len(image_filenames)} keyframes...")

    response_asset = await mediagen_service.generate_text_with_gemini(
        user_id=user_id,
        prompt=keyframe_verifier_instruction.INSTRUCTION,
        file_name=f"iter_{iteration_num}_joint_verification_cycle_{refinement_cycle}.txt",
        reference_image_filenames=image_filenames,
    )

    blob = await asset_service.get_asset_blob(response_asset.id)
    raw_text = blob.content.decode()

    try:
        start_index = raw_text.find("{")
        end_index = raw_text.rfind("}") + 1
        return json.loads(raw_text[start_index:end_index])
    except Exception as e:
        logger.error(f"Failed to parse joint verification JSON: {e}. Raw: {raw_text}")
        return {
            "score": 0,
            "feedback": "Parsing error",
            "actionable_feedback": "Retry.",
        }


async def produce_refined_keyframes(tool_context: ToolContext) -> ToolResult:
    """Phi_frame Station: Generates and self-refines keyframes as a sequence."""
    state = tool_context.state
    if (storyboard := state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure("Missing storyboard.")

    user_id = get_user_id_from_context(tool_context)
    iteration_num = state.get("mab_iteration", 0)
    params = state.get(common_utils.PARAMETERS_KEY, {})
    orientation = params.get("target_orientation", "landscape")
    aspect_ratio = "9:16" if orientation == "portrait" else "16:9"

    creative_direction = state.get(common_utils.CREATIVE_DIRECTION_KEY, {})

    # Identify global reference mapping for logo-filtering
    annotated_visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})

    num_scenes = len(storyboard["scenes"])

    # Initialize "Champion" tracking for Best-of-N selection
    champion_score = -1
    champion_assets: list[Asset | None] = [None] * num_scenes
    champion_verification: dict[str, Any] = {}

    # Working set that evolves over cycles
    current_working_assets: list[Asset | None] = [None] * num_scenes

    # In Cycle 0, we must generate EVERYTHING.
    scenes_to_generate = list(range(num_scenes))

    for cycle in range(MAX_REFINEMENT_ATTEMPTS):
        logger.info(
            f"--- Keyframe Refinement Cycle {cycle + 1}/{MAX_REFINEMENT_ATTEMPTS} ---"
        )
        logger.info(f"Regenerating scenes: {scenes_to_generate}")

        # 1. Selective Parallel Generation
        tasks = [
            _generate_single_keyframe(
                user_id,
                storyboard["scenes"][i],
                i,
                aspect_ratio,
                iteration_num,
                cycle,
                creative_direction,
                annotated_visuals,
            )
            for i in scenes_to_generate
        ]

        # Capture generated assets and update our current working set
        newly_generated_assets = await asyncio.gather(*tasks)
        from utils.adk import display_asset

        for i, new_asset in zip(
            scenes_to_generate, newly_generated_assets, strict=False
        ):
            current_working_assets[i] = new_asset
            await display_asset(tool_context=tool_context, asset_id=new_asset.id)

        # 2. Joint Verification (Always on the full working set)
        verification = await _verify_keyframes_jointly(
            user_id, storyboard, current_working_assets, iteration_num, cycle
        )
        score = verification.get("score", 0)
        logger.info(f"Joint Score: {score}/100")

        # 3. Champion Update (Best-of-N check)
        is_new_champion = score > champion_score
        if is_new_champion:
            logger.info(
                f"🏆 New Champion Sequence found! Score improved: {champion_score} -> {score}"
            )
            champion_score = score
            champion_assets = list(current_working_assets)
            champion_verification = verification
        else:
            logger.warning(
                f"⚠️ Regression or Stagnation. Current score {score} <= Champion score {champion_score}. Keeping Champion."
            )

        # 4. Store history PER SCENE (matching reference implementation structure)
        for i, scene in enumerate(storyboard["scenes"]):
            if "first_frame_generation_history" not in scene:
                scene["first_frame_generation_history"] = []

            # Optimization: Only store essential asset info to avoid state bloat
            asset_data = dataclasses.asdict(current_working_assets[i])
            asset_data["versions"] = []  # Strip deep history
            if "image_generate_config" in asset_data:
                asset_data["image_generate_config"] = None
            if "video_generate_config" in asset_data:
                asset_data["video_generate_config"] = None

            # Record the state of this scene in this cycle
            scene["first_frame_generation_history"].append(
                {
                    "cycle": cycle,
                    "regenerated": i in scenes_to_generate,
                    "asset": asset_data,
                    "is_champion": is_new_champion,
                    "joint_verification": {
                        "score": score,
                        "feedback": verification.get("feedback"),
                        "actionable_feedback": verification.get("actionable_feedback"),
                        "primary_fault": verification.get("primary_fault"),
                    },
                }
            )

        if score >= KEYFRAME_PASS_THRESHOLD:
            logger.info("Keyframe sequence passed joint verification.")
            break

        # 5. Determine next batch from verifier feedback
        # Even if we didn't pick this as the champion, we still follow the verifier's
        # feedback to try and improve the *current* working set.
        scenes_to_generate = verification.get("problematic_scenes", [])
        if not scenes_to_generate:
            logger.info("No problematic scenes flagged, stopping refinement.")
            break

        logger.warning(
            f"Refinement needed for scenes {scenes_to_generate}: {verification.get('actionable_feedback')}"
        )

    # FINAL STEP: Assign the Champion assets to the storyboard
    logger.info(
        f"🏁 Refinement concluded. Using Champion Sequence with score: {champion_score}"
    )
    for i, (scene, asset) in enumerate(zip(storyboard["scenes"], champion_assets)):
        if asset:
            scene["first_frame_prompt"]["asset_id"] = asset.id
        else:
            logger.error(f"Missing champion asset for Scene {i}")

    state[common_utils.STORYBOARD_KEY] = storyboard
    return tool_success(
        f"Keyframes produced and refined over {cycle + 1} cycles. Final Score: {champion_score}"
    )


async def generate_production_videos(tool_context: ToolContext) -> ToolResult:
    """Phi_video Station: Transforms refined keyframes into motion clips."""
    state = tool_context.state
    if (storyboard := state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure("Missing storyboard.")

    user_id = get_user_id_from_context(tool_context)
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()
    iteration_num = state.get("mab_iteration", 0)

    params = state.get(common_utils.PARAMETERS_KEY, {})
    orientation = params.get("target_orientation", "landscape")
    aspect_ratio = "9:16" if orientation == "portrait" else "16:9"

    creative_direction = state.get(common_utils.CREATIVE_DIRECTION_KEY, {})
    video_instr = creative_direction.get("video_instruction", "")

    logo_mode = _mab_config.get("logo_scene_mode", "default")

    # Use CLASSIFICATION result (semantic_role) to find the logo and product
    annotated_visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})
    logo_filename = next(
        (
            fname
            for fname, meta in annotated_visuals.items()
            if isinstance(meta, dict) and meta.get("semantic_role") == "logo"
        ),
        None,
    )
    product_filename = next(
        (
            fname
            for fname, meta in annotated_visuals.items()
            if isinstance(meta, dict) and meta.get("semantic_role") == "product"
        ),
        None,
    )

    def _is_safety_error(e: Exception) -> bool:
        err_str = str(e).lower()
        return any(
            k in err_str
            for k in [
                "safety",
                "recitation",
                "usage guidelines",
                "could not be submitted",
                "no video was generated",
                "violate",
                "policy",
            ]
        )

    async def _get_softened_prompt(idx, original_prompt):
        """Helper to invoke Gemini for prompt softening."""
        softener_instruction = (
            "You are an expert prompt engineer. The following video generation prompt failed a safety/policy check. "
            "Analyze the prompt and identify elements that may be perceived as sensitive, restricted, or proprietary "
            "(including protected categories, specific public identities, or sensitive demographics). "
            "Rewrite the prompt to be **policy-neutral** while preserving 100% of the cinematic action, lighting, and narrative intent. "
            "Use generic but visually equivalent descriptors. Output ONLY the revised prompt text."
        )

        softened_resp = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            file_name=f"iter_{iteration_num}_scene_{idx}_softened_prompt.txt",
            prompt=f"{softener_instruction}\n\nORIGINAL PROMPT:\n{original_prompt}",
            purpose="repair",
        )

        blob = await asset_service.get_asset_blob(softened_resp.id)
        softened_prompt = blob.content.decode("utf-8").strip()
        logger.info(
            f"Generated neutralized prompt for Scene {idx}: {softened_prompt[:100]}..."
        )
        return softened_prompt

    async def _gen_vid(idx, scn):
        frame_asset = await asset_service.get_asset_by_id(
            scn["first_frame_prompt"]["asset_id"]
        )

        base_prompt = scn["video_prompt"]["description"]

        # ROBUSTNESS pass: Scrub any literal asset filenames that might have leaked into the description
        scrubbed_prompt = re.sub(
            r"\b[\w-]+\.(?:png|jpg|jpeg|mp4|mp3)\b", "", base_prompt
        )
        scrubbed_prompt = re.sub(
            r"\biter_\d+_\w+\.(?:png|jpg|jpeg|mp4|mp3)\b", "", scrubbed_prompt
        )
        scrubbed_prompt = scrubbed_prompt.replace("  ", " ").strip()

        full_prompt = f"{scrubbed_prompt}\n\nMotion Guidance: {video_instr}"

        is_last_scene = idx == len(storyboard["scenes"]) - 1

        try:
            if logo_mode == "r2v" and is_last_scene and logo_filename:
                # 1. Primary Attempt: High-fidelity R2V
                r2v_references = [frame_asset.file_name]
                if logo_filename:
                    r2v_references.append(logo_filename)
                if product_filename:
                    r2v_references.append(product_filename)

                r2v_references = r2v_references[:3]
                r2v_constraint = (
                    "\n\n**CRITICAL R2V CONSISTENCY:**\n"
                    f"- Maintain absolute visual identity from the {len(r2v_references)} reference images.\n"
                    "- Do NOT introduce any new visual entities or characters not already present in these references.\n"
                    "- Ensure the sequence concludes with a clear reveal of the logo."
                )

                try:
                    video_asset = await mediagen_service.generate_video_with_veo(
                        user_id=user_id,
                        file_name=f"iter_{iteration_num}_scene_{idx}_video.mp4",
                        prompt=full_prompt + r2v_constraint,
                        duration_seconds=8,
                        aspect_ratio=aspect_ratio,
                        generate_audio=False,
                        reference_image_filenames=r2v_references,
                        method="reference_to_video",
                    )
                except Exception as r2v_err:
                    if not _is_safety_error(r2v_err):
                        raise r2v_err

                    logger.warning(
                        f"Scene {idx} R2V failed (safety/guidelines). Attempting Neutralized I2V Fallback (6s Video + 2s Hold)..."
                    )

                    # --- STAGE 2: Neutralized Extrapolation + Hold ---
                    neutralized_prompt = await _get_softened_prompt(idx, full_prompt)

                    i2v_extrap_constraint = (
                        "\n\n**CRITICAL CONSISTENCY CONSTRAINT:**\n"
                        "- This MUST be one contiguous shot starting from the provided first frame.\n"
                        "- DO NOT introduce any new characters, products, or objects."
                    )

                    video_asset = await mediagen_service.generate_video_with_veo(
                        user_id=user_id,
                        file_name=f"iter_{iteration_num}_scene_{idx}_video.mp4",
                        prompt=neutralized_prompt + i2v_extrap_constraint,
                        duration_seconds=6,  # 6s Video + 2s Hold
                        aspect_ratio=aspect_ratio,
                        generate_audio=False,
                        first_frame_filename=frame_asset.file_name,
                        method="image_to_video",
                    )

                    # Signal the stitcher to add a 2-second logo hold
                    logo_asset = await asset_service.get_asset_by_file_name(
                        user_id=user_id, file_name=logo_filename
                    )
                    if logo_asset:
                        scn["last_frame_hold_asset_id"] = logo_asset.id
                        scn["last_frame_hold_duration"] = 2.0
                        scn["video_prompt"]["duration_seconds"] = 6
                    else:
                        logger.error(
                            f"Could not find asset ID for logo '{logo_filename}' for static hold."
                        )

                # Update metadata to reflect actual generated length
                if "last_frame_hold_asset_id" not in scn:
                    scn["video_prompt"]["duration_seconds"] = 8
            else:
                # Default I2V (Extrapolation) mode for non-logo scenes
                i2v_constraint = (
                    "\n\n**CRITICAL CONSISTENCY CONSTRAINT:**\n"
                    "- This MUST be one contiguous shot starting from the provided first frame.\n"
                    "- DO NOT add new shots, cuts, transitions, or scene changes.\n"
                    "- DO NOT introduce any new characters, products, or objects.\n"
                    "- MAINTAIN absolute visual identity of the character and product from the first frame."
                )

                try:
                    video_asset = await mediagen_service.generate_video_with_veo(
                        user_id=user_id,
                        file_name=f"iter_{iteration_num}_scene_{idx}_video.mp4",
                        prompt=full_prompt + i2v_constraint,
                        duration_seconds=int(scn["video_prompt"]["duration_seconds"]),
                        aspect_ratio=aspect_ratio,
                        generate_audio=False,
                        first_frame_filename=frame_asset.file_name,
                        method="image_to_video",
                    )
                except Exception as i2v_err:
                    if not _is_safety_error(i2v_err):
                        raise i2v_err

                    logger.warning(
                        f"Scene {idx} I2V failed (safety/guidelines). Attempting Neutralized Retry..."
                    )
                    neutralized_prompt = await _get_softened_prompt(idx, full_prompt)

                    video_asset = await mediagen_service.generate_video_with_veo(
                        user_id=user_id,
                        file_name=f"iter_{iteration_num}_scene_{idx}_video.mp4",
                        prompt=neutralized_prompt + i2v_constraint,
                        duration_seconds=int(scn["video_prompt"]["duration_seconds"]),
                        aspect_ratio=aspect_ratio,
                        generate_audio=False,
                        first_frame_filename=frame_asset.file_name,
                        method="image_to_video",
                    )

        except Exception as e:
            logger.error(f"Scene {idx} video generation permanently failed: {e}")
            video_asset = None

        if video_asset:
            scn["video_prompt"]["asset_id"] = video_asset.id
            from utils.adk import display_asset

            await display_asset(tool_context=tool_context, asset_id=video_asset.id)
        else:
            scn["video_prompt"]["asset_id"] = None

    tasks = [_gen_vid(i, s) for i, s in enumerate(storyboard["scenes"])]
    await asyncio.gather(*tasks)

    state[common_utils.STORYBOARD_KEY] = storyboard
    return tool_success(
        "Scene video generation attempted. Check logs for any individual scene failures."
    )


async def _generate_global_voiceover(
    user_id: str,
    storyboard: dict[str, Any],
    iteration_num: int,
    creative_direction: dict[str, str],
):
    """Generates the unified global voiceover for the entire campaign."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    vo_prompt = storyboard.get("voiceover_prompt", {})
    text = vo_prompt.get("text", "")
    if not text:
        logger.warning("No global voiceover text found. Skipping.")
        vo_prompt["asset_id"] = None
        return

    voice_name = "Enceladus" if vo_prompt.get("gender") == "male" else "Aoede"
    audio_instr = creative_direction.get("audio_instruction", "")

    history = []

    try:
        logger.info(f"Generating global voiceover: '{text[:50]}...'")
        # STRICTURE: Force English output at the TTS model level
        vo_asset = await mediagen_service.generate_speech_single_speaker(
            user_id=user_id,
            file_name=f"iter_{iteration_num}_global_voiceover.mp3",
            text=text,
            voice_name=voice_name,
            prompt=f"{vo_prompt.get('description', '')}\n\nStyle: {audio_instr}",
        )
        vo_prompt["asset_id"] = vo_asset.id

        actual_duration = vo_asset.versions[-1].duration_seconds
        history.append(
            {
                "script": text,
                "asset": dataclasses.asdict(vo_asset),
                "duration": actual_duration,
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate global voiceover: {e}")
        vo_prompt["asset_id"] = None
        history.append({"error": str(e)})

    storyboard["voiceover_generation_history"] = history


async def _generate_background_music(
    user_id: str,
    storyboard: dict[str, Any],
    iteration_num: int,
    creative_direction: dict[str, str],
):
    """Generates the background music for the campaign."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    music_prompt = storyboard.get("background_music_prompt", {})
    prompt_text = music_prompt.get("description", "")
    if not prompt_text:
        logger.warning("No background music description found. Skipping.")
        music_prompt["asset_id"] = None
        return

    audio_instr = creative_direction.get("audio_instruction", "")
    full_music_prompt = f"{prompt_text}\n\nAesthetic: {audio_instr}"

    history = []
    try:
        logger.info(f"Generating background music: '{prompt_text[:50]}...'")
        music_asset = await mediagen_service.generate_music_with_lyria(
            user_id=user_id,
            file_name=f"iter_{iteration_num}_background_music.mp3",
            prompt=full_music_prompt,
        )
        music_prompt["asset_id"] = music_asset.id
        history.append(
            {"prompt": prompt_text, "asset": dataclasses.asdict(music_asset)}
        )
    except Exception as e:
        logger.error(f"Failed to generate background music: {e}")
        music_prompt["asset_id"] = None
        history.append({"error": str(e)})

    storyboard["background_music_generation_history"] = history


async def generate_production_audio(tool_context: ToolContext) -> ToolResult:
    """Phi_audio Station: Generates global VO and Background Music."""
    state = tool_context.state
    storyboard = state.get(common_utils.STORYBOARD_KEY)
    user_id = get_user_id_from_context(tool_context)
    iteration_num = state.get("mab_iteration", 0)

    creative_direction = state.get(common_utils.CREATIVE_DIRECTION_KEY, {})

    await asyncio.gather(
        _generate_global_voiceover(
            user_id, storyboard, iteration_num, creative_direction
        ),
        _generate_background_music(
            user_id, storyboard, iteration_num, creative_direction
        ),
    )

    # UI Sync Trigger
    from utils.adk import display_asset

    vo_id = storyboard.get("voiceover_prompt", {}).get("asset_id")
    if vo_id:
        await display_asset(tool_context=tool_context, asset_id=vo_id)

    bgm_id = storyboard.get("background_music_prompt", {}).get("asset_id")
    if bgm_id:
        await display_asset(tool_context=tool_context, asset_id=bgm_id)

    state[common_utils.STORYBOARD_KEY] = storyboard
    return tool_success("Global audio track generated.")
