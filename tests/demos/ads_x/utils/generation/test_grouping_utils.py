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

"""Tests for grouping_utils.create_voiceover_groups.

These tests intentionally cover the stable-scene-ids invariant added
in the scene_id migration: that voiceover groups reference their
member scenes by stable ``scene_id`` (not positional array index) so
that a downstream scene reorder does NOT silently misalign voiceovers.
That invariant is the M2-enabling change; without it, the moment a
user can reorder scenes the wrong audio is stitched to the wrong scene
with no error raised.
"""

from demos.backend.ads_x.utils.generation.grouping_utils import (
    MAX_GROUP_DURATION,
    create_voiceover_groups,
)
from demos.backend.ads_x.utils.storyboard.storyboard_model import (
    ImagePrompt,
    Scene,
    SpeechPrompt,
    Storyboard,
    VideoPrompt,
)


def _make_scene(
    scene_id: str, duration: float = 4.0, voiceover_text: str = "..."
) -> Scene:
    """Builds a minimal valid Scene for grouping tests."""
    return Scene(
        scene_id=scene_id,
        topic=f"topic-{scene_id}",
        first_frame_prompt=ImagePrompt(description=f"first-frame-{scene_id}"),
        video_prompt=VideoPrompt(
            description=f"video-{scene_id}",
            duration_seconds=duration,
        ),
        voiceover_prompt=SpeechPrompt(
            text=voiceover_text,
            gender="female",
            description="natural",
        ),
        duration_seconds=duration,
    )


def _make_storyboard(scenes: list[Scene]) -> Storyboard:
    return Storyboard(scenes=scenes)


def test_groups_reference_scenes_by_stable_id_not_position() -> None:
    """Every VoiceoverGroup.scene_ids entry must be one of the scenes'
    ``scene_id`` values — never a positional array index. This is the
    M2 invariant: if the caller subsequently reorders scenes, the
    group's members are still identifiable by their stable IDs.
    """
    scenes = [
        _make_scene(scene_id="hook"),
        _make_scene(scene_id="middle"),
        _make_scene(scene_id="cta"),  # last scene => CTA block per heuristic
    ]
    sb = _make_storyboard(scenes)

    groups = create_voiceover_groups(sb)

    # Extract all scene_ids across all groups; must be a subset of the
    # actual scene_ids on the storyboard.
    referenced_ids = {sid for g in groups for sid in g.scene_ids}
    expected_ids = {s.scene_id for s in scenes}
    assert referenced_ids <= expected_ids

    # Belt + suspenders: no group.scene_ids entry should ever be an int
    # (which would indicate a leftover from the pre-migration positional
    # scheme).
    for group in groups:
        for sid in group.scene_ids:
            assert isinstance(sid, str), (
                f"scene_ids must be strings; got {type(sid).__name__} in group"
                f" {group.group_id}"
            )


def test_reorder_survives_group_membership() -> None:
    """Grouping produces groups; if the caller later reorders scenes,
    the group's scene_ids still identify the same scenes (the objects
    the IDs point at moved position but retained their identity).

    This models the M2 collaborative-edit path: user reorders in the UI,
    but the agent's pre-existing groups are still coherent because they
    reference by stable ID.
    """
    scenes = [
        _make_scene(scene_id="scene_a"),
        _make_scene(scene_id="scene_b"),
        _make_scene(scene_id="scene_c"),
    ]
    sb = _make_storyboard(scenes)

    groups = create_voiceover_groups(sb)
    # Snapshot the set of (group_id, frozenset(scene_ids)) before reorder.
    before = {(g.group_id, frozenset(g.scene_ids)) for g in groups}

    # Simulate a user-driven reorder: reverse the scenes.
    reordered_scenes = list(reversed(scenes))
    _reordered_sb = _make_storyboard(reordered_scenes)

    # If we were to LOOK UP the group's scenes by ID in the reordered
    # storyboard, we'd find the same scene objects — because scene_id
    # is stable across reorder.
    scene_by_id = {s.scene_id: s for s in reordered_scenes}
    for group in groups:
        for sid in group.scene_ids:
            assert sid in scene_by_id, (
                f"scene_id {sid} missing after reorder — stable-ID" f" invariant broken"
            )

    # The groups themselves are unchanged (their scene_ids don't
    # rewrite themselves on the storyboard reorder — the caller
    # controls that).
    after = {(g.group_id, frozenset(g.scene_ids)) for g in groups}
    assert before == after


def test_last_scene_gets_cta_block() -> None:
    """The heuristic in _get_narrative_block assigns CTA to the last
    scene by position. Verify this survives the scene_id migration.
    """
    scenes = [
        _make_scene(scene_id="s0"),
        _make_scene(scene_id="s1"),
        _make_scene(scene_id="s2_final"),
    ]
    groups = create_voiceover_groups(_make_storyboard(scenes))

    # The CTA scene should be in a group with narrative_block == "CTA".
    cta_groups = [g for g in groups if g.narrative_block == "CTA"]
    assert len(cta_groups) == 1
    assert "s2_final" in cta_groups[0].scene_ids


def test_duration_flush_creates_new_group() -> None:
    """When accumulated duration would exceed MAX_GROUP_DURATION, the
    current buffer must flush into its own group before appending the
    next scene.
    """
    # Three scenes of length just over half MAX_GROUP_DURATION each —
    # any two exceed the cap, so we expect three groups (or two,
    # depending on rounding, but definitely more than one).
    per_scene = MAX_GROUP_DURATION * 0.6
    scenes = [_make_scene(scene_id=f"s{i}", duration=per_scene) for i in range(3)]
    groups = create_voiceover_groups(_make_storyboard(scenes))

    assert len(groups) > 1, (
        f"expected multiple groups due to duration cap, got {len(groups)}:"
        f" durations were {[g.total_duration for g in groups]}"
    )


def test_scene_auto_generates_scene_id_if_missing() -> None:
    """Scene.scene_id defaults to an auto-generated short UUID.
    Templates pass their own; LLM-generated scenes get one for free.
    """
    a = Scene(
        topic="anon",
        first_frame_prompt=ImagePrompt(description="x"),
        video_prompt=VideoPrompt(description="x", duration_seconds=4.0),
        voiceover_prompt=SpeechPrompt(text="x", gender="female", description="x"),
    )
    b = Scene(
        topic="anon",
        first_frame_prompt=ImagePrompt(description="x"),
        video_prompt=VideoPrompt(description="x", duration_seconds=4.0),
        voiceover_prompt=SpeechPrompt(text="x", gender="female", description="x"),
    )
    assert a.scene_id
    assert b.scene_id
    assert a.scene_id != b.scene_id, "auto-generated IDs must be unique"


def test_original_scripts_align_with_scene_ids() -> None:
    """Within a group, scene_ids[i] corresponds to original_scripts[i].
    This alignment is preserved through the migration.
    """
    scenes = [
        _make_scene(scene_id="alpha", voiceover_text="alpha_script"),
        _make_scene(scene_id="beta", voiceover_text="beta_script"),
    ]
    groups = create_voiceover_groups(_make_storyboard(scenes))

    # Both scenes end up in a single group (durations fit, same block).
    assert len(groups) >= 1
    for group in groups:
        assert len(group.scene_ids) == len(group.original_scripts)
        # The order matches — nth script came from nth scene.
        for sid, script in zip(group.scene_ids, group.original_scripts):
            expected_script = f"{sid}_script"
            assert script == expected_script, (
                f"script alignment broken: scene_id={sid} got script="
                f"{script!r}, expected {expected_script!r}"
            )
