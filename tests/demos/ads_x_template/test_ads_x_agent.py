import pytest
from google.adk.agents import llm_agent, sequential_agent

def test_ads_x_agent_definitions():
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

    # Verify Parameters Agent
    assert parameters_agent.name == "parameters_agent"
    assert "gemini" in parameters_agent.model
    assert len(parameters_agent.tools) == 1

    # Verify User Assets Agent
    assert user_assets_agent.name == "user_assets_agent"
    assert len(user_assets_agent.tools) == 1

    # Verify Storyboard Creative Agent
    assert storyboard_agent_creative.name == "storyboard_agent_creative"
    assert len(storyboard_agent_creative.tools) == 2

    # Verify Storyboard Templated Agent
    assert storyboard_agent_templated.name == "storyboard_agent_templated"
    assert len(storyboard_agent_templated.tools) == 2

    # Verify Strategy Agent
    assert strategy_agent.name == "strategy_agent"
    assert len(strategy_agent.tools) == 1

    # Verify Storyboard Router
    from google.adk.tools import AgentTool
    assert isinstance(storyboard_router.tools[0], AgentTool)

    # Verify Generation Agent
    assert generation_agent.name == "generation_agent"
    assert len(generation_agent.tools) == 3

    # Verify Planning Sequential Agent
    assert planning_agent_text.name == "planning_agent_text"
    assert len(planning_agent_text.sub_agents) == 4

    # Verify Full Pipeline Agent
    assert full_pipeline_agent.name == "full_pipeline_agent"
    assert len(full_pipeline_agent.sub_agents) == 2

    # Verify Root Agent
    assert root_agent.name == "ads_x_agent"
    assert len(root_agent.sub_agents) == 1
