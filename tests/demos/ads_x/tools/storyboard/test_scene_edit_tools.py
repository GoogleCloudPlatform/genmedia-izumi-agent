"""Tests for per-scene storyboard editing.

The invariant under test throughout: an edit releases the media it invalidates
and nothing else. Releasing too much means paying to re-render work that was
still good; releasing too little means shipping a clip that no longer matches
its prompt.
"""

from types import SimpleNamespace

import pytest

from demos.backend.ads_x.tools.storyboard import scene_edit_tools


def _rendered_scene(n: int, action: str = "an action"):
    return {
        "scene_id": f"scene_{n}",
        "topic": f"scene {n}",
        "first_frame_prompt": {"description": f"frame {n}", "asset_id": f"img-{n}"},
        "video_prompt": {
            "description": action,
            "duration_seconds": 4,
            "asset_id": f"vid-{n}",
            "enrichment_asset_id": f"enr-{n}",
        },
        "voiceover_prompt": {"text": f"line {n}", "asset_ref": {"id": f"vo-{n}"}},
        "duration_seconds": 4,
    }


def _ctx(scene_count=3):
    return SimpleNamespace(
        state={
            "storyboard": {
                "scenes": [_rendered_scene(i) for i in range(1, scene_count + 1)]
            }
        }
    )


def _scenes(ctx):
    return ctx.state["storyboard"]["scenes"]


def _by_id(ctx, scene_id):
    return next(s for s in _scenes(ctx) if s["scene_id"] == scene_id)


# --------------------------------------------------------------------------
# edit_scene
# --------------------------------------------------------------------------


async def test_editing_the_visual_action_releases_only_the_video():
    ctx = _ctx()
    result = await scene_edit_tools.edit_scene(
        ctx, "scene_2", visual_action="a brand new action"
    )
    scene = _by_id(ctx, "scene_2")

    assert result["status"] == "succeeded"
    assert scene["video_prompt"]["description"] == "a brand new action"
    assert "asset_id" not in scene["video_prompt"]
    assert "enrichment_asset_id" not in scene["video_prompt"]
    # Frame and voiceover were untouched, so their renders must survive.
    assert scene["first_frame_prompt"]["asset_id"] == "img-2"
    assert scene["voiceover_prompt"]["asset_ref"] == {"id": "vo-2"}


async def test_editing_the_voiceover_releases_only_the_audio():
    ctx = _ctx()
    await scene_edit_tools.edit_scene(ctx, "scene_1", voiceover="a new line")
    scene = _by_id(ctx, "scene_1")

    assert scene["voiceover_prompt"]["text"] == "a new line"
    assert "asset_ref" not in scene["voiceover_prompt"]
    assert scene["video_prompt"]["asset_id"] == "vid-1"
    assert scene["first_frame_prompt"]["asset_id"] == "img-1"


async def test_changing_duration_releases_the_video():
    ctx = _ctx()
    await scene_edit_tools.edit_scene(ctx, "scene_1", duration_seconds=8)
    scene = _by_id(ctx, "scene_1")

    assert scene["video_prompt"]["duration_seconds"] == 8
    assert scene["duration_seconds"] == 8
    assert "asset_id" not in scene["video_prompt"]


async def test_editing_one_scene_leaves_the_others_alone():
    ctx = _ctx()
    await scene_edit_tools.edit_scene(ctx, "scene_2", visual_action="changed")

    for other in ("scene_1", "scene_3"):
        scene = _by_id(ctx, other)
        assert scene["video_prompt"]["asset_id"]
        assert scene["first_frame_prompt"]["asset_id"]


async def test_edit_requires_at_least_one_field():
    ctx = _ctx()
    result = await scene_edit_tools.edit_scene(ctx, "scene_1")
    assert result["status"] == "failed"
    # Nothing should have been released.
    assert _by_id(ctx, "scene_1")["video_prompt"]["asset_id"] == "vid-1"


async def test_edit_rejects_unknown_scene():
    ctx = _ctx()
    result = await scene_edit_tools.edit_scene(ctx, "scene_9", visual_action="x")
    assert result["status"] == "failed"
    assert "scene_9" in result["error_message"]


# --------------------------------------------------------------------------
# add_scene
# --------------------------------------------------------------------------


async def test_added_scene_appends_by_default():
    ctx = _ctx()
    await scene_edit_tools.add_scene(ctx, visual_action="a closing shot")

    scenes = _scenes(ctx)
    assert len(scenes) == 4
    assert scenes[-1]["video_prompt"]["description"] == "a closing shot"
    assert scenes[-1]["scene_id"]
    # A brand new scene has nothing rendered yet.
    assert "asset_id" not in scenes[-1]["video_prompt"]


