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

"""Pydantic models for the storyboard asset relevance verifier."""

import pydantic

from . import common_utils


class SceneAssetCorrection(pydantic.BaseModel):
    """Corrections for a single scene's asset list."""

    scene_index: int = pydantic.Field(description="The 0-based index of the scene.")
    missing_assets: list[str] = pydantic.Field(
        default_factory=list,
        description="Filenames of PRODUCT or CHARACTER assets that MUST be added based on the storyline.",
    )
    invalid_filenames: list[str] = pydantic.Field(
        default_factory=list,
        description="Names in the current storyboard that DO NOT EXIST in the available assets list (hallucinations).",
    )
    assets_to_remove: list[str] = pydantic.Field(
        default_factory=list,
        description="Valid filenames that exist in the inventory but are narratively inappropriate for this specific scene (e.g., logo too early, premature product reveal).",
    )
    reasoning: str = pydantic.Field(
        description="Brief explanation of why these specific assets are being added or removed."
    )


class StoryboardAssetRelevanceResult(pydantic.BaseModel):
    """
    A structured representation of the global asset supervision for the entire storyboard.
    """

    corrections: list[SceneAssetCorrection] = pydantic.Field(
        default_factory=list,
        description="List of corrections for each scene in the storyboard.",
    )
    overall_score: int = pydantic.Field(
        description="A score from 0-100 evaluating the global asset accuracy. 100 means no corrections were needed."
    )


DESCRIPTION = common_utils.describe_pydantic_model(StoryboardAssetRelevanceResult)
