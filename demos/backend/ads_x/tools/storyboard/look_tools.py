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

"""Choosing and adjusting the campaign's visual Look.

The Look fixes the campaign's visual identity — aesthetic, environment, optics,
lighting, and the styling of any on-screen person. It is picked once during
strategy and injected into every scene, so these tools are what a reviewer uses
at the strategy checkpoint to see the choice and change it.

Customisation is deliberately "pick, then nudge": choose one of the curated
Looks, then override individual fields from the encyclopedia's vetted options.
Free-text overrides are accepted but discouraged, because the curated Looks are
*coherent* combinations and arbitrary prose tends to fight them.

A Look change after the storyboard exists is not self-applying: the art
direction is baked into each scene's prompt text when the storyboard is
finalised. `reapply_art_direction` re-stamps the current Look onto existing
scenes and releases the visuals it invalidates.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from google.adk.tools.tool_context import ToolContext

from ...utils.common import common_utils
from ...utils.storyboard import production_presets

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

RECIPE_KEY = "master_production_recipe"
ART_DIRECTION_MARKER = "[ART DIRECTION (NON-NEGOTIABLE)"

# Editable field -> (path into the recipe, encyclopedia location of its options).
# The encyclopedia entry is (axis, sub-axis or None).
_EDITABLE: Dict[str, Tuple[Tuple[str, ...], Tuple[str, Optional[str]]]] = {
    "aesthetic": (("brand_archetype",), ("BRAND_AESTHETICS", None)),
    "environment": (
        ("environment", "spatial_context"),
        ("ENVIRONMENT", "spatial_context"),
    ),
    "optics": (("cinematography", "optics"), ("CINEMATOGRAPHY", "optical_specs")),
    "motion": (("cinematography", "movement"), ("CINEMATOGRAPHY", "dynamic_motion")),
    "lighting": (("illumination", "vibe"), ("ILLUMINATION", "aesthetic_vibe")),
    # Character styling. Only meaningful when the ad features a person.
    "actor": (("character", "actor_vibe"), ("CHARACTER_DETAILS", "primary_actors")),
    "attire": (("character", "attire"), ("CHARACTER_DETAILS", "attire_styling")),
    "grooming": (("character", "grooming"), ("CHARACTER_DETAILS", "visage_grooming")),
}

CHARACTER_FIELDS = ("actor", "attire", "grooming")


def _options_for(field: str, style_mode: str) -> List[str]:
    """Curated values for ``field`` under the recipe's style mode."""
    if field not in _EDITABLE:
        return []
    axis, sub_axis = _EDITABLE[field][1]
    mode = production_presets.PRODUCTION_ENCYCLOPEDIA.get(style_mode) or {}
    entry = mode.get(axis)
    if sub_axis and isinstance(entry, dict):
        entry = entry.get(sub_axis)
    if isinstance(entry, dict):
        return [str(v) for v in entry.values()]
    if isinstance(entry, list):
        return [str(v) for v in entry]
    return []


def _active_recipe(tool_context: ToolContext) -> Optional[Dict[str, Any]]:
    recipe = tool_context.state.get(RECIPE_KEY)
    return recipe if isinstance(recipe, dict) else None


def _scene_count(tool_context: ToolContext) -> int:
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not isinstance(storyboard, dict):
        return 0
    return len(storyboard.get("scenes") or [])


def _stale_warning(tool_context: ToolContext) -> str:
    """Warns when a storyboard already carries the previous art direction."""
    scenes = _scene_count(tool_context)
    if not scenes:
        return ""
    return (
        f" The storyboard's {scenes} scene(s) still carry the previous art "
        "direction; call `reapply_art_direction` to restamp them."
    )


async def list_looks(tool_context: ToolContext, tier: str = "") -> ToolResult:
    """Lists the curated visual Looks a campaign can use.

    Args:
        tier: Optionally narrow to "commercial" (polished, produced) or "ugc"
            (social-native, handheld). Leave empty for all.
    """
    wanted = tier.strip().lower()
    if wanted and wanted not in {"commercial", "ugc"}:
        return tool_failure(f"Unknown tier '{tier}'. Expected 'commercial' or 'ugc'.")

    active = _active_recipe(tool_context) or {}
    active_name = active.get("look_name")

    looks = [
        {
            "name": look["name"],
            "tier": look.get("tier"),
            "description": look.get("description"),
            "tones": look.get("tones", []),
            "selected": look["name"] == active_name,
        }
        for look in production_presets.PRODUCTION_LOOKS
        if not wanted or look.get("tier") == wanted
    ]
    return tool_success({"selected": active_name, "looks": looks})


async def set_look(tool_context: ToolContext, look_name: str) -> ToolResult:
    """Switches the campaign to a different curated Look.

    Args:
        look_name: Name of the Look, exactly as `list_looks` reports it.
    """
    chosen = production_presets.get_look_by_name(look_name.strip())
    if not chosen:
        names = [look["name"] for look in production_presets.PRODUCTION_LOOKS]
        return tool_failure(f"Unknown Look '{look_name}'. Available: {names}")

    recipe: Dict[str, Any] = dict(chosen["recipe"])
    recipe["look_name"] = chosen["name"]
    style_mode = recipe.get("style_mode", "COMMERCIAL_PREMIUM")
    recipe["fidelity_guards"] = (
        production_presets.PRODUCTION_ENCYCLOPEDIA.get(style_mode) or {}
    ).get("FIDELITY_GUARDS", [])

    tool_context.state[RECIPE_KEY] = recipe
    logger.info("🎨 [RECIPE] Look switched to '%s'", chosen["name"])

    return tool_success(
        f"Look set to '{chosen['name']}'.{_stale_warning(tool_context)}"
    )


