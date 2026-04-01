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

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .instructions import root as root_instruction
from .tools import (
    generation_tools,
    stitching_tool,
    storyboard_tool,
)

logging.basicConfig(level=logging.INFO)

# --- Agent Configuration ---
MODEL_ID_FLASH = "gemini-2.5-flash"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY_SECONDS = 30
# ---------------------------


# A single, flat agent with all the tools necessary for the video generation pipeline.
# The agent's behavior is controlled by the detailed instruction in `instructions/root.py`,
# which acts as a state machine, guiding the LLM to call the correct tool based on the
# `generation_stage` variable in the session state.
root_agent = LlmAgent(
    model=MODEL_ID_FLASH,
    name="story_to_video_agent_root",
    instruction=root_instruction.INSTRUCTION,
    description="The main orchestrator for the video generation pipeline.",
    tools=[
        FunctionTool(func=storyboard_tool.create_storyboard),
        FunctionTool(func=generation_tools.generate_images_for_storyboard),
        FunctionTool(func=generation_tools.generate_videos_and_speech_for_storyboard),
        FunctionTool(func=stitching_tool.stitch_final_video),
        FunctionTool(func=generation_tools.regenerate_assets),
    ],
)

# Set retry config in the generation_tools module
# This is a way to configure the decorator from the agent definition file
generation_tools.MAX_RETRIES = MAX_RETRIES
generation_tools.INITIAL_RETRY_DELAY = INITIAL_RETRY_DELAY_SECONDS


logging.info("Started Video Generation Agent.")
