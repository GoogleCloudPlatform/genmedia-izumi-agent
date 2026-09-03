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
from google.adk.agents import loop_agent
from google.adk.agents import sequential_agent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools import AgentTool, FunctionTool
from google.adk.tools.long_running_tool import LongRunningFunctionTool

from config import settings
from utils.adk import blob_interceptor_callback
from utils.adk import sync_request_context
from .instructions import root_instruction
from .instructions.parameters import parameters_instruction
from .instructions.user_assets import user_assets_instruction
from .instructions.storyboard import storyboard_instruction
from .instructions.generation import generation_instruction
from .instructions.strategy import strategy_instruction
from .tools.user_assets import user_assets_tools
from .tools.generation import generation_tools, stitching_tools, summary_canvas_tool
from .tools.strategy import strategy_tools
from .tools.storyboard import (
    gate_tools,
    look_tools,
    production_tools,
    regenerate_tools,
    scene_edit_tools,
    storyboard_repair_tools,
)
from .utils.common import common_utils
from .utils.common.resumable_agent import ResumableLlmAgent
from .tools.parameters import campaign_edit_tools, parameters_tools

# A review is a conversation, so each gate loops until the reviewer accepts.
# Every pass suspends waiting for a human, so a loop cannot spin on its own;
# this is a backstop against a model that keeps re-gating without ever
# recording an acceptance. Exhausting it falls through, and the next stage
# refuses for want of an approval — stuck rather than expensive.
MAX_REVIEW_ROUNDS = 10


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
        logger.error(
            f"🚨🚨🚨 [ROUTING TRACE] ENTERING AGENT: {agent_name} at {datetime.utcnow().isoformat()} 🚨🚨🚨"
        )

    return debug_cb


from google.genai import types

parameters_agent = llm_agent.LlmAgent(
    name="parameters_agent",
    description="Agent that parses the user brief into ad campaign parameters.",
    model="gemini-3.7-flash",
    instruction=f"{parameters_instruction.AGENT_INSTRUCTION}\n\n{parameters_instruction.INSTRUCTION}",
    tools=[FunctionTool(parameters_tools.extract_campaign_parameters)],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_model_callback=instrument_agent("parameters_agent"),
    after_model_callback=debug_parameters_callback,
)

user_assets_agent = llm_agent.LlmAgent(
    name="user_assets_agent",
    description="Agent that ingests the user-provided assets.",
    model="gemini-3.7-flash",
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
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_model_callback=instrument_agent("storyboard_agent_creative"),
)

storyboard_agent_templated = llm_agent.LlmAgent(
    name="storyboard_agent_templated",
    description="Creates a storyboard following a strict template.",
    model="gemini-3.7-flash",
    instruction=storyboard_instruction.get_templated_instruction,
    tools=[
        FunctionTool(production_tools.recommend_production_recipe),
        FunctionTool(storyboard_repair_tools.finalize_and_persist_storyboard),
    ],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    before_model_callback=instrument_agent("storyboard_agent_templated"),
)

strategy_agent = llm_agent.LlmAgent(
    name="strategy_agent",
    description="Synchronizes campaign strategy and secures the state.",
    model="gemini-3.7-flash",
    instruction=strategy_instruction.INSTRUCTION,
    tools=[
        FunctionTool(strategy_tools.map_strategy_to_metadata),
        # The Look is a campaign-level decision, not a per-scene one: it is
        # injected into every scene, so it belongs with strategy. The storyboard
        # agents still list this tool, but by then the choice is cached and they
        # only read it back.
        FunctionTool(production_tools.recommend_production_recipe),
        # Let the Look be inspected and adjusted here, where it is decided.
        FunctionTool(look_tools.list_looks),
        FunctionTool(look_tools.set_look),
        FunctionTool(look_tools.list_look_options),
        FunctionTool(look_tools.edit_look_field),
        FunctionTool(look_tools.edit_character),
    ],
    before_model_callback=instrument_agent("strategy_agent"),
)

