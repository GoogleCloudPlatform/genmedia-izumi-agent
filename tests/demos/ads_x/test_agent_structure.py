from unittest.mock import patch

import pytest
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

# We need to ensure demos/backend is in PYTHONPATH when running this test.
# This is handled in the verification command.


def test_agent_definitions():
    """Verify that agents are defined with correct types and names."""
    # Import inside the test to allow PYTHONPATH to be set correctly
    from ads_x.agent import (
        parameters_agent,
        user_assets_agent,
        storyboard_agent_creative,
        storyboard_agent_templated,
        strategy_agent,
        storyboard_router,
        generation_agent,
        planning_agent_text,
        full_pipeline_agent,
        root_agent,
    )

    # Verify LlmAgents
    assert isinstance(parameters_agent, LlmAgent)
    assert parameters_agent.name == "parameters_agent"
    assert parameters_agent.model == "gemini-3.7-flash"

    assert isinstance(user_assets_agent, LlmAgent)
    assert user_assets_agent.name == "user_assets_agent"

    assert isinstance(storyboard_agent_creative, LlmAgent)
    assert storyboard_agent_creative.name == "storyboard_agent_creative"
    assert storyboard_agent_creative.model == "gemini-3.1-pro-preview"

    assert isinstance(storyboard_agent_templated, LlmAgent)
    assert storyboard_agent_templated.name == "storyboard_agent_templated"
    assert storyboard_agent_templated.model == "gemini-3.7-flash"

    assert isinstance(strategy_agent, LlmAgent)
    assert strategy_agent.name == "strategy_agent"

    assert isinstance(storyboard_router, LlmAgent)
    assert storyboard_router.name == "storyboard_router"

    assert isinstance(generation_agent, LlmAgent)
    assert generation_agent.name == "generation_agent"

    assert isinstance(root_agent, LlmAgent)
    assert root_agent.name == "ads_x_agent"

    # Verify SequentialAgents
    assert isinstance(planning_agent_text, SequentialAgent)
    assert planning_agent_text.name == "planning_agent_text"
    assert len(planning_agent_text.sub_agents) == 4

    assert isinstance(full_pipeline_agent, SequentialAgent)
    assert full_pipeline_agent.name == "full_pipeline_agent"
    assert len(full_pipeline_agent.sub_agents) == 2


def test_agent_tools():
    """Verify that agents have the expected tools."""
    from ads_x.agent import (
        parameters_agent,
        user_assets_agent,
        storyboard_agent_creative,
        generation_agent,
    )

    # Parameters Agent should have extract_campaign_parameters
    assert len(parameters_agent.tools) == 1
    # Tools are FunctionTool or AgentTool, we can check their names or functions if accessible
    # Assuming tools list has items we can check

    # User Assets Agent should have ingest_assets
    assert len(user_assets_agent.tools) == 1

    # Storyboard Agent Creative should have recommend_production_recipe and finalize_and_persist_storyboard
    assert len(storyboard_agent_creative.tools) == 2

    # Generation Agent: the batch pipeline plus the per-scene HITL entry points.
    assert {t.name for t in generation_agent.tools} == {
        "generate_all_media",
        "stitch_final_video",
        "create_campaign_summary",
        "regenerate_scene",
        "clear_scene_assets_for_regeneration",
    }


def test_pipeline_has_no_review_gate_by_default():
    """Standalone Izumi must be unaffected: a gate nobody answers hangs the run."""
    from ads_x.agent import _build_pipeline_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", False):
        stages = [a.name for a in _build_pipeline_stages()]

    assert stages == ["planning_agent_text", "generation_agent"]


def test_review_gate_is_inserted_before_generation_when_enabled():
    from ads_x.agent import _build_pipeline_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", True):
        stages = [a.name for a in _build_pipeline_stages()]

    assert stages == [
        "planning_agent_text",
        "storyboard_review_loop",
        "frames_agent",
        "frame_review_loop",
        "videos_agent",
        "final_cut_review_loop",
    ]
    # A checkpoint is worthless once the thing it guards has been paid for.
    assert stages.index("storyboard_review_loop") < stages.index("frames_agent")
    assert stages.index("frame_review_loop") < stages.index("videos_agent")


def test_review_is_a_bounded_loop_around_the_gate():
    """Review is a conversation: modify -> edit -> review again, until accept."""
    from ads_x.agent import storyboard_review_loop

    assert [a.name for a in storyboard_review_loop.sub_agents] == [
        "storyboard_gate_agent"
    ]
    # Each pass waits on a human, so this is a backstop against a model that
    # re-gates forever without ever recording an acceptance - not a throttle.
    assert storyboard_review_loop.max_iterations
    assert storyboard_review_loop.max_iterations <= 20


