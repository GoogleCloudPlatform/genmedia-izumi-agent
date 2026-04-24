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

"""Unit test for agent structure and definitions."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.loop_agent import LoopAgent


def test_llm_agent_definitions():
    """Verify that LLM agents are defined with correct types and names."""
    from ads_codirector.agent import (
        parameters_agent,
        user_assets_agent,
        creative_brief_agent,
        storyline_executor_agent,
        storyline_evaluator_agent,
        visual_casting_agent,
        storyboard_agent,
        voiceover_script_agent,
        storyboard_verifier_agent,
        keyframe_agent,
        video_agent,
        audio_agent,
        post_production_agent,
        final_video_verifier_agent,
        mab_logging_agent,
        mab_selection_agent,
        theoretical_definitions_agent,
        creative_director_agent,
        mab_report_agent,
        mab_initialization_agent,
        root_agent,
    )

    agents = [
        (parameters_agent, "parameters_agent"),
        (user_assets_agent, "user_assets_agent"),
        (creative_brief_agent, "creative_brief_agent"),
        (storyline_executor_agent, "storyline_executor_agent"),
        (storyline_evaluator_agent, "storyline_evaluator_agent"),
        (visual_casting_agent, "visual_casting_agent"),
        (storyboard_agent, "storyboard_agent"),
        (voiceover_script_agent, "voiceover_script_agent"),
        (storyboard_verifier_agent, "storyboard_verifier_agent"),
        (keyframe_agent, "keyframe_agent"),
        (video_agent, "video_agent"),
        (audio_agent, "audio_agent"),
        (post_production_agent, "post_production_agent"),
        (final_video_verifier_agent, "final_video_verifier_agent"),
        (mab_logging_agent, "mab_logging_agent"),
        (mab_selection_agent, "mab_selection_agent"),
        (theoretical_definitions_agent, "theoretical_definitions_agent"),
        (creative_director_agent, "creative_director_agent"),
        (mab_report_agent, "mab_report_agent"),
        (mab_initialization_agent, "mab_initialization_agent"),
        (root_agent, "orchestrator_agent"),
    ]

    for agent, name in agents:
        assert isinstance(agent, LlmAgent)
        assert agent.name == name


def test_sequential_agent_definitions():
    """Verify that sequential agents are defined with correct types and names."""
    from ads_codirector.agent import (
        pre_production_agent,
        production_agent,
        iteration_agent,
    )

    assert isinstance(pre_production_agent, SequentialAgent)
    assert pre_production_agent.name == "pre_production_agent"
    assert len(pre_production_agent.sub_agents) == 10

    assert isinstance(production_agent, SequentialAgent)
    assert production_agent.name == "production_agent"
    assert len(production_agent.sub_agents) == 3

    assert isinstance(iteration_agent, SequentialAgent)
    assert iteration_agent.name == "iteration_agent"
    assert len(iteration_agent.sub_agents) == 11


def test_loop_agent_definitions():
    """Verify that loop agents are defined with correct types and names."""
    from ads_codirector.agent import mab_loop_agent

    assert isinstance(mab_loop_agent, LoopAgent)
    assert mab_loop_agent.name == "mab_loop_agent"
