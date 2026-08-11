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

"""Merge-protection for storyboard persistence.

`finalize_and_persist_storyboard` used to assign the freshly validated storyboard
straight over `state[STORYBOARD_KEY]`. Because the incoming storyboard is parsed
from the LLM's raw JSON — which never carries asset ids — any storyboard re-run
silently discarded every already-generated asset, forcing an expensive full
re-render. This module performs the merge instead.

Two rules govern the merge:

1. **Stable identity.** Scenes carry a server-assigned ``scene_id`` so an edited
   storyboard can be matched against the previous one even after reordering.
   Ids are reused positionally when the incoming scenes have none (the normal
   case, since the LLM never authors them).

2. **Carry assets only when the prompt is unchanged.** Preserving an ``asset_id``
   whose prompt was rewritten would leave a rendered clip that no longer matches
   its prompt. So an asset is carried over only when its prompt text is
   byte-identical; otherwise it is dropped, which lets the idempotency guards in
   the generation tools re-render exactly the scenes that actually changed.
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Mirrors storyboard_model._generate_scene_id so ids minted here are
# indistinguishable from the ones minted at validation.
SCENE_ID_LENGTH = 12

# (prompt field, asset-bearing keys to carry when that prompt is unchanged)
#
# Voiceover is keyed on `asset_ref` (a dict), not `asset_id`: that is what
# generate_scene_voiceover checks for idempotency. Dropping it would force an
# expensive TTS re-render and produce a different take of identical text.
_PROMPT_ASSET_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("first_frame_prompt", ("asset_id",)),
    ("video_prompt", ("asset_id", "enrichment_asset_id")),
    ("voiceover_prompt", ("asset_ref", "asset_id")),
)

# Prompt fields compared to decide whether a rendered asset is still valid.
# `gender` matters for voiceover because it selects the TTS voice, so changing
# it invalidates the recorded audio just as surely as rewriting the script.
_COMPARE_FIELDS: Dict[str, tuple[str, ...]] = {
    "first_frame_prompt": ("description",),
    "video_prompt": ("description", "duration_seconds"),
    "voiceover_prompt": ("text", "gender"),
}


def make_scene_id(used: Optional[set] = None) -> str:
    """Mints a fresh scene id in the same style the model itself uses."""
    used = used or set()
    while True:
        candidate = uuid.uuid4().hex[:SCENE_ID_LENGTH]
        if candidate not in used:
            return candidate


def assign_scene_ids(
    scenes: List[Dict[str, Any]],
    previous: Optional[List[Dict[str, Any]]] = None,
    *,
    trust_existing: bool = True,
) -> None:
    """Keeps scene identity stable across a storyboard rewrite (mutates in place).

    Scenes normally arrive with an id already: templates set meaningful ones
    ("ugc_discovery_hook") and everything else gets a generated id when the
    storyboard is validated. Those are left alone.

    The problem this solves is churn. A rewritten storyboard is re-parsed from
    the model's JSON, which carries no ids, so every scene is minted a brand new
    one — and identity, along with every rendered asset attached to it, is lost.
    So on a rewrite an id the previous storyboard never issued is replaced by
    the previous id at that position, which re-attaches the scene to its work.
    An id the previous storyboard *did* issue is a genuine echo (the model
    repeating ids back during a reorder) and is honoured.

    Args:
        scenes: Scenes to label, in order.
        previous: Scenes from the persisted storyboard, if any.
        trust_existing: Whether to take the supplied ids at face value. False
            for storyboards coming from the model, where an unfamiliar id means
            churn rather than intent.
    """
    previous = previous or []
    issued = {str(s.get("scene_id")) for s in previous if s.get("scene_id")}
    used: set[str] = set()

    for idx, scene in enumerate(scenes):
        raw = scene.get("scene_id")
        current = str(raw) if raw else None

        # An id the previous storyboard issued: the same scene, keep it.
        if current and current in issued and current not in used:
            used.add(current)
            continue

        # A rewrite: re-attach this position to the identity it had before, so
        # the assets rendered against it are not orphaned.
        if not trust_existing and idx < len(previous):
            prior = previous[idx].get("scene_id")
            if prior and str(prior) not in used:
                scene["scene_id"] = str(prior)
                used.add(str(prior))
                continue

        # Otherwise keep what the scene already has - a template's own id, or
        # the one minted at validation. Only mint when there is nothing usable.
        if current and current not in used:
            used.add(current)
            continue

        fresh = make_scene_id(used)
        scene["scene_id"] = fresh
        used.add(fresh)


def _prompts_match(old_prompt: Any, new_prompt: Any, fields: tuple[str, ...]) -> bool:
    if not isinstance(old_prompt, dict) or not isinstance(new_prompt, dict):
        return False
    return all(old_prompt.get(f) == new_prompt.get(f) for f in fields)


def _carry_scene_assets(old_scene: Dict[str, Any], new_scene: Dict[str, Any]) -> int:
    """Copies still-valid asset ids from ``old_scene`` onto ``new_scene``."""
    carried = 0
    for prompt_key, asset_keys in _PROMPT_ASSET_KEYS:
        old_prompt = old_scene.get(prompt_key)
        new_prompt = new_scene.get(prompt_key)
        if not isinstance(new_prompt, dict) or not isinstance(old_prompt, dict):
            continue

        if not _prompts_match(old_prompt, new_prompt, _COMPARE_FIELDS[prompt_key]):
            # Prompt changed — deliberately drop the asset so it re-renders.
            continue

        for asset_key in asset_keys:
            value = old_prompt.get(asset_key)
            if value and not new_prompt.get(asset_key):
                new_prompt[asset_key] = value
                carried += 1
    return carried


def find_scene_index(storyboard: Dict[str, Any], scene_id: str) -> Optional[int]:
    """Returns the position of ``scene_id``, or ``None`` if it is not present.

    Also accepts a bare positional index rendered as a string (``"2"``) so callers
    can address storyboards created before scene ids existed.
    """
    scenes = storyboard.get("scenes") or []
    for idx, scene in enumerate(scenes):
        if isinstance(scene, dict) and str(scene.get("scene_id")) == str(scene_id):
            return idx

    text = str(scene_id).strip()
    if text.isdigit():
        idx = int(text)
        if 0 <= idx < len(scenes):
            return idx
    return None


def clear_scene_assets(scene: Dict[str, Any]) -> int:
    """Removes every generated-asset reference from ``scene`` (mutates in place).

    The generation tools are idempotent — they skip any scene that already has an
    asset — so a scene must be cleared before it can be re-rendered. Returns the
    number of references removed.
    """
    cleared = 0
    for prompt_key, asset_keys in _PROMPT_ASSET_KEYS:
        prompt = scene.get(prompt_key)
        if not isinstance(prompt, dict):
            continue
        for asset_key in asset_keys:
            if prompt.pop(asset_key, None) is not None:
                cleared += 1
    return cleared


def merge_storyboard(
    previous: Optional[Dict[str, Any]], incoming: Dict[str, Any]
) -> Dict[str, Any]:
    """Merges a freshly generated storyboard over the persisted one.

    Args:
        previous: The storyboard currently in session state (may be ``None`` on
            first generation).
        incoming: The newly validated storyboard dump. Treated as authoritative
            for creative content.

    Returns:
        The storyboard to persist: ``incoming``, enriched with stable scene ids
        and any still-valid assets recovered from ``previous``.
    """
    merged = copy.deepcopy(incoming)
    new_scenes = merged.get("scenes") or []

    if not isinstance(previous, dict):
        assign_scene_ids(new_scenes, trust_existing=False)
        return merged

    old_scenes = previous.get("scenes") or []
    assign_scene_ids(new_scenes, old_scenes, trust_existing=False)

    old_by_id = {
        str(s.get("scene_id")): s
        for s in old_scenes
        if isinstance(s, dict) and s.get("scene_id")
    }

    carried_total = 0
    for idx, new_scene in enumerate(new_scenes):
        old_scene = old_by_id.get(str(new_scene.get("scene_id")))
        if old_scene is None and idx < len(old_scenes):
            # Previous storyboard predates scene ids — fall back to position.
            candidate = old_scenes[idx]
            if isinstance(candidate, dict) and not candidate.get("scene_id"):
                old_scene = candidate
        if isinstance(old_scene, dict):
            carried_total += _carry_scene_assets(old_scene, new_scene)

    # Voiceover groups are derived downstream, not authored by the LLM: keep the
    # previously computed groups (and their audio asset ids) when none arrive.
    if not merged.get("voiceover_groups") and previous.get("voiceover_groups"):
        merged["voiceover_groups"] = copy.deepcopy(previous["voiceover_groups"])

    # Preserve linkage fields the incoming dump does not carry. `storyboard_id`
    # is deliberately excluded: the caller clears it on every finalize so that
    # Creative Studio remains the authority on storyboard identity.
    for key in ("workspace_id", "session_id"):
        if not merged.get(key) and previous.get(key):
            merged[key] = previous[key]

    if carried_total:
        logger.info(
            "Storyboard merge preserved %d asset reference(s) across %d scene(s).",
            carried_total,
            len(new_scenes),
        )
    return merged
