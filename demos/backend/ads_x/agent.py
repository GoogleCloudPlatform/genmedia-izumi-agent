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

from google.adk.agents import llm_agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.function_tool import FunctionTool

from .instructions import (
    parameters_instruction,
    root_instruction,
    storyboard_instruction,
)
from .tools import generation_tools, stitching_tools, user_assets_tools
from .utils import common_utils, parameters_model, storyboard_model

parameters_agent = llm_agent.LlmAgent(
    name="parameters_agent",
    description="Parses the user input into ad campaign parameters.",
    model="gemini-2.5-flash",
    instruction=parameters_instruction.INSTRUCTION,
    output_key=common_utils.PARAMETERS_KEY,
    output_schema=parameters_model.Parameters,
    generate_content_config=common_utils.JSON_CONFIG,
)

storyboard_agent = llm_agent.LlmAgent(
    name="storyboard_agent",
    description="Creates a storyboard for the ads campaign.",
    model="gemini-2.5-pro",
    instruction=storyboard_instruction.INSTRUCTION,
    output_schema=storyboard_model.Storyboard,
    output_key=common_utils.STORYBOARD_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
)

root_agent = llm_agent.LlmAgent(
    model="gemini-2.5-flash",
    name="ads_x_agent",
    instruction=root_instruction.INSTRUCTION,
    tools=[
        FunctionTool(user_assets_tools.ingest_assets),
        AgentTool(parameters_agent),
        AgentTool(storyboard_agent),
        FunctionTool(generation_tools.generate_all_media),
        FunctionTool(stitching_tools.stitch_final_video),
    ],
    before_model_callback=common_utils.store_user_input_model_callback,
)
