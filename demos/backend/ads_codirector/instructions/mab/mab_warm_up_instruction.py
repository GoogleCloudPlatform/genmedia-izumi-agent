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

"""Instructions for the MAB Warm-up Agent."""

from ...mab import arm_definitions
from ...utils import common_utils, mab_model


def get_warm_start_instruction(user_prompt: str, structured_constraints: dict) -> str:
    """Dynamically builds the warm-start instruction with theoretical context."""

    # Format dimensions and theory for the prompt
    dimensions_context = ""
    # Hardcoded dimensions to match current implementation
    dimensions = {
        "creative_strategy": ["informational", "transformational", "comparative"],
        "narrative_mode": ["analytical", "vignette", "narrative_drama"],
        "aesthetic_archetype": [
            "clarity_energy",
            "cinematic_premium",
            "minimalist_focus",
            "kinetic_grit",
        ],
    }

    for dim_name, arms in dimensions.items():
        dimensions_context += f"Dimension: {dim_name}\nOptions:\n"
        for arm in arms:
            theory = arm_definitions.THEORY_MAP.get(arm, "No theory defined.")
            dimensions_context += f"  - {arm}: {theory}\n"
        dimensions_context += "\n"

    return f"""
You are an elite AI Creative Strategist. Your goal is to analyze the advertisement request and suggest the most effective combination of creative dimensions to prioritize for the first iteration of a multi-armed bandit experiment.

**1. AD CONTEXT**
- **User Prompt:** {user_prompt}
- **Campaign Details (Structured Constraints):** {structured_constraints}

**2. AVAILABLE DIMENSIONS & THEORY**
Below are the dimensions you can choose from, along with their theoretical grounding:
{dimensions_context}

**3. YOUR TASK**
Based on the brand, product, and target audience, identify which combination of Creative Strategy, Narrative Mode, and Aesthetic Archetype is most likely to resonate and achieve high performance.

**JOINT CONSIDERATION (CRITICAL):**
You must consider the combination of arms JOINTLY. Certain strategies pair better with specific narrative modes or aesthetics to create a cohesive experience. Your selection should ensure that the strategy, structure, and visual style all work together to fulfill the campaign goal.

**4. OUTPUT FORMAT**
Provide your reasoning, then output your final selection for EACH dimension in the following JSON format.
{mab_model.WARM_START_DESCRIPTION}
"""
