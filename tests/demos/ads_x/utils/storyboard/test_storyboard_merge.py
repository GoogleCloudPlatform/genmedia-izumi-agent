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

"""Tests for storyboard merge-protection."""

from demos.backend.ads_x.utils.storyboard.storyboard_merge import (
    clear_scene_assets,
    find_scene_index,
    assign_scene_ids,
    merge_storyboard,
)


def _scene(topic, first_desc, video_desc, vo_text="hello", **extra):
    """Builds a scene dict shaped like a validated storyboard dump."""
    scene = {
        "topic": topic,
        "first_frame_prompt": {"description": first_desc},
        "video_prompt": {"description": video_desc, "duration_seconds": 4},
        "voiceover_prompt": {"text": vo_text},
    }
    scene.update(extra)
    return scene


def _rendered_scene(topic, first_desc, video_desc, n=1):
    """A scene that has already been generated (carries asset ids)."""
    scene = _scene(topic, first_desc, video_desc)
    scene["scene_id"] = f"scene_{n}"
    scene["first_frame_prompt"]["asset_id"] = f"frame-asset-{n}"
    scene["video_prompt"]["asset_id"] = f"video-asset-{n}"
    scene["video_prompt"]["enrichment_asset_id"] = f"enrich-asset-{n}"
    return scene


# --------------------------------------------------------------------------
# scene_id assignment
# --------------------------------------------------------------------------


def test_every_scene_ends_up_with_a_unique_id():
    scenes = [_scene("a", "f", "v"), _scene("b", "f", "v")]
    assign_scene_ids(scenes)
    ids = [s["scene_id"] for s in scenes]
    assert all(ids) and len(set(ids)) == 2


def test_existing_ids_are_preserved():
    scenes = [_scene("a", "f", "v", scene_id="scene_7"), _scene("b", "f", "v")]
    assign_scene_ids(scenes)
    assert scenes[0]["scene_id"] == "scene_7"
    # The minted id must not collide with the one already in use.
    assert scenes[1]["scene_id"] != "scene_7"


def test_ids_are_reused_positionally_from_previous():
    # A rewrite carries no usable ids, so each position inherits the identity
    # it had before - that is what keeps rendered assets attached.
    previous = [_rendered_scene("a", "f", "v", 1), _rendered_scene("b", "f", "v", 2)]
    incoming = [_scene("a2", "f", "v"), _scene("b2", "f", "v")]
    assign_scene_ids(incoming, previous, trust_existing=False)
    assert [s["scene_id"] for s in incoming] == ["scene_1", "scene_2"]


def test_extra_scenes_get_non_colliding_ids():
    previous = [_rendered_scene("a", "f", "v", 1)]
    incoming = [_scene("a", "f", "v"), _scene("b", "f", "v"), _scene("c", "f", "v")]
    assign_scene_ids(incoming, previous, trust_existing=False)
    ids = [s["scene_id"] for s in incoming]
    assert len(set(ids)) == 3, f"ids must be unique, got {ids}"


# --------------------------------------------------------------------------
# The core regression: a re-run must not wipe rendered assets
# --------------------------------------------------------------------------


def test_unchanged_prompts_keep_their_assets():
    previous = {"scenes": [_rendered_scene("a", "frame one", "video one", 1)]}
    # The LLM re-emits an identical storyboard — with no asset ids, as always.
    incoming = {"scenes": [_scene("a", "frame one", "video one")]}

    merged = merge_storyboard(previous, incoming)
    scene = merged["scenes"][0]

    assert scene["first_frame_prompt"]["asset_id"] == "frame-asset-1"
    assert scene["video_prompt"]["asset_id"] == "video-asset-1"
    assert scene["video_prompt"]["enrichment_asset_id"] == "enrich-asset-1"


def test_changed_video_prompt_drops_only_that_asset():
    previous = {"scenes": [_rendered_scene("a", "frame one", "video one", 1)]}
    incoming = {"scenes": [_scene("a", "frame one", "a totally new action")]}

    scene = merge_storyboard(previous, incoming)["scenes"][0]

    # Video was rewritten, so its asset must go (it no longer matches).
    assert scene["video_prompt"].get("asset_id") is None
    assert scene["video_prompt"].get("enrichment_asset_id") is None
    # The untouched first frame keeps its asset.
    assert scene["first_frame_prompt"]["asset_id"] == "frame-asset-1"


