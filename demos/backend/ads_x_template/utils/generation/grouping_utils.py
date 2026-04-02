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
    """
    groups: List[VoiceoverGroup] = []
    scenes = storyboard.scenes
    total_scenes = len(scenes)

    current_scene_indices: List[int] = []
    current_scripts: List[str] = []
    current_duration: float = 0.0
    current_block: str = ""

    for i, scene in enumerate(scenes):
        # Determine block for this scene
        # We don't have scene_id in the Scene object directly, relying on index/heuristics
        # If Topic is available, we could use it, but index is safer for template structure.
        block = _get_narrative_block(i, total_scenes, getattr(scene, "id", ""))

        # Check if we should flush the current group
        # Flush if:
        # 1. Block changed (e.g. Start -> Body)
        # 2. Duration would exceed limit
        # 3. We are starting a new group (first iteration)

        is_new_group = len(current_scene_indices) == 0
        block_changed = (block != current_block) and not is_new_group
        duration_exceeded = (
            current_duration + scene.duration_seconds > MAX_GROUP_DURATION
        ) and not is_new_group

        # Special case: CTA should almost always stand alone or finish a group
        # But our block logic handles "CTA" as a distinct block type, so block_changed covers it.

        if block_changed or duration_exceeded:
            # Flush existing buffer
            group_id = uuid.uuid4().hex[:8]
            groups.append(
                VoiceoverGroup(
                    group_id=group_id,
                    scene_indices=list(current_scene_indices),
                    total_duration=current_duration,
                    original_scripts=list(current_scripts),
                    narrative_block=current_block,
                )
            )
            # Reset buffer
            current_scene_indices = []
            current_scripts = []
            current_duration = 0.0

        # Add current scene to buffer
        current_scene_indices.append(i)
        current_scripts.append(scene.voiceover_prompt.text)
        current_duration += scene.duration_seconds
        current_block = block

    # Flush any remaining scenes
    if current_scene_indices:
        group_id = uuid.uuid4().hex[:8]
        groups.append(
            VoiceoverGroup(
                group_id=group_id,
                scene_indices=list(current_scene_indices),
                total_duration=current_duration,
                original_scripts=list(current_scripts),
                narrative_block=current_block,
            )
        )

    logger.info(f"Grouping complete. Created {len(groups)} voiceover groups.")
    return groups
