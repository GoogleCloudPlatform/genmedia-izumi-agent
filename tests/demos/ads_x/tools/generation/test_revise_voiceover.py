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

"""Tests for re-recording one scene's narration in a finished campaign.

The stitched video plays each voiceover group's take, not a per-scene
recording, so changing what is heard over a scene means re-recording the group
that scene belongs to, and only that group.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from demos.backend.ads_x.tools.generation import generation_tools


def _scene(scene_id, line, seconds):
    return {
        "scene_id": scene_id,
        "topic": scene_id,
        "voiceover_prompt": {"text": line, "description": "warm"},
        "video_prompt": {"duration_seconds": seconds},
    }


def _storyboard(grouped=True):
    storyboard = {
        "scenes": [
            _scene("scene_1", "Line one.", 4),
            _scene("scene_2", "Line two.", 4),
            _scene("scene_3", "Old closing line.", 3),
        ]
    }
    if grouped:
        storyboard["voiceover_groups"] = [
            {
                "group_id": "main",
                "scene_ids": ["scene_1", "scene_2"],
                "total_duration": 8.0,
                "original_scripts": ["Line one.", "Line two."],
                "narrative_block": "MAIN",
                "audio_asset_ref": {"id": "vo-main"},
            },
            {
                "group_id": "cta",
                "scene_ids": ["scene_3"],
                "total_duration": 3.0,
                "original_scripts": ["Old closing line."],
                "narrative_block": "CTA",
                "audio_asset_ref": {"id": "vo-cta"},
            },
        ]
    return storyboard


def _ctx(storyboard):
    return SimpleNamespace(
        state={"storyboard": storyboard, "workspace_id": "ws-1"},
        actions=SimpleNamespace(escalate=None),
    )


async def _record(group, workspace_id, style_prompt, group_index, rewrite=True):
    group.rewritten_script = " ".join(group.original_scripts)
    group.audio_asset_ref = {"id": "vo-new"}
    return SimpleNamespace(id="vo-new")


@pytest.fixture
def recorder():
    with patch.object(
        generation_tools.voiceover_tools,
        "generate_group_voiceover",
        new=AsyncMock(side_effect=_record),
    ) as recorded:
        yield recorded


async def test_only_the_take_holding_the_scene_is_rerecorded(recorder):
    ctx = _ctx(_storyboard())

    result = await generation_tools.revise_voiceover(
        ctx, "scene_3", line="Find it at Globoplay."
    )

    assert result["status"] == "succeeded"
    recorder.assert_awaited_once()
    group = recorder.await_args.kwargs["group"]
    assert group.group_id == "cta"
    assert group.original_scripts == ["Find it at Globoplay."]

    storyboard = ctx.state["storyboard"]
    assert storyboard["voiceover_groups"][1]["audio_asset_ref"]["id"] == "vo-new"
    assert storyboard["voiceover_groups"][0]["audio_asset_ref"]["id"] == "vo-main"
    assert storyboard["scenes"][2]["voiceover_prompt"]["text"] == (
        "Find it at Globoplay."
    )
    # The reviewer's own words, for a scene narrated alone, are not rewritten.
    assert recorder.await_args.kwargs["rewrite"] is False


async def test_a_line_inside_a_longer_take_is_rewritten_into_it(recorder):
    ctx = _ctx(_storyboard())

    await generation_tools.revise_voiceover(ctx, "scene_2", line="A new middle.")

    group = recorder.await_args.kwargs["group"]
    assert group.original_scripts == ["Line one.", "A new middle."]
    assert recorder.await_args.kwargs["rewrite"] is True


async def test_without_a_new_line_the_current_one_is_recorded_again(recorder):
    ctx = _ctx(_storyboard())

    await generation_tools.revise_voiceover(ctx, "scene_1")

    group = recorder.await_args.kwargs["group"]
    assert group.group_id == "main"
    assert group.original_scripts == ["Line one.", "Line two."]


async def test_an_unknown_scene_is_refused(recorder):
    result = await generation_tools.revise_voiceover(_ctx(_storyboard()), "scene_9")

    assert result["status"] == "failed"
    assert "scene_3" in result["error_message"]
    recorder.assert_not_awaited()


async def test_a_failed_recording_keeps_the_previous_take(recorder):
    recorder.side_effect = None
    recorder.return_value = None
    ctx = _ctx(_storyboard())

    result = await generation_tools.revise_voiceover(ctx, "scene_3", line="New line.")

    assert result["status"] == "failed"
    storyboard = ctx.state["storyboard"]
    assert storyboard["voiceover_groups"][1]["audio_asset_ref"]["id"] == "vo-cta"
    assert storyboard["scenes"][2]["voiceover_prompt"]["text"] == "Old closing line."


async def test_a_scene_narrated_on_its_own_is_rerecorded_on_its_own():
    """Without groups, the stitch plays each scene's own recording."""
    storyboard = _storyboard(grouped=False)
    storyboard["scenes"][2]["voiceover_prompt"]["asset_ref"] = {"id": "vo-old"}

    async def record_scene(workspace_id, voiceover_prompt, index, **kwargs):
        # The previous take is released first, or the recorder skips the scene
        # as already narrated.
        assert "asset_ref" not in voiceover_prompt
        voiceover_prompt["asset_ref"] = {"id": "vo-scene"}
        return SimpleNamespace(id="vo-scene")

    with patch.object(
        generation_tools.generation_helpers,
        "generate_scene_voiceover",
        new=AsyncMock(side_effect=record_scene),
    ):
        ctx = _ctx(storyboard)
        result = await generation_tools.revise_voiceover(
            ctx, "scene_3", line="New line."
        )

    assert result["status"] == "succeeded"
    prompt = ctx.state["storyboard"]["scenes"][2]["voiceover_prompt"]
    assert prompt["asset_ref"]["id"] == "vo-scene"
    assert prompt["text"] == "New line."