storyboard_router = llm_agent.LlmAgent(
    name="storyboard_router",
    description="Routes the campaign to the correct specialized storyboard generator and persists the output.",
    model="gemini-3.7-flash",
    instruction=storyboard_instruction.get_router_instruction,
    tools=[
        AgentTool(agent=storyboard_agent_creative),
        AgentTool(agent=storyboard_agent_templated),
    ],
    before_model_callback=instrument_agent("storyboard_router"),
)


frames_agent = llm_agent.LlmAgent(
    name="frames_agent",
    description="Renders the audio and every scene's first frame.",
    model="gemini-3.7-flash",
    instruction=(
        "Call `generate_scene_frames` once. It renders the narration, the "
        "music and every scene's opening frame, and stops before the videos. "
        "Say one short sentence about what was rendered. Do not call it twice "
        "and do not attempt any video work."
    ),
    tools=[FunctionTool(generation_tools.generate_scene_frames)],
    before_model_callback=instrument_agent("frames_agent"),
)

videos_agent = llm_agent.LlmAgent(
    name="videos_agent",
    description="Renders the scene videos and stitches the final cut.",
    model="gemini-3.7-flash",
    instruction=generation_instruction.INSTRUCTION,
    tools=[
        FunctionTool(generation_tools.generate_scene_videos),
        FunctionTool(stitching_tools.stitch_final_video),
        FunctionTool(summary_canvas_tool.create_campaign_summary),
        FunctionTool(generation_tools.regenerate_scene),
        FunctionTool(generation_tools.clear_scene_assets_for_regeneration),
    ],
    before_model_callback=instrument_agent("videos_agent"),
)

generation_agent = llm_agent.LlmAgent(
    name="generation_agent",
    description="Agent that generates all media and stitches them together.",
    model="gemini-3.7-flash",
    instruction=generation_instruction.INSTRUCTION,
    tools=[
        FunctionTool(generation_tools.generate_all_media),
        FunctionTool(stitching_tools.stitch_final_video),
        FunctionTool(summary_canvas_tool.create_campaign_summary),
        # Per-scene HITL: re-render one scene without touching the others.
        FunctionTool(generation_tools.regenerate_scene),
        FunctionTool(generation_tools.clear_scene_assets_for_regeneration),
    ],
    before_model_callback=instrument_agent("generation_agent"),
)

# Track 1: Traditional Planning (Text-based starting from brief)

STRATEGY_GATE_INSTRUCTION = """You are the campaign strategy checkpoint.

Change nothing before the reviewer has spoken. Your first act is to present
the strategy as it stands; `show_campaign_parameters` reads it without altering
it. The editing tools below exist to carry out what the reviewer asks for, not
to improve the plan on your own initiative - a reviewer shown a plan you have
already rewritten is not reviewing the work they were asked about.

Say one short sentence telling them what they are about to look at, then call
the tool. Calling it suspends the run immediately, so anything you plan to say
afterwards will not reach them until they have already replied.

Call `await_strategy_approval`. The run suspends there until a human responds.

When their response arrives, call `record_strategy_decision` with the decision
verbatim ("accept", "modify" or "regenerate") and any guidance they gave.

If the decision is "modify", make the changes they asked for:
- `edit_campaign_parameter` for the brief itself - audience, duration, tone,
  key message and so on. `show_campaign_parameters` lists what can be changed.
- `set_virtual_creator` to decide whether the ad features a person at all.
- `set_look`, `edit_look_field` and `edit_character` for the visual identity.
  `list_looks` and `list_look_options` show what is on offer.

Then call `await_strategy_approval` again, so they can see the result, and keep
going round until they accept.

This checkpoint is deliberately early: nothing has been written or rendered
yet, so a correction here is free, while the same correction after generation
costs a full re-render. Never assume an approval that was not given.
"""

