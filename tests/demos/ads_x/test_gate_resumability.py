"""Guards the HITL gate mechanism: a long-running tool must pause and resume.

M2's human-in-the-loop design depends on `ResumabilityConfig` being enabled on
the app. Without it the framework does NOT pause on a long-running function
call — it runs straight through into generation, silently, with no error. That
failure mode is expensive (minutes of video generation on an unapproved
storyboard) and invisible, so it is pinned down here.

These tests use trivial stand-in agents rather than the real ads_x pipeline: no
model calls, no cloud, no cost. They exercise the ADK machinery the gates rely
on. The same behaviour was verified end-to-end against a deployed Agent Engine
(see scripts/spikes/deploy_and_test_resumability.py).
"""

from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

APP_NAME = "gate_resumability_test"
USER_ID = "test-user"
GATE_CALL_ID = "gate-call-001"
GATE_TOOL_NAME = "await_storyboard_approval"


class _StageAgent(BaseAgent):
    """A stand-in pipeline stage that announces that it ran."""

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


class _GateAgent(BaseAgent):
    """Emits a long-running function call unless it was already answered.

    The state check is essential, not incidental: on resume ADK re-enters the
    sub-agent that paused, so a gate that blindly re-emits its call would gate
    itself forever. A real LlmAgent gets this for free by seeing the
    function_response in its context.
    """

    @staticmethod
    def _already_answered(ctx: InvocationContext) -> bool:
        for event in ctx.session.events:
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                response = getattr(part, "function_response", None)
                if response is not None and response.id == GATE_CALL_ID:
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


def _build_runner(*, resumable: bool) -> Runner:
    """Storyboard -> gate -> generation, mirroring the ads_x pipeline shape."""
    pipeline = SequentialAgent(
        name="full_pipeline_agent",
        sub_agents=[
            _StageAgent(name="stage_a_storyboard"),
            _GateAgent(name="storyboard_gate"),
            _StageAgent(name="stage_c_generation"),
        ],
    )
    app = App(
        name=APP_NAME,
        root_agent=pipeline,
        resumability_config=ResumabilityConfig(is_resumable=resumable),
    )
    return Runner(app=app, session_service=InMemorySessionService())


async def _drain(runner, session_id, message, invocation_id=None):
    """Runs one turn, returning (texts, invocation_id)."""
    texts, last_invocation = [], invocation_id
    kwargs = {"invocation_id": invocation_id} if invocation_id else {}
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message, **kwargs
    ):
        last_invocation = event.invocation_id or last_invocation
        for part in (event.content.parts if event.content else None) or []:
            if part.text:
                texts.append(part.text)
    return texts, last_invocation


def _user_text(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _gate_response() -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=GATE_CALL_ID,
                    name=GATE_TOOL_NAME,
                    response={"decision": "accept", "guidance": ""},
                )
            )
        ],
    )


async def test_gate_pauses_before_generation():
    runner = _build_runner(resumable=True)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    texts, _ = await _drain(runner, session.id, _user_text("make me an ad"))

    assert any("RAN:stage_a_storyboard" in t for t in texts)
    assert not any(
        "RAN:stage_c_generation" in t for t in texts
    ), "gate must halt the pipeline before the expensive generation stage"


async def test_gate_resumes_into_the_correct_stage():
    runner = _build_runner(resumable=True)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    _, invocation_id = await _drain(runner, session.id, _user_text("make me an ad"))
    resumed, _ = await _drain(
        runner, session.id, _gate_response(), invocation_id=invocation_id
    )

    assert any(
        "RAN:stage_c_generation" in t for t in resumed
    ), "approving the gate must let the pipeline continue"
    assert not any(
        "RAN:stage_a_storyboard" in t for t in resumed
    ), "resume must not replay completed stages (that would re-render assets)"


async def test_without_resumability_the_gate_is_a_no_op():
    """The control: this is what silently breaks HITL if the config is dropped."""
    runner = _build_runner(resumable=False)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    texts, _ = await _drain(runner, session.id, _user_text("make me an ad"))

    assert any(
        "RAN:stage_c_generation" in t for t in texts
    ), "documents the failure mode: no ResumabilityConfig means no pause at all"
