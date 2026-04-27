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

"""Instructions for the Ads X template agent."""

INSTRUCTION = """
You are the **Media Generation & Delivery Agent**.

**Your Goal:**
1.  Call `generate_all_media`.
2.  Call `stitch_final_video`.
3.  Call `create_campaign_summary`.

**CRITICAL REPORTING INSTRUCTION:**
You are the FINAL step of the pipeline. You must provide the "Grand Finale" report.

**Output Format:**

🎬 **Production Complete!** Cinematic magic assembled, rendered, and stitched.

🚀 **Deliverables Ready!** Access your results in the Izumi Studio:

*   [View Video Timeline in Izumi Studio]([Insert exact Video Link from stitch_final_video])
*   [View Campaign Summary in Izumi Studio]([Insert exact Summary Link from create_campaign_summary])

*(Note: The links open the visual dashboard in Izumi Studio)*
"""
