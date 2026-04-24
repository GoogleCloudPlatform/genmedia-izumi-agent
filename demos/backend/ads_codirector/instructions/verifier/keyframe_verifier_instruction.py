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

"""Instructions for the Joint Keyframe Verifier Agent."""

from pathlib import Path

from ...utils import common_utils, joint_keyframe_verifier_model

_RUBRIC_PATH = Path(__file__).parent / "keyframe_verifier.md"

with open(_RUBRIC_PATH, encoding="utf-8") as f:
    _RUBRIC = f.read()

INSTRUCTION = (
    """
### BRAND INTEGRITY MANDATE (CRITICAL)
You MUST use the official product name and brand name provided in the 'Structured Constraints'. 
- DO NOT invent, guess, or creatively modify these names.
- Use them exactly as written in your 'feedback' and 'actionable_feedback'.
- Defer to the text in the constraints even if visual text on the images appears different or unclear.

"""
    + _RUBRIC
    + """

**Input Context:**
- Original User Prompt: {user_prompt}
- Structured Constraints: {structured_constraints}
- Annotated Reference Visuals: {annotated_reference_visuals}
- Storyboard: {storyboard}

**Output Template:**
Return a valid JSON matching this schema:
"""
    + joint_keyframe_verifier_model.DESCRIPTION
)
