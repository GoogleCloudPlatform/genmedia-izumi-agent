# Copyright 2025 Google LLC
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

"""Utilities for grouping storyboard scenes for better voiceover prosody."""

import logging
import uuid
from typing import List, Dict

from ..storyboard.storyboard_model import Storyboard, VoiceoverGroup, Scene

logger = logging.getLogger(__name__)

MAX_GROUP_DURATION = (
    12.5  # Seconds - Encourages a natural 3-group structure for 30s ads.
)


def _get_narrative_block(
    scene_index: int, total_scenes: int, scene_id: str = ""
) -> str:
    """
    Determines the narrative block (MAIN, CTA) for a scene.

    Heuristics:
    - Last scene is CTA.
    - Everything else is MAIN.
    """
    # Keyword override
    sid = scene_id.lower() if scene_id else ""
    if "cta" in sid or "end" in sid:
        return "CTA"

    # Positional fallback
    if scene_index == total_scenes - 1:
        return "CTA"

    return "MAIN"


def create_voiceover_groups(storyboard: Storyboard) -> List[VoiceoverGroup]:
    """
    Groups consecutive scenes into VoiceoverGroups based on narrative structure
    and duration constraints.

    Groups reference their member scenes by stable ``scene_id`` rather than
    positional array index, so a downstream reorder does not silently
    misalign voiceovers.
    """
    groups: List[VoiceoverGroup] = []
    scenes = storyboard.scenes
    total_scenes = len(scenes)

    current_scene_ids: List[str] = []
    current_scripts: List[str] = []
    current_duration: float = 0.0
    current_block: str = ""

    for i, scene in enumerate(scenes):
        # Narrative block is determined by position + scene_id keyword. Position
        # is still used because it's a heuristic about narrative arc
        # (last scene = CTA), not an identity claim.
        block = _get_narrative_block(i, total_scenes, scene.scene_id)

        # Flush the current buffer if:
        # 1. Block changed (e.g. MAIN -> CTA)
        # 2. Duration would exceed the per-group limit
        is_new_group = len(current_scene_ids) == 0
        block_changed = (block != current_block) and not is_new_group
        duration_exceeded = (
            current_duration + scene.duration_seconds > MAX_GROUP_DURATION
        ) and not is_new_group

        if block_changed or duration_exceeded:
            group_id = uuid.uuid4().hex[:8]
            groups.append(
                VoiceoverGroup(
                    group_id=group_id,
                    scene_ids=list(current_scene_ids),
                    total_duration=current_duration,
                    original_scripts=list(current_scripts),
                    narrative_block=current_block,
                )
            )
            current_scene_ids = []
            current_scripts = []
            current_duration = 0.0

        current_scene_ids.append(scene.scene_id)
        current_scripts.append(scene.voiceover_prompt.text)
        current_duration += scene.duration_seconds
        current_block = block

    # Flush any remaining scenes
    if current_scene_ids:
        group_id = uuid.uuid4().hex[:8]
        groups.append(
            VoiceoverGroup(
                group_id=group_id,
                scene_ids=list(current_scene_ids),
                total_duration=current_duration,
                original_scripts=list(current_scripts),
                narrative_block=current_block,
            )
        )

    logger.info(f"Grouping complete. Created {len(groups)} voiceover groups.")
    # Log the scene_id membership of each group so the stable-scene-id
    # audit trail is complete from grouping to stitching. Cross-reference
    # with the "Video track built" log in stitching_tools to verify that
    # every group's scene_ids appear in the stitch's scene_id_to_clip_index.
    for g in groups:
        logger.info(
            "  group_id=%s block=%s duration=%.1fs scene_ids=%s",
            g.group_id,
            g.narrative_block,
            g.total_duration,
            g.scene_ids,
        )
    return groups
