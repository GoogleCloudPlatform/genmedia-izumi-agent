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

"""Utilities for generating media assets for scene components."""

import asyncio
import logging
from typing import Any, Tuple, Optional, List

import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset
from mediagent_kit.services.types.common import AssetRef
from mediagent_kit.utils.retry import ContentBlockedError

from ...instructions.generation import generation_prompts
from . import enrichment_utils
from . import frame_validation

logger = logging.getLogger(__name__)

# Basic semaphore to avoid overloading Veo
VEO_QUOTA_SEMAPHORE = asyncio.Semaphore(5)

# Attempts allowed for one scene's first frame. The frame anchors the whole
# clip, so a faulted one is worth regenerating, but each attempt costs an image
# call and an inspection.
MAX_FIRST_FRAME_ATTEMPTS = 2


async def generate_scene_first_frame(
    first_frame_prompt: dict[str, Any],
    index: int,
    aspect_ratio: str,
    workspace_id: str,
    voiceover_text: str = "",
    on_screen_text_hint: str = "",
    uid: str = "",
    is_ugc: bool = False,
    context: str = "",
    asset_refs: Optional[dict[str, Any]] = None,
) -> Tuple[Asset, str]:
    """Generates the first frame for one scene. Returns (Asset, final_prompt_text)."""
    logger.info(
        f"Generating first frame for scene {index} (UGC: {is_ugc}, Workspace: {workspace_id})"
    )
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    original_prompt_desc = first_frame_prompt.get("description", "")
    reference_asset_names = [
        asset.removeprefix("asset://") for asset in first_frame_prompt.get("assets", [])
    ]

    enrichment_data = first_frame_prompt.copy()
    if on_screen_text_hint:
        enrichment_data["on_screen_text_hint"] = on_screen_text_hint

    # --- ENRICHMENT STEP ---
    current_prompt_desc, enrichment_asset_id = (
        await enrichment_utils.enrich_prompt_with_llm(
            workspace_id,
            original_prompt_desc,
            enrichment_data,
            scene_index=index,
            prompt_type="image",
            context=context,
            is_ugc=is_ugc,
            reference_image_filenames=reference_asset_names,
        )
    )
    if enrichment_asset_id:
        first_frame_prompt["enrichment_asset_id"] = enrichment_asset_id

    filename = (
        f"scene_{index}_first_frame_{uid}.png"
        if uid
        else f"scene_{index}_first_frame.png"
    )

    try:

        # Resolve reference asset names/IDs to AssetRef objects
        reference_asset_refs: list[AssetRef] = []
        refs_by_name: dict[str, AssetRef] = {}
        if reference_asset_names:
            asset_refs = asset_refs or {}

            refs_by_name: dict[str, AssetRef] = {}
            for ref_name in reference_asset_names:
                if ref_name in asset_refs:
                    ref_dict = asset_refs[ref_name]
                    ref = AssetRef(
                        id=ref_dict["id"],
                        asset_type=ref_dict["asset_type"],
                        workspace_id=ref_dict.get("workspace_id", workspace_id),
                    )
                    reference_asset_refs.append(ref)
                    refs_by_name[ref_name] = ref
                else:
                    logger.warning(
                        f"Could not resolve reference asset '{ref_name}' from session state mappings."
                    )

        # Each frame is inspected against the references it was built from, and
        # a faulted frame is regenerated against that specific fault.
        product_ref, logo_ref = frame_validation.product_and_logo_references(
            reference_asset_names
        )
        attempt_prompt = current_prompt_desc
        generated_asset = None

        for attempt in range(MAX_FIRST_FRAME_ATTEMPTS):
            attempt_name = (
                filename
                if attempt == 0
                else filename.replace(".png", f"_r{attempt}.png")
            )
            try:
                # NOTE: Unified MediaGenerationServiceInterface adaptation.
                # This would break legacy version due to function signature and method name mismatch.
                generated_asset = await mediagen_service.generate_image(
                    workspace_id=workspace_id,
                    prompt=attempt_prompt,
                    generation_model="gemini-3.1-flash-image",
                    aspect_ratio=aspect_ratio,
                    resolution="1K",
                    file_name=attempt_name,
                    reference_assets=(
                        reference_asset_refs if reference_asset_refs else None
                    ),
                )
            except ContentBlockedError as e:
                if generated_asset is not None:
                    logger.warning(
                        f"Scene {index} regeneration was refused ({e}). Keeping "
                        "the previous frame."
                    )
                    break
                if attempt_prompt == original_prompt_desc:
                    raise
                # The refusal depends on the wording, and enrichment is what
                # adds the elaborate language, so the retry falls back to the
                # plain storyboard description rather than losing the scene.
                logger.warning(
                    f"Scene {index} first frame refused on policy grounds ({e}). "
                    "Retrying with the un-enriched description."
                )
                attempt_prompt = original_prompt_desc
                continue
            except Exception as e:
                # A first attempt that fails leaves the scene with nothing and
                # the error propagates. A regeneration that fails still has the
                # faulted frame from the attempt before, which beats no frame.
                if generated_asset is None:
                    raise
                logger.warning(
                    f"Scene {index} regeneration failed ({e}). Keeping the "
                    "previous frame."
                )
                break

            # The last attempt is kept whatever the inspection would say, so a
            # scene is never left without a frame.
            if not product_ref or attempt == MAX_FIRST_FRAME_ATTEMPTS - 1:
                break

            product_asset = refs_by_name.get(product_ref or "")
            if product_asset is None:
                break
            faults = await frame_validation.inspect_first_frame(
                workspace_id,
                frame=AssetRef(
                    id=generated_asset.id,
                    asset_type="generated",
                    workspace_id=workspace_id,
                ),
                product=product_asset,
                logo=refs_by_name.get(logo_ref or ""),
                others=[
                    ref
                    for name, ref in refs_by_name.items()
                    if name not in (product_ref, logo_ref)
                ],
                scene_index=index,
            )
            if not faults:
                break

            logger.warning(
                f"Scene {index} first frame rejected on attempt {attempt + 1}: "
                f"{' '.join(faults)}"
            )
            attempt_prompt = current_prompt_desc + frame_validation.corrective_note(
                faults
            )

        if generated_asset is None:
            raise ValueError(f"No first frame was produced for scene {index}")

        first_frame_prompt["asset_id"] = generated_asset.id
        first_frame_prompt["asset_ref"] = {
            "id": generated_asset.id,
            "asset_type": "generated",
            "workspace_id": workspace_id,
        }
        first_frame_prompt["description"] = current_prompt_desc
        return generated_asset, current_prompt_desc

    except Exception as e:
        logger.error(f"Failed to generate valid first frame for scene {index}: {e}")
        raise Exception(f"Failed to generate valid first frame for scene {index}: {e}")


