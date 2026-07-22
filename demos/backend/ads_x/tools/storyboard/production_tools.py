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

"""Tools for providing curated production recommendations."""

import logging
import random
from typing import Dict, Any, List, Optional
from ...utils.storyboard import production_presets
from google.adk.tools.tool_context import ToolContext
import mediagent_kit.services.aio
from utils.adk import get_user_id_from_context

logger = logging.getLogger(__name__)


async def recommend_production_recipe(
    vertical: str,
    campaign_theme: Optional[str] = None,
    campaign_tone: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    Returns a curated, brief-aligned technical production recipe (lighting,
    camera, attire, etc.) for a campaign. Use this instead of inventing
    technical specs.

    Rather than sampling each field independently (which yields clashing
    combinations), this selects ONE internally-coherent "Look" whose aesthetic
    best fits the campaign's vertical, theme, and tone, and returns its complete
    art-direction bundle so every scene can be anchored to it.

    Args:
        vertical: The campaign vertical (e.g., 'Social Native', 'Consumer Tech').
        campaign_theme: The strategic theme (e.g., 'Modern Elegance').
        campaign_tone: The emotional tone (e.g., 'Energetic', 'Moody').

    Returns:
        A dictionary containing a structured Production Recipe with coherent
        technical anchors.
    """
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `recommend_production_recipe` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    logger.info(
        f"🎬 [ADS-X PRODUCTION TOOL FIRED] Recommending Recipe for Vertical: '{vertical}', Theme: '{campaign_theme}', Tone: '{campaign_tone}'"
    )

    tier = "ugc" if vertical in ["Social Native", "UGC"] else "commercial"
    candidates = production_presets.get_looks_for_tier(tier)

    chosen = await _select_look(
        candidates, vertical, campaign_theme, campaign_tone, tool_context
    )

    # Return a copy of the Look's recipe so callers cannot mutate the preset.
    recipe: Dict[str, Any] = dict(chosen["recipe"])
    recipe["look_name"] = chosen.get("name", "Custom")
    style_mode = recipe.get("style_mode", "COMMERCIAL_PREMIUM")
    recipe["fidelity_guards"] = production_presets.PRODUCTION_ENCYCLOPEDIA.get(
        style_mode, {}
    ).get("FIDELITY_GUARDS", [])

    logger.info(f"🎨 [RECIPE] Selected Look '{recipe['look_name']}' (tier={tier})")

    # Persist to state for the summary canvas dashboard + downstream binding.
    if tool_context is not None:
        tool_context.state["master_production_recipe"] = recipe

    return recipe


async def _select_look(
    candidates: List[Dict[str, Any]],
    vertical: str,
    theme: Optional[str],
    tone: Optional[str],
    tool_context: Optional[ToolContext],
) -> Dict[str, Any]:
    """Selects the best-fit Look via a small LLM call, with a deterministic
    tag-scoring fallback if the model call fails or returns an unknown name."""
    if not candidates:
        candidates = production_presets.PRODUCTION_LOOKS
    if len(candidates) == 1:
        return candidates[0]

    menu = "\n".join(
        f"- {c['name']}: {c.get('description', '')} "
        f"(tones: {', '.join(c.get('tones', []))})"
        for c in candidates
    )
    prompt = (
        "You are a creative director selecting the single best visual 'Look' for "
        "an ad campaign. Choose the ONE Look whose aesthetic best fits the "
        "campaign below.\n\n"
        f"Campaign vertical: {vertical or 'General'}\n"
        f"Campaign theme: {theme or 'N/A'}\n"
        f"Campaign tone: {tone or 'N/A'}\n\n"
        f"Available Looks:\n{menu}\n\n"
        "Respond with ONLY the exact name of the best-fit Look, nothing else."
    )

    try:
        workspace_id = "recipe_selector"
        if tool_context is not None:
            workspace_id = str(
                tool_context.state.get("workspace_id")
                or get_user_id_from_context(tool_context)
                or workspace_id
            )
        mediagen = mediagent_kit.services.aio.get_media_generation_service()
        raw = await mediagen.generate_text(workspace_id=workspace_id, prompt=prompt)
        name = (raw or "").strip().splitlines()[0].strip().strip("\"'*`. ")
        chosen = production_presets.get_look_by_name(name)
        if chosen and chosen in candidates:
            return chosen
        # Fuzzy match if the model added stray words around the name.
        for c in candidates:
            if c["name"].lower() in name.lower() or name.lower() in c["name"].lower():
                return c
        logger.warning(
            f"LLM look selection '{name}' did not match a candidate; "
            "falling back to tag scoring."
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM look selection failed ({e}); falling back to tag scoring.")

    return _score_look(candidates, theme, tone)


def _score_look(
    candidates: List[Dict[str, Any]],
    theme: Optional[str],
    tone: Optional[str],
) -> Dict[str, Any]:
    """Deterministic fallback: pick the Look with the best tag overlap against
    the theme/tone text, random among candidates if nothing matches."""
    text = f"{theme or ''} {tone or ''}".lower()
    best: Optional[Dict[str, Any]] = None
    best_score = -1
    for c in candidates:
        score = sum(2 for t in c.get("tones", []) if t.lower() in text)
        score += sum(1 for k in c.get("keywords", []) if k.lower() in text)
        if score > best_score:
            best_score = score
            best = c
    if best is None or best_score <= 0:
        return random.choice(candidates)
    return best
