"""Tests for choosing and adjusting the campaign's visual Look."""

from types import SimpleNamespace

import pytest

from demos.backend.ads_x.tools.storyboard import look_tools
from demos.backend.ads_x.utils.storyboard.production_presets import PRODUCTION_LOOKS


def _ctx(state=None):
    return SimpleNamespace(
        state=dict(state or {}), actions=SimpleNamespace(escalate=None)
    )


def _with_look(name="Luxury Heritage", **extra):
    look = next(l for l in PRODUCTION_LOOKS if l["name"] == name)
    recipe = dict(look["recipe"])
    recipe["look_name"] = name
    state = {look_tools.RECIPE_KEY: recipe}
    state.update(extra)
    return _ctx(state)


def _rendered_storyboard(n=2):
    return {
        "scenes": [
            {
                "scene_id": f"scene_{i}",
                "first_frame_prompt": {
                    "description": f"frame {i}. [ART DIRECTION (NON-NEGOTIABLE) -> Mode: OLD]",
                    "asset_id": f"img-{i}",
                },
                "video_prompt": {
                    "description": f"action {i}. [ART DIRECTION (NON-NEGOTIABLE) -> Mode: OLD]",
                    "asset_id": f"vid-{i}",
                    "enrichment_asset_id": f"enr-{i}",
                },
                "voiceover_prompt": {
                    "text": f"line {i}",
                    "asset_ref": {"id": f"vo-{i}"},
                },
            }
            for i in range(1, n + 1)
        ]
    }


# --------------------------------------------------------------------------
# list_looks
# --------------------------------------------------------------------------


async def test_lists_the_whole_catalog_and_marks_the_active_one():
    result = await look_tools.list_looks(_with_look("Luxury Heritage"))
    payload = result["result"]

    assert len(payload["looks"]) == len(PRODUCTION_LOOKS)
    assert payload["selected"] == "Luxury Heritage"
    assert [l for l in payload["looks"] if l["selected"]][0][
        "name"
    ] == "Luxury Heritage"
    # A reviewer needs enough to choose between them.
    assert all(l["description"] and "tones" in l for l in payload["looks"])


async def test_looks_can_be_narrowed_by_tier():
    result = await look_tools.list_looks(_ctx(), tier="ugc")
    assert {l["tier"] for l in result["result"]["looks"]} == {"ugc"}


async def test_unknown_tier_is_rejected():
    assert (await look_tools.list_looks(_ctx(), tier="cinema"))["status"] == "failed"


# --------------------------------------------------------------------------
# set_look
# --------------------------------------------------------------------------


async def test_set_look_switches_the_recipe():
    ctx = _with_look("Luxury Heritage")
    result = await look_tools.set_look(ctx, "Vibrant CPG Pop")

    assert result["status"] == "succeeded"
    assert ctx.state[look_tools.RECIPE_KEY]["look_name"] == "Vibrant CPG Pop"


async def test_set_look_rejects_an_unknown_name():
    ctx = _with_look()
    result = await look_tools.set_look(ctx, "Cyberpunk Noir")

    assert result["status"] == "failed"
    assert ctx.state[look_tools.RECIPE_KEY]["look_name"] == "Luxury Heritage"


async def test_changing_look_warns_that_existing_scenes_are_stale():
    # Art direction is baked into scene prompts, so a later Look change does not
    # reach them on its own. Silence here would be misleading.
    ctx = _with_look(storyboard=_rendered_storyboard(3))
    result = await look_tools.set_look(ctx, "Vibrant CPG Pop")

    assert "3 scene(s)" in result["result"]
    assert "reapply_art_direction" in result["result"]


async def test_no_stale_warning_before_a_storyboard_exists():
    result = await look_tools.set_look(_with_look(), "Vibrant CPG Pop")
    assert "reapply_art_direction" not in result["result"]