def test_unchanged_voiceover_keeps_its_asset_ref():
    # Voiceover idempotency keys off `asset_ref` (a dict), not `asset_id`.
    prior = _rendered_scene("a", "frame one", "video one", 1)
    prior["voiceover_prompt"]["asset_ref"] = {"id": "vo-42", "asset_type": "audio"}
    previous = {"scenes": [prior]}
    incoming = {"scenes": [_scene("a", "frame one", "video one", vo_text="hello")]}

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["voiceover_prompt"]["asset_ref"]["id"] == "vo-42"


def test_rewritten_script_drops_the_voiceover_asset():
    prior = _rendered_scene("a", "frame one", "video one", 1)
    prior["voiceover_prompt"]["asset_ref"] = {"id": "vo-42"}
    previous = {"scenes": [prior]}
    incoming = {
        "scenes": [_scene("a", "frame one", "video one", vo_text="a new script")]
    }

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["voiceover_prompt"].get("asset_ref") is None


def test_changed_voice_gender_drops_the_voiceover_asset():
    # gender selects the TTS voice, so the recorded take is no longer valid.
    prior = _rendered_scene("a", "frame one", "video one", 1)
    prior["voiceover_prompt"]["asset_ref"] = {"id": "vo-42"}
    prior["voiceover_prompt"]["gender"] = "male"
    previous = {"scenes": [prior]}
    incoming = {"scenes": [_scene("a", "frame one", "video one")]}
    incoming["scenes"][0]["voiceover_prompt"]["gender"] = "female"

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["voiceover_prompt"].get("asset_ref") is None


def test_changed_duration_invalidates_video_asset():
    previous = {"scenes": [_rendered_scene("a", "frame one", "video one", 1)]}
    incoming = {"scenes": [_scene("a", "frame one", "video one")]}
    incoming["scenes"][0]["video_prompt"]["duration_seconds"] = 9

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["video_prompt"].get("asset_id") is None


def test_reordered_scenes_follow_their_scene_id():
    previous = {
        "scenes": [
            _rendered_scene("intro", "frame A", "video A", 1),
            _rendered_scene("outro", "frame B", "video B", 2),
        ]
    }
    # Same two scenes, swapped, each carrying its stable id.
    incoming = {
        "scenes": [
            _scene("outro", "frame B", "video B", scene_id="scene_2"),
            _scene("intro", "frame A", "video A", scene_id="scene_1"),
        ]
    }

    scenes = merge_storyboard(previous, incoming)["scenes"]

    # Assets must follow identity, not position.
    assert scenes[0]["video_prompt"]["asset_id"] == "video-asset-2"
    assert scenes[1]["video_prompt"]["asset_id"] == "video-asset-1"


def test_legacy_storyboard_without_scene_ids_matches_by_position():
    legacy = _scene("a", "frame one", "video one")
    legacy["video_prompt"]["asset_id"] = "legacy-video"
    previous = {"scenes": [legacy]}
    incoming = {"scenes": [_scene("a", "frame one", "video one")]}

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["video_prompt"]["asset_id"] == "legacy-video"
    assert scene["scene_id"]


def test_removed_scene_does_not_leak_its_asset():
    previous = {
        "scenes": [
            _rendered_scene("a", "frame A", "video A", 1),
            _rendered_scene("b", "frame B", "video B", 2),
        ]
    }
    incoming = {"scenes": [_scene("b", "frame B", "video B", scene_id="scene_2")]}

    scenes = merge_storyboard(previous, incoming)["scenes"]
    assert len(scenes) == 1
    assert scenes[0]["video_prompt"]["asset_id"] == "video-asset-2"


# --------------------------------------------------------------------------
# Surrounding state
# --------------------------------------------------------------------------


def test_first_generation_needs_no_previous():
    incoming = {"scenes": [_scene("a", "f", "v")]}
    merged = merge_storyboard(None, incoming)
    assert merged["scenes"][0]["scene_id"]


