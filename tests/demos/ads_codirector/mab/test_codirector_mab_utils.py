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

"""Unit tests for MAB utility functions and agents."""

from typing import AsyncGenerator, Any
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.mab import utils as mab_utils
from ads_codirector.utils import common_utils
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.readonly_context import ReadonlyContext


class MockInvocationContext:
    """A minimal mock for InvocationContext that satisfies ADK requirements."""

    def __init__(self):
        self.agent_name = "test_agent"
        self.session = MagicMock()
        self.session.state = {}
        self.session.app_name = "test_app"
        self.session.user_id = "test_user"
        self.session.id = "test_session"
        self.plugin_manager = MagicMock()
        self.plugin_manager.run_before_agent_callback = AsyncMock(return_value=None)
        self.plugin_manager.run_after_agent_callback = AsyncMock(return_value=None)
        self.end_invocation = False

    def model_copy(self, update=None):
        if update:
            for k, v in update.items():
                setattr(self, k, v)
        return self


@pytest.fixture(name="mock_invocation_ctx")
def fixture_mock_invocation_ctx():
    return MockInvocationContext()


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext for testing."""
    context = MagicMock()
    context.state = {
        common_utils.USER_INPUT_KEY: "Test prompt",
        common_utils.STRUCTURED_USER_INPUT_KEY: {"brand": "TestBrand"},
        common_utils.USER_ASSETS_KEY: {},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }
    return context


@pytest.mark.asyncio
@patch("ads_codirector.mab.utils.save_mab_state", new_callable=AsyncMock)
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("ads_codirector.mab.utils.get_mab_config")
async def test_initialize_mab_experiment(
    mock_config, _mock_user, _mock_save, mock_tool_context
):
    """Verify experiment initialization and ID generation."""
    mock_config.return_value = {"mab": {"warm_up": False}}
    result = await mab_utils.initialize_mab_experiment(mock_tool_context)
    assert "MAB experiment initialized" in result
    assert common_utils.MAB_EXPERIMENT_ID_KEY in mock_tool_context.state
    assert mock_tool_context.state["mab_iteration"] == -1


def test_prepare_iteration_state(mock_tool_context):
    """Verify that state is scrubbed between iterations."""
    mock_tool_context.state = {
        "mab_iteration": 0,
        common_utils.STORYLINE_KEY: {"old": "data"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "00_logo.png": "Logo",
            "iter_0_character_collage.png": "Old collage",
        },
    }
    mab_utils.prepare_iteration_state(mock_tool_context)
    assert mock_tool_context.state["mab_iteration"] == 1
    assert mock_tool_context.state[common_utils.STORYLINE_KEY] == {}
    annotated = mock_tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY]
    assert "00_logo.png" in annotated
    assert "iter_0_character_collage.png" not in annotated


@pytest.mark.asyncio
async def test_asset_inventory_preparer(mock_invocation_ctx):
    """Verify that the inventory string is correctly formatted for the Storyboard agent."""
    preparer = mab_utils.AssetInventoryPreparer(name="test_preparer")
    mock_invocation_ctx.session.state = {
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "prod.png": {"semantic_role": "product"},
            "logo.jpg": {"semantic_role": "logo"},
            "plain.webp": "Just a caption",
        }
    }
    events = []
    async for event in preparer.run_async(mock_invocation_ctx):
        events.append(event)
    assert len(events) > 0
    inventory_str = mock_invocation_ctx.session.state.get(
        "temp:asset_inventory_list", ""
    )
    assert "- prod.png (Role: product)" in inventory_str
    assert "- logo.jpg (Role: logo)" in inventory_str
    assert "- plain.webp (Role: unknown)" in inventory_str


@pytest.mark.asyncio
async def test_storyboard_instruction_resolution():
    """Verify that storyboard instruction placeholders are resolved."""
    mock_invocation_ctx_raw = MagicMock()
    mock_invocation_ctx_raw.session.state = {
        "temp:asset_inventory_list": "- product_01.png (Role: product)",
        common_utils.STORYLINE_KEY: "Scene 1: Action",
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
        common_utils.CREATIVE_CONFIG_KEY: {},
        common_utils.CREATIVE_DIRECTION_KEY: {},
        common_utils.MAB_ITERATION_KEY: 0,
    }
    mock_invocation_ctx_raw.session.app_name = "test_app"
    mock_invocation_ctx_raw.session.user_id = "test_user"
    mock_invocation_ctx_raw.session.id = "test_session"
    ctx = ReadonlyContext(mock_invocation_ctx_raw)
    instruction = mab_utils.get_storyboard_instruction_with_mab(ctx)
    if hasattr(instruction, "__await__"):
        instruction = await instruction
    assert "{temp:asset_inventory_list}" not in instruction
    assert "- product_01.png (Role: product)" in instruction


@pytest.mark.asyncio
async def test_storyline_loop_instruction_resolution(mock_invocation_ctx):
    """Verify that storyline loop agent resolves placeholders in stored templates."""
    mock_invocation_ctx.session.state = {
        "creative_brief": "A great campaign",
        "annotated_reference_visuals": "Rustic lock",
        "creative_configuration": {},
        "creative_direction": {"storyline_instruction": "Instruction text"},
    }
    selector = mab_utils.StorylineLoopInstructionSelector(name="test_selector")
    async for _ in selector.run_async(mock_invocation_ctx):
        pass
    stored_instruction = mock_invocation_ctx.session.state.get(
        "temp:storyline_instruction"
    )
    assert stored_instruction is not None
    assert "{creative_brief}" not in stored_instruction
    assert "A great campaign" in stored_instruction


class MockAgent(BaseAgent):
    """Simple agent for testing that yields a predefined list of events."""

    event_to_yield: Any = None

    async def _run_async_impl(
        self, parent_context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield self.event_to_yield

    async def _run_live_impl(
        self, parent_context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield self.event_to_yield


@pytest.mark.asyncio
async def test_escalation_shielding(mock_invocation_ctx):
    """Verify that escalation is cleared for parent but preserved for child."""
    orig_event = Event(author="test_agent", actions=EventActions(escalate=True))
    sub_agent = MockAgent(name="sub_agent", event_to_yield=orig_event)
    filter_agent = mab_utils.LocalEscalationFilter(
        name="test_filter", sub_agents=[sub_agent]
    )
    results = []
    async for event in filter_agent.run_async(mock_invocation_ctx):
        results.append(event)
    assert len(results) == 1
    assert results[0].actions.escalate is False
    assert orig_event.actions.escalate is True
    assert results[0] is not orig_event


@pytest.mark.asyncio
async def test_normal_event_passthrough(mock_invocation_ctx):
    """Verify that normal events are passed through without modification."""
    normal_event = Event(author="test_agent", actions=EventActions(escalate=False))
    sub_agent = MockAgent(name="sub_agent", event_to_yield=normal_event)
    filter_agent = mab_utils.LocalEscalationFilter(
        name="test_filter", sub_agents=[sub_agent]
    )
    results = []
    async for event in filter_agent.run_async(mock_invocation_ctx):
        results.append(event)
    assert len(results) == 1
    assert results[0].author == "test_agent"
    assert results[0].actions.escalate is False
    assert results[0] is normal_event
