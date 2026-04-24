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

"""Instructions for the parameters agent."""

from ..utils import common_utils, parameters_model

# Alignment with ads_x reference:
# Do NOT use explicit session state injection for the user prompt.
# The agent can see the chat history.
INSTRUCTION = """\
Parse the ads campaign brief provided by the user into campaign parameters.

**User Input:**
{user_prompt}

Deduce available parameter values and report them as the following JSON object:

""" + parameters_model.DESCRIPTION
