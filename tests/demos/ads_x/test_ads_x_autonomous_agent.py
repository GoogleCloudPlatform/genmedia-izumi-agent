import pytest
from google.adk.agents import llm_agent
from google.adk.tools import AgentTool, FunctionTool

def test_ads_x_agent_definitions():
    from ads_x.agent import (
        parameters_agent,
        storyboard_agent,
        root_agent,
    )

    # Verify Parameters Agent
    assert parameters_agent.name == "parameters_agent"
    assert "gemini" in parameters_agent.model
    assert len(parameters_agent.tools) == 0

    # Verify Storyboard Agent
    assert storyboard_agent.name == "storyboard_agent"
    assert "gemini" in storyboard_agent.model
    assert len(storyboard_agent.tools) == 0

    # Verify Root Agent
    assert root_agent.name == "ads_x_agent"
    assert len(root_agent.tools) == 5

    # Verify Root Agent Tools
    tool_names = [t.name if hasattr(t, 'name') else t.__class__.__name__ for t in root_agent.tools]
    assert "ingest_assets" in tool_names
    assert "parameters_agent" in tool_names
    assert "storyboard_agent" in tool_names
    assert "generate_all_media" in tool_names
    assert "stitch_final_video" in tool_names