async def test_added_scene_can_be_inserted_mid_sequence():
    ctx = _ctx()
    await scene_edit_tools.add_scene(
        ctx, visual_action="an interlude", after_scene_id="scene_1"
    )

    scenes = _scenes(ctx)
    assert [s["scene_id"] for s in scenes][0] == "scene_1"
    assert scenes[1]["video_prompt"]["description"] == "an interlude"


async def test_inserting_does_not_disturb_existing_renders():
    ctx = _ctx()
    await scene_edit_tools.add_scene(
        ctx, visual_action="an interlude", after_scene_id="scene_1"
    )

    # Every original scene keeps its id and its media.
    for n in (1, 2, 3):
        scene = _by_id(ctx, f"scene_{n}")
        assert scene["video_prompt"]["asset_id"] == f"vid-{n}"


async def test_added_scene_id_does_not_collide():
    ctx = _ctx()
    await scene_edit_tools.add_scene(ctx, visual_action="one")
    await scene_edit_tools.add_scene(ctx, visual_action="two")

    ids = [s["scene_id"] for s in _scenes(ctx)]
    assert len(ids) == len(set(ids)), f"duplicate scene ids: {ids}"


async def test_add_requires_a_visual_action():
    ctx = _ctx()
    assert (await scene_edit_tools.add_scene(ctx, visual_action="  "))[
        "status"
    ] == "failed"


async def test_add_rejects_unknown_anchor():
    ctx = _ctx()
    result = await scene_edit_tools.add_scene(
        ctx, visual_action="x", after_scene_id="scene_9"
    )
    assert result["status"] == "failed"


# --------------------------------------------------------------------------
# remove_scene
# --------------------------------------------------------------------------


async def test_remove_deletes_the_named_scene():
    ctx = _ctx()
    result = await scene_edit_tools.remove_scene(ctx, "scene_2")

    assert result["status"] == "succeeded"
    assert [s["scene_id"] for s in _scenes(ctx)] == ["scene_1", "scene_3"]


async def test_remove_keeps_survivors_media():
    ctx = _ctx()
    await scene_edit_tools.remove_scene(ctx, "scene_1")

    assert _by_id(ctx, "scene_3")["video_prompt"]["asset_id"] == "vid-3"


async def test_cannot_remove_the_last_remaining_scene():
    ctx = _ctx(scene_count=1)
    result = await scene_edit_tools.remove_scene(ctx, "scene_1")

    assert result["status"] == "failed"
    assert len(_scenes(ctx)) == 1


# --------------------------------------------------------------------------
# reorder_scenes
# --------------------------------------------------------------------------


async def test_reorder_moves_scenes_with_their_media():
    ctx = _ctx()
    result = await scene_edit_tools.reorder_scenes(
        ctx, ["scene_3", "scene_1", "scene_2"]
    )

    assert result["status"] == "succeeded"
    scenes = _scenes(ctx)
    assert [s["scene_id"] for s in scenes] == ["scene_3", "scene_1", "scene_2"]
    # Reordering renders nothing new: each scene keeps the media it had.
    assert scenes[0]["video_prompt"]["asset_id"] == "vid-3"
    assert scenes[1]["video_prompt"]["asset_id"] == "vid-1"


@pytest.mark.parametrize(
    "order",
    [
        ["scene_1", "scene_2"],  # omits scene_3
        ["scene_1", "scene_2", "scene_2"],  # duplicate
        ["scene_1", "scene_2", "scene_9"],  # unknown id
    ],
)
async def test_reorder_rejects_a_malformed_order(order):
    ctx = _ctx()
    result = await scene_edit_tools.reorder_scenes(ctx, order)

    assert result["status"] == "failed"
    # The storyboard must be left exactly as it was.
    assert [s["scene_id"] for s in _scenes(ctx)] == ["scene_1", "scene_2", "scene_3"]


# --------------------------------------------------------------------------
# Shared guards
# --------------------------------------------------------------------------


async def test_every_tool_reports_a_missing_storyboard():
    ctx = SimpleNamespace(state={})
    assert (await scene_edit_tools.edit_scene(ctx, "scene_1", voiceover="x"))[
        "status"
    ] == "failed"
    assert (await scene_edit_tools.add_scene(ctx, visual_action="x"))[
        "status"
    ] == "failed"
    assert (await scene_edit_tools.remove_scene(ctx, "scene_1"))["status"] == "failed"
    assert (await scene_edit_tools.reorder_scenes(ctx, ["scene_1"]))[
        "status"
    ] == "failed"
