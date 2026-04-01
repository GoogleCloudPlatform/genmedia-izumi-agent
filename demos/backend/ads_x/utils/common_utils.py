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

"""Utils shared among agents and tools."""

from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

USER_INPUT_KEY = "user_input"
PARAMETERS_KEY = "parameters"
USER_ASSETS_KEY = "user_assets"
STORYBOARD_KEY = "storyboard"

JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")


ToolResult = dict[str, Any]


def tool_success(result: Any = "") -> ToolResult:
    """Returns a tool success result."""
    return {"status": "succeeded", "result": result}


def tool_failure(error_message: str) -> ToolResult:
    """Returns a tool failure result with the given error message."""
    return {"status": "failed", "error_message": error_message}


async def store_user_input_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    """Model callback to store user text input into session state."""
    user_input = ""
    for content in llm_request.contents:
        if content.role == "user":
            for part in content.parts:
                if part.text and part.text.startswith("For context:"):
                    break
                if part.text and not part.text.startswith("<asset://"):
                    user_input += "\n\n" + part.text
    callback_context.state[USER_INPUT_KEY] = user_input.strip()