def test_planning_has_no_strategy_gate_by_default():
    from ads_x.agent import _planning_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", False):
        stages = [a.name for a in _planning_stages()]

    assert stages == [
        "parameters_agent",
        "user_assets_agent",
        "strategy_agent",
        "storyboard_router",
    ]


def test_strategy_gate_sits_between_strategy_and_the_storyboard():
    from ads_x.agent import _planning_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", True):
        stages = [a.name for a in _planning_stages()]

    # Late enough that there is a plan to review, early enough that changing
    # it costs nothing.
    assert stages.index("strategy_agent") < stages.index("strategy_review_loop")
    assert stages.index("strategy_review_loop") < stages.index("storyboard_router")


def test_both_review_loops_are_bounded():
    from ads_x.agent import storyboard_review_loop, strategy_review_loop

    for loop in (strategy_review_loop, storyboard_review_loop):
        assert loop.max_iterations and loop.max_iterations <= 20


def test_every_checkpoint_appears_in_order_when_enabled():
    from ads_x.agent import _build_pipeline_stages, _planning_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", True):
        planning = [a.name for a in _planning_stages()]
        pipeline = [a.name for a in _build_pipeline_stages()]

    # Each checkpoint sits where the correction it invites is still cheap.
    # Strategy is reviewed before a scene is written...
    assert planning.index("strategy_review_loop") < planning.index("storyboard_router")
    # ...the storyboard before anything is rendered...
    assert pipeline.index("storyboard_review_loop") < pipeline.index("frames_agent")
    # ...the frames once they exist but before the videos they anchor...
    assert pipeline.index("frames_agent") < pipeline.index("frame_review_loop")
    assert pipeline.index("frame_review_loop") < pipeline.index("videos_agent")
    # ...and the cut after it is assembled.
    assert pipeline.index("videos_agent") < pipeline.index("final_cut_review_loop")


def test_no_checkpoints_at_all_when_disabled():
    from ads_x.agent import _build_pipeline_stages, _planning_stages, settings

    with patch.object(settings, "ENABLE_HITL_GATES", False):
        names = [a.name for a in _planning_stages()] + [
            a.name for a in _build_pipeline_stages()
        ]

    assert not [n for n in names if "gate" in n or "review" in n]


def test_a_finished_campaign_can_be_revised_without_the_pipeline():
    """A change to a finished video must not rebuild it from the brief."""
    from ads_x.agent import _build_root_sub_agents, settings

    with patch.object(settings, "ENABLE_HITL_GATES", True):
        names = [a.name for a in _build_root_sub_agents()]
    with patch.object(settings, "ENABLE_HITL_GATES", False):
        names_without_gates = [a.name for a in _build_root_sub_agents()]

    assert names == ["full_pipeline_agent", "revision_loop"]
    # The revision loop ends on the final-cut checkpoint, which needs the gates.
    assert names_without_gates == ["full_pipeline_agent"]


def test_the_revision_loop_changes_only_what_is_named_then_asks_again():
    from ads_x.agent import revision_agent, revision_loop

    tools = {getattr(t, "name", None) or t.func.__name__ for t in revision_agent.tools}

    assert [a.name for a in revision_loop.sub_agents] == ["revision_agent"]
    assert {
        "regenerate_scene",
        "revise_voiceover",
        "regenerate_music",
        "stitch_final_video",
        "await_final_cut_approval",
        "record_final_cut_decision",
    } == tools
    # Nothing that rebuilds every scene or the storyboard.
    assert "generate_all_media" not in tools
    assert revision_loop.max_iterations


def test_narration_can_be_changed_at_the_final_cut():
    from ads_x.agent import final_cut_gate_agent

    tools = {
        getattr(t, "name", None) or t.func.__name__ for t in final_cut_gate_agent.tools
    }

    assert "revise_voiceover" in tools


def _root_instruction(state, gates):
    from types import SimpleNamespace
    from config import settings
    from ads_x.instructions import root_instruction

    ctx = SimpleNamespace(session=SimpleNamespace(state=state))
    with patch.object(settings, "ENABLE_HITL_GATES", gates):
        return root_instruction.get_instruction(ctx)


def test_the_root_sends_changes_to_a_finished_video_to_the_revision_loop():
    text = _root_instruction({"final_video_asset_id": "v-1"}, gates=True)

    assert "transfer to `revision_loop`" in text
    assert "This campaign HAS a finished video" in text


def test_the_root_knows_when_there_is_no_finished_video_yet():
    text = _root_instruction({}, gates=True)

    assert "This campaign does NOT have a finished video" in text


def test_no_revision_route_without_the_gates():
    assert "revision_loop" not in _root_instruction(
        {"final_video_asset_id": "v-1"}, gates=False
    )