# --------------------------------------------------------------------------
# list_look_options / edit_look_field
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field", ["aesthetic", "environment", "optics", "motion", "lighting"]
)
async def test_each_editable_field_offers_curated_options(field):
    result = await look_tools.list_look_options(_with_look(), field)
    payload = result["result"]

    assert payload["options"], f"{field} exposes no options to choose from"
    assert payload["current"]


async def test_options_for_an_unknown_field_are_rejected():
    assert (await look_tools.list_look_options(_with_look(), "vibes"))[
        "status"
    ] == "failed"


async def test_edit_applies_a_curated_value_cleanly():
    ctx = _with_look()
    options = (await look_tools.list_look_options(ctx, "optics"))["result"]["options"]

    result = await look_tools.edit_look_field(ctx, "optics", options[1])

    assert result["status"] == "succeeded"
    assert "custom value" not in result["result"]
    assert ctx.state[look_tools.RECIPE_KEY]["cinematography"]["optics"] == options[1]


async def test_free_text_is_accepted_but_flagged():
    ctx = _with_look()
    result = await look_tools.edit_look_field(ctx, "optics", "shot on a potato")

    assert result["status"] == "succeeded"
    assert "custom value" in result["result"]


async def test_an_edited_look_is_no_longer_the_pure_preset():
    ctx = _with_look("Luxury Heritage")
    await look_tools.edit_look_field(ctx, "optics", "anything")
    await look_tools.edit_look_field(ctx, "lighting", "anything else")

    # Marked once, not once per edit.
    assert ctx.state[look_tools.RECIPE_KEY]["look_name"] == "Luxury Heritage (modified)"


async def test_edit_requires_a_look_and_a_value():
    assert (await look_tools.edit_look_field(_ctx(), "optics", "x"))[
        "status"
    ] == "failed"
    assert (await look_tools.edit_look_field(_with_look(), "optics", " "))[
        "status"
    ] == "failed"


# --------------------------------------------------------------------------
# edit_character
# --------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["actor", "attire", "grooming"])
async def test_character_styling_can_be_changed(field):
    ctx = _with_look()
    result = await look_tools.edit_character(ctx, field, "something distinctive")

    assert result["status"] == "succeeded"
    assert "something distinctive" in str(ctx.state[look_tools.RECIPE_KEY]["character"])


async def test_edit_character_rejects_a_non_character_field():
    result = await look_tools.edit_character(_with_look(), "optics", "x")
    assert result["status"] == "failed"


# --------------------------------------------------------------------------
# reapply_art_direction
# --------------------------------------------------------------------------


async def test_restamping_replaces_stale_direction_and_frees_visuals():
    ctx = _with_look(storyboard=_rendered_storyboard(2), parameters={})
    await look_tools.set_look(ctx, "Vibrant CPG Pop")

    result = await look_tools.reapply_art_direction(ctx)

    assert result["status"] == "succeeded"
    for index, scene in enumerate(ctx.state["storyboard"]["scenes"], start=1):
        video = scene["video_prompt"]
        assert "Mode: OLD" not in video["description"]
        assert "[ART DIRECTION" in video["description"]
        # Visuals no longer match the direction, so they must re-render...
        assert "asset_id" not in video
        assert "enrichment_asset_id" not in video
        assert "asset_id" not in scene["first_frame_prompt"]
        # ...but the script did not change, so the voiceover survives.
        assert scene["voiceover_prompt"]["asset_ref"] == {"id": f"vo-{index}"}


async def test_restamping_preserves_the_human_readable_action():
    ctx = _with_look(storyboard=_rendered_storyboard(1), parameters={})
    await look_tools.reapply_art_direction(ctx)

    description = ctx.state["storyboard"]["scenes"][0]["video_prompt"]["description"]
    assert description.startswith("action 1.")


async def test_restamping_needs_a_storyboard_and_a_look():
    assert (await look_tools.reapply_art_direction(_with_look()))["status"] == "failed"
    assert (await look_tools.reapply_art_direction(_ctx()))["status"] == "failed"
