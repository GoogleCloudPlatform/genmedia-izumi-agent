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

from google.adk.agents import LoopAgent, llm_agent, sequential_agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.function_tool import FunctionTool

from utils.adk import blob_interceptor_callback

from .instructions import (
    root_instruction,
    parameters_instruction,
)
from .instructions.mab import (
    creative_director_instruction,
)
from .instructions.pre_production import (
    creative_brief_instruction,
    casting_instruction,
    voiceover_script_instruction,
)
from .instructions.verifier import (
    storyline_verifier_instruction,
)
from .mab import utils as mab_utils
from .tools import (
    user_assets_tools,
    casting_tools,
    storyboard_verifier_tools,
    video_verifier_tools,
    generation_tools,
    stitching_tools,
)
from .utils import (
    common_utils,
    parameters_model,
    casting_model,
    storyboard_model,
    storyline_evaluator_model,
    storyline_model,
    mab_model,
)

# Reference Alignment: num_iterations is loaded from config
mab_config = mab_utils.get_mab_config()
mab_params = mab_config.get("mab", {})
num_iterations = mab_params.get("num_iterations", 1)

# Storyline refinement config
sl_refine_config = mab_config.get("self_refinement", {}).get("storyline", {})
storyline_max_attempts = sl_refine_config.get("max_attempts", 2)

LLM_MODEL_NAME = "gemini-2.5-flash"

