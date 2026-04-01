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

logger = logging.getLogger(__name__)

def recommend_production_recipe(
    vertical: str,
    campaign_theme: Optional[str] = None,
    campaign_tone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns a curated and strategically aligned technical production recipe 
    (lighting, camera, attire, etc.) for a campaign. Use this instead of 
    inventing technical specs.
    
    Args:
        vertical: The campaign vertical (e.g., 'Social Native', 'Consumer Tech').
        campaign_theme: The strategic theme (e.g., 'Modern Elegance').
        campaign_tone: The emotional tone (e.g., 'Energetic', 'Moody').
    
    Returns:
        A dictionary containing a structured Production Recipe with validated technical anchors.
    """
    logger.error("⭐⭐⭐ [NATIVE TOOL INVOCATION] `recommend_production_recipe` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐")
    logger.info(f"🎬 [ADS-X PRODUCTION TOOL FIRED] Recommending Recipe for Vertical: '{vertical}', Theme: '{campaign_theme}', Tone: '{campaign_tone}'")
    
    # Selection logic: UGC/Social Native vs Commercial Premium
    style_key = "SOCIAL_NATIVE" if vertical in ["Social Native", "UGC"] else "COMMERCIAL_PREMIUM"
    library = production_presets.PRODUCTION_ENCYCLOPEDIA[style_key]
    
    # Helper to pick a diverse but aligned set of ingredients
    def pick(category: str, subfield: str, count: int = 1, fallback: str = "TBD") -> Any:
        options = library.get(category, {}).get(subfield, [])
        if not options:
            return fallback if count == 1 else [fallback]
        
        # In a real system, we'd use semantic search here. 
        # For now, we return a curated random slice to ensure variety.
        results = random.sample(options, min(len(options), count))
        if count == 1:
            return results[0] if results else fallback
        return results

    # Construct the recipe
    recipe = {
        "style_mode": style_key,
        "brand_archetype": list(library.get("BRAND_AESTHETICS", {}).values())[0] if campaign_theme is None else "Matched to theme",
        "character": {
            "actor_vibe": pick("CHARACTER_DETAILS", "primary_actors", 1, "Professional Model"),
            "attire": pick("CHARACTER_DETAILS", "attire_styling", 2, "Modern Casual"),
            "grooming": pick("CHARACTER_DETAILS", "visage_grooming", 1, "Clean and Polished"),
            "motion": pick("CHARACTER_DETAILS", "stance_and_mood", 1, "Engaging and Natural")
        },
        "environment": {
            "spatial_context": pick("ENVIRONMENT", "location", 2, "Versatile Studio Set"),
            "temporal": pick("ENVIRONMENT", "temporal_setting", 1, "Anytime Lighting")
        },
        "cinematography": {
            "optics": pick("CINEMATOGRAPHY", "optical_specs", 2, "Prime Lenses"),
            "movement": pick("CINEMATOGRAPHY", "dynamic_motion", 2, "Smooth Camera Work"),
            "motion_texture": pick("CINEMATOGRAPHY", "motion_texture", 1, "Crisp Digital 4K")
        },
        "illumination": {
            "vibe": pick("ILLUMINATION", "aesthetic_vibe", 1, "Cinematic Quality"),
            "chromatic_scheme": pick("ILLUMINATION", "chromatic_scheme", 1, "Natural Balance"),
            "key_lighting": pick("ILLUMINATION", "primary_source", 1, "Soft Three-Point Mix"),
            "highlights": pick("ILLUMINATION", "tonal_highlights", 2, "Subtle Glow")
        },
        "sonic_landscape": pick("SONIC_LANDSCAPE", "composition_styles", 1, "Modern Ambient Soundscape"),
        "fidelity_guards": library.get("FIDELITY_GUARDS", [])
    }
    
    # Overwrite brand archetype with thematic matching if possible
    if campaign_theme and "BRAND_AESTHETICS" in library:
        # Simple keyword matching for demo purposes
        theme_lower = campaign_theme.lower()
        for key, val in library["BRAND_AESTHETICS"].items():
            if any(word in theme_lower for word in key.lower().split('_')):
                recipe["brand_archetype"] = val
                break
    
    return recipe
