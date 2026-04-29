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

"""Tools for Multi-Armed Bandit selection."""

import asyncio
import datetime
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import yaml
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.adk.utils.context_utils import Aclosing
from google.genai import types as genai_types

import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset, Html

from ..mab.bandit import EpsilonGreedyBandit, UCBBandit
from ..utils import common_utils
from ..utils.common_utils import tool_failure, tool_success, ToolResult
from ..utils.mab_model import (
    ArmsSelected,
    MabExperimentState,
    MabIterationLog,
    MabWarmStart,
)

logger = logging.getLogger(__name__)

_MAB_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, o):
        if isinstance(o, datetime.datetime | datetime.date | datetime.time):
            return o.isoformat()
        return super().default(o)


def get_mab_config():
    """Loads the MAB configuration from the YAML file."""
    with open(_MAB_CONFIG_PATH) as f:
        return yaml.safe_load(f)


async def save_mab_state(mab_state: MabExperimentState, user_id: str) -> Asset:
    """Saves the MAB state to a JSON asset in the AssetService."""
    asset_service = mediagent_kit.services.aio.get_asset_service()
    json_bytes = mab_state.model_dump_json(indent=2).encode("utf-8")
    file_name = f"{mab_state.experiment_id}_mab_state.json"

    gcs_path_override = None
    if os.environ.get("BATCH_JOB_MODE") == "True":
        gcs_root = os.environ.get("ASSET_GCS_ROOT", "batch_job")
        # Save state JSON at the root of the task folder
        gcs_path_override = f"{gcs_root}/{user_id}/{file_name}"

    asset = await asset_service.save_asset(
        user_id=user_id,
        file_name=file_name,
        blob=json_bytes,
        mime_type="application/json",
        gcs_path_override=gcs_path_override,
    )
    return asset


async def load_mab_state(
    user_id: str, experiment_id: str
) -> tuple[MabExperimentState | None, Asset | None]:
    """Loads and parses the MAB state from an asset in AssetService."""
    asset_service = mediagent_kit.services.aio.get_asset_service()
    file_name = f"{experiment_id}_mab_state.json"
    try:
        asset = await asset_service.get_asset_by_file_name(
            user_id=user_id, file_name=file_name
        )
        if not asset:
            logger.warning(
                f"MAB state asset not found with filename: {file_name}. "
                "This might indicate an initialization issue or data loss."
            )
            return None, None

        blob = await asset_service.get_asset_blob(asset.id)
        mab_state = MabExperimentState.model_validate_json(blob.content)
        return mab_state, asset
    except Exception as e:
        logger.error(f"Failed to load MAB state from asset {file_name}: {e}")
        return None, None


def _initialize_bandit(config: dict[str, Any], mab_state: MabExperimentState):
    """Initializes and returns a bandit instance based on config and current MAB state."""
    mab_params = config.get("mab", {})
    arms = mab_params.get("arms", {})
    algorithm = mab_params.get("algorithm", "ucb").lower()
    algo_params = mab_params.get("algorithm_params", {})

    # Convert Pydantic model back to a dict for the bandit library
    mab_state_dict = mab_state.model_dump()

    # Extract recommendations from warm_start if present
    recommendations = {}
    if mab_state.warm_start and mab_state.warm_start.recommendations:
        recommendations = mab_state.warm_start.recommendations.model_dump()
        logger.info(f"[MAB Brain] Initializing with recommendations: {recommendations}")

    if algorithm == "ucb":
        params = algo_params.get("ucb", {})
        return UCBBandit(
            arms=arms,
            c=params.get("c", 2.0),
            arm_stats=mab_state_dict["arm_stats"],
            iterations=mab_state_dict["iterations"],
            recommendations=recommendations,
        )
    else:  # Default to epsilon_greedy
        params = algo_params.get("epsilon_greedy", {})
        return EpsilonGreedyBandit(
            arms=arms,
            epsilon=params.get("epsilon", 0.1),
            arm_stats=mab_state_dict["arm_stats"],
            iterations=mab_state_dict["iterations"],
            recommendations=recommendations,
        )


async def select_mab_arms(tool_context: ToolContext) -> dict[str, str]:
    """Selects the MAB arms and returns them as a dictionary."""
    config = get_mab_config()
    experiment_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
    if not experiment_id:
        raise ValueError("MAB experiment_id not found in tool context state.")

    user_id = common_utils.get_user_id(tool_context)
    mab_state, _ = await load_mab_state(user_id, experiment_id)
    if not mab_state:
        raise ValueError(
            f"MAB experiment state could not be loaded for experiment ID: {experiment_id}. "
            "This indicates a critical issue."
        )

    bandit = _initialize_bandit(config, mab_state)

    creative_strategy_choice = bandit.select_arm("creative_strategy")
    narrative_mode_choice = bandit.select_arm("narrative_mode")
    aesthetic_archetype_choice = bandit.select_arm("aesthetic_archetype")

    selected_arms_dict = {
        "creative_strategy": creative_strategy_choice,
        "narrative_mode": narrative_mode_choice,
        "aesthetic_archetype": aesthetic_archetype_choice,
    }

    tool_context.state[common_utils.ARMS_SELECTED_KEY] = selected_arms_dict
    return selected_arms_dict


def get_theoretical_definitions(tool_context: ToolContext) -> dict[str, str]:
    """Retrieves theoretical definitions for the selected arms."""
    from .arm_definitions import THEORY_MAP

    arms_selected = tool_context.state.get(common_utils.ARMS_SELECTED_KEY, {})
    definitions = {}

    for dimension, arm_value in arms_selected.items():
        # Handle potential capitalization differences or mapping needs
        key = arm_value.lower()
        if key in THEORY_MAP:
            definitions[dimension] = THEORY_MAP[key]
        else:
            definitions[dimension] = "No definition found."

    tool_context.state[common_utils.THEORETICAL_DEFS_KEY] = definitions
    return definitions