strategy_gate_agent = llm_agent.LlmAgent(
    name="strategy_gate_agent",
    description="Pauses the pipeline for human review of the campaign strategy.",
    model="gemini-3.7-flash",
    instruction=STRATEGY_GATE_INSTRUCTION,
    tools=[
        LongRunningFunctionTool(func=gate_tools.await_strategy_approval),
        FunctionTool(gate_tools.record_strategy_decision),
        FunctionTool(campaign_edit_tools.show_campaign_parameters),
        FunctionTool(campaign_edit_tools.edit_campaign_parameter),
        FunctionTool(campaign_edit_tools.set_virtual_creator),
        FunctionTool(look_tools.list_looks),
        FunctionTool(look_tools.set_look),
        FunctionTool(look_tools.list_look_options),
        FunctionTool(look_tools.edit_look_field),
        FunctionTool(look_tools.edit_character),
    ],
    before_model_callback=instrument_agent("strategy_gate_agent"),
)

strategy_review_loop = loop_agent.LoopAgent(
    name="strategy_review_loop",
    description="Reviews the campaign strategy with a human until they accept it.",
    sub_agents=[strategy_gate_agent],
    max_iterations=MAX_REVIEW_ROUNDS,
)


def _planning_stages() -> list:
    """Planning stages, with the strategy checkpoint inserted when enabled.

    The gate sits after strategy and before the storyboard: late enough that
    there is a coherent plan to review, early enough that changing it costs
    nothing.
    """
    stages: list = [parameters_agent, user_assets_agent, strategy_agent]
    if settings.ENABLE_HITL_GATES:
        stages.append(strategy_review_loop)
    stages.append(storyboard_router)
    return stages


planning_agent_text = sequential_agent.SequentialAgent(
    name="planning_agent_text",
    description="Planning pipeline that parses a text brief into a storyboard.",
    sub_agents=_planning_stages(),
)


from mediagent_kit.services.creative_studio import get_cs_tools

GATE_INSTRUCTION = """You are the storyboard review checkpoint.

Before calling it, say one short sentence telling the reviewer what they are
about to look at. Calling the tool suspends the run immediately, so anything
you plan to say afterwards will not reach them until they have already replied.

Call `await_storyboard_approval`. The run suspends there until a human
responds; you will then see their response.

When it arrives, call `record_storyboard_decision` with the reviewer's decision
verbatim ("accept", "modify" or "regenerate") along with any guidance they gave.

If the decision is "modify", translate the reviewer's guidance into the
smallest set of edits that satisfies it, using `edit_scene`, `add_scene`,
`remove_scene` and `reorder_scenes`. Address scenes by their `scene_id`, and
change only what was asked for: every edited prompt discards media that has
already been rendered and paid for, so a needless edit is a needless re-render.

If they want a different visual Look, use `set_look` and then
`reapply_art_direction`, which restamps the new styling onto the existing
scenes. Say plainly that this re-renders every visual, because it does.

If the decision is "regenerate", they are rejecting the storyboard itself, not
asking for corrections — no amount of editing turns a wrong concept into a
right one. Call `regenerate_storyboard` with what they want different, then
immediately call `storyboard_agent_creative` to write the replacement. Never
leave the campaign without a storyboard. Use `regenerate_music` if it is only
the music they dislike.

Then call `await_storyboard_approval` again. Someone who asked for changes has
not seen the result yet, so the revised storyboard goes back to them, and round
it goes until they accept. Summarise what you changed each time.

Never assume an approval that was not given, and never call
`await_storyboard_approval` twice in a row without having changed something in
between. Media follows an "accept" and nothing else.
"""

