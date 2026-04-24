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

"""Pydantic models for Visual Casting (Phi_cast)."""

import pydantic

from . import common_utils


class CharacterCasting(pydantic.BaseModel):
    """Visual identity and wardrobe for the primary character."""

    character_present: bool = pydantic.Field(
        description="True if a 'character' role was already identified in the user_assets."
    )
    character_profile: str = pydantic.Field(
        description="Detailed description of the character's age, gender, ethnicity, and facial features based on demographics."
    )
    wardrobe_description: str = pydantic.Field(
        description="Detailed description of the clothing and accessories derived from the Storyline actions and setting."
    )
    collage_prompt: str = pydantic.Field(
        description="A technical prompt to generate a 3-view collage (Front, Lateral/Profile, Close-up) of this character."
    )


DESCRIPTION = common_utils.describe_pydantic_model(CharacterCasting)
