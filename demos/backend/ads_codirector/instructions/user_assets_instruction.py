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

"""Instructions for ingesting the user-provided assets."""

from ..utils import asset_model

# Alignment with ads_x: Simplified prompt to focus strictly on visual content.
# This prevents the model from speculating or hallucinating based on campaign context.
INSTRUCTION = """\
You are annotating the image asset: {file_name}

### FILENAME INTEGRITY MANDATE (CRITICAL)
You MUST use the exact filename provided above ({file_name}) in your response's "file_name" field. 
DO NOT invent, guess, or modify the filename based on the visual content of the image.

### FOREGROUND FOCUS MANDATE (CRITICAL)
Focus EXCLUSIVELY on the primary subject (the product or character). 
- COMPLETELY IGNORE the background, surface, or environment shown in the reference image. 
- Do NOT describe the background (e.g., white studio, plain surface, shadows on floor) in your caption.
- Your goal is to provide a "clean" description of the subject that can be placed into any environment.

### TASK
Provide a concise, high-fidelity visual summary of the SUBJECT in this image.
Describe colors, textures, and key objects precisely.

Also, assign exactly one of the following semantic roles:
- 'product': The main item being advertised.
- 'logo': Brand identity elements.
- 'character': Key characters or figures.

You MUST respond with exactly ONE JSON object following this schema:
""" + asset_model.DESCRIPTION
