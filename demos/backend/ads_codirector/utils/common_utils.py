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

"""Utils shared among agents and tools."""

import inspect
import json
import logging
import re
from typing import Any, get_args, get_origin

import pydantic
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

logger = logging.getLogger(__name__)

# State Keys
USER_INPUT_KEY = "user_prompt"
STRUCTURED_USER_INPUT_KEY = "structured_constraints"
USER_ASSETS_KEY = "user_assets"  # ads_x parity for UI sync
ANNOTATED_REFERENCE_VISUALS_KEY = "annotated_reference_visuals"
CREATIVE_CONFIG_KEY = "creative_configuration"
CREATIVE_BRIEF_KEY = "creative_brief"
CREATIVE_DIRECTION_KEY = "creative_direction"
THEORETICAL_DEFS_KEY = "theoretical_definitions"
CASTING_KEY = "character_casting"
STORYBOARD_KEY = "storyboard"
STORYLINE_KEY = "storyline"
CHARACTER_COLLAGE_ID_KEY = "character_collage_asset_id"
REFINEMENT_HISTORY_KEY = "refinement_history"

# Creative Direction Sub-keys (Nested Paths)
CD_STORYLINE_KEY = "cd_storyline"
CD_KEYFRAME_KEY = "cd_keyframe"
CD_VIDEO_KEY = "cd_video"
CD_AUDIO_KEY = "cd_audio"


def resolve_template(template: str, state: dict[str, Any]) -> str:
    """
    Robustly resolves placeholders in a template string using a provided state.
    Supports nested keys (e.g., {key.subkey}) and recursive resolution.
    """
    if not isinstance(template, str):
        return str(template)

    def _get_nested_value(data, path):
        parts = path.split(".")
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            elif hasattr(data, part):
                data = getattr(data, part)
            else:
                return None
        return data

    def _replacer(match):
        # Extract the key, removing any triple/double/single braces
        raw_key = match.group()
        key = raw_key.strip("{} ")

        # 1. Try exact match in state
        val = state.get(key)

        # 2. Try nested match (dot notation)
        if val is None and "." in key:
            val = _get_nested_value(state, key)

        # 3. Handle missing values
        if val is None:
            # If it looks like a Pydantic description (braced JSON), don't flag as missing
            if key.startswith('"') or key.startswith("\n"):
                return raw_key
            return raw_key  # Keep as is if not found

        return str(val)

    # Resolve placeholders (handles single, double, and triple braces)
    # Regex finds anything between braces that isn't another brace
    # We do multiple passes for recursion
    result = template
    for _ in range(3):  # Max 3 levels of recursion
        new_result = re.sub(r"\{+[a-zA-Z0-9_:.-]+\}+", _replacer, result)
        if new_result == result:
            break
        result = new_result

    return result


# Legacy/Internal keys
PARAMETERS_KEY = STRUCTURED_USER_INPUT_KEY
VERIFICATION_RESULT_KEY = "verification_result"
ARMS_SELECTED_KEY = CREATIVE_CONFIG_KEY
MAB_EXPERIMENT_ID_KEY = "mab_experiment_id"
MAB_ITERATION_KEY = "mab_iteration"


JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")

ToolResult = dict[str, Any]


def tool_success(result: Any = "") -> ToolResult:
    """Returns a tool success result."""
    return {"status": "succeeded", "result": result}


def tool_failure(error_message: str) -> ToolResult:
    """Returns a tool failure result with the given error message."""
    return {"status": "failed", "error_message": error_message}


async def store_user_input_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    """Model callback to store user text input into session state."""
    user_input = ""
    for content in llm_request.contents:
        if content.role == "user":
            for part in content.parts:
                if part.text and part.text.startswith("For context:"):
                    break
                if part.text and not part.text.startswith("<asset://"):
                    user_input += "\n\n" + part.text
    # Ensure user_prompt key exists
    callback_context.state[USER_INPUT_KEY] = user_input.strip()

    # Initialize downstream keys to avoid KeyError during recursive template resolution
    for key in [
        USER_INPUT_KEY,
        STRUCTURED_USER_INPUT_KEY,
        USER_ASSETS_KEY,
        ANNOTATED_REFERENCE_VISUALS_KEY,
        CREATIVE_CONFIG_KEY,
        CREATIVE_BRIEF_KEY,
        STORYLINE_KEY,
        CASTING_KEY,
        STORYBOARD_KEY,
        REFINEMENT_HISTORY_KEY,
    ]:
        if key not in callback_context.state:
            callback_context.state[key] = [] if key == REFINEMENT_HISTORY_KEY else {}


