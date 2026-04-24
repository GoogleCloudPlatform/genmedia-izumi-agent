# Copyright 2026 Google LLC
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

"""
Theory Definitions and Academic References for Creative Direction Mode.
This file provides the theoretical grounding for the MAB arms, drawing from
foundational literature in marketing science, narrative theory, and media aesthetics.
"""

THEORY_MAP = {
    # Dimension 1: Creative Strategy (Laskey, Day, and Crask, 1989)
    "informational": (
        "Focus on functional utility and verifiable product attributes. "
        "Provide factual evidence for product superiority and logical advantages."
    ),
    "transformational": (
        "Focus on the psychological experience, social meaning, or emotional state "
        "associated with the brand. Aim to build a lifestyle connection rather than a spec-based one."
    ),
    "comparative": (
        "Define the product by positioning it against a known standard, common "
        "urban norm, or a generalized competitor to highlight a unique value proposition."
    ),
    # Dimension 2: Narrative Mode (Escalas, 2004; Green & Brock, 2000)
    "analytical": (
        "Utilize an argument-based structure. Use direct address or logical points "
        "without a temporal story arc or diegetic characters."
    ),
    "vignette": (
        "Present a series of brief, atmospheric 'slices of life.' Focus on a "
        "consistent 'vibe' and visual textures rather than a plot with a climax."
    ),
    "narrative_drama": (
        "Construct a full temporal sequence (beginning, middle, end) with a "
        "character-driven conflict that the product helps resolve, maximizing 'narrative transportation'."
    ),
    # Dimension 3: Aesthetic Archetype (Zettl, 2016; Lang, 2000)
    "clarity_energy": (
        "High-key illumination (low contrast) paired with high-temporal motion (fast cuts/arousal). "
        "Use upbeat, high-tempo audio to suggest transparency and vitality."
    ),
    "cinematic_premium": (
        "Chiaroscuro lighting (high contrast/heavy shadows) paired with low-temporal motion (slow dolly/reflective pace). "
        "Use orchestral or ambient cinematic audio for a premium, high-end feel."
    ),
    "minimalist_focus": (
        "Bright, clean, high-key backgrounds with static or micro-movements. "
        "Focus on extreme detail and texture, paired with clean foley/ASMR-style audio."
    ),
    "kinetic_grit": (
        "Low-key/shadowy lighting with dynamic, unstable motion (handheld/FPV drone). "
        "Use driving electronic synth audio to suggest intensity and modern authenticity."
    ),
}

REFERENCES = [
    "Laskey, H. A., Day, E., & Crask, M. R. (1989). A typology of main creative advertising strategies. Journal of Advertising, 18(1), 36-41.",
    "Escalas, J. E. (2004). Narrative processing: Building consumer connections to brands. Journal of Consumer Psychology, 14(1-2), 168-180.",
    "Zettl, H. (1973). Sight, sound, motion: Applied media aesthetics (8th ed.). Cengage Learning.",
    "Lang, A. (2000). The limited capacity model of motivated mediated message processing. Journal of Communication, 50(1), 46-70.",
    "Green, M. C., & Brock, T. C. (2000). The role of transportation in the persuasiveness of public narratives. Journal of Personality and Social Psychology, 79(5), 701-721.",
    "Nisbett, R. E., & Ross, L. (1980). Human inference: Strategies and shortcomings of social judgment. Prentice-Hall.",
]
