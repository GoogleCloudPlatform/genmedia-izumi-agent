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

"""Per-scene storyboard editing.

These are the tools a reviewer's requested changes turn into: edit one scene,
add or remove a scene, reorder the sequence. They exist because the alternative
- regenerating the whole storyboard - throws away every rendered asset and
every earlier edit.

Three rules hold throughout:

* Scenes are addressed by ``scene_id``, never by position, because an index
  stops identifying the same scene the moment anything is reordered or removed.
* Editing a prompt releases only that prompt's rendered asset. A scene whose
  visuals changed must be re-rendered; its untouched voiceover must not be.
* Structural edits leave other scenes' assets alone, so inserting a scene in
  the middle does not invalidate the four that were already generated.
"""

import logging
from typing import Any, Dict, Optional

from google.adk.tools.tool_context import ToolContext

from ...utils.common import common_utils
from ...utils.storyboard import storyboard_merge

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Which rendered asset each editable field invalidates.
_FIELD_TO_PROMPT = {
    "visual_action": "video_prompt",
    "first_frame": "first_frame_prompt",
    "voiceover": "voiceover_prompt",
    "duration_seconds": "video_prompt",
}

_PROMPT_ASSET_KEYS = {
    "video_prompt": ("asset_id", "enrichment_asset_id"),
    "first_frame_prompt": ("asset_id",),
    "voiceover_prompt": ("asset_ref", "asset_id"),
}


NO_STORYBOARD = "No storyboard found in session state."


def _load(tool_context: ToolContext) -> Optional[Dict[str, Any]]:
    """Returns the storyboard in state, or None if there is not a usable one."""
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not isinstance(storyboard, dict) or not isinstance(
        storyboard.get("scenes"), list
    ):
        return None
    return storyboard


def _unknown_scene(storyboard: Dict[str, Any], scene_id: str) -> str:
    available = [s.get("scene_id") for s in storyboard.get("scenes") or []]
    return f"Unknown scene_id '{scene_id}'. Available: {available}"


def _persist(tool_context: ToolContext, storyboard: Dict[str, Any]) -> None:
    tool_context.state[common_utils.STORYBOARD_KEY] = storyboard


def _release(prompt: Any, prompt_key: str) -> int:
    """Drops the rendered asset for one prompt, so it will be generated again."""
    if not isinstance(prompt, dict):
        return 0
    released = 0
    for key in _PROMPT_ASSET_KEYS.get(prompt_key, ()):
        if prompt.pop(key, None) is not None:
            released += 1
    return released


async def edit_scene(
    tool_context: ToolContext,
    scene_id: str,
    visual_action: str = "",
    first_frame: str = "",
    voiceover: str = "",
    duration_seconds: float = 0.0,
) -> ToolResult:
    """Edits one scene in place, leaving every other scene untouched.

    Supply only the fields being changed; omitted fields keep their current
    value. Any field that is changed releases the media it invalidates, so the
    scene re-renders on the next generation pass while unaffected media is kept.

    Args:
        scene_id: Stable id of the scene to edit (e.g. "scene_2").
        visual_action: New description of what happens on screen.
        first_frame: New description of the scene's opening frame.
        voiceover: New spoken line for this scene.
        duration_seconds: New target duration, in seconds.
    """
    storyboard = _load(tool_context)
    if storyboard is None:
        return tool_failure(NO_STORYBOARD)

    index = storyboard_merge.find_scene_index(storyboard, scene_id)
    if index is None:
        return tool_failure(_unknown_scene(storyboard, scene_id))

    scene = storyboard["scenes"][index]
    changes: list[str] = []
    invalidated: set[str] = set()

    if visual_action.strip():
        scene.setdefault("video_prompt", {})["description"] = visual_action.strip()
        changes.append("visual action")
        invalidated.add(_FIELD_TO_PROMPT["visual_action"])

    if first_frame.strip():
        scene.setdefault("first_frame_prompt", {})["description"] = first_frame.strip()
        changes.append("first frame")
        invalidated.add(_FIELD_TO_PROMPT["first_frame"])

    if voiceover.strip():
        scene.setdefault("voiceover_prompt", {})["text"] = voiceover.strip()
        changes.append("voiceover")
        invalidated.add(_FIELD_TO_PROMPT["voiceover"])

    if duration_seconds and duration_seconds > 0:
        scene.setdefault("video_prompt", {})["duration_seconds"] = duration_seconds
        scene["duration_seconds"] = duration_seconds
        changes.append("duration")
        invalidated.add(_FIELD_TO_PROMPT["duration_seconds"])

    if not changes:
        return tool_failure(
            "No changes supplied. Provide at least one of visual_action, "
            "first_frame, voiceover or duration_seconds."
        )

    released = sum(_release(scene.get(key), key) for key in invalidated)
    _persist(tool_context, storyboard)

    logger.info("Edited scene %s (%s).", scene_id, ", ".join(changes))
    return tool_success(
        f"Updated {', '.join(changes)} on scene '{scene_id}'. "
        f"Released {released} rendered asset(s) for re-rendering."
    )