async def prompt_logging_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    """Model callback to log the full prompt sent to the LLM."""
    full_prompt = ""

    # 1. Capture the Resolved System Instruction
    if llm_request.config and llm_request.config.system_instruction:
        instr = llm_request.config.system_instruction
        if isinstance(instr, str):
            full_prompt += f"[SYSTEM INSTRUCTION]\n{instr}\n\n"
        elif hasattr(instr, "parts"):
            # Handle Content object
            instr_text = "".join([p.text for p in instr.parts if p.text])
            full_prompt += f"[SYSTEM INSTRUCTION]\n{instr_text}\n\n"

    # 2. Capture the Conversation History
    for content in llm_request.contents:
        role = content.role or "user"
        for part in content.parts:
            if part.text:
                full_prompt += f"[{role.upper()}]\n{part.text}\n\n"

    # Use a separator for visibility in logs
    header = f"--- LLM REQUEST PROMPT: {callback_context.agent_name} ---"
    logger.info(
        f"\n{'='*len(header)}\n{header}\n{full_prompt.strip()}\n{'='*len(header)}\n"
    )


async def repair_json_with_gemini(user_id: str, malformed_text: str) -> dict:
    """Uses a small model call to repair malformed JSON."""
    import mediagent_kit.services.aio

    logger.warning("Attempting JSON repair via Gemini...")
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    repair_prompt = f"""
Fix the following malformed JSON string so it can be parsed by json.loads().
Ensure all braces are closed, all commas are present, and there are no trailing commas.
Return ONLY the corrected JSON object.

MALFORMED TEXT:
{malformed_text}
"""
    try:
        # We use a raw text call for the repair itself to avoid recursion
        repair_result = await mediagen_service.generate_text_with_gemini(
            user_id=user_id, prompt=repair_prompt, file_name="repaired_json.txt"
        )
        asset_service = mediagent_kit.services.aio.get_asset_service()
        blob = await asset_service.get_asset_blob(repair_result.id)
        fixed_text = blob.content.decode().strip()

        # Strip potential markdown from the repair's own output
        fixed_text = re.sub(r"```json\s*", "", fixed_text)
        fixed_text = re.sub(r"```\s*", "", fixed_text)
        start = fixed_text.find("{")
        end = fixed_text.rfind("}") + 1
        return json.loads(fixed_text[start:end])
    except Exception as e:
        logger.error(f"JSON Repair failed: {e}")
        raise ValueError(f"Could not repair JSON: {malformed_text}") from e


async def parse_json_from_text(text: str, user_id: str = "default-user") -> dict:
    """Robustly extracts and parses JSON, with automatic LLM repair on failure."""
    # 1. Strip markdown
    clean_text = re.sub(r"```json\s*", "", text)
    clean_text = re.sub(r"```\s*", "", clean_text)

    # 2. Find outer-most braces
    start_index = clean_text.find("{")
    if start_index == -1:
        return await repair_json_with_gemini(user_id, text)

    # Simple brace counter to find the end of the first object
    count = 0
    end_index = -1
    for i in range(start_index, len(clean_text)):
        if clean_text[i] == "{":
            count += 1
        elif clean_text[i] == "}":
            count -= 1
            if count == 0:
                end_index = i + 1
                break

    if end_index == -1:
        return await repair_json_with_gemini(user_id, text)

    json_string = clean_text[start_index:end_index]

    # 3. Clean common trailing commas
    json_string = re.sub(r",\s*([\]}])", r"\1", json_string)

    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        # 4. Final attempt: Auto-repair
        return await repair_json_with_gemini(user_id, json_string)


def json_for_pydantic_model(model: type[pydantic.BaseModel]) -> dict[str, Any]:
    """Returns a JSON representing the structure of a Pydantic model."""
    result: dict[str, Any] = {}
    for field_name, field in model.model_fields.items():
        if field.annotation is None:
            continue
        field_type = field.annotation
        field_description = field.description if field.description else str(field_type)

        if get_origin(field_type) is list:
            # Handle lists
            list_item_type = get_args(field_type)[0]
            if inspect.isclass(list_item_type) and issubclass(
                list_item_type, pydantic.BaseModel
            ):
                result[field_name] = [json_for_pydantic_model(list_item_type)]
            else:
                result[field_name] = [field_description]
            result[field_name].append(f"... # More {field_name} can be present")
        elif inspect.isclass(field_type) and issubclass(field_type, pydantic.BaseModel):
            # Handle nested Pydantic models
            result[field_name] = json_for_pydantic_model(field_type)
        else:
            # Handle leaf types
            result[field_name] = field_description

    return result


def describe_pydantic_model(model: type[pydantic.BaseModel]) -> str:
    """Returns a JSON string representing the structure of a Pydantic model."""
    return json.dumps(json_for_pydantic_model(model), indent=2)