async def generate_scene_video(
    workspace_id: str,
    scene: dict[str, Any],
    index: int,
    valid_duration: float,
    aspect_ratio: str,
    allow_veo_audio: bool,
    veo_method: str,
    first_frame_asset: Asset,
    final_video_prompt: str,
    uid: str = "",
) -> Asset:
    """Generates the video for one scene."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    voiceover_text = scene.get("voiceover", {}).get("text", "")

    # Conditional Audio Generation for Veo
    should_generate_audio = False
    if allow_veo_audio:
        should_generate_audio = bool(
            voiceover_text or scene.get("audio_hints", {}).get("dialogue_hint")
        )

    # Gather references for reference_to_video mode
    refs = scene["first_frame_prompt"].get("assets", []).copy()
    if veo_method == "reference_to_video":
        if first_frame_asset.file_name not in refs:
            refs = [first_frame_asset.file_name] + refs
        refs = refs[:3]

    filename = f"scene_{index}_video_{uid}.mp4" if uid else f"scene_{index}_video.mp4"

    async with VEO_QUOTA_SEMAPHORE:
        try:
            # NOTE: Unified MediaGenerationServiceInterface adaptation.
            # Image-to-Video mode is indicated declaratively by passing start_image AssetRef.
            # This would break legacy version due to function signature and method name mismatch.
            start_image_ref = (
                AssetRef(
                    id=str(first_frame_asset.id),
                    asset_type="generated",
                    workspace_id=workspace_id,
                )
                if first_frame_asset
                else None
            )

            video_asset = await mediagen_service.generate_video(
                workspace_id=workspace_id,
                prompt=final_video_prompt,
                aspect_ratio=aspect_ratio,
                duration_seconds=int(valid_duration),
                file_name=filename,
                start_image=start_image_ref,
            )
            if "video_prompt" in scene:
                scene["video_prompt"]["asset_id"] = video_asset.id
                scene["video_prompt"]["asset_ref"] = {
                    "id": video_asset.id,
                    "asset_type": "generated",
                    "workspace_id": workspace_id,
                }
            return video_asset
        except Exception as e:
            logger.error(f"Failed to generate valid video clip for scene {index}: {e}")
            raise Exception(
                f"Failed to generate valid video clip for scene {index}: {e}"
            )
