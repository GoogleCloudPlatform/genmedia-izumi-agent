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

"""Provides context for the final video verifier agent."""

from pathlib import Path

from ...utils import common_utils, final_video_verifier_model

_VERIFIER_RUBRIC_PATH = Path(__file__).parent / "video_verifier.md"

# This produces literal single-braced strings for ADK resolution.
INSTRUCTION_CONTEXT = """
**Structured Constraints:**
{structured_constraints}

**Annotated Reference Visuals:**
{annotated_reference_visuals}

**Selected Creative Arms:**
{creative_configuration}

**Theoretical Definitions:**
{theoretical_definitions}

**Storyboard:**
{storyboard}
"""

with open(_VERIFIER_RUBRIC_PATH, encoding="utf-8") as f:
    _RUBRIC = f.read()

# We AVOID Python's .format() here because it will crash on the braces in INSTRUCTION_CONTEXT.
# Instead, we perform manual replacement for the two static placeholders in the .md file.
INSTRUCTION = _RUBRIC.replace("{context}", INSTRUCTION_CONTEXT).replace(
    "{json_output_schema}", final_video_verifier_model.DESCRIPTION
)