async def flatten_creative_direction(tool_context: ToolContext) -> ToolResult:
    """
    Spreads the nested instructions from the CreativeDirection object
    into top-level state keys for easier template resolution.
    """
    state = tool_context.state
    cd = state.get(common_utils.CREATIVE_DIRECTION_KEY)

    if not cd:
        return tool_failure("No creative direction found in state.")

    # Handle both dict and Pydantic model
    cd_dict = cd.model_dump() if hasattr(cd, "model_dump") else cd

    state[common_utils.CD_STORYLINE_KEY] = cd_dict.get("storyline_instruction", "")
    state[common_utils.CD_KEYFRAME_KEY] = cd_dict.get("keyframe_instruction", "")
    state[common_utils.CD_VIDEO_KEY] = cd_dict.get("video_instruction", "")
    state[common_utils.CD_AUDIO_KEY] = cd_dict.get("audio_instruction", "")

    return tool_success("Creative direction flattened into state.")


async def get_storyboard_instruction_with_mab(ctx) -> str:
    """
    Determines which visual storyboard instruction to use based on MAB choices.
    """
    from ..instructions.pre_production import storyboard_instruction

    config = get_mab_config()
    logo_mode = config.get("logo_scene_mode", "default")

    instruction = storyboard_instruction.INSTRUCTION

    if logo_mode == "r2v":
        instruction += """
**Reference-to-Video (R2V) Constraints for the FINAL Scene (HARD REQUIREMENT):**
- **Product & Character Heroism**: The primary product and character MUST remain the center of attention (the 'heroes') for the first 6-7 seconds of the final scene.
- **Duration**: The final scene of the video MUST be exactly **8 seconds** in duration to support R2V logo integration.
- **Assets**: You MUST include ALL filenames from the `Annotated Reference Visuals` in the `assets` list for this final scene. This includes the primary product(s), character(s), and the brand logo. DO NOT OMIT THE PRODUCT.
- **Video Prompt**: The `video_prompt` for this final scene MUST explicitly describe a transition or camera move that concludes with a clear, static, centered reveal of the logo against its original background.
- **Timing**: Explicitly state in the prompt that the final 1-2 seconds should be a still hold on the logo.
- **Total Duration**: Ensure the total duration of all scenes still matches the target campaign duration by adjusting previous scenes if necessary.
"""

    # MANDATORY DETERMINISTIC RESOLUTION:
    # ADK ignores state injection for callable providers, and its regex is limited.
    return common_utils.resolve_template(instruction, ctx.session.state)


async def log_mab_iteration_results(tool_context: ToolContext) -> str:
    """Logs the results and resets the 'ready' flag for the next iteration."""
    # Reset the flag so prepare_iteration_state can run again for the next loop
    tool_context.state["mab_iteration_ready"] = False

    config = get_mab_config()
    experiment_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
    if not experiment_id:
        return tool_failure("MAB experiment_id not found in tool context state.")

    user_id = common_utils.get_user_id(tool_context)
    mab_state, _ = await load_mab_state(user_id, experiment_id)
    if not mab_state:
        return tool_failure(
            f"MAB experiment state could not be loaded for experiment ID: {experiment_id}. "
            "This indicates a critical issue."
        )

    iteration_num = len(mab_state.iterations) + 1
    arms_selected = tool_context.state.get(common_utils.ARMS_SELECTED_KEY, {})
    verification_result = tool_context.state.get(
        common_utils.VERIFICATION_RESULT_KEY, {}
    )
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY, {})

    # Capture correct asset versions
    asset_service = mediagent_kit.services.aio.get_asset_service()

    async def get_and_store_version(scene):
        prompt = scene.get("first_frame_prompt", {})
        asset_id = prompt.get("asset_id")
        if asset_id:
            try:
                asset = await asset_service.get_asset_by_id(asset_id)
                if asset:
                    prompt["asset_version"] = asset.current_version
            except Exception as e:
                logger.error(f"Could not retrieve asset {asset_id} to log version: {e}")

    if storyboard and "scenes" in storyboard:
        await asyncio.gather(*[get_and_store_version(s) for s in storyboard["scenes"]])

    bandit = _initialize_bandit(config, mab_state)

    # The bandit library works with dicts, so we update the dict form
    mab_state_dict = mab_state.model_dump()
    updated_bandit_state = bandit.update_reward(
        iteration_num=iteration_num,
        mab_choices=arms_selected,
        verification_result=verification_result,
    )
    mab_state_dict.update(updated_bandit_state)
    # Re-validate the state with the Pydantic model
    mab_state = MabExperimentState.model_validate(mab_state_dict)

    # Update the global annotated visuals in MAB state with any newly generated assets
    # We defensively merge from both keys if available
    if not mab_state.user_assets:
        mab_state.user_assets = {}

    # 1. Update with structured visuals (preferred)
    annotated_visuals = tool_context.state.get(
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {}
    )
    if annotated_visuals:
        mab_state.user_assets.update(annotated_visuals)

    # 2. Sync with legacy visuals (fallback for captions)
    legacy_assets = tool_context.state.get(common_utils.USER_ASSETS_KEY, {})
    for filename, caption in legacy_assets.items():
        if filename not in mab_state.user_assets:
            mab_state.user_assets[filename] = {
                "file_name": filename,
                "caption": caption,
            }
        elif isinstance(mab_state.user_assets[filename], dict):
            mab_state.user_assets[filename]["caption"] = caption

    # Construct the structured log entry
    # Optimization: Strip bloated metadata from storyboard assets for logging
    def strip_asset_bloat(data):
        if isinstance(data, dict):
            if "versions" in data:
                data["versions"] = []  # Remove full version history
            if "image_generate_config" in data:
                data["image_generate_config"] = None  # Remove large prompts
            if "video_generate_config" in data:
                data["video_generate_config"] = None
            for v in data.values():
                strip_asset_bloat(v)
        elif isinstance(data, list):
            for item in data:
                strip_asset_bloat(item)

    log_storyboard = json.loads(json.dumps(storyboard, cls=DateTimeEncoder))
    strip_asset_bloat(log_storyboard)

    final_video_asset_id = storyboard.get("final_video_asset_id", "N/A")

    log_entry = MabIterationLog(
        iteration_num=iteration_num,
        project_folder_id=user_id,
        arms_selected=arms_selected,
        creative_brief=tool_context.state.get(common_utils.CREATIVE_BRIEF_KEY),
        storyline=tool_context.state.get(common_utils.STORYLINE_KEY),
        storyline_refinement_history=tool_context.state.get(
            common_utils.REFINEMENT_HISTORY_KEY
        ),
        character_casting=tool_context.state.get(common_utils.CASTING_KEY),
        creative_direction=tool_context.state.get(common_utils.CREATIVE_DIRECTION_KEY),
        verifier_results=verification_result,
        artifact_uri=f"asset/{final_video_asset_id}",
        verifiers={"video": "final_video_verifier_agent"},
        storyboard=log_storyboard,
        character_collage_asset_id=tool_context.state.get(
            common_utils.CHARACTER_COLLAGE_ID_KEY
        ),
        arm_stats=mab_state.arm_stats,
    )

    mab_state.iterations.append(log_entry)
    await save_mab_state(mab_state, user_id)

    return "Logged MAB results for iteration."


