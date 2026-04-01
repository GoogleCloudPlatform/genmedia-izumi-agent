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

from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import FunctionTool

from .instructions import (
    canvas_management,
    media_generation,
    root,
)
from .tools import (
    asset_tools,
    canvas_tools,
    gemini_llm_tools,
    image_gen_tools,
    music_gen_tools,
    speech_gen_tools,
    video_gen_tools,
)

logging.basicConfig(level=logging.INFO)

MODEL_ID_FLASH_MODEL = "gemini-2.5-flash"
MODEL_ID_PRO_MODEL = "gemini-2.5-pro"

media_generation_agent = LlmAgent(
    model=MODEL_ID_FLASH_MODEL,
    name="media_generation",
    instruction=media_generation.INSTRUCTION,
    description="Generates images using Imagen and Gemini Image. Generate videos using Veo. Generate speech or narration using Gemini Text-to-Speech (TTS) and Chirp. Generate music using Lyria.",
    tools=[
        FunctionTool(
            func=image_gen_tools.generate_image_with_imagen,
        ),
        FunctionTool(
            func=image_gen_tools.generate_image_with_gemini,
        ),
        FunctionTool(
            func=video_gen_tools.generate_video_with_veo,
        ),
        FunctionTool(
            func=speech_gen_tools.generate_speech_single_speaker,
        ),
        FunctionTool(
            func=speech_gen_tools.generate_speech_multiple_speaker,
        ),
        FunctionTool(
            func=music_gen_tools.generate_music_with_lyria,
        ),
        FunctionTool(
            func=asset_tools.list_assets,
        ),
    ],
)

parallel_media_generation_agent = ParallelAgent(
    name="parallel_media_generation",
    sub_agents=[media_generation_agent],
    description="A parallel agent that runs multiple media_generation agents concurrently. This is useful for generating a batch of multimedia assets such as images, videos and audio at once, significantly speeding up the process.",
)

canvas_management_agent = LlmAgent(
    model=MODEL_ID_PRO_MODEL,
    name="canvas_management",
    instruction=canvas_management.INSTRUCTION,
    description="Creates and manages HTML canvases to visually display a collection of media assets. Can also list existing canvases.",
    tools=[
        FunctionTool(func=canvas_tools.create_html_canvas),
        FunctionTool(func=canvas_tools.update_canvas_title),
        FunctionTool(func=canvas_tools.update_canvas_html),
        FunctionTool(func=canvas_tools.list_canvases),
    ],
)

root_agent = LlmAgent(
    model=MODEL_ID_FLASH_MODEL,
    name="creative_toolbox_root",
    instruction=root.INSTRUCTION,
    description="The main orchestrator agent that manages the workflow. It creates a story, generates assets and visualizes them.",
    sub_agents=[parallel_media_generation_agent, canvas_management_agent],
    tools=[
        FunctionTool(func=asset_tools.load_asset_and_save_as_artifact),
        FunctionTool(func=gemini_llm_tools.creative_writer_with_gemini),
        FunctionTool(func=asset_tools.list_assets),
    ],
)

logging.info("Started GenMedia Agent.")
