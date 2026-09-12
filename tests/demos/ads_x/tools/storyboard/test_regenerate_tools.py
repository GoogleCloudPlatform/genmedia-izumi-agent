"""Tests for wholesale regeneration.

The distinction under test: an edit keeps the work and changes part of it, a
regeneration discards it. A "regeneration" that quietly preserved the thing
being rejected would not be one.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from demos.backend.ads_x.tools.storyboard import regenerate_tools


@pytest.fixture(autouse=True)
def rendered_music():
    """Stubs the renderer, which regenerate_music now invokes directly.

    Without it these tests call the live music API.
    """
    with patch.object(
        regenerate_tools.generation_helpers,
        "generate_background_music",
        new=AsyncMock(return_value=SimpleNamespace(id="music-2")),
    ) as rendered:
        yield rendered


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


async def test_music_is_rendered_not_merely_released(rendered_music):
    """Releasing the reference alone leaves the storyboard declaring music
    that does not exist, and the next stitch produces a silent cut."""
    ctx = _ctx()
    result = await regenerate_tools.regenerate_music(ctx)

    assert result["status"] == "succeeded"
    rendered_music.assert_awaited_once()
    prompt = ctx.state["storyboard"]["background_music_prompt"]
    # The stale reference is gone before rendering, so the renderer does not
    # skip the track as already present.
    assert rendered_music.await_args.args[1] is prompt
    # The brief is untouched when no new one is given.
    assert prompt["description"] == "calm ambient"


async def test_a_failed_music_render_is_reported(rendered_music):
    """A failed render must not be reported as a successful one."""
    rendered_music.return_value = None
    ctx = _ctx()

    result = await regenerate_tools.regenerate_music(ctx)

    assert result["status"] == "failed"
    assert "no background track" in result["error_message"]


async def test_music_renders_into_the_session_workspace(rendered_music):
    """The workspace is on the ADK context, not in state.

    Native mode never puts ``workspace_id`` in session state, so deriving it
    from state alone yields an empty string and the track is written to a
    workspace nobody can read back.
    """
    ctx = _ctx()
    ctx._invocation_context = SimpleNamespace(
        session=SimpleNamespace(user_id="project_1789168370652", id="s-1")
    )

    result = await regenerate_tools.regenerate_music(ctx)

    assert result["status"] == "succeeded"
    assert rendered_music.await_args.args[0] == "project_1789168370652"


async def test_music_brief_can_be_replaced(rendered_music):
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

    # Cleared by assignment: ADK's State has no pop/del, so a real run would
    # crash if this tried to remove the keys.
    assert not ctx.state["final_video_asset_id"]
    assert not ctx.state["final_video_asset_ref"]


async def test_clearing_the_cut_works_on_a_real_adk_state_object():
    # The plain dict used elsewhere in these tests hides the pop/del problem.
    from google.adk.sessions.state import State

    ctx = _ctx()
    ctx.state = State(value=dict(ctx.state), delta={})

    result = await regenerate_tools.regenerate_all_media(ctx)

    assert result["status"] == "succeeded"
    assert not ctx.state.get("final_video_asset_id")


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