async def list_look_options(tool_context: ToolContext, field: str) -> ToolResult:
    """Lists the vetted values available for one Look field.

    Args:
        field: One of aesthetic, environment, optics, motion, lighting, actor,
            attire, grooming.
    """
    key = field.strip().lower()
    if key not in _EDITABLE:
        return tool_failure(
            f"Unknown field '{field}'. Editable fields: {sorted(_EDITABLE)}"
        )

    recipe = _active_recipe(tool_context)
    if recipe is None:
        return tool_failure("No Look selected yet. Choose one with `set_look`.")

    options = _options_for(key, recipe.get("style_mode", "COMMERCIAL_PREMIUM"))
    path = _EDITABLE[key][0]
    current: Any = recipe
    for part in path:
        current = (current or {}).get(part) if isinstance(current, dict) else None

    return tool_success({"field": key, "current": current, "options": options})


async def edit_look_field(
    tool_context: ToolContext, field: str, value: str
) -> ToolResult:
    """Overrides a single field of the active Look.

    Prefer a value from `list_look_options`: the curated Looks are coherent
    combinations, and free prose tends to fight the rest of the styling. Free
    text is accepted, but it is reported back so the choice is visible.

    Args:
        field: One of aesthetic, environment, optics, motion, lighting, actor,
            attire, grooming.
        value: The new value for that field.
    """
    key = field.strip().lower()
    if key not in _EDITABLE:
        return tool_failure(
            f"Unknown field '{field}'. Editable fields: {sorted(_EDITABLE)}"
        )
    if not value.strip():
        return tool_failure("A value is required.")

    recipe = _active_recipe(tool_context)
    if recipe is None:
        return tool_failure("No Look selected yet. Choose one with `set_look`.")

    path = _EDITABLE[key][0]
    target = recipe
    for part in path[:-1]:
        nested = target.get(part)
        if not isinstance(nested, dict):
            nested = {}
            target[part] = nested
        target = nested
    target[path[-1]] = value.strip()

    # A Look is no longer purely one of the presets once a field is overridden.
    base = str(recipe.get("look_name", "Custom"))
    if not base.endswith("(modified)"):
        recipe["look_name"] = f"{base} (modified)"

    tool_context.state[RECIPE_KEY] = recipe

    options = _options_for(key, recipe.get("style_mode", "COMMERCIAL_PREMIUM"))
    curated = value.strip() in options
    note = "" if curated else " Note: this is a custom value, not a curated option."
    return tool_success(
        f'Set {key} to "{value.strip()}".{note}{_stale_warning(tool_context)}'
    )


async def edit_character(
    tool_context: ToolContext, field: str, value: str
) -> ToolResult:
    """Adjusts the on-screen person's styling.

    Only affects ads that feature a person; a product-only campaign never
    renders these fields.

    Args:
        field: One of actor, attire, grooming.
        value: The new value, ideally from `list_look_options`.
    """
    key = field.strip().lower()
    if key not in CHARACTER_FIELDS:
        return tool_failure(
            f"Unknown character field '{field}'. Expected one of "
            f"{list(CHARACTER_FIELDS)}."
        )
    return await edit_look_field(tool_context, key, value)


async def reapply_art_direction(tool_context: ToolContext) -> ToolResult:
    """Restamps the current Look onto an existing storyboard.

    Art direction is baked into each scene's prompt when the storyboard is
    finalised, so changing the Look afterwards does not reach scenes that
    already exist. This replaces the stale direction on every scene and releases
    the visuals it invalidates, so they re-render against the new Look.
    Voiceover is untouched — the script did not change.
    """
    # Imported here to avoid a circular import at module load.
    from . import storyboard_repair_tools  # pylint: disable=import-outside-toplevel

    recipe = _active_recipe(tool_context)
    if recipe is None:
        return tool_failure("No Look selected yet. Choose one with `set_look`.")

    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        return tool_failure("There is no storyboard to restamp yet.")

    parameters = tool_context.state.get(common_utils.PARAMETERS_KEY) or {}
    include_character = bool(parameters.get("generate_virtual_creator", False))
    block = storyboard_repair_tools._build_art_direction_block(  # pylint: disable=protected-access
        recipe, include_character=include_character
    )

    restamped, released = 0, 0
    for scene in storyboard["scenes"]:
        if not isinstance(scene, dict):
            continue
        touched = False
        for prompt_key in ("first_frame_prompt", "video_prompt"):
            prompt = scene.get(prompt_key)
            if not isinstance(prompt, dict):
                continue
            description = str(prompt.get("description") or "")
            head, marker, _ = description.partition(ART_DIRECTION_MARKER)
            if not marker and not description:
                continue
            prompt["description"] = head.rstrip() + block
            touched = True
            for asset_key in ("asset_id", "enrichment_asset_id"):
                if prompt.pop(asset_key, None) is not None:
                    released += 1
        if touched:
            restamped += 1

    tool_context.state[common_utils.STORYBOARD_KEY] = storyboard
    logger.info(
        "Restamped art direction on %d scene(s); released %d visual(s).",
        restamped,
        released,
    )
    return tool_success(
        f"Restamped '{recipe.get('look_name')}' onto {restamped} scene(s) and "
        f"released {released} rendered visual(s) for re-rendering. Voiceover "
        "was left alone."
    )
