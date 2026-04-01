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

import asyncio
import json
import logging

from google import genai
from google.adk.tools import ToolContext
from google.genai import types

import mediagent_kit
import config
from utils.adk import get_user_id_from_context

from ..instructions import creative_writer

# Initialize the Google Cloud Logging client
logger = logging.getLogger(__name__)


async def creative_writer_with_gemini(
    tool_context: ToolContext, *, request: str, reference_files: str
) -> str:
    """Generates creative text content using the Gemini model.

    Args:
        tool_context: The tool context, used to load assets.
        request: The user's request for the creative writing task.
        reference_files: A comma-separated string of file names for reference file assets.

    Returns:
        A JSON string representing a dictionary that indicates the outcome.
        If the operation is successful, the dictionary will have a 'status' of 'success'
        and a 'writer_result' key with the generated text.
        If the operation fails, the 'status' will be 'failure' and there will be
        an 'error_message' key with details about the error.
    """
    logger.info(
        json.dumps(
            {
                "message": "Starting creative_writer_with_gemini",
                "request": request,
                "reference_files": reference_files,
            }
        )
    )
    project = config.settings.GOOGLE_CLOUD_PROJECT
    region = config.settings.GOOGLE_CLOUD_LOCATION

    if not project or not region:
        raise ValueError(
            "Missing required environment variables: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION"
        )

    client = genai.Client(vertexai=True, project=project, location=region)

    model = "gemini-2.5-flash"

    contents = []

    contents.append(request)

    if reference_files:
        reference_file_names = [
            f.strip() for f in reference_files.split(",") if f.strip()
        ]
        asset_service = mediagent_kit.services.aio.get_asset_service()
        user_id = get_user_id_from_context(tool_context)
        for file_name in reference_file_names:
            try:
                asset = await asset_service.get_asset_by_file_name(
                    user_id=user_id, file_name=file_name
                )
                if not asset:
                    error_message = f"Could not find reference file asset with file name: {file_name}"
                    logger.warning(error_message)
                    return json.dumps(
                        {"status": "failure", "error_message": error_message}
                    )

                asset_blob = await asset_service.get_asset_blob(asset_id=asset.id)
                file_part = types.Part.from_bytes(
                    data=asset_blob.content, mime_type=asset_blob.mime_type
                )

                if (
                    file_part
                    and hasattr(file_part, "inline_data")
                    and file_part.inline_data
                ):
                    contents.append(file_part)
                else:
                    error_message = f"Could not load reference file asset or asset is empty: {file_name}"
                    logger.warning(error_message)
                    return json.dumps(
                        {"status": "failure", "error_message": error_message}
                    )
            except Exception as e:
                error_message = f"Error loading reference file asset {file_name}: {e}"
                logger.error(
                    json.dumps(
                        {
                            "message": error_message,
                            "file_name": file_name,
                            "error": str(e),
                        }
                    )
                )
                return json.dumps({"status": "failure", "error_message": error_message})

    system_instruction = creative_writer.INSTRUCTION

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=1.3
            ),
        )
        success_payload = {"status": "success", "writer_result": response.text}
        logger.info("Successfully generated creative content")
        return json.dumps(success_payload)
    except Exception as e:
        error_payload = {"status": "failure", "error_message": str(e)}
        logger.error(f"Failed to generate creative content: {e}")
        return json.dumps(error_payload)
