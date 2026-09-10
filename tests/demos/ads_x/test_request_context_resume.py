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

"""Guards the credentials a resumed run needs to reach Creative Studio.

Creative Studio services read the user's token from a contextvar. A contextvar
belongs to the request that set it, and a run with review gates spans several:
it suspends at the gate and the reviewer answers later on a new request. The
work that resumes on that request is generation, which is exactly the part that
calls Creative Studio, so losing the token there fails the expensive half of
the run while the cheap half looked fine.

The pipeline therefore republishes credentials from session state - which does
survive the boundary - on every entry. These tests pin that down, including the
ADK behaviour it depends on: that the pipeline's `before_agent_callback` really
does fire again on a resumed request.
"""

from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from mediagent_kit.utils.context import get_request_context, request_context_var
from utils.adk import resolve_user_auth_token, sync_request_context

APP_NAME = "request_context_resume_test"
USER_ID = "test-user"
GATE_CALL_ID = "gate-call-001"
GATE_TOOL_NAME = "await_storyboard_approval"


# Isolation from the rest of the suite comes from the autouse
# reset_request_context fixture in tests/conftest.py.


# --------------------------------------------------------------------------
# sync_request_context
# --------------------------------------------------------------------------


def _ctx(state):
    return SimpleNamespace(state=state)


def test_credentials_are_published_from_session_state():
    sync_request_context(_ctx({"user_auth_token": "jwt-abc", "workspace_id": "42"}))

    context = get_request_context()
    assert context is not None
    assert context["user_auth_token"] == "jwt-abc"
    assert context["workspace_id"] == "42"


def test_the_token_key_is_configurable():
    # Creative Studio names the state key, and it is not always the default.
    with patch.dict(
        "os.environ", {"CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY": "cs_auth_1234"}
    ):
        sync_request_context(_ctx({"cs_auth_1234": "jwt-xyz", "workspace_id": "7"}))

    context = get_request_context()
    assert context is not None
    assert context["user_auth_token"] == "jwt-xyz"


def test_a_run_without_a_token_still_publishes_its_workspace():
    # The native path has no user token at all, and must not be broken by an
    # attempt to find one.
    sync_request_context(_ctx({"workspace_id": "42"}))

    context = get_request_context()
    assert context is not None
    assert context["user_auth_token"] is None
    assert context["workspace_id"] == "42"


def test_an_empty_context_is_left_alone():
    sync_request_context(_ctx({}))
    sync_request_context(SimpleNamespace(state=None))

    assert get_request_context() is None


def test_it_returns_nothing_so_it_can_gate_an_agent():
    # A before_agent_callback that returns content replaces the agent's own
    # output; this one must let every stage run.
    assert sync_request_context(_ctx({"workspace_id": "42"})) is None


# --------------------------------------------------------------------------
# resolve_user_auth_token
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stored",
    ["jwt-abc", "Bearer jwt-abc", "bearer jwt-abc", "  Bearer jwt-abc  "],
)
def test_the_scheme_is_stripped_from_a_stored_token(stored):
    """The scheme belongs to the header, not to the credential.

    How the token reaches session state varies by frontend, and one that
    stored it with the scheme attached produced "Bearer Bearer <jwt>" once the
    header was built around it.
    """
    assert resolve_user_auth_token({"user_auth_token": stored}) == "jwt-abc"


def test_the_configured_key_is_preferred_over_the_default():
    state = {"cs_auth_1234": "jwt-configured", "user_auth_token": "jwt-default"}

    with patch.dict(
        "os.environ", {"CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY": "cs_auth_1234"}
    ):
        assert resolve_user_auth_token(state) == "jwt-configured"


def test_the_default_key_still_answers_when_the_configured_one_is_absent():
    with patch.dict(
        "os.environ", {"CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY": "cs_auth_1234"}
    ):
        assert resolve_user_auth_token({"user_auth_token": "jwt-default"}) == (
            "jwt-default"
        )