parameters_agent = llm_agent.LlmAgent(
    name="parameters_agent",
    description="Agent that parses the user brief into ad campaign parameters.",
    model=LLM_MODEL_NAME,
    instruction=parameters_instruction.INSTRUCTION,
    output_schema=parameters_model.Parameters,
    output_key=common_utils.PARAMETERS_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

user_assets_agent = llm_agent.LlmAgent(
    name="user_assets_agent",
    description="Agent that ingests and annotates the user-provided reference visuals.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'ingest_assets' tool. Return ONLY the tool output.",
    tools=[FunctionTool(user_assets_tools.ingest_assets)],
)

creative_brief_agent = llm_agent.LlmAgent(
    name="creative_brief_agent",
    description="Agent that performs contextual enrichment (Creative Brief B).",
    model=LLM_MODEL_NAME,
    instruction=creative_brief_instruction.INSTRUCTION,
    output_key=common_utils.CREATIVE_BRIEF_KEY,
    before_model_callback=common_utils.prompt_logging_callback,
)

creative_brief_saver = mab_utils.CreativeBriefSaver(name="creative_brief_saver")

storyline_loop_selector = mab_utils.StorylineLoopInstructionSelector(
    name="storyline_loop_selector"
)

storyline_executor_agent = llm_agent.LlmAgent(
    name="storyline_executor_agent",
    description="Agent that generates or revises the storyline script.",
    model=LLM_MODEL_NAME,
    instruction="{temp:storyline_instruction}",
    output_schema=storyline_model.Storyline,
    output_key=common_utils.STORYLINE_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
    before_model_callback=common_utils.prompt_logging_callback,
)

storyline_evaluator_agent = llm_agent.LlmAgent(
    name="storyline_evaluator_agent",
    description="Agent that evaluates the storyline against a rubric.",
    model=LLM_MODEL_NAME,
    instruction=storyline_verifier_instruction.INSTRUCTION,
    output_schema=storyline_evaluator_model.StorylineEvaluation,
    output_key="storyline_evaluation",
    generate_content_config=common_utils.JSON_CONFIG,
    before_model_callback=common_utils.prompt_logging_callback,
)

storyline_loop_checker = mab_utils.StorylineRefinementChecker(
    name="storyline_loop_checker"
)

storyline_core_loop = LoopAgent(
    name="storyline_core_loop",
    description="Loop agent that refines the storyline script.",
    sub_agents=[
        storyline_loop_selector,
        storyline_executor_agent,
        storyline_evaluator_agent,
        storyline_loop_checker,
    ],
    max_iterations=storyline_max_attempts,
)

# Filter: Prevent storyline loop escalation from stopping the global MAB loop
storyline_loop_agent = mab_utils.LocalEscalationFilter(
    name="storyline_loop_agent", sub_agents=[storyline_core_loop]
)

visual_casting_agent = llm_agent.LlmAgent(
    name="visual_casting_agent",
    description="Agent that identifies character demographics and wardrobe (Visual Assets V).",
    model=LLM_MODEL_NAME,
    instruction=casting_instruction.INSTRUCTION,
    output_schema=casting_model.CharacterCasting,
    output_key=common_utils.CASTING_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
)

casting_generation_agent = llm_agent.LlmAgent(
    name="casting_generation_agent",
    description="Agent that generates the character collage image.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `generate_character_collage` tool.",
    tools=[FunctionTool(casting_tools.generate_character_collage)],
)

storyboard_agent = llm_agent.LlmAgent(
    name="storyboard_agent",
    description="Agent that expands storyline into a visual sequence (Storyboard S).",
    model=LLM_MODEL_NAME,
    instruction=mab_utils.get_storyboard_instruction_with_mab,
    output_schema=storyboard_model.Storyboard,
    output_key=common_utils.STORYBOARD_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_model_callback=common_utils.prompt_logging_callback,
)

voiceover_script_agent = llm_agent.LlmAgent(
    name="voiceover_script_agent",
    description="Agent that writes a unified narration script synchronized with visuals.",
    model=LLM_MODEL_NAME,
    instruction=voiceover_script_instruction.INSTRUCTION,
    output_schema=storyboard_model.Storyboard,
    output_key=common_utils.STORYBOARD_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

storyboard_verifier_agent = llm_agent.LlmAgent(
    name="storyboard_verifier_agent",
    description="Agent that verifies the generated storyboard for correctness.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'verify_storyboard_assets' tool. Your response should be ONLY the raw output of the tool.",
    tools=[FunctionTool(storyboard_verifier_tools.verify_storyboard_assets)],
)

storyboard_saver = mab_utils.StoryboardSaver(name="storyboard_saver")

asset_inventory_preparer = mab_utils.AssetInventoryPreparer(
    name="asset_inventory_preparer"
)

pre_production_agent = sequential_agent.SequentialAgent(
    name="pre_production_agent",
    description="Pre-Production Agent (Phi_pre) that transforms constraints into a storyboard.",
    sub_agents=[
        creative_brief_agent,
        creative_brief_saver,
        storyline_loop_agent,
        visual_casting_agent,
        casting_generation_agent,
        asset_inventory_preparer,
        storyboard_agent,
        voiceover_script_agent,
        storyboard_verifier_agent,
        storyboard_saver,
    ],
)

keyframe_agent = llm_agent.LlmAgent(
    name="keyframe_agent",
    description="Agent that produces and refines keyframes jointly (Phi_frame).",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'produce_refined_keyframes' tool.",
    tools=[FunctionTool(generation_tools.produce_refined_keyframes)],
)

video_agent = llm_agent.LlmAgent(
    name="video_agent",
    description="Agent that transforms keyframes into video clips (Phi_video).",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'generate_production_videos' tool.",
    tools=[FunctionTool(generation_tools.generate_production_videos)],
)

audio_agent = llm_agent.LlmAgent(
    name="audio_agent",
    description="Agent that synthesizes acoustic elements (Phi_audio).",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'generate_production_audio' tool.",
    tools=[FunctionTool(generation_tools.generate_production_audio)],
)

production_agent = sequential_agent.SequentialAgent(
    name="production_agent",
    description="Production Agent (Phi_prod) that generates multimodal artifacts.",
    sub_agents=[
        keyframe_agent,
        video_agent,
        audio_agent,
    ],
)

post_production_agent = llm_agent.LlmAgent(
    name="post_production_agent",
    description="Post-Production Agent (Phi_post) that consolidates clips and audio.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the 'stitch_final_video' tool.",
    tools=[
        FunctionTool(stitching_tools.stitch_final_video),
    ],
)

final_video_verifier_agent = llm_agent.LlmAgent(
    name="final_video_verifier_agent",
    description="Agent that evaluates the quality of the final video.",
    model=LLM_MODEL_NAME,
    instruction=(
        "You MUST call the 'evaluate_final_video' tool. "
        "After the tool runs, you MUST return the tool's output EXACTLY as it was provided to you, "
        "with no modifications, summarizations, or added text. "
        "DO NOT add any pleasantries, explanations, or confirmation messages."
    ),
    tools=[FunctionTool(video_verifier_tools.evaluate_final_video)],
)

mab_logging_agent = llm_agent.LlmAgent(
    name="mab_logging_agent",
    description="Agent that logs the results of the MAB iteration.",
    model=LLM_MODEL_NAME,
    instruction="Log the results of this MAB iteration. Return ONLY the tool output.",
    tools=[FunctionTool(mab_utils.log_mab_iteration_results)],
)

mab_selection_agent = llm_agent.LlmAgent(
    name="mab_selection_agent",
    description="Agent that selects the MAB arms.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `select_mab_arms` tool. Return ONLY the tool output.",
    tools=[FunctionTool(mab_utils.select_mab_arms)],
)

theoretical_definitions_agent = llm_agent.LlmAgent(
    name="theoretical_definitions_agent",
    description="Agent that retrieves theoretical definitions for the selected arms.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `get_theoretical_definitions` tool. Return ONLY the tool output.",
    tools=[FunctionTool(mab_utils.get_theoretical_definitions)],
)

creative_director_agent = llm_agent.LlmAgent(
    name="creative_director_agent",
    description="Agent that synthesizes the creative direction (Phi_orch synthesis).",
    model=LLM_MODEL_NAME,
    instruction=creative_director_instruction.INSTRUCTION,
    output_schema=mab_model.CreativeDirection,
    output_key=common_utils.CREATIVE_DIRECTION_KEY,
    generate_content_config=common_utils.JSON_CONFIG,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_model_callback=common_utils.prompt_logging_callback,
)

cd_flattener_agent = llm_agent.LlmAgent(
    name="cd_flattener_agent",
    description="Tool agent that flattens creative direction into the state.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `flatten_creative_direction` tool. Return ONLY the tool output.",
    tools=[FunctionTool(mab_utils.flatten_creative_direction)],
)

creative_direction_saver = mab_utils.CreativeDirectionSaver(
    name="creative_direction_saver"
)

iteration_manager_agent = llm_agent.LlmAgent(
    name="iteration_manager_agent",
    description="Agent that manages iteration state (counter and scrubbing).",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `prepare_iteration_state` tool. After the tool runs, you MUST return the tool's output EXACTLY as it was provided to you, with no modifications, summarizations, or added text.",
    tools=[FunctionTool(mab_utils.prepare_iteration_state)],
)

iteration_agent = sequential_agent.SequentialAgent(
    name="iteration_agent",
    description="Agent that produces a video ad.",
    sub_agents=[
        iteration_manager_agent,
        mab_selection_agent,
        theoretical_definitions_agent,
        creative_director_agent,
        cd_flattener_agent,
        creative_direction_saver,
        pre_production_agent,
        production_agent,
        post_production_agent,
        final_video_verifier_agent,
        mab_logging_agent,
    ],
)

mab_report_agent = llm_agent.LlmAgent(
    name="mab_report_agent",
    description="Agent that generates the final MAB report.",
    model=LLM_MODEL_NAME,
    instruction=(
        "You MUST call the `finalize_and_save_reports` tool to generate and save reports. "
        "After the tool runs, you MUST return the tool's output EXACTLY as it was provided to you, "
        "with no modifications, summarizations, or added text. "
        "DO NOT add any pleasantries, explanations, or confirmation messages."
    ),
    tools=[FunctionTool(mab_utils.finalize_and_save_reports)],
)

# mab_initialization_agent must come before the LoopAgent to reset state
mab_initialization_agent = llm_agent.LlmAgent(
    name="mab_initialization_agent",
    description="Agent that initializes the MAB experiment.",
    model=LLM_MODEL_NAME,
    instruction="You MUST call the `initialize_mab_experiment` tool. Return ONLY the tool output.",
    tools=[FunctionTool(mab_utils.initialize_mab_experiment)],
)

mab_loop_agent = LoopAgent(
    name="mab_loop_agent",
    description=f"Loop agent that runs the production pipeline {num_iterations} times.",
    sub_agents=[iteration_agent],
    max_iterations=num_iterations,
)


async def combined_callback(callback_context, llm_request):
    """Combines user input storage and blob interception."""
    await common_utils.store_user_input_model_callback(callback_context, llm_request)
    return await blob_interceptor_callback(callback_context, llm_request)


root_agent = llm_agent.LlmAgent(
    model=LLM_MODEL_NAME,
    name="orchestrator_agent",
    instruction=root_instruction.INSTRUCTION,
    tools=[
        AgentTool(user_assets_agent),
        AgentTool(parameters_agent),
        AgentTool(mab_initialization_agent),
        AgentTool(mab_loop_agent),
        AgentTool(mab_report_agent),
    ],
    before_model_callback=combined_callback,
)
