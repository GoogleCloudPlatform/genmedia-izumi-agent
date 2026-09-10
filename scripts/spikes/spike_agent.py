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

"""Self-contained agent for the I0 resumability spike.

Mirrors the ads_x pipeline shape (Stage A -> Gate -> Stage C) but with no LLM,
no ads_x, and no mediagent_kit — so it deploys in a couple of minutes and costs
nothing to run. Its only job is to answer: does a long-running function call
pause and resume correctly on Agent Engine (VertexAiSessionService)?
"""

from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.genai import types

GATE_CALL_ID = "gate-call-001"
GATE_TOOL_NAME = "await_storyboard_approval"
APP_NAME = "hitl_resumability_spike"


class StageAgent(BaseAgent):
    """A trivial stage that announces it ran."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model", parts=[types.Part(text=f"RAN:{self.name}")]
            ),
        )


class GateAgent(BaseAgent):
    """Emits a long-running function call unless it has already been answered.

    The state-awareness matters: on resume ADK re-enters this sub-agent, so a
    gate that blindly re-emits its call would pause forever.
    """

    @staticmethod
    def _already_answered(ctx: InvocationContext) -> bool:
        for event in ctx.session.events:
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                fr = getattr(part, "function_response", None)
                if fr is not None and fr.id == GATE_CALL_ID:
                    return True
        return False

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if self._already_answered(ctx):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model", parts=[types.Part(text=f"RAN:{self.name}:resolved")]
                ),
            )
            return

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id=GATE_CALL_ID,
                            name=GATE_TOOL_NAME,
                            args={"storyboard_version": 1},
                        )
                    )
                ],
            ),
            long_running_tool_ids={GATE_CALL_ID},
        )


def build_app() -> App:
    """Stage A -> Gate -> Stage C, with resumability enabled."""
    pipeline = SequentialAgent(
        name="full_pipeline_agent",
        sub_agents=[
            StageAgent(name="stage_a_storyboard"),
            GateAgent(name="storyboard_gate"),
            StageAgent(name="stage_c_generation"),
        ],
    )
    return App(
        name=APP_NAME,
        root_agent=pipeline,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
