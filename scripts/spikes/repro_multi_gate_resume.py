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

"""Minimal repro: only the first resume works under a transferring root agent.

An invocation that suspends at two long-running gates can be resumed once. The
second resume returns zero events and the pipeline never finishes — silently,
with no error.

The trigger is the root being an LlmAgent that transfers into the pipeline.
Runner._setup_context_for_resumed_invocation short-circuits when the context's
agent is already in end_of_agents (runners.py:597-602), and after the first
resume the transferring root is marked finished.

Comment out the LlmAgent wrapper in build() and the same pipeline resumes twice
without trouble, which is what isolates the cause.

Run: uv run python scripts/spikes/repro_multi_gate_resume.py
"""

import asyncio
from typing import AsyncGenerator
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
import os, sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "demos/backend"
    ),
)
from google.adk.agents.llm_agent import LlmAgent
from ads_x.utils.common.resumable_agent import ResumableLlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

TRACE = []


class Stage(BaseAgent):
    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        TRACE.append(self.name)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model", parts=[types.Part(text=f"RAN:{self.name}")]
            ),
        )


class Gate(BaseAgent):
    call_id: str = ""

    def _answered(self, ctx):
        for e in ctx.session.events:
            for p in (e.content.parts if e.content else None) or []:
                fr = getattr(p, "function_response", None)
                if fr is not None and fr.id == self.call_id:
                    return True
        return False

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        if self._answered(ctx):
            TRACE.append(f"{self.name}:resolved")
            ev = Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model", parts=[types.Part(text=f"RAN:{self.name}:resolved")]
                ),
            )
            ev.actions.escalate = True  # end this gate's loop
            yield ev
            return
        TRACE.append(self.name)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id=self.call_id, name=f"await_{self.name}", args={}
                        )
                    )
                ],
            ),
            long_running_tool_ids={self.call_id},
        )


def build():
    a = Gate(name="gate_a")
    a.call_id = "call-a"
    b = Gate(name="gate_b")
    b.call_id = "call-b"
    # Mirror the real shape: gate A lives inside an inner sequence that
    # completes before gate B is reached at the outer level.
    planning = SequentialAgent(
        name="planning",
        sub_agents=[
            Stage(name="stage_1"),
            LoopAgent(name="loop_a", sub_agents=[a], max_iterations=5),
            Stage(name="stage_2"),
        ],
    )
    pipeline = SequentialAgent(
        name="pipeline",
        sub_agents=[
            planning,
            LoopAgent(name="loop_b", sub_agents=[b], max_iterations=5),
            Stage(name="stage_3"),
        ],
    )
    # The real system wraps the pipeline in an LlmAgent that transfers into it.
    root_cls = ResumableLlmAgent if os.environ.get("USE_FIX") else LlmAgent
    root = root_cls(
        model="gemini-3.5-flash",
        name="root_agent",
        instruction=("Immediately transfer to the `pipeline` agent. Say nothing else."),
        sub_agents=[pipeline],
    )
    return App(
        name="repro",
        root_agent=root,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )


def answer(cid, name):
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=cid, name=name, response={"decision": "accept"}
                )
            )
        ],
    )


async def main():
    r = Runner(app=build(), session_service=InMemorySessionService())
    s = await r.session_service.create_session(app_name="repro", user_id="u")

    async def turn(msg, label):
        n = 0
        async for _ in r.run_async(user_id="u", session_id=s.id, new_message=msg):
            n += 1
        print(f"  {label}: {n} events | trace={TRACE}")

    await turn(types.Content(role="user", parts=[types.Part(text="go")]), "start      ")
    await turn(answer("call-a", "await_gate_a"), "answer gate A")
    await turn(answer("call-b", "await_gate_b"), "answer gate B")
    print(f"\nreached stage_3? {'stage_3' in TRACE}")


asyncio.run(main())
