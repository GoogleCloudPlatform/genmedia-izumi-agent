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

"""Model containing ad parameters."""

import pydantic
from pydantic import model_validator
from typing import Any

from ..common import common_utils


class TargetAudience(pydantic.BaseModel):
    """Structured target audience info."""

    persona: str = pydantic.Field(
        default="general audience", description="The primary audience persona."
    )
    pain_points: list[str] = pydantic.Field(
        default_factory=list, description="Top user pain points."
    )
    desires: list[str] = pydantic.Field(
        default_factory=list, description="What the user wants to achieve."
    )


class BriefResults(pydantic.BaseModel):
    """Market research results."""

    @model_validator(mode="before")
    @classmethod
    def coerce_brand_voice(cls, data: Any) -> Any:
        """Coerces brand_voice into a list if it's a string."""
        if isinstance(data, dict):
            brand_voice = data.get("brand_voice")
            if isinstance(brand_voice, str):
                data["brand_voice"] = [
                    s.strip() for s in brand_voice.split(",") if s.strip()
                ]
        return data

    primary_hook: str = pydantic.Field(
        default="Premium quality offering", description="The core 'Reason to Buy'."
    )
    audience: TargetAudience = pydantic.Field(
        default_factory=TargetAudience, description="Detailed audience profile."
    )
    brand_voice: list[str] = pydantic.Field(
        default_factory=list, description="Keywords defining the brand's tone."
    )


class SceneGuidance(pydantic.BaseModel):
    """Guidance for a specific scene."""

    visual_action: str = pydantic.Field(
        default="Continue the narrative flow.", description="Explicit visual direction."
    )
    voiceover_script: str = pydantic.Field(
        default="", description="The spoken text for this scene."
    )
    setting: str | None = pydantic.Field(
        default=None, description="The environment/weather."
    )


class StorylineGuidance(pydantic.BaseModel):
    """Narrative skeleton for creative mode."""

    narrative_arc: str = pydantic.Field(
        default="A compelling brand story.",
        description="Strategic overview of the storyline.",
    )
    scenes: list[SceneGuidance] = pydantic.Field(
        default_factory=list, description="Ordered list of scene-by-scene guidance."
    )


