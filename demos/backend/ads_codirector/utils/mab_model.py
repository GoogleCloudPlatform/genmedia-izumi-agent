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

"""Pydantic models for MAB experiment state management."""

from typing import Any

import pydantic


class CreativeDirection(pydantic.BaseModel):
    """Synthesized creative directions for different production stages."""

    storyline_instruction: str = pydantic.Field(
        description="Specific narrative and plot guidance based on the chosen creative strategy and narrative mode."
    )
    keyframe_instruction: str = pydantic.Field(
        description="Aesthetic and lighting guidance for static images based on the aesthetic archetype."
    )
    video_instruction: str = pydantic.Field(
        description="Guidance for temporal dynamics and camera motion based on the aesthetic archetype and narrative mode."
    )
    audio_instruction: str = pydantic.Field(
        description="Guidance for music genre, tempo, and voiceover tone based on the overall creative configuration."
    )


class MabIterationLog(pydantic.BaseModel):
    """A structured log for a single MAB iteration."""

    iteration_num: int = pydantic.Field(
        description="The sequential number of the iteration."
    )
    project_folder_id: str = pydantic.Field(
        description="The user or project ID for this iteration."
    )
    arms_selected: dict[str, str] = pydantic.Field(
        description="The MAB arms selected for this iteration."
    )
    creative_brief: str | None = pydantic.Field(
        default=None,
        description="The enriched creative brief (Module B) for this iteration.",
    )
    storyline: str | dict[str, Any] | None = pydantic.Field(
        default=None,
        description="The narrative script (Module L) for this iteration.",
    )
    storyline_refinement_history: list[dict[str, Any]] | None = pydantic.Field(
        default=None,
        description="The complete refinement history for the storyline.",
    )
    character_casting: str | dict[str, Any] | None = pydantic.Field(
        default=None,
        description="The character demographics and wardrobe specs for this iteration.",
    )
    creative_direction: CreativeDirection | None = pydantic.Field(
        default=None,
        description="The synthesized creative directions for this iteration.",
    )
    verifier_results: dict[str, Any] = pydantic.Field(
        description="The structured results from the final video verifier."
    )
    artifact_uri: str = pydantic.Field(
        description="The URI of the final generated video artifact for this iteration."
    )
    verifiers: dict[str, Any] = pydantic.Field(
        description="Metadata about the verifiers used in this iteration."
    )
    storyboard: dict[str, Any] = pydantic.Field(
        description="The final storyboard object, updated with all generated asset IDs."
    )
    character_collage_asset_id: str | None = pydantic.Field(
        default=None,
        description="The asset ID of the generated character collage reference.",
    )
    arm_stats: dict[str, dict[str, Any]] | None = pydantic.Field(
        default=None,
        description="A snapshot of the MAB arm statistics at the end of this iteration.",
    )


class ArmsSelected(pydantic.BaseModel):
    """A structured representation of the MAB arms selected for an iteration."""

    creative_strategy: str = pydantic.Field(
        description="The selected arm for the Creative Strategy."
    )
    narrative_mode: str = pydantic.Field(
        description="The selected arm for the Narrative Mode."
    )
    aesthetic_archetype: str = pydantic.Field(
        description="The selected arm for the Aesthetic Archetype."
    )


class MabWarmStart(pydantic.BaseModel):
    """LLM-initialized expected values for MAB arms."""

    reasoning: str = pydantic.Field(
        description="Technical justification for why this specific combination of arms was chosen jointly to resonate with the target audience."
    )
    recommendations: ArmsSelected = pydantic.Field(
        description="The chosen combination of initial arms."
    )


class MabExperimentState(pydantic.BaseModel):
    """The complete, serializable state of a MAB experiment."""

    experiment_id: str = pydantic.Field(
        description="A unique UUID for this entire experiment run."
    )
    user_prompt: str = pydantic.Field(
        description="The initial user prompt that kicked off the experiment."
    )
    structured_constraints: dict[str, Any] | None = pydantic.Field(
        default=None, description="The parsed campaign parameters and constraints."
    )
    user_assets: dict[str, Any] | None = pydantic.Field(
        description="A dictionary of user-provided assets and their annotations."
    )
    arm_stats: dict[str, dict[str, Any]] = pydantic.Field(
        description="Statistics for each arm, tracking pulls and rewards."
    )
    iterations: list[MabIterationLog] = pydantic.Field(
        description="A detailed log of each MAB iteration."
    )
    warm_start: MabWarmStart | None = pydantic.Field(
        default=None,
        description="LLM-initialized expected values for MAB arms (Module S).",
    )


DESCRIPTION = """{
  "creative_strategy": "The selected arm for the Creative Strategy.",
  "narrative_mode": "The selected arm for the Narrative Mode.",
  "aesthetic_archetype": "The selected arm for the Aesthetic Archetype."
}"""

WARM_START_DESCRIPTION = """{
  "reasoning": "Detailed justification for the joint selection...",
  "recommendations": {
    "creative_strategy": "informational",
    "narrative_mode": "analytical",
    "aesthetic_archetype": "clarity_energy"
  }
}"""
