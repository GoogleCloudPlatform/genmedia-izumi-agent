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

"""Tools for verifying and correcting the generated storyboard."""

import json
import logging

from google.adk.tools import ToolContext

import mediagent_kit.services.aio
from utils.adk import get_user_id_from_context

from ..instructions.verifier import storyboard_asset_relevance_verifier
from ..mab import utils as mab_utils
from ..utils import common_utils, storyboard_asset_relevance_verifier_model

logger = logging.getLogger(__name__)


async def verify_storyboard_assets(tool_context: ToolContext) -> dict:
    """
    Global Narrative Asset Supervisor: Performs a single-pass verification
    of the entire storyboard against the narrative intent (storyline).
    """
    state = tool_context.state
    storyboard = state.get(common_utils.STORYBOARD_KEY)
    storyline = state.get(common_utils.STORYLINE_KEY)
    annotated_visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})
    user_id = get_user_id_from_context(tool_context)
    iteration_num = state.get("mab_iteration", 0)

    if not storyboard or not storyline:
        logger.warning(
            "Verification skipped: missing storyboard or storyline in state."
        )
        return {"status": "succeeded", "result": "Verification skipped: missing data."}

    # 1. Prepare Context Data for LLM
    sl_data = []
    if isinstance(storyline, dict) and "scenes" in storyline:
        sl_data = [
            {"index": i, "topic": s.get("topic"), "action": s.get("action")}
            for i, s in enumerate(storyline["scenes"])
        ]
    else:
        sl_data = str(storyline)

    sb_data = []
    for i, scene in enumerate(storyboard.get("scenes", [])):
        sb_data.append(
            {
                "index": i,
                "topic": scene.get("topic"),
                "first_frame_description": scene.get("first_frame_prompt", {}).get(
                    "description"
                ),
                "video_description": scene.get("video_prompt", {}).get("description"),
                "current_assets": scene.get("first_frame_prompt", {}).get("assets", []),
            }
        )

    available_assets = {
        fname: meta.get("semantic_role", "unknown")
        for fname, meta in annotated_visuals.items()
    }

    # 2. Build Prompt
    prompt = storyboard_asset_relevance_verifier.INSTRUCTION.format(
        storyline=json.dumps(sl_data, indent=2),
        storyboard=json.dumps(sb_data, indent=2),
        available_assets=json.dumps(available_assets, indent=2),
        json_output_schema=storyboard_asset_relevance_verifier_model.DESCRIPTION,
    )

    header = "--- GLOBAL ASSET VERIFICATION PROMPT ---"
    logger.info(f"\n{'='*len(header)}\n{header}\n{prompt.strip()}\n{'='*len(header)}\n")

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    try:
        # 3. Single-pass LLM Call
        response_asset = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            prompt=prompt,
            file_name=f"iter_{iteration_num}_global_asset_verification.txt",
        )
        blob = await asset_service.get_asset_blob(response_asset.id)
        raw_text = blob.content.decode()

        # 4. Parse JSON results
        verification_results = await common_utils.parse_json_from_text(
            raw_text, user_id=user_id
        )
        corrections = verification_results.get("corrections", [])

        # 5. Apply Corrections to Storyboard
        valid_filenames = set(annotated_visuals.keys())

        for correction in corrections:
            idx = correction.get("scene_index")
            if idx is None or idx >= len(storyboard["scenes"]):
                continue

            scene = storyboard["scenes"][idx]
            ff_prompt = scene.get("first_frame_prompt", {})
            v_prompt = scene.get("video_prompt", {})

            # Assets to scrub (Invalid or Inappropriate)
            invalid = set(correction.get("invalid_filenames", []))
            to_remove = set(correction.get("assets_to_remove", []))
            scrub_set = invalid.union(to_remove)

            for p in [ff_prompt, v_prompt]:
                current_assets = p.get("assets", [])
                p["assets"] = [
                    a
                    for a in current_assets
                    if a.removeprefix("asset://") not in scrub_set
                    and a.removeprefix("asset://") in valid_filenames
                ]

            # B. Add Missing Assets (PRODUCT or CHARACTER)
            missing = correction.get("missing_assets", [])
            for asset_name in missing:
                if asset_name in valid_filenames:
                    for p in [ff_prompt, v_prompt]:
                        if asset_name not in p.get(
                            "assets", []
                        ) and f"asset://{asset_name}" not in p.get("assets", []):
                            p.setdefault("assets", []).append(asset_name)

        # 6. MANDATORY R2V ASSET SYNC (Safeguard)
        # For the final scene in R2V mode, we MUST have Logo and Product for the transition.
        config = mab_utils.get_mab_config()
        if config.get("logo_scene_mode") == "r2v":
            last_scene = storyboard["scenes"][-1]
            for p in [
                last_scene.get("first_frame_prompt", {}),
                last_scene.get("video_prompt", {}),
            ]:
                for fname, meta in annotated_visuals.items():
                    # Force both Logo and Product
                    if meta.get("semantic_role") in ["logo", "product"]:
                        if fname not in p.get(
                            "assets", []
                        ) and f"asset://{fname}" not in p.get("assets", []):
                            logger.info(
                                f"Forcing R2V dependency '{fname}' ({meta.get('semantic_role')}) into final scene."
                            )
                            p.setdefault("assets", []).append(fname)

        state[common_utils.STORYBOARD_KEY] = storyboard
        return {
            "status": "succeeded",
            "result": f"Global narrative asset verification complete. {len(corrections)} scenes processed.",
        }

    except Exception as e:
        logger.error(f"Global verifier failed: {e}")
        return {"status": "failed", "error_message": str(e)}
