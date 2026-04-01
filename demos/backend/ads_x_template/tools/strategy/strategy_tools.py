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

"""Tools for strategy mapping and security enforcement."""

from google.adk.tools.tool_context import ToolContext
from ...utils.common import common_utils
from ...utils.parameters.parameters_model import Parameters
from ...utils.storyboard.storyboard_model import Storyboard

def map_strategy_to_metadata(tool_context: ToolContext) -> str:
    """Explicitly maps campaign research into the global storyboard metadata AND enforces least privilege.
    
    This ensures reliability and prevents state leakage in a single atomic tool call.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.error("⭐⭐⭐ [NATIVE TOOL INVOCATION] `map_strategy_to_metadata` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐")
    state = tool_context.state
    params_dict = state.get(common_utils.PARAMETERS_KEY)
    
    if not params_dict:
        return "No parameters found in state. Skipping mapping."
        
    params = Parameters.model_validate(params_dict)
    
    # 1. Mapping Metadata
    metadata = {
        "campaign_title": params.campaign_name,
        "campaign_theme": params.campaign_theme,
        "campaign_tone": params.campaign_tone,
        "global_visual_style": params.global_visual_style,
        "global_setting": params.global_setting,
        "concept_description": (params.storyline_guidance.narrative_arc if params.storyline_guidance else params.campaign_brief),
        "key_message": params.key_message or (params.brief_results.primary_hook if params.brief_results else None),
        "target_audience_profile": (
            f"Persona: {params.brief_results.audience.persona} | Pain Points: {', '.join(params.brief_results.audience.pain_points)} | Desires: {', '.join(params.brief_results.audience.desires)}"
            if params.brief_results and params.brief_results.audience
            else params.target_audience
        )
    }
    state["forced_metadata"] = metadata

    # 3. Beautify Output for UI
    summary = "Strategy context synchronized.\n"
    
    # 2. Enforcing Least Privilege (Sanitization)
    # If mode is NOT custom, we wipe sensitive storyline_guidance from the state.
    if params.template_name != "Custom":
        if "storyline_guidance" in params_dict:
            del params_dict["storyline_guidance"]
            state[common_utils.PARAMETERS_KEY] = params_dict
            return summary + "\n*(Note: Storyline sanitized for templated mode)*"
            
    return summary
