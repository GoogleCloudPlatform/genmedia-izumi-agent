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

"""Wholesale regeneration, as opposed to targeted edits.

A reviewer has two different kinds of dissatisfaction, and they need different
answers. "Make scene 2 shorter" is a correction, handled by the editing tools:
change one thing, keep everything else. "I don't like this at all, try again" is
a rejection — no sequence of edits gets there, because the reviewer is not
asking for the current work adjusted, they are asking for different work.

These tools serve the second case. They deliberately discard, because a
regeneration that quietly preserved the thing being rejected would not be a
regeneration.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from google.adk.tools.tool_context import ToolContext

from utils.adk import resolve_workspace_id

from ...utils.common import common_utils
from ...utils.generation import generation_helpers
from ...utils.storyboard import storyboard_merge

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Guidance left for the storyboard agent when a storyboard is thrown away, so
# the replacement differs in the way the reviewer asked for.
REVISION_GUIDANCE_KEY = "storyboard_revision_guidance"


def _storyboard(tool_context: ToolContext) -> Optional[Dict[str, Any]]:
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    return storyboard if isinstance(storyboard, dict) else None


async def regenerate_storyboard(
    tool_context: ToolContext, guidance: str = ""
) -> ToolResult:
    """Throws away the current storyboard so a different one can be written.

    Use this when the reviewer rejects the storyboard as a whole rather than
    asking for specific changes — editing cannot get from a wrong concept to a
    right one. For anything narrower, prefer `edit_scene` and friends, which
    keep the work that was already approved and paid for.

    This only clears the way. Write the replacement immediately afterwards by
    calling the storyboard generator, or the campaign is left with no
    storyboard at all.

    Args:
        guidance: What should be different this time. Recorded so the
            replacement is not a re-roll of the same idea.
    """
    storyboard = _storyboard(tool_context)
    if storyboard is None:
        return tool_failure("There is no storyboard to regenerate.")

    scenes = storyboard.get("scenes") or []
    rendered = sum(
        1
        for scene in scenes
        if isinstance(scene, dict) and (scene.get("video_prompt") or {}).get("asset_id")
    )

    tool_context.state[common_utils.STORYBOARD_KEY] = None
    if guidance.strip():
        tool_context.state[REVISION_GUIDANCE_KEY] = guidance.strip()

    logger.info(
        "Storyboard discarded for regeneration (%d scene(s), %d rendered).",
        len(scenes),
        rendered,
    )

    lost = (
        f" {rendered} rendered clip(s) are discarded with it."
        if rendered
        else " Nothing had been rendered yet."
    )
    return tool_success(
        f"Discarded the {len(scenes)}-scene storyboard.{lost} Write the "
        "replacement now, taking the reviewer's direction into account."
    )


async def regenerate_music(
    tool_context: ToolContext, description: str = ""
) -> ToolResult:
    """Re-renders the campaign's background music.

    Args:
        description: A new description of the music wanted. Leave empty to
            re-render the existing brief for a different take.
    """
    storyboard = _storyboard(tool_context)
    if storyboard is None:
        return tool_failure("There is no storyboard, so there is no music to redo.")

    prompt = storyboard.get("background_music_prompt")
    if not isinstance(prompt, dict):
        return tool_failure("This campaign has no background music track.")

    if description.strip():
        prompt["description"] = description.strip()

    # Music generation skips any track that already has a reference, so the
    # reference has to go before it will render again.
    prompt.pop("asset_ref", None)
    prompt.pop("asset_id", None)

    # Render here rather than only releasing the reference, matching
    # regenerate_scene. A released track leaves the storyboard declaring music
    # that no longer exists, and the next stitch produces a silent cut.
    workspace_id, ws_error = resolve_workspace_id(tool_context)
    if ws_error:
        return tool_failure(ws_error)
    logger.info(
        "Re-rendering background music %s: %s",
        "with a new brief" if description.strip() else "for a different take",
        prompt.get("description", "")[:120],
    )
    asset = await generation_helpers.generate_background_music(
        workspace_id, prompt, uuid.uuid4().hex[:4]
    )
    tool_context.state[common_utils.STORYBOARD_KEY] = storyboard

    if asset is None:
        logger.error("Background music re-render produced no track.")
        return tool_failure(
            "The music could not be re-rendered, so the campaign now has no "
            "background track. Try again, or adjust the description."
        )

    what = "a new brief" if description.strip() else "a different take"
    logger.info("Background music re-rendered (asset %s).", asset.id)
    return tool_success(f"Background music re-rendered with {what}.")


async def regenerate_all_media(
    tool_context: ToolContext, guidance: str = ""
) -> ToolResult:
    """Releases every rendered clip so the whole cut is produced again.

    Use this only when the reviewer rejects the video as a whole. If they named
    particular clips, `regenerate_scene` re-renders just those and leaves the
    rest — which is nearly always what they meant, and far cheaper.

    Args:
        guidance: Direction to fold into every scene's visual prompt.
    """
    storyboard = _storyboard(tool_context)
    if storyboard is None or not storyboard.get("scenes"):
        return tool_failure("There is no storyboard, so there is nothing to re-render.")

    scenes = storyboard["scenes"]
    released = 0
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        if guidance.strip():
            for prompt_key in ("first_frame_prompt", "video_prompt"):
                prompt = scene.get(prompt_key)
                if isinstance(prompt, dict) and prompt.get("description"):
                    prompt["description"] = (
                        f"{prompt['description'].strip()}\n\n"
                        f"**REVISION DIRECTION:** {guidance.strip()}"
                    )
        released += storyboard_merge.clear_scene_assets(scene)

    # The stitched cut is assembled from clips that no longer exist. Cleared by
    # assignment rather than deletion: ADK's State supports neither pop nor del,
    # so removing a key raises at runtime.
    tool_context.state["final_video_asset_id"] = None
    tool_context.state["final_video_asset_ref"] = None
    tool_context.state[common_utils.STORYBOARD_KEY] = storyboard

    logger.info(
        "Released %d asset(s) across %d scene(s) for a full re-render.",
        released,
        len(scenes),
    )
    return tool_success(
        f"Released {released} asset(s) across all {len(scenes)} scene(s). "
        "Generate the media again, then restitch."
    )