async def initialize_mab_experiment(tool_context: ToolContext) -> str:
    """
    Initializes a new MAB experiment.
    Idempotency: Reuses existing experiment ID if found in state.
    Hardwired: Performs LLM-driven Warm Start analysis if configured in YAML.
    """
    # 1. Check for existing experiment ID to prevent double initialization
    existing_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
    if existing_id:
        logger.info(
            f"⏭️ [MAB INITIALIZATION SKIP] Experiment already active. ID: {existing_id}"
        )
        return f"MAB experiment already initialized with ID: {existing_id}."

    experiment_id = str(uuid.uuid4())
    user_id = common_utils.get_user_id(tool_context)
    config = get_mab_config()

    user_prompt = tool_context.state.get(common_utils.USER_INPUT_KEY, "N/A")
    structured_constraints = tool_context.state.get(
        common_utils.STRUCTURED_USER_INPUT_KEY, {}
    )

    # Defensively merge assets from structured and legacy keys
    user_assets = {}

    # 1. Start with structured visuals (Preferred source for semantic roles)
    annotated_visuals = tool_context.state.get(
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {}
    )
    if annotated_visuals:
        for fname, meta in annotated_visuals.items():
            user_assets[fname] = (
                meta.copy()
                if isinstance(meta, dict)
                else {"file_name": fname, "caption": str(meta)}
            )

    # 2. Sync with legacy visuals (Ensure captions are up to date without overwriting roles)
    legacy_assets = tool_context.state.get(common_utils.USER_ASSETS_KEY, {})
    for filename, caption in legacy_assets.items():
        if filename not in user_assets:
            user_assets[filename] = {"file_name": filename, "caption": caption}
        else:
            # ONLY update caption if it's missing or if legacy has more detail
            current = user_assets[filename]
            if not current.get("caption") or len(caption) > len(
                current.get("caption", "")
            ):
                current["caption"] = caption

    logger.info(
        f"Initialized MAB experiment with {len(user_assets)} total reference assets."
    )

    # --- INITIAL STATE ---
    mab_state = MabExperimentState(
        experiment_id=experiment_id,
        user_prompt=user_prompt,
        structured_constraints=structured_constraints,
        user_assets=user_assets,
        arm_stats={},
        iterations=[],
    )

    mab_params = config.get("mab", {})
    mab_warm_up = mab_params.get("warm_up", False)
    log_msg = f"MAB experiment initialized with ID: {experiment_id}."

    # --- DETERMINISTIC WARM START ---
    if mab_warm_up:
        logger.info(
            f"[MAB] Warm-up enabled. Performing strategic analysis for experiment {experiment_id}..."
        )

        from ..instructions.mab import mab_warm_up_instruction

        mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
        asset_service = mediagent_kit.services.aio.get_asset_service()

        # Build prompt using current context (Arguments passed directly to avoid format() KeyError)
        analysis_prompt = mab_warm_up_instruction.get_warm_start_instruction(
            user_prompt=user_prompt, structured_constraints=structured_constraints
        )

        try:
            # Direct LLM call for strategy analysis
            analysis_asset = await mediagen_service.generate_text_with_gemini(
                user_id=user_id,
                file_name=f"mab_warm_start_{experiment_id}.txt",
                model="gemini-2.5-flash",
                prompt=analysis_prompt,
            )
            blob = await asset_service.get_asset_blob(analysis_asset.id)
            raw_text = blob.content.decode()

            # Parse structured recommendations
            warm_start_data = await common_utils.parse_json_from_text(
                raw_text, user_id=user_id
            )
            recommendations = warm_start_data.get("recommendations", {})
            reasoning = warm_start_data.get("reasoning", "No reasoning provided.")

            # Store in MAB state for reporting
            mab_state.warm_start = MabWarmStart(
                reasoning=reasoning, recommendations=ArmsSelected(**recommendations)
            )

            logger.info(f"[MAB Warm Start] Recommendations: {recommendations}")
            logger.info(f"[MAB Warm Start] Reasoning: {reasoning}")

            log_msg += " Warm-up completed using joint strategy analysis."

        except Exception as e:
            logger.error(
                f"[MAB Warm Start] Strategic analysis failed: {e}. Falling back to cold start."
            )
            log_msg += " Warm-up failed; fell back to cold start."

    await save_mab_state(mab_state, user_id)

    # Update session state for orchestrator
    tool_context.state[common_utils.MAB_EXPERIMENT_ID_KEY] = experiment_id
    tool_context.state["mab_iteration"] = -1
    tool_context.state["mab_warm_up"] = mab_warm_up

    return log_msg


