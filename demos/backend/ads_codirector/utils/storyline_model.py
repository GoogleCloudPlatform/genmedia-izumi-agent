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

"""Pydantic model for Storyline (Phi_story)."""

import pydantic

from . import common_utils


class StorylineScene(pydantic.BaseModel):
    """A single scene in the narrative storyline."""

    topic: str = pydantic.Field(
        description="A short, descriptive topic for this scene (e.g., 'The Problem', 'Product Reveal')."
    )
    action: str = pydantic.Field(
        description="A detailed description of the visual action and character movement in this scene."
    )


class Storyline(pydantic.BaseModel):
    """A structured narrative script comprising multiple scenes."""

    scenes: list[StorylineScene] = pydantic.Field(
        description="A sequence of 4 to 6 scenes that form the narrative arc."
    )


DESCRIPTION = common_utils.describe_pydantic_model(Storyline)