def test_voiceover_groups_survive_when_absent_from_incoming():
    previous = {
        "scenes": [_rendered_scene("a", "f", "v", 1)],
        "voiceover_groups": [{"group_id": "g1", "audio_asset_id": "vo-1"}],
    }
    incoming = {"scenes": [_scene("a", "f", "v")]}

    merged = merge_storyboard(previous, incoming)
    assert merged["voiceover_groups"][0]["audio_asset_id"] == "vo-1"


def test_incoming_voiceover_groups_win():
    previous = {
        "scenes": [_rendered_scene("a", "f", "v", 1)],
        "voiceover_groups": [{"group_id": "old"}],
    }
    incoming = {
        "scenes": [_scene("a", "f", "v")],
        "voiceover_groups": [{"group_id": "new"}],
    }

    merged = merge_storyboard(previous, incoming)
    assert merged["voiceover_groups"] == [{"group_id": "new"}]


def test_creative_content_from_incoming_always_wins():
    previous = {"scenes": [_rendered_scene("old topic", "old frame", "old video", 1)]}
    incoming = {"scenes": [_scene("new topic", "new frame", "new video")]}

    scene = merge_storyboard(previous, incoming)["scenes"][0]
    assert scene["topic"] == "new topic"
    assert scene["first_frame_prompt"]["description"] == "new frame"
    assert scene["video_prompt"]["description"] == "new video"


def test_merge_does_not_mutate_inputs():
    previous = {"scenes": [_rendered_scene("a", "f", "v", 1)]}
    incoming = {"scenes": [_scene("a", "f", "v")]}

    merge_storyboard(previous, incoming)

    assert "scene_id" not in incoming["scenes"][0]
    assert "asset_id" not in incoming["scenes"][0]["video_prompt"]


def test_storyboard_id_is_not_resurrected():
    previous = {"scenes": [_rendered_scene("a", "f", "v", 1)], "storyboard_id": "sb-1"}
    incoming = {"scenes": [_scene("a", "f", "v")]}

    merged = merge_storyboard(previous, incoming)
    assert not merged.get("storyboard_id")


# --------------------------------------------------------------------------
# Clearing assets so a scene can be re-rendered (I2)
# --------------------------------------------------------------------------


def test_find_scene_index_by_id():
    sb = {
        "scenes": [_rendered_scene("a", "f", "v", 1), _rendered_scene("b", "f", "v", 2)]
    }
    assert find_scene_index(sb, "scene_2") == 1
    assert find_scene_index(sb, "scene_9") is None


def test_find_scene_index_accepts_positional_fallback():
    sb = {"scenes": [_scene("a", "f", "v"), _scene("b", "f", "v")]}
    assert find_scene_index(sb, "1") == 1
    assert find_scene_index(sb, "5") is None


def test_clear_scene_assets_removes_every_reference():
    scene = _rendered_scene("a", "f", "v", 1)
    scene["voiceover_prompt"]["asset_ref"] = {"id": "vo-1"}

    cleared = clear_scene_assets(scene)

    assert cleared == 4  # frame, video, enrichment, voiceover
    assert "asset_id" not in scene["first_frame_prompt"]
    assert "asset_id" not in scene["video_prompt"]
    assert "enrichment_asset_id" not in scene["video_prompt"]
    assert "asset_ref" not in scene["voiceover_prompt"]
    # Creative content must survive — only the renders are dropped.
    assert scene["video_prompt"]["description"] == "v"


def test_clear_scene_assets_is_safe_on_ungenerated_scene():
    scene = _scene("a", "f", "v")
    assert clear_scene_assets(scene) == 0


# --------------------------------------------------------------------------
# Model-invented scene ids must not become permanent identity
# --------------------------------------------------------------------------


def test_ids_present_on_a_first_generation_are_left_alone():
    # Nothing to compare against yet, and the id may be a template's own
    # ("ugc_discovery_hook"), which downstream grouping relies on.
    incoming = {
        "scenes": [
            _scene("a", "f", "v", scene_id="ugc_discovery_hook"),
            _scene("b", "f", "v", scene_id="7f3a91c04b22"),
        ]
    }
    merged = merge_storyboard(None, incoming)
    assert [s["scene_id"] for s in merged["scenes"]] == [
        "ugc_discovery_hook",
        "7f3a91c04b22",
    ]


