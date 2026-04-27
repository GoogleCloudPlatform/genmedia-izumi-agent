# Copyright 2026 Google LLC
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

"""
Unit tests for MAB and local refinement iteration logic.
"""

import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from ads_codirector.mab import utils as mab_utils
from ads_codirector.tools import generation_tools
from ads_codirector.utils import common_utils
from ads_codirector.utils.mab_model import MabExperimentState, ArmsSelected
from mediagent_kit.services.types import Asset
from google.adk.events import Event, EventActions


class MockInvocationContext:
    """A mock that satisfies ADK's model_copy and execution requirements."""

    def __init__(self, user_id="test_user"):
        self.session = MagicMock()
        self.session.state = {}
        self.session.user_id = user_id
        self.session.app_name = "test_app"
        self.session.session_id = "test_session"
        self.session.id = "test_session"
        self.name = "test_checker"
        self.agent_name = "test_agent"
        self.end_invocation = False
        self.plugin_manager = MagicMock()
        self.plugin_manager.run_before_agent_callback = AsyncMock(return_value=None)
        self.plugin_manager.run_after_agent_callback = AsyncMock(return_value=None)

    def model_copy(self, update=None):
        new_obj = MockInvocationContext(user_id=self.session.user_id)
        new_obj.session = self.session
        new_obj.end_invocation = self.end_invocation
        if update:
            for k, v in update.items():
                setattr(new_obj, k, v)
        return new_obj


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a mock ToolContext for utility functions."""
    context = MagicMock()
    context.state = {
        common_utils.USER_INPUT_KEY: "test",
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
        "mab_iteration": 0,
    }
    context._invocation_context.session.user_id = "test_user"
    return context


@pytest.fixture(name="mock_ctx")
def fixture_mock_ctx():
    return MockInvocationContext()


# --- 1. MAB Iteration Tests ---


def test_prepare_iteration_state_restart_behavior(mock_tool_context):
    """Verify that restarting an iteration clears state but does NOT increment the counter."""
    mock_tool_context.state["mab_iteration"] = 0
    mock_tool_context.state["mab_iteration_ready"] = True
    mock_tool_context.state[common_utils.REFINEMENT_HISTORY_KEY] = [{"old": "data"}]

    # Call with ready=True: should NOT increment, but SHOULD clear history
    mab_utils.prepare_iteration_state(mock_tool_context)

    assert mock_tool_context.state["mab_iteration"] == 0
    assert mock_tool_context.state[common_utils.REFINEMENT_HISTORY_KEY] == []
    assert mock_tool_context.state["mab_iteration_ready"] is True


def test_prepare_iteration_state_next_behavior(mock_tool_context):
    """Verify that starting a NEW iteration increments the counter and clears state."""
    mock_tool_context.state["mab_iteration"] = 0
    mock_tool_context.state["mab_iteration_ready"] = False
    mock_tool_context.state[common_utils.REFINEMENT_HISTORY_KEY] = [{"old": "data"}]

    # Call with ready=False: should increment and clear history
    mab_utils.prepare_iteration_state(mock_tool_context)

    assert mock_tool_context.state["mab_iteration"] == 1
    assert mock_tool_context.state[common_utils.REFINEMENT_HISTORY_KEY] == []
    assert mock_tool_context.state["mab_iteration_ready"] is True


@pytest.mark.asyncio
@patch("ads_codirector.mab.utils.save_mab_state", new_callable=AsyncMock)
@patch("ads_codirector.mab.utils.load_mab_state", new_callable=AsyncMock)
@patch("ads_codirector.mab.utils.get_mab_config")
@patch("ads_codirector.utils.common_utils.get_user_id", return_value="test_user")
async def test_mab_ready_flag_reset(
    _mock_user, _mock_config, _mock_load, _mock_save, mock_tool_context
):
    """Verify that the ready flag is reset after an iteration is logged."""
    mock_tool_context.state["mab_iteration_ready"] = True
    mock_tool_context.state[common_utils.MAB_EXPERIMENT_ID_KEY] = "test_exp"

    mab_state = MabExperimentState(
        experiment_id="test_exp",
        user_prompt="test",
        structured_constraints={},
        user_assets={},
        arm_stats={},
        iterations=[],
    )
    _mock_load.return_value = (mab_state, None)

    with patch("mediagent_kit.services.aio.get_asset_service") as mock_asset_service:
        await mab_utils.log_mab_iteration_results(mock_tool_context)

    assert mock_tool_context.state["mab_iteration_ready"] is False


# --- 2. Storyline Iteration Tests ---


@pytest.mark.asyncio
@patch("ads_codirector.mab.utils.get_mab_config")
@patch("ads_codirector.utils.common_utils.get_user_id", return_value="test_user")
async def test_storyline_refinement_termination(_mock_user, mock_config, mock_ctx):
    """Verify that storyline refinement stops at exactly max_attempts."""
    mock_config.return_value = {
        "self_refinement": {"storyline": {"max_attempts": 2, "score_threshold": 80}}
    }

    mock_ctx.session.state = {
        common_utils.REFINEMENT_HISTORY_KEY: [],
        common_utils.STORYLINE_KEY: {"scenes": []},
        "storyline_evaluation": {"score": 75},
    }

    checker = mab_utils.StorylineRefinementChecker(name="checker")

    # Attempt 1
    events = []
    async for event in checker.run_async(mock_ctx):
        events.append(event)
    assert not events[-1].actions.escalate
    assert len(mock_ctx.session.state[common_utils.REFINEMENT_HISTORY_KEY]) == 1

    # Attempt 2
    mock_ctx.session.state["storyline_evaluation"]["score"] = 77
    async for event in checker.run_async(mock_ctx):
        events.append(event)
    assert events[-1].actions.escalate is True
    assert len(mock_ctx.session.state[common_utils.REFINEMENT_HISTORY_KEY]) == 2
    assert mock_ctx.session.state["temp:storyline_done"] is True


# --- 3. Keyframe Iteration Tests ---


@pytest.mark.asyncio
@patch(
    "ads_codirector.tools.generation_tools._generate_single_keyframe",
    new_callable=AsyncMock,
)
@patch(
    "ads_codirector.tools.generation_tools._verify_keyframes_jointly",
    new_callable=AsyncMock,
)
@patch("ads_codirector.mab.utils.get_mab_config")
@patch("ads_codirector.utils.common_utils.get_user_id", return_value="test_user")
async def test_keyframe_refinement_loop(
    _mock_user, mock_config, mock_verify, mock_gen, mock_tool_context
):
    """Verify that keyframe refinement loop respects thresholds and problematic scene flags."""
    mock_config.return_value = {
        "self_refinement": {"keyframe": {"max_attempts": 3, "score_threshold": 85}}
    }
    generation_tools.MAX_REFINEMENT_ATTEMPTS = 3
    generation_tools.KEYFRAME_PASS_THRESHOLD = 85

    mock_tool_context.state[common_utils.STORYBOARD_KEY] = {
        "scenes": [{"first_frame_prompt": {}}, {"first_frame_prompt": {}}]
    }

    real_asset = Asset(
        id="asset_id",
        user_id="test_user",
        file_name="file.png",
        mime_type="image/png",
        current_version=1,
        versions=[],
    )
    mock_gen.return_value = real_asset

    mock_verify.side_effect = [
        {"score": 70, "problematic_scenes": [1], "feedback": "fix 1"},
        {"score": 90, "problematic_scenes": [], "feedback": "perfect"},
    ]

    with patch("utils.adk.display_asset", new_callable=AsyncMock):
        await generation_tools.produce_refined_keyframes(mock_tool_context)

    assert mock_verify.call_count == 2
    assert mock_gen.call_count == 3


@pytest.mark.asyncio
@patch(
    "ads_codirector.tools.generation_tools._generate_single_keyframe",
    new_callable=AsyncMock,
)
@patch(
    "ads_codirector.tools.generation_tools._verify_keyframes_jointly",
    new_callable=AsyncMock,
)
@patch("ads_codirector.mab.utils.get_mab_config")
@patch("ads_codirector.utils.common_utils.get_user_id", return_value="test_user")
async def test_keyframe_best_of_n_selection(
    _mock_user, mock_config, mock_verify, mock_gen, mock_tool_context
):
    """Verify that the system selects the highest scoring sequence even if a regression occurs."""
    mock_config.return_value = {
        "self_refinement": {"keyframe": {"max_attempts": 2, "score_threshold": 90}}
    }
    generation_tools.MAX_REFINEMENT_ATTEMPTS = 2
    generation_tools.KEYFRAME_PASS_THRESHOLD = 90

    mock_tool_context.state[common_utils.STORYBOARD_KEY] = {
        "scenes": [{"first_frame_prompt": {}}]
    }

    asset_cycle_0 = Asset(
        id="cycle_0_id",
        user_id="u",
        file_name="c0.png",
        mime_type="i",
        current_version=1,
        versions=[],
    )
    asset_cycle_1 = Asset(
        id="cycle_1_id",
        user_id="u",
        file_name="c1.png",
        mime_type="i",
        current_version=1,
        versions=[],
    )

    # Cycle 0: 80, Cycle 1: 50 (Regression)
    mock_gen.side_effect = [asset_cycle_0, asset_cycle_1]
    mock_verify.side_effect = [
        {"score": 80, "problematic_scenes": [0], "feedback": "good but fix"},
        {"score": 50, "problematic_scenes": [0], "feedback": "worse"},
    ]

    with patch("utils.adk.display_asset", new_callable=AsyncMock):
        await generation_tools.produce_refined_keyframes(mock_tool_context)

    # Verify that the final storyboard uses the CYCLE 0 asset (the champion)
    storyboard = mock_tool_context.state[common_utils.STORYBOARD_KEY]
    assert storyboard["scenes"][0]["first_frame_prompt"]["asset_id"] == "cycle_0_id"

    # Check history flags
    history = storyboard["scenes"][0]["first_frame_generation_history"]
    assert history[0]["is_champion"] is True
    assert history[1]["is_champion"] is False


# --- 4. User ID Extraction Tests ---


def test_get_user_id_robustness():
    """Verify that get_user_id can extract ID from various context structures."""
    # Case 1: Direct user_id
    ctx1 = MagicMock()
    ctx1.user_id = "user1"
    assert common_utils.get_user_id(ctx1) == "user1"

    # Case 2: Nested in session
    ctx2 = MagicMock()
    del ctx2.user_id
    ctx2.session.user_id = "user2"
    assert common_utils.get_user_id(ctx2) == "user2"

    # Case 3: Fallback
    ctx3 = object()
    assert common_utils.get_user_id(ctx3) == "default_user_agent_engine"
