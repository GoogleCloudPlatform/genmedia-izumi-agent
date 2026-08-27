"""Tests for the storyboard review gate."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from demos.backend.ads_x.tools.storyboard import gate_tools


def _ctx(state=None):
    # A real ToolContext always carries .actions; the gate sets escalate on it.
    return SimpleNamespace(
        state=dict(state or {}), actions=SimpleNamespace(escalate=None)
    )


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
# Reaching the reviewer's client
#
# The storyboard lives in session state, and Creative Studio renders its own
# copy. Suspending without pushing it across asks a reviewer to approve
# something their client has no way to show them.
# --------------------------------------------------------------------------


def _save_patch(returns: str | None = "17"):
    """Stands in for the push the gate makes before it suspends."""
    return patch.object(
        gate_tools.storyboard_persistence,
        "save_to_creative_studio",
        AsyncMock(return_value=returns),
    )


async def test_the_gate_saves_the_storyboard_before_it_suspends():
    ctx = _ctx({"storyboard": _storyboard()})

    with _save_patch() as saved:
        payload = (await gate_tools.await_storyboard_approval(ctx))["result"]

    saved.assert_awaited_once()
    assert payload["storyboard_id"] == "17", "the client is told what to fetch"


async def test_the_review_still_goes_ahead_when_the_save_fails():
    # An unreachable backend costs the reviewer the rendered view, not their
    # say: the digest in the payload is enough to answer the gate from.
    ctx = _ctx({"storyboard": _storyboard()})

    with _save_patch(returns=None):
        payload = (await gate_tools.await_storyboard_approval(ctx))["result"]

    assert payload["storyboard_id"] is None
    assert payload["status"] == "awaiting_human_review"
    assert len(payload["scenes"]) == 2


async def test_nothing_is_saved_when_there_is_no_storyboard_to_review():
    with _save_patch() as saved:
        result = await gate_tools.await_storyboard_approval(_ctx())

    assert result["status"] == "failed"
    saved.assert_not_awaited()


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


# --------------------------------------------------------------------------
# Loop control — accept ends the review, anything else continues it
# --------------------------------------------------------------------------


async def test_accept_escalates_to_end_the_review_loop():
    ctx = _ctx()
    await gate_tools.record_storyboard_decision(ctx, "accept")

    assert ctx.actions.escalate is True
    assert gate_tools.storyboard_is_approved(ctx.state)


@pytest.mark.parametrize("decision", ["modify", "regenerate"])
async def test_other_verdicts_keep_the_loop_running(decision):
    # Not escalating is what sends the revised storyboard back for another look.
    ctx = _ctx()
    await gate_tools.record_storyboard_decision(ctx, decision, "make it shorter")

    assert not ctx.actions.escalate
    assert not gate_tools.storyboard_is_approved(ctx.state)


async def test_a_rejected_decision_does_not_end_the_loop():
    ctx = _ctx()
    result = await gate_tools.record_storyboard_decision(ctx, "ship it")

    assert result["status"] == "failed"
    assert not ctx.actions.escalate


# --------------------------------------------------------------------------
# Strategy gate (Stage A)
# --------------------------------------------------------------------------


async def test_strategy_gate_summarises_the_campaign_for_review():
    ctx = _ctx(
        {
            "parameters": {
                "campaign_name": "Aurora",
                "target_audience": "urban professionals",
                "campaign_tone": "refined",
                "generate_virtual_creator": False,
            },
            "master_production_recipe": {"look_name": "Organic Wellness"},
            "user_assets": {"bottle.png": {}},
        }
    )
    payload = (await gate_tools.await_strategy_approval(ctx))["result"]

    assert payload["stage"] == "strategy"
    assert payload["campaign"]["name"] == "Aurora"
    assert payload["look"]["name"] == "Organic Wellness"
    assert payload["features_a_person"] is False
    assert payload["uploaded_assets"] == ["bottle.png"]


async def test_strategy_gate_refuses_before_a_brief_exists():
    assert (await gate_tools.await_strategy_approval(_ctx()))["status"] == "failed"


async def test_accepting_strategy_ends_its_review_loop():
    ctx = _ctx()
    await gate_tools.record_strategy_decision(ctx, "accept")

    assert ctx.actions.escalate is True
    assert gate_tools.strategy_is_approved(ctx.state)


async def test_modifying_strategy_keeps_its_loop_running():
    ctx = _ctx()
    await gate_tools.record_strategy_decision(ctx, "modify", "shorter, please")

    assert not ctx.actions.escalate
    assert not gate_tools.strategy_is_approved(ctx.state)


async def test_the_two_gates_keep_separate_verdicts():
    # Approving strategy must not imply approving the storyboard.
    ctx = _ctx()
    await gate_tools.record_strategy_decision(ctx, "accept")

    assert gate_tools.strategy_is_approved(ctx.state)
    assert not gate_tools.storyboard_is_approved(ctx.state)


# --------------------------------------------------------------------------
# Final cut gate (Stage C)
# --------------------------------------------------------------------------


def _finished_campaign():
    return {
        "storyboard": {
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "topic": "hero",
                    "video_prompt": {
                        "description": "a hero shot. [ART DIRECTION (NON-NEGOTIABLE) -> Mode: X]",
                        "duration_seconds": 4,
                        "asset_id": "vid-1",
                    },
                }
            ]
        },
        "final_video_asset_id": "final-42",
        "final_video_asset_ref": {"id": "final-42"},
    }


async def test_final_gate_presents_the_cut_and_its_clips():
    payload = (await gate_tools.await_final_cut_approval(_ctx(_finished_campaign())))[
        "result"
    ]

    assert payload["stage"] == "final_cut"
    assert payload["final_video"]["asset_id"] == "final-42"
    clip = payload["clips"][0]
    assert clip["scene_id"] == "scene_1"
    assert clip["asset_id"] == "vid-1"
    # The reviewer reads the action, not the art direction.
    assert clip["action"] == "a hero shot."


async def test_final_gate_refuses_before_anything_is_stitched():
    state = _finished_campaign()
    del state["final_video_asset_id"]
    del state["final_video_asset_ref"]

    assert (await gate_tools.await_final_cut_approval(_ctx(state)))[
        "status"
    ] == "failed"


async def test_accepting_the_final_cut_ends_its_loop():
    ctx = _ctx(_finished_campaign())
    await gate_tools.record_final_cut_decision(ctx, "accept")

    assert ctx.actions.escalate is True
    assert gate_tools.final_cut_is_approved(ctx.state)


async def test_asking_for_changes_keeps_the_final_loop_running():
    ctx = _ctx(_finished_campaign())
    await gate_tools.record_final_cut_decision(ctx, "modify", "scene_1 is too dark")

    assert not ctx.actions.escalate
    assert not gate_tools.final_cut_is_approved(ctx.state)


async def test_all_three_gates_hold_independent_verdicts():
    ctx = _ctx(_finished_campaign())
    await gate_tools.record_strategy_decision(ctx, "accept")
    await gate_tools.record_storyboard_decision(ctx, "accept")

    # Approving the plan and the storyboard says nothing about the final cut.
    assert gate_tools.strategy_is_approved(ctx.state)
    assert gate_tools.storyboard_is_approved(ctx.state)
    assert not gate_tools.final_cut_is_approved(ctx.state)


# --------------------------------------------------------------------------
# Every checkpoint must say what it is asking for
#
# Reported from integration: the run stopped with nothing on screen explaining
# why. The agent's prose all arrives *after* the verdict, because calling the
# tool suspends the run immediately - so the payload itself has to carry
# something a reviewer can read.
# --------------------------------------------------------------------------


def _rctx(state=None):
    return SimpleNamespace(
        state=dict(state or {}),
        actions=SimpleNamespace(escalate=None),
        _invocation_context=SimpleNamespace(is_resumable=True),
    )


async def test_strategy_gate_explains_itself():
    payload = (
        await gate_tools.await_strategy_approval(
            _rctx(
                {
                    "parameters": {
                        "campaign_name": "Aurora",
                        "target_audience": "urban professionals",
                        "target_duration": "15s",
                        "generate_virtual_creator": False,
                    },
                    "master_production_recipe": {"look_name": "Organic Wellness"},
                }
            )
        )
    )["result"]

    assert payload["message"], "a reviewer needs to be told what to look at"
    # It should describe this campaign, not be boilerplate.
    assert "urban professionals" in payload["message"]
    assert "Organic Wellness" in payload["message"]
    assert "product-only" in payload["message"]


async def test_storyboard_gate_explains_itself():
    payload = (
        await gate_tools.await_storyboard_approval(_rctx({"storyboard": _storyboard()}))
    )["result"]

    assert payload["message"]
    assert "2 scenes" in payload["message"], "say how much there is to review"
    assert payload["stage"] == "storyboard"


async def test_final_cut_gate_explains_itself():
    payload = (await gate_tools.await_final_cut_approval(_rctx(_finished_campaign())))[
        "result"
    ]

    assert payload["message"]
    assert "ready" in payload["message"].lower()


async def test_every_gate_payload_carries_a_message():
    gates = (
        (gate_tools.await_strategy_approval, {"parameters": {"campaign_name": "A"}}),
        (gate_tools.await_storyboard_approval, {"storyboard": _storyboard()}),
        (gate_tools.await_final_cut_approval, _finished_campaign()),
    )
    for gate, state in gates:
        payload = (await gate(_rctx(state)))["result"]
        assert payload.get("message"), f"{gate.__name__} gives the reviewer nothing"
        assert payload.get("stage"), f"{gate.__name__} does not identify its stage"


# --------------------------------------------------------------------------
# Payload detail
#
# Each checkpoint carries what the reviewer needs to judge that stage, and
# nothing from a later one. A change requested at an earlier checkpoint
# rewrites what the next one presents, so anticipating it would show the
# reviewer a plan that is about to stop being true.
# --------------------------------------------------------------------------


def _recipe_state(virtual_creator=False):
    return {
        "parameters": {
            "campaign_name": "Aurora",
            "generate_virtual_creator": virtual_creator,
        },
        "master_production_recipe": {
            "look_name": "Organic Wellness",
            "style_mode": "COMMERCIAL_PREMIUM",
            "sonic_landscape": ["warm strings", "soft piano"],
            "cinematography": {"optics": "85mm f/1.8", "motion_texture": "filmic"},
            "illumination": {"vibe": "golden hour", "key_lighting": "soft key"},
            "environment": {"setting": "a sunlit kitchen"},
            "character": {"actor_vibe": "a chef", "attire": "linen apron"},
        },
    }


async def test_strategy_gate_shows_the_direction_every_scene_inherits():
    payload = (await gate_tools.await_strategy_approval(_ctx(_recipe_state())))[
        "result"
    ]

    direction = payload["direction"]
    assert direction["lighting"] == "golden hour"
    assert direction["key_light"] == "soft key"
    assert direction["optics"] == "85mm f/1.8"
    assert direction["texture"] == "filmic"
    assert direction["setting"] == "a sunlit kitchen"
    # Lists are flattened; a reviewer reads a line, not a JSON array.
    assert direction["music"] == "warm strings, soft piano"


async def test_strategy_gate_hides_casting_for_a_product_only_ad():
    """Cast and wardrobe are only bound to scenes when someone is on screen."""
    payload = (await gate_tools.await_strategy_approval(_ctx(_recipe_state())))[
        "result"
    ]

    assert "cast" not in payload["direction"]
    assert "wardrobe" not in payload["direction"]


async def test_strategy_gate_shows_casting_when_a_person_features():
    state = _recipe_state(virtual_creator=True)
    state["virtual_creator_metadata"] = {"demographics": "a chef in her forties"}
    payload = (await gate_tools.await_strategy_approval(_ctx(state)))["result"]

    assert payload["direction"]["cast"] == "a chef in her forties"
    assert payload["direction"]["wardrobe"] == "linen apron"


async def test_strategy_gate_carries_nothing_from_the_storyboard():
    """The storyboard does not exist yet, and a change asked for here would
    rewrite it anyway."""
    state = _recipe_state()
    state["storyboard"] = _storyboard()
    payload = (await gate_tools.await_strategy_approval(_ctx(state)))["result"]

    assert "scenes" not in payload
    assert "clips" not in payload
    assert "storyboard" not in payload


async def test_storyboard_gate_shows_the_shot_behind_each_scene():
    storyboard = _storyboard()
    storyboard["background_music_prompt"] = "warm acoustic bed"
    storyboard["scenes"][0]["video_prompt"]["cinematography"] = {
        "camera": "slow dolly in",
        "lens": ["50mm", "shallow depth of field"],
        "mood": "",
    }
    storyboard["scenes"][0]["first_frame_prompt"] = {
        "description": "a bottle on a lit counter"
    }
    payload = (
        await gate_tools.await_storyboard_approval(_ctx({"storyboard": storyboard}))
    )["result"]

    scene = payload["scenes"][0]
    assert scene["shot"] == {
        "camera": "slow dolly in",
        "lens": "50mm, shallow depth of field",
    }
    assert scene["opening_frame"] == "a bottle on a lit counter"
    assert payload["music"] == "warm acoustic bed"


async def test_final_cut_clips_carry_the_scene_detail_and_the_render():
    storyboard = _storyboard()
    storyboard["scenes"][0]["voiceover_prompt"] = {"text": "Pour something better."}
    ctx = _ctx({"storyboard": storyboard, "final_video_asset_id": "final-1"})
    payload = (await gate_tools.await_final_cut_approval(ctx))["result"]

    clip = payload["clips"][0]
    assert clip["asset_id"] == "vid-1"
    assert clip["voiceover"] == "Pour something better."
    assert clip["action"] == "a hero shot"