def test_llm_invented_ids_are_discarded_on_rewrite():
    previous = {"scenes": [_rendered_scene("a", "frame one", "video one", 1)]}
    incoming = {"scenes": [_scene("a", "frame one", "video one", scene_id="temp-9")]}

    scene = merge_storyboard(previous, incoming)["scenes"][0]

    # Positionally reunited with its real identity - and therefore its assets.
    assert scene["scene_id"] == "scene_1"
    assert scene["video_prompt"]["asset_id"] == "video-asset-1"


def test_ids_the_previous_storyboard_issued_are_honoured():
    previous = {
        "scenes": [
            _rendered_scene("a", "frame A", "video A", 1),
            _rendered_scene("b", "frame B", "video B", 2),
        ]
    }
    # A genuine reorder echoes ids that really exist; those must be trusted.
    incoming = {
        "scenes": [
            _scene("b", "frame B", "video B", scene_id="scene_2"),
            _scene("a", "frame A", "video A", scene_id="scene_1"),
        ]
    }
    scenes = merge_storyboard(previous, incoming)["scenes"]

    assert [s["scene_id"] for s in scenes] == ["scene_2", "scene_1"]
    assert scenes[0]["video_prompt"]["asset_id"] == "video-asset-2"


def test_direct_callers_may_still_trust_supplied_ids():
    # add_scene relabels an existing list and must not renumber it.
    scenes = [
        _scene("a", "f", "v", scene_id="scene_1"),
        _scene("new", "f", "v"),
    ]
    assign_scene_ids(scenes)
    assert scenes[0]["scene_id"] == "scene_1"
    assert scenes[1]["scene_id"] and scenes[1]["scene_id"] != "scene_1"


# --------------------------------------------------------------------------
# The real path: model_validate -> model_dump -> merge
#
# The dict fixtures above hand-write scene ids, which hides how ids actually
# arrive. In production they come from the Scene model - minted at validation,
# or set explicitly by a template - and a rewrite re-mints them. These tests go
# through that path.
# --------------------------------------------------------------------------


def _valid_scene(topic, scene_id=None, action="an action"):
    scene = {
        "topic": topic,
        "first_frame_prompt": {"description": "a frame"},
        "video_prompt": {"description": action, "duration_seconds": 4},
        "voiceover_prompt": {
            "text": "a line",
            "gender": "female",
            "description": "calm",
        },
    }
    if scene_id:
        scene["scene_id"] = scene_id
    return scene


def _dump(scenes):
    from demos.backend.ads_x.utils.storyboard.storyboard_model import Storyboard

    return Storyboard.model_validate(
        {"campaign_title": "T", "scenes": scenes}
    ).model_dump()


def test_a_templates_own_scene_id_is_never_overwritten():
    # Templates set meaningful ids and downstream grouping looks scenes up by
    # them; renaming one would break audio-to-scene alignment.
    merged = merge_storyboard(None, _dump([_valid_scene("hook", "ugc_discovery_hook")]))
    assert merged["scenes"][0]["scene_id"] == "ugc_discovery_hook"


def test_generated_ids_survive_a_first_generation():
    merged = merge_storyboard(None, _dump([_valid_scene("a"), _valid_scene("b")]))
    ids = [s["scene_id"] for s in merged["scenes"]]
    assert all(ids) and len(set(ids)) == 2


def test_a_rewrite_reattaches_scenes_to_their_original_identity():
    """The core case: re-validating mints new ids, which would orphan assets."""
    raw = [_valid_scene("a"), _valid_scene("b", "ugc_discovery_hook")]
    first = merge_storyboard(None, _dump(raw))
    for scene in first["scenes"]:
        scene["video_prompt"]["asset_id"] = f"vid-{scene['scene_id']}"
    original_ids = [s["scene_id"] for s in first["scenes"]]

    # The model re-emits the same storyboard; validation mints fresh ids.
    rewrite = _dump(raw)
    assert rewrite["scenes"][0]["scene_id"] != original_ids[0], "fixture assumption"

    merged = merge_storyboard(first, rewrite)

    assert [s["scene_id"] for s in merged["scenes"]] == original_ids
    assert [s["video_prompt"].get("asset_id") for s in merged["scenes"]] == [
        f"vid-{i}" for i in original_ids
    ]