@pytest.mark.parametrize(
    "state",
    [{}, None, {"user_auth_token": ""}, {"user_auth_token": "   "}],
)
def test_no_usable_token_reports_none(state):
    assert resolve_user_auth_token(state) is None


def test_a_non_string_token_is_not_passed_on():
    # State is arbitrary session data; a key collision must not put an object
    # where a credential is expected.
    assert resolve_user_auth_token({"user_auth_token": {"nested": "value"}}) is None


def test_only_a_bare_scheme_counts_as_no_token():
    assert resolve_user_auth_token({"user_auth_token": "Bearer "}) is None


# --------------------------------------------------------------------------
# The resumed request
#
# Stand-in agents rather than the real pipeline: no model calls, no cost. What
# is under test is the ADK wiring the real pipeline relies on.
# --------------------------------------------------------------------------


class _RecordingStage(BaseAgent):
    """A pipeline stage that reports the credentials visible while it runs."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        context = get_request_context() or {}
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"{self.name}:token={context.get('user_auth_token')}"
                    )
                ],
            ),
        )


class _GateAgent(BaseAgent):
    """Suspends on a long-running call until the reviewer answers it."""

    @staticmethod
    def _already_answered(ctx: InvocationContext) -> bool:
        for event in ctx.session.events:
            for part in (event.content.parts if event.content else None) or []:
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
                    role="model", parts=[types.Part(text=f"{self.name}:resolved")]
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
                            id=GATE_CALL_ID, name=GATE_TOOL_NAME, args={}
                        )
                    )
                ],
            ),
            long_running_tool_ids={GATE_CALL_ID},
        )


def _build_runner(*, with_callback: bool) -> Runner:
    pipeline = SequentialAgent(
        name="full_pipeline_agent",
        sub_agents=[
            _RecordingStage(name="planning"),
            _GateAgent(name="storyboard_gate"),
            _RecordingStage(name="generation"),
        ],
        before_agent_callback=sync_request_context if with_callback else None,
    )
    app = App(
        name=APP_NAME,
        root_agent=pipeline,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    return Runner(app=app, session_service=InMemorySessionService())


async def _drain(runner, session_id, message, invocation_id=None):
    texts, last = [], invocation_id
    kwargs = {"invocation_id": invocation_id} if invocation_id else {}
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message, **kwargs
    ):
        last = event.invocation_id or last
        for part in (event.content.parts if event.content else None) or []:
            if part.text:
                texts.append(part.text)
    return texts, last


def _approval() -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=GATE_CALL_ID,
                    name=GATE_TOOL_NAME,
                    response={"decision": "accept"},
                )
            )
        ],
    )


async def _run_to_generation(*, with_callback: bool) -> list[str]:
    """Runs up to the gate, drops the request context, then resumes."""
    runner = _build_runner(with_callback=with_callback)
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"user_auth_token": "jwt-abc", "workspace_id": "42"},
    )

    _, invocation_id = await _drain(
        runner, session.id, types.Content(role="user", parts=[types.Part(text="go")])
    )

    # The reviewer answers on a new request, which does not inherit the
    # context the first one built.
    resumed, _ = await _drain(
        runner, session.id, _approval(), invocation_id=invocation_id
    )
    return resumed


async def test_generation_still_has_credentials_after_a_resume():
    resumed = await _run_to_generation(with_callback=True)

    assert any(
        "generation:token=jwt-abc" in t for t in resumed
    ), f"generation ran without the caller's token: {resumed}"


async def test_without_the_callback_the_resumed_run_loses_them():
    """The control: this is the failure the callback exists to prevent."""
    resumed = await _run_to_generation(with_callback=False)

    assert any("generation:token=None" in t for t in resumed), (
        "expected the unguarded pipeline to reach generation with no token; "
        f"got {resumed}"
    )


async def test_completed_stages_are_not_replayed_on_resume():
    # Republishing credentials must not come at the cost of re-running work
    # that is already paid for.
    resumed = await _run_to_generation(with_callback=True)

    assert not any("planning:" in t for t in resumed)
