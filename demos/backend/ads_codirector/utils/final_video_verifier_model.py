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

"""Pydantic models for verifiers."""

import pydantic

from . import common_utils


class VerificationResult(pydantic.BaseModel):
    """A structured representation of a verification result."""

    breakdown: dict[str, int] = pydantic.Field(
        description=(
            "Detailed scores for coherence, visual_quality, engagement, "
            "prompt_adherence, and logical_consistency, each from 0 to 20."
        )
    )
    mab_efficacy_scores: dict[str, int] = pydantic.Field(
        description=(
            "Dimension-specific efficacy scores (0-100) for "
            "creative_strategy, narrative_mode, and aesthetic_archetype."
        )
    )
    mab_efficacy_justifications: dict[str, str] = pydantic.Field(
        description="Brief theoretical reasoning for each efficacy score."
    )
    feedback: str = pydantic.Field(
        description="Detailed, constructive feedback on the ad's quality."
    )
    primary_fault: str = pydantic.Field(
        description="The single most important issue to fix ('storyline', 'image', or 'video')."
    )
    actionable_feedback: str = pydantic.Field(
        description="Holistic feedback to guide improvements across the entire ad generation process."
    )
    score: int = pydantic.Field(
        description="The final execution score on a scale from 0 to 100 (sum of breakdown scores)."
    )


DESCRIPTION = common_utils.describe_pydantic_model(VerificationResult)
