import pytest
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

# We need to ensure demos/backend is in PYTHONPATH when running this test.
# This is handled in the verification command.


def test_agent_definitions():
    """Verify that agents are defined with correct types and names."""
    # Import inside the test to allow PYTHONPATH to be set correctly
    from ads_x_template.agent import (
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
    assert parameters_agent.model == "gemini-2.5-flash"

    assert isinstance(user_assets_agent, LlmAgent)
    assert user_assets_agent.name == "user_assets_agent"

    assert isinstance(storyboard_agent_creative, LlmAgent)
    assert storyboard_agent_creative.name == "storyboard_agent_creative"
    assert storyboard_agent_creative.model == "gemini-3.1-pro-preview"

    assert isinstance(storyboard_agent_templated, LlmAgent)
    assert storyboard_agent_templated.name == "storyboard_agent_templated"
    assert storyboard_agent_templated.model == "gemini-3-flash-preview"

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
    from ads_x_template.agent import (
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

    # Generation Agent should have generate_all_media, stitch_final_video, create_campaign_summary
    assert len(generation_agent.tools) == 3
