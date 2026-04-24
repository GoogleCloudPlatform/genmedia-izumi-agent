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

"""Pydantic models for the joint keyframe verifier."""

import pydantic

from . import common_utils


class Breakdown(pydantic.BaseModel):
    visual_consistency: int
    narrative_flow: int
    product_appeal: int
    engagement: int
    prompt_adherence: int


class JointKeyframeVerificationResult(pydantic.BaseModel):
    """Structured representation of joint keyframe evaluation."""

    breakdown: Breakdown
    score: int = pydantic.Field(description="Total score (sum of breakdown).")
    score_out_of: int = 100
    feedback: str = pydantic.Field(description="Critical review of the sequence.")
    primary_fault: str = pydantic.Field(description="'storyline' or 'image'")
    problematic_scenes: list[int] = pydantic.Field(
        default_factory=list,
        description="List of 0-based indices of scenes that need regeneration.",
    )
    actionable_feedback: str = pydantic.Field(
        description="Direct command to fix the primary issue."
    )


DESCRIPTION = common_utils.describe_pydantic_model(JointKeyframeVerificationResult)