storyboard_gate_agent = llm_agent.LlmAgent(
    name="storyboard_gate_agent",
    description="Pauses the pipeline for human review of the storyboard.",
    model="gemini-3.7-flash",
    instruction=GATE_INSTRUCTION,
    tools=[
        LongRunningFunctionTool(func=gate_tools.await_storyboard_approval),
        FunctionTool(gate_tools.record_storyboard_decision),
        # Editing tools, so a "modify" verdict can be acted on in place
        # rather than by regenerating the whole storyboard.
        FunctionTool(scene_edit_tools.edit_scene),
        FunctionTool(scene_edit_tools.add_scene),
        FunctionTool(scene_edit_tools.remove_scene),
        FunctionTool(scene_edit_tools.reorder_scenes),
        # A reviewer may want a different visual Look once they see the scenes.
        # Changing it does not reach scenes that already exist, so restamping
        # is offered alongside it.
        FunctionTool(look_tools.list_looks),
        FunctionTool(look_tools.set_look),
        FunctionTool(look_tools.reapply_art_direction),
        # "Regenerate" is a rejection, not a correction: discard and rewrite
        # rather than trying to edit a wrong concept into a right one.
        FunctionTool(regenerate_tools.regenerate_storyboard),
        FunctionTool(regenerate_tools.regenerate_music),
        AgentTool(agent=storyboard_agent_creative),
    ],
    before_model_callback=instrument_agent("storyboard_gate_agent"),
)

# Review is a conversation, not a single question: a reviewer who asks for a
# change has to see the result before approving it. The loop repeats
# review -> edit -> review and exits when record_storyboard_decision escalates
# on "accept".
#
storyboard_review_loop = loop_agent.LoopAgent(
    name="storyboard_review_loop",
    description="Reviews the storyboard with a human until they accept it.",
    sub_agents=[storyboard_gate_agent],
    max_iterations=MAX_REVIEW_ROUNDS,
)


FRAME_GATE_INSTRUCTION = """You are the first frame checkpoint.

Say one short sentence telling the reviewer what they are about to look at,
then call `await_frame_approval`. Calling it suspends the run, so anything you
plan to say afterwards will not reach them until they have replied.

When their response arrives, call `record_frame_decision` with the decision
verbatim ("accept", "modify" or "regenerate") and any guidance they gave.

If they want changes, redo only the frames they named. Use `regenerate_scene`
with that scene's `scene_id` and their direction, then call
`await_frame_approval` again so they can see the result. Keep going until they
accept.

Redo only the frames they named. Re-rendering a frame they did not mention
discards work they had already accepted.

Do not render any video from this agent. Video generation runs after this
checkpoint records an acceptance.
"""

frame_gate_agent = llm_agent.LlmAgent(
    name="frame_gate_agent",
    description="Pauses for human review of the rendered first frames.",
    model="gemini-3.7-flash",
    instruction=FRAME_GATE_INSTRUCTION,
    tools=[
        LongRunningFunctionTool(func=gate_tools.await_frame_approval),
        FunctionTool(gate_tools.record_frame_decision),
        FunctionTool(generation_tools.regenerate_scene),
    ],
    before_model_callback=instrument_agent("frame_gate_agent"),
)

frame_review_loop = loop_agent.LoopAgent(
    name="frame_review_loop",
    description="Reviews the rendered first frames with a human until they accept.",
    sub_agents=[frame_gate_agent],
    max_iterations=MAX_REVIEW_ROUNDS,
)


FINAL_CUT_GATE_INSTRUCTION = """You are the final cut checkpoint.

Before calling it, say one short sentence telling the reviewer what they are
about to watch. Calling the tool suspends the run immediately, so anything you
plan to say afterwards will not reach them until they have already replied.

Call `await_final_cut_approval`. The run suspends there until a human has
watched the video and responded.

When their response arrives, call `record_final_cut_decision` with the decision
verbatim ("accept", "modify" or "regenerate") and any guidance they gave.

If they want changes, re-render only the clips they called out, using
`regenerate_scene` with that scene's `scene_id` and their direction. Then call
`stitch_final_video` to rebuild the cut, and `await_final_cut_approval` again so
they can watch the new version. Keep going until they accept.

Re-render only what was called out. Every clip costs real money and minutes to
produce, and the ones they did not mention are ones they were happy with.

If the decision is "regenerate" and they are rejecting the whole video rather
than naming clips, call `regenerate_all_media` with their direction, then
`generate_all_media` and `stitch_final_video`. Reach for this only when they
really do mean all of it. If only the music is wrong, call
`regenerate_music` with their direction as the description, then
`stitch_final_video`. It renders the new track itself, so do not call
`generate_all_media` for music alone.
"""

