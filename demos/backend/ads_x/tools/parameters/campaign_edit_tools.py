# Copyright 2026 Google LLC
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

"""Editing the campaign brief at the strategy checkpoint.

Parameters are extracted from the user's brief by an LLM, so they are a
best-effort reading of intent: the audience may be too broad, the duration
wrong, the tone slightly off. These tools let a reviewer correct that at the
strategy checkpoint, before a storyboard is written against a misreading.

Only the fields worth correcting by hand are exposed. Derived and structural
state — the extracted persona breakdown, the template mode, the storyboard
itself — is left alone.
"""

import logging
from typing import Any, Dict

from google.adk.tools.tool_context import ToolContext

from ...utils.common import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Reviewer-facing name -> key in the persisted parameters.
_EDITABLE = {
    "campaign_name": "campaign_name",
    "target_audience": "target_audience",
    "target_duration": "target_duration",
    "target_orientation": "target_orientation",
    "campaign_theme": "campaign_theme",
    "campaign_tone": "campaign_tone",
    "key_message": "key_message",
    "global_visual_style": "global_visual_style",
    "global_setting": "global_setting",
    "creator_description": "creator_description",
    "vertical": "vertical",
}


def _parameters(tool_context: ToolContext) -> Dict[str, Any] | None:
    params = tool_context.state.get(common_utils.PARAMETERS_KEY)
    return params if isinstance(params, dict) else None


async def show_campaign_parameters(tool_context: ToolContext) -> ToolResult:
    """Shows the campaign brief as it was understood, for review."""
    params = _parameters(tool_context)
    if params is None:
        return tool_failure("No campaign parameters in state yet.")

    recipe = tool_context.state.get("master_production_recipe") or {}
    assets = tool_context.state.get(common_utils.USER_ASSETS_KEY) or {}

    return tool_success(
        {
            "parameters": {
                name: params.get(key) for name, key in sorted(_EDITABLE.items())
            },
            "features_a_person": bool(params.get("generate_virtual_creator")),
            "look": recipe.get("look_name"),
            "uploaded_assets": sorted(assets) if isinstance(assets, dict) else [],
            "editable_fields": sorted(_EDITABLE),
        }
    )


async def edit_campaign_parameter(
    tool_context: ToolContext, field: str, value: str
) -> ToolResult:
    """Corrects one field of the campaign brief.

    Args:
        field: Which field to change. `show_campaign_parameters` lists the
            editable ones.
        value: The corrected value.
    """
    key = field.strip().lower()
    if key not in _EDITABLE:
        return tool_failure(
            f"'{field}' is not editable here. Editable fields: {sorted(_EDITABLE)}"
        )
    if not value.strip():
        return tool_failure("A value is required.")

    params = _parameters(tool_context)
    if params is None:
        return tool_failure("No campaign parameters in state yet.")

    previous = params.get(_EDITABLE[key])
    params[_EDITABLE[key]] = value.strip()
    tool_context.state[common_utils.PARAMETERS_KEY] = params

    logger.info("Campaign parameter '%s' changed by reviewer.", key)
    return tool_success(f'Changed {key} from "{previous}" to "{value.strip()}".')


async def set_virtual_creator(
    tool_context: ToolContext, enabled: bool, description: str = ""
) -> ToolResult:
    """Decides whether the ad features an on-screen person, and who they are.

    This is a defining choice: with it off the ad is product-only and no person
    is ever invented; with it on, every scene is styled around the described
    creator.

    Args:
        enabled: True for an ad featuring a person, False for product-only.
        description: What that person looks like. Authoritative when given — it
            overrides the Look's own casting.
    """
    params = _parameters(tool_context)
    if params is None:
        return tool_failure("No campaign parameters in state yet.")

    params["generate_virtual_creator"] = bool(enabled)
    if description.strip():
        params["creator_description"] = description.strip()
    tool_context.state[common_utils.PARAMETERS_KEY] = params

    if not enabled:
        return tool_success(
            "This is now a product-only ad; no on-screen person will appear."
        )
    who = description.strip() or "cast from the campaign's brand and Look"
    return tool_success(f"The ad will feature a person: {who}.")