async def _create_standalone_html_report(
    tool_context: ToolContext, mab_state: MabExperimentState
) -> Path | None:
    """
    Downloads all MAB artifacts and generates a standalone HTML report in a temporary directory.
    Returns the path to the generated HTML file.
    """
    user_id = common_utils.get_user_id(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()

    # Convert Pydantic model to dict for report generator
    mab_state_dict = mab_state.model_dump()
    user_prompt = mab_state_dict.get("user_prompt", "N/A")
    iterations = mab_state_dict.get("iterations", [])

    if not iterations:
        logger.warning("No iterations found in MAB log. Cannot generate HTML report.")
        return None

    semaphore = asyncio.Semaphore(8)  # Limit concurrent GCS downloads

    async def _download_and_save(asset_id: str, path: Path, version: int | None):
        async with semaphore:
            try:
                blob = await asset_service.get_asset_blob(
                    asset_id=asset_id, version=version
                )
                with open(path, "wb") as f:
                    f.write(blob.content)
                return True
            except Exception as e:
                logger.error(
                    f"Failed to download asset '{asset_id}' (version: {version}) to '{path}': {e}"
                )
                return False

    # Create a temporary directory that will be cleaned up by the calling function
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    output_path = temp_path / f"mab_report_{mab_state.experiment_id}.html"
    local_artifact_dirs = {}
    download_tasks = []

    # Create a dedicated directory for original user assets
    user_assets_dir = temp_path / "user_assets"
    user_assets_dir.mkdir(exist_ok=True)
    local_artifact_dirs["user_asset_paths"] = {}

    all_user_assets = await asset_service.list_assets(user_id=user_id)
    user_asset_map = {asset.file_name: asset for asset in all_user_assets}

    user_assets_from_log = mab_state_dict.get(common_utils.USER_ASSETS_KEY) or {}
    for filename in user_assets_from_log:
        if filename in user_asset_map:
            asset = user_asset_map[filename]
            destination_path = user_assets_dir / filename
            local_artifact_dirs["user_asset_paths"][filename] = destination_path
            download_tasks.append(
                _download_and_save(
                    asset_id=asset.id,
                    path=destination_path,
                    version=asset.current_version,
                )
            )

    for i, iteration_data in enumerate(iterations):
        iteration_dir = temp_path / f"iter_{i}"
        iteration_dir.mkdir(exist_ok=True)
        local_artifact_dirs[i] = {
            "dir_path": iteration_dir,
            "final_first_frames": [],
            "first_frame_history_paths": {},
            "voiceover_history_paths": {},
            "character_collage_path": None,
        }

        collage_id = iteration_data.get("character_collage_asset_id")
        if collage_id:
            collage_filename = f"iter_{i}_character_collage.png"
            collage_path = iteration_dir / collage_filename
            local_artifact_dirs[i]["character_collage_path"] = collage_path
            download_tasks.append(
                _download_and_save(
                    asset_id=collage_id,
                    path=collage_path,
                    version=None,
                )
            )

        storyboard = iteration_data.get("storyboard", {})

        # Download Global Voiceover history
        vo_history = storyboard.get("voiceover_generation_history", [])
        for attempt_data in vo_history:
            asset = attempt_data.get("asset", {})
            if "id" in asset and "current_version" in asset:
                download_tasks.append(
                    _download_and_save(
                        asset_id=asset["id"],
                        path=iteration_dir / Path(asset["file_name"]).name,
                        version=asset["current_version"],
                    )
                )

        # Download Background Music history
        bgm_history = storyboard.get("background_music_generation_history", [])
        for attempt_data in bgm_history:
            asset = attempt_data.get("asset", {})
            if "id" in asset and "current_version" in asset:
                download_tasks.append(
                    _download_and_save(
                        asset_id=asset["id"],
                        path=iteration_dir / Path(asset["file_name"]).name,
                        version=asset["current_version"],
                    )
                )

        final_video_asset_id = storyboard.get("final_video_asset_id")
        if final_video_asset_id:
            destination_path = iteration_dir / f"iter_{i}_final_video.mp4"
            video_version = storyboard.get("final_video_asset_version", (i + 1))
            download_tasks.append(
                _download_and_save(
                    asset_id=final_video_asset_id,
                    path=destination_path,
                    version=video_version,
                )
            )

        for j, scene in enumerate(storyboard.get("scenes", [])):
            final_frame_prompt = scene.get("first_frame_prompt", {})
            final_frame_asset_id = final_frame_prompt.get("asset_id")
            asset_version = final_frame_prompt.get("asset_version", 1)
            if final_frame_asset_id:
                frame_path = iteration_dir / f"iter_{i}_scene_{j}_final_frame.png"
                local_artifact_dirs[i]["final_first_frames"].append(frame_path)
                download_tasks.append(
                    _download_and_save(
                        asset_id=final_frame_asset_id,
                        path=frame_path,
                        version=asset_version,
                    )
                )

            frame_history = scene.get("first_frame_generation_history", [])
            for attempt_num, attempt_data in enumerate(frame_history):
                asset = attempt_data.get("asset", {})
                if "id" in asset and "current_version" in asset:
                    attempt_path = iteration_dir / Path(asset["file_name"]).name
                    local_artifact_dirs[i]["first_frame_history_paths"][
                        (j, attempt_num)
                    ] = attempt_path
                    download_tasks.append(
                        _download_and_save(
                            asset_id=asset["id"],
                            path=attempt_path,
                            version=asset["current_version"],
                        )
                    )

    await asyncio.gather(*download_tasks)

    try:
        from . import report_generator

        report_generator.generate_html_report(
            user_prompt=user_prompt,
            mab_state=mab_state_dict,
            local_artifact_dirs=local_artifact_dirs,
            output_path=str(output_path),
            use_asset_uris=False,
        )
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate MAB report: {e}", exc_info=True)
        return None


async def _upload_html_report(
    tool_context: ToolContext, report_path: Path
) -> common_utils.ToolResult:
    """
    Uploads the generated HTML report to GCS as both a user asset and a tool artifact.
    """
    try:
        if not report_path.exists():
            logger.error(
                f"Upload failed: Local report file not found at: {report_path}"
            )
            return common_utils.tool_failure(
                f"Local report file not found at: {report_path}"
            )
        report_content_bytes = report_path.read_bytes()
        user_id = common_utils.get_user_id(tool_context)
        asset_service = mediagent_kit.services.aio.get_asset_service()

        gcs_path_override = None
        if os.environ.get("BATCH_JOB_MODE") == "True":
            gcs_root = os.environ.get("ASSET_GCS_ROOT", "batch_job")
            gcs_path_override = f"{gcs_root}/{user_id}/{report_path.name}"

        # 1. Save as a user asset to appear in the Assets tab
        report_asset = await asset_service.save_asset(
            user_id=user_id,
            file_name=report_path.name,
            blob=report_content_bytes,
            mime_type="text/html",
            gcs_path_override=gcs_path_override,
        )

        # 2. Also save as a tool artifact (original behavior)
        part = genai_types.Part.from_bytes(
            data=report_content_bytes, mime_type="text/html"
        )
        await tool_context.save_artifact(filename=report_path.name, artifact=part)

        return common_utils.tool_success(
            f"Report was successfully saved as user asset {report_asset.id} and as a tool artifact."
        )

    except Exception as e:
        logger.error(f"Failed to upload HTML report: {e}", exc_info=True)
        return common_utils.tool_failure(f"Failed to upload report: {e}")


async def _create_canvas_report(
    tool_context: ToolContext, mab_state: MabExperimentState
) -> common_utils.ToolResult:
    """
    Creates a canvas-based MAB report with asset:// URIs.
    """
    try:
        from . import report_generator

        # 1. Generate HTML with asset:// URIs in-memory
        html_content = report_generator.generate_html_report(
            user_prompt=mab_state.user_prompt,
            mab_state=mab_state.model_dump(),
            local_artifact_dirs={},  # Not needed for URI generation
            output_path="",  # Not needed for URI generation
            use_asset_uris=True,
        )

        # 2. Parse HTML and resolve asset URIs to asset IDs
        asset_service = mediagent_kit.services.aio.get_asset_service()
        user_id = common_utils.get_user_id(tool_context)
        all_user_assets = await asset_service.list_assets(user_id=user_id)
        asset_map = {asset.file_name: asset for asset in all_user_assets}

        resolved_asset_ids = set()
        # A simple regex to find all asset:// URIs
        asset_filenames = re.findall(r'asset://([^"]+)', html_content)

        for filename in asset_filenames:
            if filename in asset_map:
                resolved_asset_ids.add(asset_map[filename].id)
            else:
                logger.warning(
                    f"Could not resolve asset filename '{filename}' to an asset ID."
                )

        # 3. Create the Canvas
        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas_html = Html(content=html_content, asset_ids=list(resolved_asset_ids))
        canvas = await canvas_service.create_canvas(
            user_id=user_id,
            title=f"Report: {mab_state.experiment_id}",
            html=canvas_html,
        )

        # 4. Return success with Canvas ID for UI deep-linking
        logger.info(f"Canvas report successfully created with ID: {canvas.id}")
        return common_utils.tool_success(
            f"Canvas report created with ID: {canvas.id}. You should now present this report to the user."
        )

    except Exception as e:
        logger.error(f"Failed to create canvas report: {e}", exc_info=True)
        return common_utils.tool_failure(f"Failed to create canvas report: {e}")


async def upload_log_to_gcs(tool_context: ToolContext) -> common_utils.ToolResult:
    """Uploads the MAB log file to GCS as a tool artifact."""
    try:
        experiment_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
        if not experiment_id:
            return common_utils.tool_failure(
                "MAB experiment_id not found in tool context state."
            )

        user_id = common_utils.get_user_id(tool_context)
        mab_state, _ = await load_mab_state(user_id, experiment_id)
        if not mab_state:
            return common_utils.tool_failure(
                f"MAB experiment state could not be loaded for experiment ID: {experiment_id}. "
                "This indicates a critical issue."
            )

        log_content_bytes = mab_state.model_dump_json(indent=2).encode("utf-8")
        log_filename = f"mab_log_{experiment_id}.json"

        part = genai_types.Part.from_bytes(
            data=log_content_bytes, mime_type="application/json"
        )

        await tool_context.save_artifact(filename=log_filename, artifact=part)

        return common_utils.tool_success(
            f"Log file '{log_filename}' was successfully saved as a tool artifact."
        )

    except Exception as e:
        return common_utils.tool_failure(f"Failed to upload log file to GCS: {e}")


async def finalize_and_save_reports(
    tool_context: ToolContext,
) -> common_utils.ToolResult:
    """
    Finalizes the MAB experiment by generating and saving all configured reports.
    """
    experiment_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
    if not experiment_id:
        return tool_failure("MAB experiment_id not found in tool context state.")

    user_id = common_utils.get_user_id(tool_context)
    mab_state, _ = await load_mab_state(user_id, experiment_id)
    if not mab_state:
        return tool_failure(
            f"MAB experiment state could not be loaded for experiment ID: {experiment_id}."
        )

    config = get_mab_config()
    results = []

    # Save the JSON report as a primary user asset
    try:
        json_bytes = mab_state.model_dump_json(indent=2).encode("utf-8")
        file_name = f"mab_report_{experiment_id}.json"

        gcs_path_override = None
        if os.environ.get("BATCH_JOB_MODE") == "True":
            gcs_root = os.environ.get("ASSET_GCS_ROOT", "batch_job")
            gcs_path_override = f"{gcs_root}/{user_id}/{file_name}"

        json_asset = await mediagent_kit.services.aio.get_asset_service().save_asset(
            user_id=user_id,
            file_name=file_name,
            blob=json_bytes,
            mime_type="application/json",
            gcs_path_override=gcs_path_override,
        )
        results.append(f"Successfully saved JSON report as asset {json_asset.id}.")
    except Exception as e:
        results.append(f"Failed to save JSON report: {e}")

    # Upload the final log file as a tool artifact
    try:
        log_upload_result = await upload_log_to_gcs(tool_context)
        results.append(f"GCS Log Upload: {log_upload_result['status']}")
    except Exception as e:
        results.append(f"Failed to upload GCS log artifact: {e}")

    # Conditionally generate and upload the standalone HTML report
    if config.get("generate_html_report", False):
        try:
            report_path = await _create_standalone_html_report(tool_context, mab_state)
            if report_path:
                upload_result = await _upload_html_report(tool_context, report_path)
                results.append(f"HTML Report: {upload_result['status']}")
                # Clean up the temporary directory
                shutil.rmtree(report_path.parent)
            else:
                results.append("HTML Report: Failed (no file generated).")
        except Exception as e:
            results.append(f"Failed to generate or upload HTML report: {e}")

    # Conditionally generate the canvas report
    if config.get("generate_canvas_report", False):
        try:
            canvas_result = await _create_canvas_report(tool_context, mab_state)
            if canvas_result["status"] == "succeeded":
                results.append(f"Canvas Report: {canvas_result['result']}")
            else:
                results.append(
                    f"Canvas Report: Failed - {canvas_result['error_message']}"
                )
        except Exception as e:
            results.append(f"Canvas Report: Exception - {e}")

    return tool_success(" ".join(results))


def prepare_iteration_state(tool_context: ToolContext) -> str:
    """
    Atomic management of iteration state.
    Always clears local iteration state; conditionally increments MAB counter.
    """
    state = tool_context.state
    user_id = common_utils.get_user_id(tool_context)

    # 1. ALWAYS clear iteration-specific state keys
    # This ensures that even if we restart the SAME iteration, we start fresh.
    keys_to_clear = [
        common_utils.CREATIVE_BRIEF_KEY,
        common_utils.CREATIVE_DIRECTION_KEY,
        common_utils.THEORETICAL_DEFS_KEY,
        common_utils.STORYLINE_KEY,
        common_utils.CASTING_KEY,
        common_utils.STORYBOARD_KEY,
        common_utils.VERIFICATION_RESULT_KEY,
        "storyline_evaluation",
    ]
    for key in keys_to_clear:
        state[key] = {}

    # 2. ALWAYS reset local refinement and temporary flags
    state[common_utils.REFINEMENT_HISTORY_KEY] = []
    state["temp:storyline_done"] = False
    state[common_utils.CHARACTER_COLLAGE_ID_KEY] = None

    # 3. Scrub previous iteration artifacts (collages) from long-lived asset keys
    scrubbed_count = 0
    for asset_key in [
        common_utils.USER_ASSETS_KEY,
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY,
    ]:
        assets_dict = state.get(asset_key, {})
        if isinstance(assets_dict, dict):
            keys_before = set(assets_dict.keys())
            state[asset_key] = {
                k: v for k, v in assets_dict.items() if not k.startswith("iter_")
            }
            scrubbed_count += len(keys_before - set(state[asset_key].keys()))

    # 4. CONDITIONAL increment of MAB counter
    if state.get("mab_iteration_ready"):
        current_iter = state.get("mab_iteration", 0)
        logger.info(
            f"♻️ [ITERATION RESTART] User: {user_id}, Re-preparing MAB iteration: {current_iter}. Local state cleared."
        )
        return f"MAB iteration {current_iter} state has been reset for a clean restart."

    current_iter = state.get("mab_iteration", -1)
    new_iter = current_iter + 1
    state["mab_iteration"] = new_iter
    state["mab_iteration_ready"] = True

    logger.info(
        f"🔄 [ITERATION START] User: {user_id}, Incrementing MAB iteration: {current_iter} -> {new_iter}"
    )

    msg = f"MAB iteration incremented to {new_iter}. State cleared and {scrubbed_count} artifacts scrubbed."
    logger.info(f"✅ [ITERATION READY] {msg}")
    return msg


async def check_mab_loop_status(tool_context: ToolContext) -> str:
    """Checks if the MAB loop should continue or stop based on config."""
    config = get_mab_config()
    mab_params = config.get("mab", {})
    target_iterations = mab_params.get("num_iterations", 1)

    experiment_id = tool_context.state.get(common_utils.MAB_EXPERIMENT_ID_KEY)
    if not experiment_id:
        return "STOP - No experiment initialized."

    user_id = common_utils.get_user_id(tool_context)
    mab_state, _ = await load_mab_state(user_id, experiment_id)
    if not mab_state:
        return "STOP - State lost."

    current_count = len(mab_state.iterations)
    if current_count >= target_iterations:
        return "STOP - Target number of iterations reached."

    return f"CONTINUE - {current_count}/{target_iterations} iterations complete."


class LocalEscalationFilter(BaseAgent):
    """Wraps an agent and consumes any 'escalate' signals to prevent bubbling."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        # We assume this filter wraps exactly one sub-agent
        sub_agent = self.sub_agents[0]

        async with Aclosing(sub_agent.run_async(ctx)) as agen:
            async for event in agen:
                if event.actions.escalate:
                    # Log the interception for debugging
                    logger.info(
                        f"[{self.name}] Intercepted 'escalate' signal from {event.author}. "
                        "Cloning event and consuming signal for parent."
                    )
                    # CLONE the event before modification to avoid aliasing bugs
                    # This allows the inner LoopAgent to see the True value for its own exit logic,
                    # while the parent agent receives a False value and continues.
                    event_for_parent = event.model_copy(deep=True)
                    event_for_parent.actions.escalate = False
                    yield event_for_parent
                else:
                    yield event


class StorylineRefinementChecker(BaseAgent):
    """Checks storyline score and manages refinement history."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        history = state.get(common_utils.REFINEMENT_HISTORY_KEY, [])
        storyline = state.get(common_utils.STORYLINE_KEY)
        evaluation = state.get("storyline_evaluation")

        # Filter for storyline attempts
        storyline_attempts = [h for h in history if h.get("stage") == "storyline"]
        # The number of the attempt we just completed
        attempt_num = len(storyline_attempts) + 1

        if storyline and evaluation:
            # Robustly convert to dict for logging and saving
            def to_dict(obj):
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if isinstance(obj, dict):
                    return obj
                return str(obj)

            storyline_dict = to_dict(storyline)
            evaluation_dict = to_dict(evaluation)

            # Replicate the log structure from Station 5
            history.append(
                {
                    "stage": "storyline",
                    "attempt": attempt_num,
                    "output": storyline_dict,
                    "score": evaluation_dict.get("score", 0),
                    "evaluation": evaluation_dict,
                }
            )
            state[common_utils.REFINEMENT_HISTORY_KEY] = history

            # Replicate "files are copied" (saving text assets)
            try:
                asset_service = mediagent_kit.services.aio.get_asset_service()
                # Robust user ID retrieval
                user_id = common_utils.get_user_id(ctx)
                mab_iter = state.get("mab_iteration", 0)

                logger.info(
                    f"Saving storyline attempt {attempt_num-1} for user {user_id}..."
                )

                await asset_service.save_asset(
                    user_id=user_id,
                    file_name=f"iter_{mab_iter}_storyline_attempt_{attempt_num-1}.txt",
                    blob=json.dumps(storyline_dict, indent=2).encode(),
                    mime_type="text/plain",
                )
                await asset_service.save_asset(
                    user_id=user_id,
                    file_name=f"iter_{mab_iter}_storyline_eval_attempt_{attempt_num-1}.txt",
                    blob=json.dumps(evaluation_dict, indent=2).encode(),
                    mime_type="text/plain",
                )
            except Exception as e:
                logger.error(f"Failed to save storyline attempt as asset: {e}")

        config = get_mab_config()
        sl_config = config.get("self_refinement", {}).get("storyline", {})
        threshold = sl_config.get("score_threshold", 80)
        max_attempts = sl_config.get("max_attempts", 2)

        # Use the serialized dict to get the score safely
        score = evaluation_dict.get("score", 0) if evaluation and evaluation_dict else 0

        user_id = common_utils.get_user_id(ctx)
        mab_iter = state.get("mab_iteration", 0)

        # OFF-BY-ONE FIX: Stop IMMEDIATELY if we hit max_attempts
        if score >= threshold or attempt_num >= max_attempts:
            logger.info(
                f"🎯 [STORYLINE DONE] User: {user_id}, MAB Iter: {mab_iter}, Score: {score} (target: {threshold}), Attempt: {attempt_num}/{max_attempts}. Terminating loop."
            )
            state["temp:storyline_done"] = True
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logger.info(
                f"🔄 [STORYLINE CONTINUE] User: {user_id}, MAB Iter: {mab_iter}, Score: {score} (target: {threshold}), Attempt: {attempt_num}/{max_attempts}. Continuing loop."
            )
            yield Event(author=self.name)


class StorylineLoopInstructionSelector(BaseAgent):
    """Selects between initial and revision instructions for the storyline agent."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        from ..instructions.pre_production import (
            storyline_instruction,
            storyline_refinement_instruction,
        )
        from ..instructions.verifier import storyline_verifier_instruction

        state = ctx.session.state
        if state.get("temp:storyline_done"):
            # If already done, switch to a "no-op" instruction to skip LLM work
            # This applies to both the Executor and the Evaluator turns
            instruction = (
                "The storyline is already refined. Return the current session state "
                "data EXACTLY as it is. Do NOT perform any new analysis or changes."
            )
            logger.info("Storyline already done. Using skip instruction.")
        else:
            history = state.get(common_utils.REFINEMENT_HISTORY_KEY, [])
            storyline_attempts = [h for h in history if h.get("stage") == "storyline"]

            # We use a state key to tell this agent which prompt to select
            # 'temp:storyline_prompt_type' should be set by the caller or inferred
            prompt_type = state.get("temp:storyline_prompt_type", "executor")

            if prompt_type == "evaluator":
                instruction = storyline_verifier_instruction.INSTRUCTION
                logger.info("Using storyline evaluation instruction.")
            elif not storyline_attempts:
                instruction = storyline_instruction.INSTRUCTION
                logger.info("Using initial storyline instruction.")
            else:
                instruction = storyline_refinement_instruction.INSTRUCTION
                logger.info("Using storyline revision instruction.")

        # MANDATORY DETERMINISTIC RESOLUTION:
        # Since this instruction is stored in state and then used by another agent,
        # ADK won't automatically resolve placeholders inside it. We must do it here.
        resolved_instruction = common_utils.resolve_template(instruction, state)

        # Update the instruction dynamically in the context
        ctx.session.state["temp:storyline_instruction"] = resolved_instruction
        yield Event(author=self.name)


class CreativeBriefSaver(BaseAgent):
    """Saves the creative brief as a persistent text asset."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        brief = state.get(common_utils.CREATIVE_BRIEF_KEY)
        if brief:
            try:
                asset_service = mediagent_kit.services.aio.get_asset_service()
                user_id = (
                    ctx.session.user_id
                    if hasattr(ctx, "session")
                    else common_utils.get_user_id(ctx)
                )
                mab_iter = state.get(common_utils.MAB_ITERATION_KEY, 0)

                logger.info(f"Saving creative brief for user {user_id}...")

                await asset_service.save_asset(
                    user_id=user_id,
                    file_name=f"iter_{mab_iter}_creative_brief.txt",
                    blob=(
                        brief.encode()
                        if isinstance(brief, str)
                        else json.dumps(brief, indent=2).encode()
                    ),
                    mime_type="text/plain",
                )
            except Exception as e:
                logger.error(f"Failed to save creative brief as asset: {e}")
        yield Event(author=self.name)


class CreativeDirectionSaver(BaseAgent):
    """Consolidates and saves synthesized creative directions as a persistent text asset."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        cd = state.get(common_utils.CREATIVE_DIRECTION_KEY)
        if cd:
            try:
                # Handle both dict and Pydantic model
                cd_dict = cd.model_dump() if hasattr(cd, "model_dump") else cd

                # Format the consolidated content
                content = "### CREATIVE DIRECTIONS (Synthesized Theory)\n\n"

                sections = [
                    ("STORYLINE INSTRUCTION", "storyline_instruction"),
                    ("KEYFRAME INSTRUCTION (VISUAL STYLE)", "keyframe_instruction"),
                    ("VIDEO INSTRUCTION (CAMERA & PACING)", "video_instruction"),
                    ("AUDIO INSTRUCTION (MUSIC & VO)", "audio_instruction"),
                ]

                for title, key in sections:
                    instr = cd_dict.get(key, "No instruction provided.")
                    content += f"---\n#### {title}\n{instr}\n\n"

                asset_service = mediagent_kit.services.aio.get_asset_service()
                user_id = (
                    ctx.session.user_id
                    if hasattr(ctx, "session")
                    else common_utils.get_user_id(ctx)
                )
                mab_iter = state.get(common_utils.MAB_ITERATION_KEY, 0)

                logger.info(
                    f"Saving consolidated creative directions for user {user_id}..."
                )

                await asset_service.save_asset(
                    user_id=user_id,
                    file_name=f"iter_{mab_iter}_creative_directions.txt",
                    blob=content.encode(),
                    mime_type="text/plain",
                )
            except Exception as e:
                logger.error(f"Failed to save creative direction asset: {e}")

        yield Event(author=self.name)


class StoryboardSaver(BaseAgent):
    """Saves the final storyboard as a persistent JSON asset."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        storyboard = state.get(common_utils.STORYBOARD_KEY)
        if storyboard:
            try:
                asset_service = mediagent_kit.services.aio.get_asset_service()
                user_id = (
                    ctx.session.user_id
                    if hasattr(ctx, "session")
                    else common_utils.get_user_id(ctx)
                )
                mab_iter = state.get("mab_iteration", 0)

                logger.info(f"Saving storyboard for user {user_id}...")

                # Convert Pydantic model to dict if necessary
                if hasattr(storyboard, "model_dump"):
                    storyboard_dict = storyboard.model_dump()
                elif isinstance(storyboard, dict):
                    storyboard_dict = storyboard
                else:
                    storyboard_dict = str(storyboard)

                await asset_service.save_asset(
                    user_id=user_id,
                    file_name=f"iter_{mab_iter}_storyboard.json",
                    blob=json.dumps(storyboard_dict, indent=2).encode(),
                    mime_type="application/json",
                )
            except Exception as e:
                logger.error(f"Failed to save storyboard as asset: {e}")
        yield Event(author=self.name)


class AssetInventoryPreparer(BaseAgent):
    """Formats the valid asset list into a simple string for the Storyboard agent."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        visuals = state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {})

        inventory = []
        for fname, meta in visuals.items():
            role = (
                meta.get("semantic_role", "unknown")
                if isinstance(meta, dict)
                else "unknown"
            )
            inventory.append(f"- {fname} (Role: {role})")

        state["temp:asset_inventory_list"] = (
            "\n".join(inventory) if inventory else "No assets available."
        )
        yield Event(author=self.name)
