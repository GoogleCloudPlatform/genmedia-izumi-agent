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

"""Library of hardcoded Ad Templates."""

from typing import List
from .templates_model import AdTemplate
from .templates import general_purpose
from .templates import vertical_specific
from .templates import social_native


def get_all_templates() -> List[AdTemplate]:
    """Returns a list of all available templates."""
    return [
        # General Purpose
        general_purpose.get_general_purpose_problem_solution(),
        general_purpose.get_general_purpose_problem_solution_fast_pace(),
        general_purpose.get_feature_spotlight(),
        general_purpose.get_feature_spotlight_fast_pace(),
        # Vertical
        vertical_specific.get_pet_companion(),
        vertical_specific.get_pet_companion_fast_pace(),
        vertical_specific.get_apparel_style_showcase(),
        vertical_specific.get_apparel_style_showcase_fast_pace(),
        vertical_specific.get_beauty_routine(),
        vertical_specific.get_beauty_routine_fast_pace(),
        vertical_specific.get_home_comfort(),
        vertical_specific.get_home_comfort_fast_pace(),
        vertical_specific.get_meal_prep(),
        vertical_specific.get_meal_prep_fast_pace(),
        # UGC / Social Native
        social_native.get_ugc_first_impression(),
        social_native.get_ugc_honest_opinion(),
    ]


def get_template_by_name(name: str) -> AdTemplate:
    """Retrieves a template by its exact name."""
    templates = get_all_templates()
    for t in templates:
        if t.template_name == name:
            return t
    # Fallback
    return general_purpose.get_general_purpose_problem_solution()


def suggest_template(industry: str, vertical: str = None) -> AdTemplate:
    """Simple logic to suggest a template based on industry and vertical."""
    # Basic keyword matching
    if not vertical:
        if industry.lower() == "social native":
            return social_native.get_ugc_first_impression()
        return general_purpose.get_general_purpose_problem_solution()

    v = vertical.lower()
    if "ugc" in v or "social" in v or "review" in v or "tiktok" in v:
        if "first" in v or "impression" in v or "unboxing" in v:
            return social_native.get_ugc_first_impression()
        return social_native.get_ugc_honest_opinion()

    if "pet" in v:
        return vertical_specific.get_pet_companion()
    if "apparel" in v or "fashion" in v:
        return vertical_specific.get_apparel_style_showcase()
    if "beauty" in v:
        return vertical_specific.get_beauty_routine()
    if "home" in v:
        return vertical_specific.get_home_comfort()
    if "food" in v or "meal" in v:
        return vertical_specific.get_meal_prep()

    return general_purpose.get_general_purpose_problem_solution()