final_cut_gate_agent = llm_agent.LlmAgent(
    name="final_cut_gate_agent",
    description="Pauses for human review of the finished video.",
    model="gemini-3.7-flash",
    instruction=FINAL_CUT_GATE_INSTRUCTION,
    tools=[
        LongRunningFunctionTool(func=gate_tools.await_final_cut_approval),
        FunctionTool(gate_tools.record_final_cut_decision),
        # Fix a clip, then rebuild the cut around it.
        FunctionTool(generation_tools.regenerate_scene),
        FunctionTool(stitching_tools.stitch_final_video),
        # For a wholesale rejection rather than a note about specific clips.
        FunctionTool(regenerate_tools.regenerate_all_media),
        FunctionTool(regenerate_tools.regenerate_music),
        FunctionTool(generation_tools.generate_all_media),
    ],
    before_model_callback=instrument_agent("final_cut_gate_agent"),
)

final_cut_review_loop = loop_agent.LoopAgent(
    name="final_cut_review_loop",
    description="Reviews the finished video with a human until they accept it.",
    sub_agents=[final_cut_gate_agent],
    max_iterations=MAX_REVIEW_ROUNDS,
)


def _build_pipeline_stages() -> list:
    """Pipeline stages, with the review gate inserted only when enabled.

    The gate suspends the run until a client answers it, so a frontend that
    cannot render the approval control would hang forever. It is therefore
    opt-in: with ENABLE_HITL_GATES off the pipeline is exactly what it was
    before gates existed, which is what the standalone Izumi app relies on.
    """
    stages: list = [planning_agent_text]
    if settings.ENABLE_HITL_GATES:
        stages.append(storyboard_review_loop)
        # Generation is split so the frames can be reviewed before the
        # videos anchored to them are rendered.
        stages.append(frames_agent)
        stages.append(frame_review_loop)
        stages.append(videos_agent)
    else:
        stages.append(generation_agent)
    if settings.ENABLE_HITL_GATES:
        # After stitching, not before: the fault a reviewer catches here is
        # usually one that only shows up in the assembled cut.
        stages.append(final_cut_review_loop)
    return stages


full_pipeline_agent = sequential_agent.SequentialAgent(
    name="full_pipeline_agent",
    description="Sequential agent for the Ads-X pipeline.",
    sub_agents=_build_pipeline_stages(),
    # Runs before any stage, on the first request and on every resume after a
    # review gate. That is the only hook the resumed request passes through
    # ahead of generation, so it is where the caller's credentials are put
    # back within reach of the Creative Studio services.
    before_agent_callback=sync_request_context,
)

# ResumableLlmAgent, not LlmAgent: a transferring root can only be resumed once
# in stock ADK, which would cap a run at a single review. See resumable_agent.
root_agent = ResumableLlmAgent(
    model="gemini-3.7-flash",
    name="ads_x_agent",
    instruction=root_instruction.get_instruction,
    tools=get_cs_tools(),
    sub_agents=[full_pipeline_agent],
    before_model_callback=blob_interceptor_callback,
)

# Exported so both entry points get identical wiring: ADK's AgentLoader prefers a
# module-level `app` over `root_agent`, and the Agent Engine deployment passes
# this same object to AdkApp.
#
# Resumability is enabled only alongside the gates. A long-running call cannot
# suspend a run unless the app is resumable, so the two must travel together;
# leaving it off otherwise keeps the standalone pipeline on exactly the code
# path it has always used.
app = App(
    name="ads_x",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=settings.ENABLE_HITL_GATES),
)
