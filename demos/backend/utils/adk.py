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

import logging
import uuid

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from google.genai import types as genai_types

import mediagent_kit

logger = logging.getLogger(__name__)


def get_user_id_from_context(context: ReadonlyContext) -> str:
    user_id = None
    try:
        if context and context._invocation_context and context._invocation_context.session:
            user_id = context._invocation_context.session.user_id
    except Exception:
        pass
        
    if user_id is None:
        # Fallback for environments where context is missing
        user_id = "default_user_agent_engine"
        logger.warning(f"user_id not found in context. Using fallback: {user_id}")
        
    return user_id


def get_session_id_from_context(context: ReadonlyContext) -> str:
    session_id = None
    try:
        if context and context._invocation_context and context._invocation_context.session:
            session_id = context._invocation_context.session.session_id
    except Exception:
        pass
        
    if session_id is None:
        # Fallback
        session_id = "default_session"
        logger.warning(f"session_id not found in context. Using fallback: {session_id}")
        
    return session_id


async def display_asset(tool_context: ToolContext, asset_id: str) -> str:
    """Loads a persistent asset and displays it on ADK Web / Gemini Enterprise UI.

    This saves the content of a saved asset (like an image or video) into ADK Artifact
    Service.

    Args:
        tool_context: The context for tool execution.
        asset_id: The ID of the asset to display.

    Returns:
        A confirmation message indicating the asset is available as an artifact.
    """
    try:
        asset_service = mediagent_kit.services.aio.get_asset_service()
        # asset_blob = await asset_service.get_asset_blob(asset_id=asset_id)
        
        # Optimization: Fetch metadata only to get the GCS URI
        asset = await asset_service.get_asset_by_id(asset_id)
        if not asset:
             return f"Error: Asset {asset_id} not found."
             
        # Use Part.from_uri to avoid loading bytes into memory/payload
        part = genai_types.Part.from_uri(
            file_uri=asset.current.gcs_uri, mime_type=asset.mime_type
        )
        
        await tool_context.save_artifact(filename=asset.file_name, artifact=part)

        msg = f"Asset {asset.file_name} is now available as a tool artifact."
        logger.info(msg)
        return msg
    except Exception as e:
        # CRITICAL FIX: If artifact saving fails (e.g. GcsArtifactService local limitations),
        # we MUST NOT fail the tool. The Asset itself is safe in GCS/Firestore.
        # Just log the warning and continue so the Deep Link is generated.
        error_msg = f"Warning: Could not display asset {asset_id} as artifact: {e}"
        logger.warning(error_msg)
        # Return success message anyway so the tool doesn't abort
        return f"Asset {asset_id} saved (Artifact display skipped)."


async def blob_interceptor_callback(callback_context, llm_request):
    """
    Intercepts user messages to find and save blobs as assets.
    If a blob is found, it is saved.
    Execution then continues to the LLM.
    """
    # Initialize campaign state to prevent KeyError in instructions
    if callback_context and callback_context._invocation_context and callback_context._invocation_context.session:
        session = callback_context._invocation_context.session
        if "parameters" not in session.state:
            session.state["parameters"] = {}
        if "user_assets" not in session.state:
            session.state["user_assets"] = {}
        if "storyboard" not in session.state:
            session.state["storyboard"] = {}
        if "forced_metadata" not in session.state:
            session.state["forced_metadata"] = {}

    # llm_request is expected to be an LlmRequest object, but we omit the
    # type hint to avoid import errors on older ADK versions.
    if not hasattr(llm_request, "contents") or not llm_request.contents:
        return None

    last_content = llm_request.contents[-1]

    if hasattr(last_content, "role") and last_content.role == "user":
        if hasattr(last_content, "parts"):
            for i, part in enumerate(last_content.parts):
                if hasattr(part, "inline_data") and part.inline_data:
                    blob = part.inline_data
                    mime_type = blob.mime_type
                    blob_data = blob.data
                    file_name = blob.display_name

                    if not file_name:
                        # Generate a filename if not found in text.
                        file_extension = mime_type.split("/")[-1]
                        file_name = f"{uuid.uuid4()}.{file_extension}"

                    logger.info(
                        f"Intercepted blob of type {mime_type}. Saving as asset with name {file_name}"
                    )

                    try:
                        asset_service = mediagent_kit.services.aio.get_asset_service()
                        user_id = get_user_id_from_context(callback_context)

                        await asset_service.save_asset(
                            user_id=user_id,
                            mime_type=mime_type,
                            file_name=file_name,
                            blob=blob_data,
                        )
                        logger.info(f"Successfully saved blob as asset: {file_name}")

                        # Replace the blob part with a system message to inform the model
                        # that the asset was saved.
                        success_message = f"System note: The file referred to in this user query is an asset named '{file_name}'. Use this file as reference asset for tasks like image or video generation as needed."

                        last_content.parts[i] = genai_types.Part(text=success_message)

                    except Exception as e:
                        logger.error(f"Failed to save blob as asset: {e}")

    # Return None to allow the agent to proceed with the model call.
    return None
