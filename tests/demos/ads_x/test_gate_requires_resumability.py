"""A checkpoint that cannot pause must refuse, not approve itself.

Found in Creative Studio integration: the deployed agent sailed through all
three checkpoints, inventing its own verdicts ("Continue processing previous
requests as instructed") and rendering the campaign. The cause was that the
Agent Engine deployment passed the bare root_agent, so the Runner had no
resumability config, so the long-running call never suspended - it returned its
"awaiting review" payload like any other tool result, and the model answered it.

That failure is silent and expensive, which is why it is guarded twice: the
deployment wires the App through, and the tools refuse if it did not.
"""

from types import SimpleNamespace

import pytest

from demos.backend.ads_x.tools.storyboard import gate_tools


def _ctx(resumable, state=None):
    return SimpleNamespace(
        state=dict(state or {}),
        actions=SimpleNamespace(escalate=None),
        _invocation_context=SimpleNamespace(is_resumable=resumable),
    )


def _campaign():
    return {
        "parameters": {"campaign_name": "Aurora"},
        "storyboard": {
            "scenes": [
                {
                    "scene_id": "s1",
                    "topic": "hero",
                    "video_prompt": {"description": "a shot", "duration_seconds": 4},
                }
            ]
        },
        "final_video_asset_id": "final-1",
    }


@pytest.mark.parametrize(
    "gate",
    [
        gate_tools.await_strategy_approval,
        gate_tools.await_storyboard_approval,
        gate_tools.await_final_cut_approval,
    ],
    ids=["strategy", "storyboard", "final_cut"],
)
async def test_a_gate_refuses_when_the_run_cannot_suspend(gate):
    result = await gate(_ctx(resumable=False, state=_campaign()))

    assert result["status"] == "failed"
    assert "cannot pause" in result["error_message"]
    # The message has to say what to do, or whoever hits it is stuck.
    assert "ENABLE_HITL_GATES" in result["error_message"]


@pytest.mark.parametrize(
    "gate",
    [
        gate_tools.await_strategy_approval,
        gate_tools.await_storyboard_approval,
        gate_tools.await_final_cut_approval,
    ],
    ids=["strategy", "storyboard", "final_cut"],
)
async def test_a_gate_asks_for_review_when_the_run_can_suspend(gate):
    result = await gate(_ctx(resumable=True, state=_campaign()))

    assert result["status"] == "succeeded"
    assert result["result"]["status"] == "awaiting_human_review"


def test_the_deployment_hands_agent_engine_the_app_not_the_agent():
    """AdkApp builds Runner(app=app, agent=(None if app else agent)).

    Passing the agent alone leaves resumability unset, which is precisely the
    bug above.
    """
    source = open("scripts/deploy_to_agent_platform.py").read()
    block = source[source.index("AgentEngineApp(") :][:200]

    assert "app=" in block, "the deployment must pass the App"
    assert "agent=root_agent" not in block, (
        "passing the bare agent drops resumability and the checkpoints "
        "silently approve themselves"
    )
