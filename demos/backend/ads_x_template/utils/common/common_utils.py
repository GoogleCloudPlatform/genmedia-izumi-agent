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

import json
import pydantic
from typing import Any, get_args, get_origin
from google.genai import types

PARAMETERS_KEY = "parameters"
USER_ASSETS_KEY = "user_assets"
STORYBOARD_KEY = "storyboard"
VIRTUAL_CREATOR_KEY = "virtual_creator_metadata"

JSON_CONFIG = types.GenerateContentConfig(response_mime_type="application/json")

ToolResult = dict[str, Any]


def tool_success(result: Any = "") -> ToolResult:
    """Returns a tool success result."""
    return {"status": "succeeded", "result": result}


def tool_failure(error_message: str) -> ToolResult:
    """Returns a tool failure result with the given error message."""
    return {"status": "failed", "error_message": error_message}


def json_for_pydantic_model(model: type[pydantic.BaseModel]) -> dict[str, Any]:
    """Returns a JSON representing the structure of a Pydantic model."""
    result: dict[str, Any] = {}
    for field_name, field in model.model_fields.items():
        if field.annotation is None:
            continue
        field_type = field.annotation
        field_description = field.description if field.description else str(field_type)

        if get_origin(field_type) is list:
            # Handle lists
            list_item_type = get_args(field_type)[0]
            if issubclass(list_item_type, pydantic.BaseModel):
                result[field_name] = [json_for_pydantic_model(list_item_type)]
            else:
                result[field_name] = [field_description]
            result[field_name].append(f"... # More {field_name} can be present")
        elif (
            field_type is not None
            and isinstance(field_type, type)
            and issubclass(field_type, pydantic.BaseModel)
        ):
            # Handle nested Pydantic models
            result[field_name] = json_for_pydantic_model(field_type)
        else:
            # Handle leaf types
            result[field_name] = field_description

    return result


def describe_pydantic_model(model: type[pydantic.BaseModel]) -> str:
    """Returns a JSON string representing the structure of a Pydantic model."""
    return json.dumps(json_for_pydantic_model(model), indent=2)
