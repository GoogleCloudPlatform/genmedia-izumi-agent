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

"""Tests for rewording a scene the safety filter refused.

The same words are refused again, so the reviewer's words replace them, and
only what the new words affect is rendered again.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from demos.backend.ads_x.tools.generation import generation_tools
from mediagent_kit.utils.retry import ContentBlockedError

ART = "[ART DIRECTION (NON-NEGOTIABLE): warm light]"
REFUSED = {"kind": "blocked", "message": "The video was blocked: refused."}


def _ctx(stage="generation"):
    scene = {
        "scene_id": "scene_2",
        "first_frame_prompt": {
            "description": f"a model at a vanity\n\n{ART}",
            "asset_id": "img-2",
            "asset_ref": {"id": "img-2", "asset_type": "generated"},
        },
        "video_prompt": {
            "description": f"she applies the foundation\n\n{ART}",
            "asset_id": "img-2",
            "asset_ref": {"id": "img-2", "asset_type": "generated"},
            "enriched_description": "an elaborate prompt",
            "render_failure": dict(REFUSED),
        },
    }
    return SimpleNamespace(
        state={"storyboard": {"scenes": [scene]}, "stage_completed": stage}
    )


def _scene(ctx):
    return ctx.state["storyboard"]["scenes"][0]


@pytest.fixture
def render():
    with patch.object(
        generation_tools,
        "generate_single_scene",
        new=AsyncMock(return_value={"status": "succeeded", "result": "ok"}),
    ) as rendered:
        yield rendered


async def test_a_new_action_replaces_the_refused_one_and_keeps_the_look(render):
    ctx = _ctx()

    result = await generation_tools.rewrite_scene(
        ctx, "scene_2", action="the bottle turns in soft light"
    )

    video = _scene(ctx)["video_prompt"]
    assert result["status"] == "succeeded"
    assert video["description"] == f"the bottle turns in soft light\n\n{ART}"
    assert "render_failure" not in video
    assert "asset_ref" not in video and "enriched_description" not in video


async def test_a_new_action_keeps_the_frame_and_renders_the_clip(render):
    ctx = _ctx()

    await generation_tools.rewrite_scene(ctx, "scene_2", action="the bottle turns")

    assert _scene(ctx)["first_frame_prompt"]["asset_id"] == "img-2"
    render.assert_awaited_once_with(ctx, 0, frame_only=False)


async def test_a_new_frame_also_needs_a_new_clip(render):
    ctx = _ctx()

    await generation_tools.rewrite_scene(ctx, "scene_2", opening_frame="a bottle")

    scene = _scene(ctx)
    assert scene["first_frame_prompt"]["description"] == f"a bottle\n\n{ART}"
    assert "asset_id" not in scene["first_frame_prompt"]
    assert "asset_id" not in scene["video_prompt"]
    render.assert_awaited_once_with(ctx, 0, frame_only=False)


async def test_before_the_videos_only_the_frame_is_rendered(render):
    ctx = _ctx(stage="storyboard")

    await generation_tools.rewrite_scene(ctx, "scene_2", opening_frame="a bottle")

    render.assert_awaited_once_with(ctx, 0, frame_only=True)


async def test_before_the_videos_a_new_action_waits_for_the_video_pass(render):
    ctx = _ctx(stage="storyboard")

    result = await generation_tools.rewrite_scene(
        ctx, "scene_2", action="the bottle turns"
    )

    assert result["status"] == "succeeded"
    render.assert_not_awaited()


async def test_refused_again_it_asks_for_other_words(render):
    ctx = _ctx()

    async def refuse_again(context, index, frame_only):
        _scene(context)["video_prompt"]["render_failure"] = dict(REFUSED)
        return {"status": "succeeded", "result": "ok"}

    render.side_effect = refuse_again

    result = await generation_tools.rewrite_scene(
        ctx, "scene_2", action="the bottle turns"
    )

    assert result["status"] == "failed"
    assert "different wording" in result["error_message"]


async def test_it_needs_new_words():
    result = await generation_tools.rewrite_scene(_ctx(), "scene_2")

    assert result["status"] == "failed"


async def test_an_unknown_scene_is_refused():
    result = await generation_tools.rewrite_scene(_ctx(), "scene_9", action="x")

    assert result["status"] == "failed"
    assert "scene_2" in result["error_message"], "list the scenes there are"


def test_a_refusal_is_recorded_as_one_whatever_its_text():
    failure = generation_tools._describe_render_failure(
        ContentBlockedError("Request blocked for an unspecified policy reason.")
    )

    assert failure["kind"] == "blocked"
    assert failure["message"].startswith("The video was blocked")


def test_a_refused_frame_is_described_as_a_frame():
    failure = generation_tools._describe_render_failure(
        ContentBlockedError("blocked"), subject="opening frame"
    )

    assert failure["message"].startswith("The opening frame was blocked")