class Parameters(pydantic.BaseModel):
    """Campaign parameters."""

    @model_validator(mode="before")
    @classmethod
    def hydrate_nested_data(cls, data: Any) -> Any:
        """Pulls structural mapping burden off the LLM into code."""
        if not isinstance(data, dict):
            return data

        # 1. Structural Marshalling: Pack root-level fields into BriefResults
        # This allows the LLM to output flat keys while keeping the schema nested.
        if not data.get("brief_results"):
            # Extract audience info from flat or semi-flat keys
            raw_audience = data.get("audience") or {}
            if isinstance(raw_audience, str):
                raw_audience = {"persona": raw_audience}

            persona = (
                data.get("audience_persona")
                or raw_audience.get("persona")
                or data.get("target_audience")
                or "general audience"
            )
            pain_points = (
                data.get("audience_pain_points")
                or raw_audience.get("pain_points")
                or []
            )
            desires = data.get("audience_desires") or raw_audience.get("desires") or []

            primary_hook = (
                data.get("primary_hook")
                or data.get("key_message")
                or "Premium quality offering"
            )
            brand_voice = data.get("brand_voice") or []
            if isinstance(brand_voice, str):
                brand_voice = [s.strip() for s in brand_voice.split(",") if s.strip()]

            data["brief_results"] = {
                "primary_hook": primary_hook,
                "audience": {
                    "persona": persona,
                    "pain_points": pain_points,
                    "desires": desires,
                },
                "brand_voice": brand_voice,
            }
        else:
            # If brief_results IS present, ensure brand_voice is a list (nested check)
            br = data["brief_results"]
            if isinstance(br, dict) and isinstance(br.get("brand_voice"), str):
                bv = br["brand_voice"]
                br["brand_voice"] = [s.strip() for s in bv.split(",") if s.strip()]

        # 2. Strategic Invention (Hardened Defaults): Ensure strategic fields are never null
        vertical = data.get("vertical")
        if not vertical:
            vertical = "General"
            data["vertical"] = vertical
        if not data.get("campaign_theme"):
            data["campaign_theme"] = f"Modern {vertical} Lifestyle"
        else:
            # Coerce list to string if LLM over-provides
            if isinstance(data["campaign_theme"], list):
                data["campaign_theme"] = ", ".join(data["campaign_theme"])

        if not data.get("campaign_tone"):
            data["campaign_tone"] = "Cinematic and Engaging"
        else:
            # Coerce list to string if LLM over-provides
            if isinstance(data["campaign_tone"], list):
                data["campaign_tone"] = ", ".join(data["campaign_tone"])

        if not data.get("global_visual_style"):
            data["global_visual_style"] = "Professional Studio Aesthetic"
        if not data.get("global_setting"):
            data["global_setting"] = f"{vertical} Context"

        # 3. Clean up empty optionals that have required nested fields
        if "storyline_guidance" in data and not data["storyline_guidance"]:
            data.pop("storyline_guidance")

        # 4. Input Robustness: Ensure target_duration is a string
        td = data.get("target_duration")
        if not td:
            data["target_duration"] = "12s"
        elif isinstance(td, int) or isinstance(td, float):
            data["target_duration"] = f"{int(td)}s"

        return data

    campaign_brief: str = pydantic.Field(
        description="Direct copy of the user provided campaign brief."
    )
    campaign_name: str = pydantic.Field(
        description=(
            "A short, descriptive name for the campaign."
            " If none is provided, you MUST deduce a short, descriptive name"
            " from the campaign brief itself."
        )
    )
    target_audience: str = pydantic.Field(
        description=(
            "Target audience for the campaign."
            " If none is provided, you MUST default to 'general audience'."
        ),
        default="general audience",
    )
    target_duration: str = pydantic.Field(
        description=(
            "Target duration of the final video in seconds (e.g. '15s', '30s')."
            " You MUST extract this precisely from the brief if mentioned. Default to '12s' only if missing."
        ),
        default="12s",
    )
    target_orientation: str = pydantic.Field(
        description=(
            "Target orientation of the final video."
            " If none is provided, you MUST default to 'landscape'."
        ),
        default="landscape",
    )

    # Strategic Context (Rich Brief)
    campaign_theme: str | None = pydantic.Field(
        default=None,
        description="The creative/narrative theme of the campaign (e.g., 'Neon Cyberpunk', 'Minimalist Zen').",
    )
    campaign_tone: str | None = pydantic.Field(
        default=None,
        description="The emotional vibe (e.g., 'Energetic', 'Empathetic', 'Gritty').",
    )
    global_visual_style: str | None = pydantic.Field(
        default=None, description="Cinematic style and aesthetic direction."
    )
    global_setting: str | None = pydantic.Field(
        default=None,
        description="Physical environment or context (e.g., 'Urban Interior', 'Forest Dusk').",
    )

    key_message: str | None = pydantic.Field(
        default=None,
        description="The one single sentence the audience should remember (Final takeaway).",
    )

    # Template Selection
    template_name: str = pydantic.Field(
        default="Custom",
        description=(
            "The name of the Ad Template to use."
            " If the user does not specify a specific template, set this to 'Custom'."
            " Choose a specific template from the available list only if explicitly requested or industry-appropriate."
        ),
    )
    generate_virtual_creator: bool = pydantic.Field(
        default=False,
        description="Whether to generate a virtual creator character. Set to True for UGC templates OR if the user explicitly requests an influencer, spokesperson, virtual creator, or character in the brief.",
    )
    vertical: str = pydantic.Field(
        default="General",
        description=(
            "The industry vertical (e.g., 'Pets', 'Retail', 'Food')."
            " Deduce this from the campaign brief."
        ),
    )
    brief_results: BriefResults | None = pydantic.Field(
        default=None,
        description="Structured market research results.",
    )
    storyline_guidance: StorylineGuidance | None = pydantic.Field(
        default=None,
        description="Structured scene-by-scene script and action instructions.",
    )


DESCRIPTION = common_utils.describe_pydantic_model(Parameters)
