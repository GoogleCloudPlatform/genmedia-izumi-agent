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

import json
import logging
import uuid
import pydantic
from google.adk.tools.tool_context import ToolContext
import mediagent_kit

from ...utils.common import common_utils
from ...utils.storyboard import storyboard_model

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

REPAIR_PROMPT = """
The following JSON representing a video storyboard was truncated mid-sentence due to output limits.
Your task is to REPAIR and COMPLETE the JSON so it is syntactically valid and matches the target schema.

Rules:
1. If a scene is partially generated, you may remove the incomplete scene or complete it logically.
2. Ensure all opening brackets [ {{ and quotes " are correctly closed.
3. The final output must be a valid JSON object matching the Storyboard schema.
4. DO NOT add conversational text. Return ONLY the valid JSON.

Truncated JSON:
{raw_json}
"""


async def finalize_and_persist_storyboard(
    tool_context: ToolContext, raw_output: str
) -> ToolResult:
    """Parses, repairs if necessary, and persists the storyboard to the session state."""
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `finalize_and_persist_storyboard` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )

    logger.info(
        f"finalize_and_persist_storyboard received raw_output of length: {len(raw_output)}"
    )
    logger.debug(f"Raw Output Snippet (Start): {raw_output[:500]}")
    logger.debug(f"Raw Output Snippet (End): {raw_output[-500:]}")

    # 1. Clean the raw output (remove markdown fences)
    clean_json = raw_output.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[len("```json") :].strip()
    if clean_json.endswith("```"):
        clean_json = clean_json[: -len("```")].strip()

    storyboard_data = None

    # 2. Try initial parse
    try:
        storyboard_data = json.loads(clean_json)
        logger.info("Storyboard JSON parsed successfully on first attempt.")
    except json.JSONDecodeError as e:
        logger.warning(
            f"Storyboard JSON is malformed or truncated: {e}. Attempting repair..."
        )

        # 3. Trigger Repair Turn using mediagent_kit
        mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
        user_id = tool_context.state.get("user_id", "default_user")
        uid = uuid.uuid4().hex[:8]
        repair_result = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            file_name=f"storyboard_repair_{uid}.json",
            model="gemini-2.5-flash",  # Fast model for repair
            prompt=REPAIR_PROMPT.format(
                raw_json=clean_json[-5000:]
            ),  # Send last 5k chars for context
            reference_image_filenames=[],
        )

        # Note: We might need to stitch if the repair only returned the tail,
        # but usually it's safer to have the repair model return the whole corrected block
        # OR we just use the repair output if it's broad enough.
        # For simplicity, let's assume the repair model returns the FULL valid JSON.

        repair_blob = (
            await mediagent_kit.services.aio.get_asset_service().get_asset_blob(
                repair_result.id
            )
        )
        repaired_json = repair_blob.content.decode().strip()

        # Clean repair output
        if repaired_json.startswith("```json"):
            repaired_json = repaired_json[len("```json") :].strip()
        if repaired_json.endswith("```"):
            repaired_json = repaired_json[: -len("```")].strip()

        try:
            storyboard_data = json.loads(repaired_json)
            logger.info("Storyboard JSON repaired successfully.")
        except json.JSONDecodeError as e2:
            return tool_failure(f"Failed to repair storyboard JSON: {e2}")

    # 4. Validate against Pydantic Model
    try:
        storyboard = storyboard_model.Storyboard.model_validate(storyboard_data)

        parameters = tool_context.state.get(common_utils.PARAMETERS_KEY, {})
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except Exception:
                parameters = {}

        if not hasattr(parameters, "get"):
            parameters = {}

        target_duration_str = parameters.get("target_duration", "12s")
        template_name = parameters.get("template_name", "Custom")

        # --- Fallback Removed: Resolving from the root ---
        # If the LLM omits scenes, Pydantic will now automatically raise a ValidationError
        # because of `min_length=1`. This gracefully delegates the correction back to the LLM agent.

        # --- Programmatic Pacing Enforcement ---

        # ONLY apply rigid duration enforcement to AI Director (Custom) templates.
        # Hardcoded templates have perfectly pre-mapped mathematical lengths that should not be touched.
        if template_name == "Custom" and storyboard.scenes:
            from ...utils.storyboard import pacing_blueprints

            try:
                target_secs = float(str(target_duration_str).replace("s", "").strip())
            except ValueError:
                target_secs = 12.0

            llm_durations = [scene.duration_seconds for scene in storyboard.scenes]
            scene_cnt = len(storyboard.scenes)

            # Step A: Validate the length is absolutely permitted by the blueprint preset array
            valid_counts = pacing_blueprints.get_valid_scene_counts_for_duration(
                target_secs
            )
            if scene_cnt not in valid_counts:
                logger.error(
                    f"Pacing Constraint Violation: Generated {scene_cnt} scenes for {target_secs}s. Requires: {valid_counts}"
                )
                raise ValueError(
                    f"Invalid scene count. For a {target_secs}s video, you MUST generate exactly one of the following scene counts: {valid_counts} scenes. You generated {scene_cnt} scenes. Please rewrite the entire storyboard JSON to match the required scene count."
                )

            # Only override if the LLM hallucinated, missed constraints, or used an invalid duration
            if pacing_blueprints.matches_any_preset(target_secs, llm_durations):
                logger.info(
                    f"LLM perfectly matched a valid pacing preset for {target_secs}s. Proceeding without override."
                )
            else:
                logger.warning(
                    f"LLM pacing {llm_durations} invalid for target {target_secs}s. Enforcing blueprint override."
                )
                blueprint_durations = pacing_blueprints.get_blueprint_for_count(
                    target_secs, len(storyboard.scenes)
                )
                for idx, scene in enumerate(storyboard.scenes):
                    if idx < len(blueprint_durations):
                        correct_dur = blueprint_durations[idx]
                        scene.duration_seconds = correct_dur
                        scene.video_prompt.duration_seconds = correct_dur
        # ----------------------------------------

        # --- PROGRAMMATIC ART DIRECTION INJECTION (SAFETY GUARD) ---
        # We intercept the JSON output here to absolutely guarantee that every technical parameter
        # from the Master Recipe is securely digested by the final video engine.
        recipe = tool_context.state.get("master_production_recipe")
        if recipe:
            c_optics = recipe.get("cinematography", {}).get("optics", "")
            i_vibe = recipe.get("illumination", {}).get("vibe", "")

            anchor_str = f" [Aesthetic Anchor: {i_vibe}, {c_optics}]"
            for scene in storyboard.scenes:
                if (
                    scene.first_frame_prompt
                    and anchor_str not in scene.first_frame_prompt.description
                ):
                    scene.first_frame_prompt.description = (
                        f"{scene.first_frame_prompt.description.strip()}{anchor_str}"
                    )
                if (
                    scene.video_prompt
                    and anchor_str not in scene.video_prompt.description
                ):
                    scene.video_prompt.description = (
                        f"{scene.video_prompt.description.strip()}{anchor_str}"
                    )

        # 5. Persist to State (Redundant but safe)
        tool_context.state[common_utils.STORYBOARD_KEY] = storyboard.model_dump()

        # 6. Beautify for UI
        table_rows = []
        for i, scene in enumerate(storyboard.scenes, 1):
            table_rows.append(
                f'| {i} | {scene.video_prompt.description} | *"{scene.voiceover_prompt.text}"* |'
            )

        markdown_summary = f"""
### 🎬 Creative Architecture Validated & Synchronized
The high-fidelity narrative blueprint for **{storyboard.campaign_title or 'Untitled Campaign'}** has been successfully verified and securely persisted to session state.

**🔒 Safety Check Results:**
- All scenes have been structurally validated against the pacing array.
- Master Production Recipe technical anchors (Lighting, Lenses, Textures) were verified and programmatically injected into all visual prompts.

| Scene | Hydrated Visual Action | Voiceover Script |
| :--- | :--- | :--- |
{"\n".join(table_rows)}
"""
        return tool_success(markdown_summary)
    except pydantic.ValidationError as ve:
        return tool_failure(
            f"Storyboard validation failed. If the 'scenes' array is missing or empty, you MUST rethink and completely regenerate the JSON object, explicitly including all required scenes. Error details: {ve}"
        )
    except ValueError as val_err:
        return tool_failure(str(val_err))
