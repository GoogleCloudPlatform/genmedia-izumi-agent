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
from google.adk.tools.tool_context import ToolContext
import mediagent_kit

from ...utils.common import common_utils
from ...utils.parameters import parameters_model
from ...instructions.parameters import (
    parameters_instruction,
    parameters_repair_instruction,
)

logger = logging.getLogger(__name__)


async def extract_campaign_parameters(
    tool_context: ToolContext, user_brief: str
) -> str:
    """Parses the user brief into structured campaign parameters silently in the background."""

    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `extract_campaign_parameters` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    logger.error(
        f"⭐⭐⭐ [NATIVE TOOL CONTEXT] Received User Brief Length: {len(user_brief)} characters ⭐⭐⭐"
    )
    logger.info("Extracting campaign parameters via background tool...")

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    workspace_id = str(
        tool_context.state.get("workspace_id")
        or tool_context.state.get("user_id", "default_user")
    )

    # Call Gemini to get the JSON. INSTRUCTION is shared with the parameters
    # agent (which has the tool); here there is no tool, so append the
    # text-output override or Gemini 3.x returns a MALFORMED_FUNCTION_CALL.
    raw_json = await mediagen_service.generate_text(
        workspace_id=workspace_id,
        prompt=parameters_instruction.INSTRUCTION
        + f"\n\n**USER BRIEF:**\n{user_brief}"
        + parameters_instruction.TEXT_OUTPUT_OVERRIDE,
    )

    # Clean JSON helper
    def clean_markdown_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[len("```json") :].strip()
        if text.endswith("```"):
            text = text[: -len("```")].strip()
        return text

    clean_json = clean_markdown_json(raw_json)

    params_data = None
    first_error = None

    # 1. First Attempt
    try:
        params_data = json.loads(clean_json)
        params = parameters_model.Parameters.model_validate(params_data)

        # Hardened state persistence for downstream agents
        dumped = params.model_dump()
        tool_context.state[common_utils.PARAMETERS_KEY] = dumped
        logger.warning(
            f"🚨 [DEEP DEBUG UPSTREAM] Persisting to state type: {type(dumped)}"
        )
        logger.warning(
            f"🚨 [DEEP DEBUG UPSTREAM] Persisting to state repr: {repr(dumped)}"
        )
        logger.info(
            f"Successfully persisted parameters to state: {params.campaign_name}"
        )

        return "Campaign parameters extracted successfully."
    except Exception as e:
        first_error = e
        logger.warning(
            f"First parameter extraction failed: {e}. Attempting self-correction..."
        )

    # 2. Repair Turn (Self-Correction)
    try:
        repaired_raw = await mediagen_service.generate_text(
            workspace_id=workspace_id,
            prompt=parameters_repair_instruction.REPAIR_PROMPT.format(
                user_brief=user_brief, raw_json=clean_json, error=str(first_error)
            ),
        )
        repaired_json = clean_markdown_json(repaired_raw)

        params_data = json.loads(repaired_json)
        params = parameters_model.Parameters.model_validate(params_data)

        # Hardened state persistence for downstream agents
        tool_context.state[common_utils.PARAMETERS_KEY] = params.model_dump()
        logger.info(
            f"Successfully persisted repaired parameters to state: {params.campaign_name}"
        )

        return "Campaign parameters extracted (Repaired)."
    except Exception as e2:
        logger.error(
            f"Parameter repair also failed: {e2}. Falling back to intelligent guessing."
        )

        # 3. Final Safety: Intelligent Fallback
        from ...utils.storyboard import template_library

        # 3.1. Best guess for template name.
        #
        # Default to "Custom" (AI Director / creative mode). We ONLY switch to
        # a specific template if the user explicitly named one in the brief.
        #
        # We deliberately do NOT call suggest_template() here: it never returns
        # "Custom" (its floor is a generic Problem/Solution template), so using
        # it as a fallback silently forces every failed-extraction run into
        # templated mode. Creative is the system's preferred default, so a
        # parse failure must degrade to creative, not to an arbitrary template.
        # (Root cause of the "creative brief routed to templated mode" bug.)
        detected_template = "Custom"
        all_templates = template_library.get_all_templates()
        brief_upper = user_brief.upper()
        for t in all_templates:
            if t.template_name.upper() in brief_upper:
                detected_template = t.template_name
                break

        # 3.3 Dynamic Fallback Detection
        detected_orientation = "landscape"
        if "PORTRAIT" in user_brief.upper() or "VERTICAL" in user_brief.upper():
            detected_orientation = "portrait"

        detected_duration = "12s"
        import re

        duration_match = re.search(r"(\d+s)", user_brief)
        if duration_match:
            detected_duration = duration_match.group(1)

        # 3.4. Create robust fallback object
        fallback_params = parameters_model.Parameters(
            campaign_brief=user_brief,
            campaign_name="New Campaign",
            target_audience="General Audience",
            target_duration=detected_duration,
            target_orientation=detected_orientation,
            template_name=detected_template,
        )

        # Persist to state so following agents have a baseline
        tool_context.state[common_utils.PARAMETERS_KEY] = fallback_params.model_dump()
        logger.info(
            f"Successfully persisted fallback parameters to state: {fallback_params.campaign_name}"
        )

        return (
            "⚠️ **Brief Decoded (Robust Mode)!** Encountered persistent issues parsing the full structured data. "
            f"I've established a baseline campaign using the **{detected_template}** template."
        )
