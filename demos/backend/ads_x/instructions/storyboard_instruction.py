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

"""Instructions for the storyboard agent."""

from ..utils import common_utils

INSTRUCTION = f"""
Generate a JSON campaign breakdown for the following video ad campaign:

**Campaign Parameters:**
{{{common_utils.PARAMETERS_KEY}}}

**User Assets:**
{{{common_utils.USER_ASSETS_KEY}}}

**Instructions:**
1.  Your primary goal is to create a storyboard that showcases the products listed in the 'User Assets'.
2.  Your output should be detailed and creative, incorporating the assets and adhering to the campaign brief.
3.  Each scene should be designed to highlight a feature/benefit of the product(s) described in the assets.
4.  The narrative must revolve around the provided products.
5.  Create a storyboard with a logical flow that matches the campaign brief and target audience.
6.  For each scene, you MUST select the most appropriate asset(s) from the available assets.
7.  You MUST incorporate the `description` of the chosen asset(s) into that scene's `image_prompt` and `video_prompt`.
8.  The scene video should have harmonized colors if a logo is being placed on it.

**Constraints:**
1.  NEVER generate prompts that would produce images or videos of children.
"""
