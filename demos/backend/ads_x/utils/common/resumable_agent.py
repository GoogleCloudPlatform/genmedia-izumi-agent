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

"""Workaround for an ADK bug that limits a run to one human review.

An `LlmAgent` that transfers into a sub-agent can only be resumed **once**. On
the second resume the run returns no events at all — no error, no output, the
pipeline simply stops. With three review checkpoints in one run, that means only
the first one can ever be answered.

The cause is in `LlmAgent._run_async_impl`. Its resume branch runs the
transferred sub-agent and then marks itself finished unconditionally:

    if agent_state is not None and (
        agent_to_transfer := self._get_subagent_to_resume(ctx)
    ):
      async with Aclosing(agent_to_transfer.run_async(ctx)) as agen:
        async for event in agen:
          yield event

      ctx.set_agent_state(self.name, end_of_agent=True)   # <-- even if paused
      yield self._create_agent_state_event(ctx)
      return

If the sub-agent suspended again at another gate, the agent has *not* finished,
but it says it has. `Runner._setup_context_for_resumed_invocation` then sees the
root in `end_of_agents` and returns immediately, so every later resume is a
silent no-op. The non-resume path a few lines below gets this right — it checks
`should_pause` and skips the marking — so the omission looks accidental.

Verified present in the pinned 1.29.0 and unchanged in 1.37.0 and 2.6.2, so
upgrading does not help. `scripts/spikes/repro_multi_gate_resume.py` reproduces
it in isolation.

This subclass restores the missing check. It is a copy of ADK's method with one
guard added, so it must be revisited on an ADK upgrade — `test_resumable_agent`
fails loudly if upstream changes shape. Delete it once ADK ships the fix.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.events.event import Event
from google.adk.utils.context_utils import Aclosing
from typing_extensions import override

logger = logging.getLogger(__name__)


class ResumableLlmAgent(LlmAgent):
    """An `LlmAgent` that can be resumed more than once per invocation.

    Behaves exactly like `LlmAgent` except that, when resuming a transferred
    sub-agent which suspends again, it does not claim to have finished.
    """

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        agent_state = self._load_agent_state(ctx, BaseAgentState)

        if agent_state is not None and (
            agent_to_transfer := self._get_subagent_to_resume(ctx)
        ):
            paused_again = False
            async with Aclosing(agent_to_transfer.run_async(ctx)) as agen:
                async for event in agen:
                    yield event
                    if ctx.should_pause_invocation(event):
                        paused_again = True

            if paused_again:
                # The sub-agent stopped at another gate, so this agent is not
                # finished. Saying otherwise makes every later resume a no-op.
                logger.debug(
                    "%s: transferred agent paused again; staying resumable.",
                    self.name,
                )
                return

            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)
            return

        # Unchanged from ADK below this point.
        should_pause = False
        async with Aclosing(self._llm_flow.run_async(ctx)) as agen:
            async for event in agen:
                self._LlmAgent__maybe_save_output_to_state(event)  # noqa: SLF001
                yield event
                if ctx.should_pause_invocation(event):
                    should_pause = True
        if should_pause:
            return

        if ctx.is_resumable:
            events = ctx._get_events(  # pylint: disable=protected-access
                current_invocation=True, current_branch=True
            )
            if events and any(ctx.should_pause_invocation(e) for e in events[-2:]):
                return
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)