async def add_scene(
    tool_context: ToolContext,
    visual_action: str,
    voiceover: str = "",
    duration_seconds: float = 4.0,
    after_scene_id: str = "",
) -> ToolResult:
    """Inserts a new scene without disturbing the scenes already rendered.

    Args:
        visual_action: What happens on screen in the new scene.
        voiceover: Spoken line for the new scene, if any.
        duration_seconds: Target duration, in seconds.
        after_scene_id: Insert directly after this scene. Leave empty to append
            the new scene at the end.
    """
    storyboard = _load(tool_context)
    if storyboard is None:
        return tool_failure(NO_STORYBOARD)

    if not visual_action.strip():
        return tool_failure("A new scene needs a visual_action.")

    scenes = storyboard["scenes"]
    position = len(scenes)
    if after_scene_id.strip():
        anchor = storyboard_merge.find_scene_index(storyboard, after_scene_id)
        if anchor is None:
            return tool_failure(_unknown_scene(storyboard, after_scene_id))
        position = anchor + 1

    scene = {
        "topic": visual_action.strip()[:60],
        "first_frame_prompt": {"description": visual_action.strip()},
        "video_prompt": {
            "description": visual_action.strip(),
            "duration_seconds": duration_seconds,
        },
        "voiceover_prompt": {"text": voiceover.strip()},
        "duration_seconds": duration_seconds,
    }
    scenes.insert(position, scene)

    # Mint an id for the newcomer only; existing ids must survive so their
    # rendered media stays attached to the right scene.
    storyboard_merge.assign_scene_ids(scenes)
    _persist(tool_context, storyboard)

    return tool_success(
        f"Added scene '{scene.get('scene_id')}' at position {position + 1} of "
        f"{len(scenes)}. It has no media yet and will render on the next pass."
    )


async def remove_scene(tool_context: ToolContext, scene_id: str) -> ToolResult:
    """Deletes a scene from the storyboard.

    Args:
        scene_id: Stable id of the scene to remove (e.g. "scene_3").
    """
    storyboard = _load(tool_context)
    if storyboard is None:
        return tool_failure(NO_STORYBOARD)

    index = storyboard_merge.find_scene_index(storyboard, scene_id)
    if index is None:
        return tool_failure(_unknown_scene(storyboard, scene_id))

    if len(storyboard["scenes"]) <= 1:
        return tool_failure(
            "Cannot remove the only scene; a storyboard needs at least one."
        )

    removed = storyboard["scenes"].pop(index)
    _persist(tool_context, storyboard)

    logger.info("Removed scene %s.", scene_id)
    return tool_success(
        f"Removed scene '{scene_id}' ({removed.get('topic', 'untitled')}). "
        f"{len(storyboard['scenes'])} scene(s) remain."
    )


async def reorder_scenes(tool_context: ToolContext, scene_ids: list[str]) -> ToolResult:
    """Rearranges the scenes into the given order.

    Reordering moves the scenes themselves, so any media already rendered
    travels with its scene and nothing needs regenerating.

    Args:
        scene_ids: Every scene id, in the order they should now play.
    """
    storyboard = _load(tool_context)
    if storyboard is None:
        return tool_failure(NO_STORYBOARD)

    scenes = storyboard["scenes"]
    by_id = {str(s.get("scene_id")): s for s in scenes if isinstance(s, dict)}

    requested = [str(s) for s in scene_ids]
    if len(requested) != len(set(requested)):
        return tool_failure("The same scene id appears more than once.")

    missing = [s for s in requested if s not in by_id]
    if missing:
        return tool_failure(f"Unknown scene id(s): {missing}. Available: {list(by_id)}")

    # Demanding the full set avoids silently dropping or duplicating a scene.
    omitted = [s for s in by_id if s not in requested]
    if omitted:
        return tool_failure(
            f"Every scene must be listed. Missing from the new order: {omitted}"
        )

    storyboard["scenes"] = [by_id[s] for s in requested]
    _persist(tool_context, storyboard)

    logger.info("Reordered scenes to %s.", requested)
    return tool_success(f"Scenes reordered: {' -> '.join(requested)}.")
