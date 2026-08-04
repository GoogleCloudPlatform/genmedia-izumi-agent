"""Tests for the storyboard review gate."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from demos.backend.ads_x.tools.storyboard import gate_tools


def _ctx(state=None):
    return SimpleNamespace(state=dict(state or {}))


def _storyboard():
    return {
        "campaign_title": "Test Campaign",
        "scenes": [
            {
                "scene_id": "scene_1",
                "topic": "hero",
                "video_prompt": {
                    "description": "a hero shot",
                    "duration_seconds": 4,
                    "asset_id": "vid-1",
                },
            },
            {
                "scene_id": "scene_2",
                "topic": "detail",
                "video_prompt": {"description": "a detail shot", "duration_seconds": 3},
            },
        ],
    }


# --------------------------------------------------------------------------
# await_storyboard_approval
# --------------------------------------------------------------------------


async def test_gate_returns_pending_payload_for_the_reviewer():
    ctx = _ctx({"storyboard": _storyboard()})

    result = await gate_tools.await_storyboard_approval(ctx)

    assert result["status"] == "succeeded"
    payload = result["result"]
    assert payload["status"] == "awaiting_human_review"
    assert payload["campaign_title"] == "Test Campaign"
    assert [s["scene_id"] for s in payload["scenes"]] == ["scene_1", "scene_2"]
    # The UI needs to know which scenes already have media.
    assert payload["scenes"][0]["rendered"] is True
    assert payload["scenes"][1]["rendered"] is False


async def test_gate_clears_any_previous_verdict():
    # A stale approval must not let a re-gated storyboard through.
    ctx = _ctx(
        {
            "storyboard": _storyboard(),
            gate_tools.STORYBOARD_DECISION_KEY: {"decision": "accept"},
        }
    )

    await gate_tools.await_storyboard_approval(ctx)

    assert ctx.state[gate_tools.STORYBOARD_DECISION_KEY] is None
    assert not gate_tools.storyboard_is_approved(ctx.state)


@pytest.mark.parametrize("state", [{}, {"storyboard": {"scenes": []}}])
async def test_gate_refuses_when_there_is_nothing_to_review(state):
    result = await gate_tools.await_storyboard_approval(_ctx(state))
    assert result["status"] == "failed"


# --------------------------------------------------------------------------
# record_storyboard_decision
# --------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["accept", "modify", "regenerate"])
async def test_records_each_valid_decision(decision):
    ctx = _ctx()
    result = await gate_tools.record_storyboard_decision(ctx, decision)

    assert result["status"] == "succeeded"
    assert ctx.state[gate_tools.STORYBOARD_DECISION_KEY]["decision"] == decision


async def test_decision_is_case_and_whitespace_tolerant():
    ctx = _ctx()
    await gate_tools.record_storyboard_decision(ctx, "  ACCEPT ")
    assert gate_tools.storyboard_is_approved(ctx.state)


async def test_unknown_decision_is_rejected():
    ctx = _ctx()
    result = await gate_tools.record_storyboard_decision(ctx, "looks good to me")

    assert result["status"] == "failed"
    assert not gate_tools.storyboard_is_approved(ctx.state)


async def test_guidance_is_preserved_for_the_agent():
    ctx = _ctx()
    await gate_tools.record_storyboard_decision(ctx, "modify", "  make scene 2 darker ")
    assert (
        ctx.state[gate_tools.STORYBOARD_DECISION_KEY]["guidance"]
        == "make scene 2 darker"
    )


# --------------------------------------------------------------------------
# storyboard_is_approved
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        {},
        {gate_tools.STORYBOARD_DECISION_KEY: None},
        {gate_tools.STORYBOARD_DECISION_KEY: {"decision": "modify"}},
        {gate_tools.STORYBOARD_DECISION_KEY: {"decision": "regenerate"}},
        {gate_tools.STORYBOARD_DECISION_KEY: "accept"},  # wrong shape
    ],
)
def test_only_an_explicit_accept_counts_as_approval(state):
    assert gate_tools.storyboard_is_approved(state) is False


def test_accept_counts_as_approval():
    assert gate_tools.storyboard_is_approved(
        {gate_tools.STORYBOARD_DECISION_KEY: {"decision": "accept"}}
    )


# --------------------------------------------------------------------------
# Generation backstop
# --------------------------------------------------------------------------


async def test_generation_refuses_an_unapproved_storyboard_when_gated():
    from demos.backend.ads_x.tools.generation import generation_tools

    ctx = MagicMock()
    ctx.state = {"storyboard": _storyboard()}

    with patch.object(generation_tools.settings, "ENABLE_HITL_GATES", True):
        result = await generation_tools.generate_all_media(ctx)

    assert result["status"] == "failed"
    assert "not been approved" in result["error_message"]


async def test_generation_is_not_gated_when_the_feature_is_off():
    """Standalone Izumi has no reviewer, so the backstop must not engage."""
    from demos.backend.ads_x.tools.generation import generation_tools

    ctx = MagicMock()
    ctx.state = {}  # no storyboard -> should fail for that reason, not approval

    with patch.object(generation_tools.settings, "ENABLE_HITL_GATES", False):
        result = await generation_tools.generate_all_media(ctx)

    assert result["status"] == "failed"
    assert "not been approved" not in result.get("error_message", "")


# --------------------------------------------------------------------------
# Payload readability
# --------------------------------------------------------------------------


def test_art_direction_is_split_from_the_action():
    description = (
        "Extreme close-up of a water droplet. "
        "[ART DIRECTION (NON-NEGOTIABLE) -> Mode: COMMERCIAL_PREMIUM; "
        "Lighting: Golden Hour]"
    )
    action, art = gate_tools.split_art_direction(description)

    assert action == "Extreme close-up of a water droplet."
    assert art.startswith("[ART DIRECTION")
    assert "COMMERCIAL_PREMIUM" in art


def test_prompt_without_art_direction_is_unchanged():
    action, art = gate_tools.split_art_direction("Just a plain prompt.")
    assert action == "Just a plain prompt."
    assert art == ""


def test_split_tolerates_empty_description():
    assert gate_tools.split_art_direction("") == ("", "")


async def test_digest_surfaces_a_readable_action_and_the_voiceover():
    storyboard = _storyboard()
    storyboard["scenes"][0]["video_prompt"][
        "description"
    ] = "A hero shot. [ART DIRECTION (NON-NEGOTIABLE) -> Mode: X]"
    storyboard["scenes"][0]["voiceover_prompt"] = {"text": "Stay cold. Stay sharp."}

    result = await gate_tools.await_storyboard_approval(
        _ctx({"storyboard": storyboard})
    )
    scene = result["result"]["scenes"][0]

    assert scene["action"] == "A hero shot."
    assert scene["art_direction"] == "[ART DIRECTION (NON-NEGOTIABLE) -> Mode: X]"
    assert scene["voiceover"] == "Stay cold. Stay sharp."
