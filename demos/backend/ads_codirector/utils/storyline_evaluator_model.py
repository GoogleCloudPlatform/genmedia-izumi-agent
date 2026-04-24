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

"""Pydantic model for storyline evaluation."""

import pydantic

from . import common_utils


class ScoreBreakdown(pydantic.BaseModel):
    hook_quality: int
    narrative_arc: int
    product_integration: int
    engagement: int
    prompt_adherence: int


class StorylineEvaluation(pydantic.BaseModel):
    """Result of the storyline refinement check."""

    breakdown: ScoreBreakdown
    score: int = pydantic.Field(description="Total score (0-100).")
    feedback: str = pydantic.Field(description="Critical review.")
    actionable_feedback: str = pydantic.Field(
        description="Direct command for the next iteration."
    )


DESCRIPTION = common_utils.describe_pydantic_model(StorylineEvaluation)
