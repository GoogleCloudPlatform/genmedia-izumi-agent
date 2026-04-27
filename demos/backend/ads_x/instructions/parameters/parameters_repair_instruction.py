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

"""Instruction for repairing malformed parameter JSON."""

REPAIR_PROMPT = """
The following JSON representing campaign parameters contains errors or validation failures.
Your task is to REPAIR the JSON so it is syntactically valid and matches the target schema.

Rules:
1. Ensure all brackets, quotes, and commas are correct.
2. The final output must be a valid JSON object matching the Parameters schema.
3. DO NOT add conversational text. Return ONLY the valid JSON.

Original User Brief:
{user_brief}

Malformed JSON/Error:
{raw_json}

Error Message:
{error}
"""
