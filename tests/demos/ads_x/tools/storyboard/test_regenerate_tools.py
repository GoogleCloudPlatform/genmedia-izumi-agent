"""Tests for wholesale regeneration.

The distinction under test: an edit keeps the work and changes part of it, a
regeneration discards it. A "regeneration" that quietly preserved the thing
being rejected would not be one.
"""

from types import SimpleNamespace

from demos.backend.ads_x.tools.storyboard import regenerate_tools


def _scene(n, rendered=True):
    scene = {
        "scene_id": f"scene_{n}",
        "first_frame_prompt": {"description": f"frame {n}"},
        "video_prompt": {"description": f"action {n}", "duration_seconds": 4},
        "voiceover_prompt": {"text": f"line {n}"},
    }
    if rendered:
        scene["first_frame_prompt"]["asset_id"] = f"img-{n}"
        scene["video_prompt"]["asset_id"] = f"vid-{n}"
        scene["voiceover_prompt"]["asset_ref"] = {"id": f"vo-{n}"}
    return scene


def _ctx(scenes=2, rendered=True, music=True, stitched=True):
    storyboard = {"scenes": [_scene(i, rendered) for i in range(1, scenes + 1)]}
    if music:
        storyboard["background_music_prompt"] = {
            "description": "calm ambient",
            "asset_ref": {"id": "music-1"},
        }
    state = {"storyboard": storyboard}
    if stitched:
        state["final_video_asset_id"] = "final-1"
        state["final_video_asset_ref"] = {"id": "final-1"}
    return SimpleNamespace(state=state, actions=SimpleNamespace(escalate=None))


# --------------------------------------------------------------------------
# regenerate_storyboard
# --------------------------------------------------------------------------


async def test_discards_the_storyboard_entirely():
    ctx = _ctx()
    result = await regenerate_tools.regenerate_storyboard(ctx, "make it funnier")

    assert result["status"] == "succeeded"
    assert ctx.state["storyboard"] is None
    assert ctx.state[regenerate_tools.REVISION_GUIDANCE_KEY] == "make it funnier"


async def test_reports_what_is_being_thrown_away():
    # A reviewer should learn that rendered work is being discarded.
    result = await regenerate_tools.regenerate_storyboard(_ctx(scenes=3))
    assert "3-scene" in result["result"]
    assert "3 rendered clip(s)" in result["result"]


async def test_says_so_when_nothing_had_been_rendered():
    result = await regenerate_tools.regenerate_storyboard(_ctx(rendered=False))
    assert "Nothing had been rendered" in result["result"]


async def test_regenerating_needs_a_storyboard():
    empty = SimpleNamespace(state={}, actions=SimpleNamespace(escalate=None))
    assert (await regenerate_tools.regenerate_storyboard(empty))["status"] == "failed"


# --------------------------------------------------------------------------
# regenerate_music
# --------------------------------------------------------------------------


async def test_music_reference_is_released_so_it_renders_again():
    ctx = _ctx()
    result = await regenerate_tools.regenerate_music(ctx)

    assert result["status"] == "succeeded"
    prompt = ctx.state["storyboard"]["background_music_prompt"]
    assert "asset_ref" not in prompt
    # The brief is untouched when no new one is given.
    assert prompt["description"] == "calm ambient"


async def test_music_brief_can_be_replaced():
    ctx = _ctx()
    await regenerate_tools.regenerate_music(ctx, "driving percussion")

    assert (
        ctx.state["storyboard"]["background_music_prompt"]["description"]
        == "driving percussion"
    )


async def test_music_regeneration_leaves_the_scenes_alone():
    ctx = _ctx()
    await regenerate_tools.regenerate_music(ctx)

    for scene in ctx.state["storyboard"]["scenes"]:
        assert scene["video_prompt"]["asset_id"]


async def test_music_regeneration_needs_a_track():
    ctx = _ctx(music=False)
    assert (await regenerate_tools.regenerate_music(ctx))["status"] == "failed"


# --------------------------------------------------------------------------
# regenerate_all_media
# --------------------------------------------------------------------------


async def test_every_clip_is_released():
    ctx = _ctx(scenes=3)
    result = await regenerate_tools.regenerate_all_media(ctx)

    assert result["status"] == "succeeded"
    for scene in ctx.state["storyboard"]["scenes"]:
        assert "asset_id" not in scene["video_prompt"]
        assert "asset_id" not in scene["first_frame_prompt"]
        assert "asset_ref" not in scene["voiceover_prompt"]


async def test_the_stale_stitched_cut_is_dropped():
    # The cut was assembled from clips that no longer exist.
    ctx = _ctx()
    await regenerate_tools.regenerate_all_media(ctx)

    assert "final_video_asset_id" not in ctx.state
    assert "final_video_asset_ref" not in ctx.state


async def test_guidance_reaches_every_scene():
    ctx = _ctx(scenes=2)
    await regenerate_tools.regenerate_all_media(ctx, "shoot it all at night")

    for scene in ctx.state["storyboard"]["scenes"]:
        assert "shoot it all at night" in scene["video_prompt"]["description"]
        # The original action survives; the direction is added to it.
        assert scene["video_prompt"]["description"].startswith("action")


async def test_full_regeneration_needs_scenes():
    empty = SimpleNamespace(
        state={"storyboard": {"scenes": []}}, actions=SimpleNamespace(escalate=None)
    )
    assert (await regenerate_tools.regenerate_all_media(empty))["status"] == "failed"
