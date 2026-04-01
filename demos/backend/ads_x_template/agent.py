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

"""Ads-X agent implemented using the Mediagent Kit."""

import os
import mediagent_kit
from mediagent_kit import MediagentKitConfig
from google.adk.agents import llm_agent
from google.adk.agents import sequential_agent
from google.adk.tools import AgentTool, FunctionTool

from utils.adk import blob_interceptor_callback
from .instructions import root_instruction
from .instructions.parameters import parameters_instruction
from .instructions.user_assets import user_assets_instruction
from .instructions.storyboard import storyboard_instruction
from .instructions.generation import generation_instruction
from .instructions.strategy import strategy_instruction
from .tools.user_assets import user_assets_tools
from .tools.generation import generation_tools, stitching_tools, summary_canvas_tool
from .tools.strategy import strategy_tools
from .tools.storyboard import production_tools, storyboard_repair_tools
from .utils.common import common_utils
from .tools.parameters import parameters_tools

async def debug_parameters_callback(*args, **kwargs):
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"🚨 [PARAMETERS AGENT RAW OUTPUT] args: {args}")
    logger.error(f"🚨 [PARAMETERS AGENT RAW OUTPUT] kwargs: {kwargs}")

def instrument_agent(agent_name: str):
    async def debug_cb(*args, **kwargs):
        import logging
        from datetime import datetime
        logger = logging.getLogger(__name__)
        logger.error(f"🚨🚨🚨 [ROUTING TRACE] ENTERING AGENT: {agent_name} at {datetime.utcnow().isoformat()} 🚨🚨🚨")
    return debug_cb

from google.genai import types

parameters_agent = llm_agent.LlmAgent(
    name="parameters_agent",
    description="Agent that parses the user brief into ad campaign parameters.",
    model="gemini-2.5-flash",
    instruction=parameters_instruction.AGENT_INSTRUCTION,
    tools=[FunctionTool(parameters_tools.extract_campaign_parameters)],
    disallow_transfer_to_parent=False,
    disallow_transfer_to_peers=False,
    before_model_callback=instrument_agent("parameters_agent"),
    after_model_callback=debug_parameters_callback
)

user_assets_agent = llm_agent.LlmAgent(
    name="user_assets_agent",
    description="Agent that ingests the user-provided assets.",
    model="gemini-2.5-flash",
    instruction=user_assets_instruction.INSTRUCTION,
    tools=[FunctionTool(user_assets_tools.ingest_assets)],
    before_model_callback=instrument_agent("user_assets_agent"),
)


storyboard_agent_creative = llm_agent.LlmAgent(
    name="storyboard_agent_creative",
    description="Creates a highly creative, cinematic storyboard invented by the AI.",
    model="gemini-3.1-pro-preview",
    instruction=storyboard_instruction.get_ai_director_instruction,
    tools=[
        FunctionTool(production_tools.recommend_production_recipe),
        FunctionTool(storyboard_repair_tools.finalize_and_persist_storyboard),
    ],
    disallow_transfer_to_parent=False,
    disallow_transfer_to_peers=False,
    before_model_callback=instrument_agent("storyboard_agent_creative"),
)

storyboard_agent_templated = llm_agent.LlmAgent(
    name="storyboard_agent_templated",
    description="Creates a storyboard following a strict template.",
    model="gemini-3-flash-preview",
    instruction=storyboard_instruction.get_templated_instruction,
    tools=[
        FunctionTool(production_tools.recommend_production_recipe),
        FunctionTool(storyboard_repair_tools.finalize_and_persist_storyboard),
    ],
    disallow_transfer_to_parent=False,
    disallow_transfer_to_peers=False,
    before_model_callback=instrument_agent("storyboard_agent_templated"),
)

strategy_agent = llm_agent.LlmAgent(
    name="strategy_agent",
    description="Synchronizes campaign strategy and secures the state.",
    model="gemini-2.5-flash",
    instruction=strategy_instruction.INSTRUCTION,
    tools=[FunctionTool(strategy_tools.map_strategy_to_metadata)],
    before_model_callback=instrument_agent("strategy_agent"),
)

storyboard_router = llm_agent.LlmAgent(
    name="storyboard_router",
    description="Routes the campaign to the correct specialized storyboard generator and persists the output.",
    model="gemini-2.5-flash",
    instruction=storyboard_instruction.get_router_instruction,
    tools=[
        AgentTool(agent=storyboard_agent_creative),
        AgentTool(agent=storyboard_agent_templated),
    ],
    before_model_callback=instrument_agent("storyboard_router"),
)


generation_agent = llm_agent.LlmAgent(
    name="generation_agent",
    description="Agent that generates all media and stitches them together.",
    model="gemini-2.5-flash",
    instruction=generation_instruction.INSTRUCTION,
    tools=[
        FunctionTool(generation_tools.generate_all_media),
        FunctionTool(stitching_tools.stitch_final_video),
        FunctionTool(summary_canvas_tool.create_campaign_summary),
    ],
    before_model_callback=instrument_agent("generation_agent"),
)

# Track 1: Traditional Planning (Text-based starting from brief)
planning_agent_text = sequential_agent.SequentialAgent(
    name="planning_agent_text",
    description="Planning pipeline that parses a text brief into a storyboard.",
    sub_agents=[
        parameters_agent,
        user_assets_agent,
        strategy_agent,    # Stage 3
        storyboard_router, # Stage 4
    ],
)


full_pipeline_agent = sequential_agent.SequentialAgent(
    name="full_pipeline_agent",
    description="Sequential agent for the Ads-X pipeline.",
    sub_agents=[
        planning_agent_text,  # Use the specialized planning agent
        generation_agent,     # Step 4: Generate & Stitch
    ],
)

root_agent = llm_agent.LlmAgent(
    model="gemini-2.5-flash",
    name="ads_x_agent",
    instruction=root_instruction.get_instruction,
    sub_agents=[full_pipeline_agent],
    before_model_callback=blob_interceptor_callback,
)
