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
import logging
import uuid

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.context import Context
from google.adk.models import LlmRequest
from google.adk.tools import ToolContext
from google.genai import types as genai_types

import mediagent_kit

logger = logging.getLogger(__name__)

DESCRIPTION_INSTRUCTION = """\
Provide a concise (1-2 sentence) summary of this image for an advertising campaign, focusing on its key visual elements.
If visible in the image, include the product's name and price.
The description should be brief but contain essential product details.
"""


def get_user_id_from_context(context: ReadonlyContext) -> str:
    user_id = None
    try:
        if (
            context
            and context._invocation_context
            and context._invocation_context.session
        ):
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
        if (
            context
            and context._invocation_context
            and context._invocation_context.session
        ):
            session = context._invocation_context.session
            id_val = getattr(session, "id", None)
            sid_val = getattr(session, "session_id", None)
            if isinstance(id_val, str):
                session_id = id_val
            elif isinstance(sid_val, str):
                session_id = sid_val
    except Exception:
        pass

    if session_id is None:
        # Fallback
        session_id = "default_session"
        logger.warning(f"session_id not found in context. Using fallback: {session_id}")

    return session_id


def resolve_workspace_id(context: ReadonlyContext) -> tuple[str, str | None]:
    """Resolves the effective workspace id for a generation tool call.

    Creative Studio establishes a numeric ``workspace_id`` in session state via
    the ``select_workspace`` tool. Native (Izumi) mode has no workspace
    selection, so the session ``user_id`` is used as the workspace/tenant id
    (an arbitrary non-empty string, e.g. ``project_1784661758983``).

    Returns a ``(workspace_id, error_message)`` tuple; ``error_message`` is
    ``None`` when the id is valid, otherwise a message suitable for
    ``tool_failure``. The numeric-format requirement is enforced only when
    Creative Studio is active.
    """
    from mediagent_kit.services import _get_service_factory

    state = getattr(context, "state", None) or {}
    workspace_id = str(
        state.get("workspace_id") or get_user_id_from_context(context) or ""
    )
    if not workspace_id:
        return "", "Could not determine a workspace_id from the session."

    if _get_service_factory().get_config().use_creative_studio and (
        not workspace_id.isdigit()
    ):
        return workspace_id, (
            f"Invalid workspace_id: '{workspace_id}'. "
            "Workspace ID must be a non-empty numeric string."
        )

    return workspace_id, None


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


async def generate_image_description(
    mime_type: str, workspace_id: str, blob_data: bytes = None, gcs_uri: str = None
) -> str:
    """Generates a concise visual description for an image blob or GCS URI using Gemini multimodal."""
    try:
        from google import genai
        from google.genai import types as genai_types
        from mediagent_kit.services.aio import get_config

        config = get_config()
        client = genai.Client(
            vertexai=True,
            project=config.google_cloud_project,
            location=config.google_cloud_location or "us-central1",
        )
        model = config.models.get("text", {}).get("default", "gemini-2.5-flash")

        if gcs_uri:
            image_part = genai_types.Part.from_uri(
                file_uri=gcs_uri, mime_type=mime_type
            )
        elif blob_data:
            image_part = genai_types.Part.from_bytes(
                data=blob_data, mime_type=mime_type
            )
        else:
            return "No image data or URI provided."
        prompt_part = genai_types.Part.from_text(text=DESCRIPTION_INSTRUCTION)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=[image_part, prompt_part],
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.warning(f"Failed to generate description for asset blob: {e}")
        return "User provided visual reference asset."


async def blob_interceptor_callback(callback_context: Context, llm_request: LlmRequest):
    """Intercepts user messages to process blobs, session artifacts, and Creative Studio asset references."""
    state = None
    if callback_context and callback_context.state:
        state = callback_context.state
        for key in [
            "parameters",
            "user_assets",
            "storyboard",
            "forced_metadata",
            "asset_refs",
        ]:
            if key not in state:
                state[key] = {}

        import os
        from mediagent_kit.utils.context import set_request_context

        token_key = os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token")
        workspace_id = state.get("workspace_id")
        auth_token = state.get(token_key)
        set_request_context(user_auth_token=auth_token, workspace_id=workspace_id)

    if not hasattr(llm_request, "contents") or not llm_request.contents:
        return None

    last_content = llm_request.contents[-1]

    if hasattr(last_content, "role") and last_content.role == "user":
        if hasattr(last_content, "parts"):
            import re
            from google.genai import types as genai_types
            from mediagent_kit.services.types.common import AssetRef, GeneratedAsset

            asset_service = mediagent_kit.services.aio.get_asset_service()
            user_id = get_user_id_from_context(callback_context)
            workspace_id = str(state.get("workspace_id") or user_id)

            for i, part in enumerate(last_content.parts):
                # Scenario A: Multimodal inline blob part
                blob_data = None
                mime_type = None
                file_name = None
                if hasattr(part, "inline_data") and part.inline_data:
                    blob = part.inline_data
                    mime_type = blob.mime_type
                    blob_data = blob.data
                    file_name = blob.display_name
                elif hasattr(part, "file_data") and part.file_data:
                    blob = part.file_data
                    mime_type = blob.mime_type
                    file_uri = blob.file_uri
                    file_name = getattr(blob, "display_name", None)
                    if file_uri and file_uri.startswith("gs://"):
                        from google.cloud import storage

                        path = file_uri.removeprefix("gs://")
                        bucket_name, blob_path = path.split("/", 1)
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob_obj = bucket.blob(blob_path)
                        blob_data = await asyncio.to_thread(blob_obj.download_as_bytes)

                if blob_data and mime_type:

                    if not file_name:
                        file_extension = mime_type.split("/")[-1]
                        file_name = f"{uuid.uuid4()}.{file_extension}"

                    logger.info(
                        f"Intercepted blob of type {mime_type}. Uploading asset '{file_name}'..."
                    )

                    try:
                        uploaded = await asset_service.upload_asset(
                            workspace_id=workspace_id,
                            file_name=file_name,
                            blob=blob_data,
                            mime_type=mime_type,
                        )
                        logger.info(
                            f"Successfully uploaded blob asset: {file_name} with ID: {uploaded.id}"
                        )

                        asset_key = f"uploaded_{uploaded.id}"
                        if mime_type.startswith("image/"):
                            desc = await generate_image_description(
                                mime_type=mime_type,
                                workspace_id=workspace_id,
                                blob_data=blob_data,
                                gcs_uri=None,
                            )
                            user_assets = dict(state.get("user_assets") or {})
                            user_assets[asset_key] = (
                                f"(Original file: {asset_key}) {desc}"
                            )
                            state["user_assets"] = user_assets

                        # Save to asset_refs state map under the unique asset_key
                        asset_refs = dict(state.get("asset_refs") or {})
                        asset_refs[asset_key] = {
                            "id": uploaded.id,
                            "asset_type": "uploaded",
                            "workspace_id": workspace_id,
                        }
                        state["asset_refs"] = asset_refs

                        success_message = f"System note: The file referred to in this user query is an asset named '{file_name}'. Use this file as reference asset for tasks like image or video generation as needed using the ID: {asset_key}"
                        last_content.parts[i] = genai_types.Part(text=success_message)

                    except Exception as e:
                        logger.error(f"Failed to save blob as asset: {e}")

                # Scenario B: Text reference to user-uploaded session artifact
                elif hasattr(part, "text") and part.text:
                    clean_text = part.text
                    artifact_matches = re.findall(
                        r"<start_of_user_uploaded_file:\s*([^>]+)>", clean_text
                    )
                    for file_name in artifact_matches:
                        file_name = file_name.strip()
                        logger.info(
                            f"Intercepted session artifact reference: '{file_name}'."
                        )
                        try:
                            artifact_part = await callback_context.load_artifact(
                                file_name
                            )
                            blob_data = None
                            mime_type = None
                            if artifact_part:
                                if getattr(artifact_part, "inline_data", None):
                                    blob_data = artifact_part.inline_data.data
                                    mime_type = artifact_part.inline_data.mime_type
                                elif getattr(artifact_part, "file_data", None):
                                    file_uri = artifact_part.file_data.file_uri
                                    mime_type = artifact_part.file_data.mime_type
                                    if file_uri and file_uri.startswith("gs://"):
                                        from google.cloud import storage

                                        path = file_uri.removeprefix("gs://")
                                        bucket_name, blob_path = path.split("/", 1)
                                        storage_client = storage.Client()
                                        bucket = storage_client.bucket(bucket_name)
                                        blob_obj = bucket.blob(blob_path)
                                        blob_data = await asyncio.to_thread(
                                            blob_obj.download_as_bytes
                                        )

                            if blob_data and mime_type:

                                uploaded_asset = await asset_service.upload_asset(
                                    workspace_id=workspace_id,
                                    file_name=file_name,
                                    blob=blob_data,
                                    mime_type=mime_type,
                                )
                                logger.info(
                                    f"Successfully uploaded session artifact: {file_name} with ID: {uploaded_asset.id}"
                                )

                                if mime_type.startswith("image/"):
                                    desc = await generate_image_description(
                                        mime_type=mime_type,
                                        workspace_id=workspace_id,
                                        blob_data=blob_data,
                                        gcs_uri=None,
                                    )
                                    user_assets = dict(state.get("user_assets") or {})
                                    asset_key = f"uploaded_{uploaded_asset.id}"
                                    user_assets[asset_key] = (
                                        f"(Original file: {asset_key}) {desc}"
                                    )
                                    state["user_assets"] = user_assets

                                # Save to asset_refs state map under the unique asset_key
                                asset_refs = dict(state.get("asset_refs") or {})
                                asset_key = f"uploaded_{uploaded_asset.id}"
                                asset_refs[asset_key] = {
                                    "id": uploaded_asset.id,
                                    "asset_type": "uploaded",
                                    "workspace_id": workspace_id,
                                }
                                state["asset_refs"] = asset_refs

                                clean_text = re.sub(
                                    rf"<start_of_user_uploaded_file:\s*{re.escape(file_name)}>",
                                    "",
                                    clean_text,
                                )
                                clean_text = re.sub(
                                    rf"<end_of_user_uploaded_file:\s*{re.escape(file_name)}>",
                                    "",
                                    clean_text,
                                )
                                clean_text += f"\n(System note: The file '{file_name}' was uploaded as an asset to Creative Studio. Use it as a reference asset for media generation as needed using the ID: uploaded_{uploaded_asset.id})"
                        except Exception as e:
                            logger.error(
                                f"Failed to process session artifact '{file_name}': {e}"
                            )

                    # Scenario C: Reference to a Creative Studio Asset by ID and type
                    cs_asset_matches = re.findall(
                        r'<creative_studio_asset\s+id=["\']?([0-9a-fA-F\-]+)["\']?\s+type=["\']?([^"\'>\s]+)["\']?\s*/?>',
                        clean_text,
                    )
                    for asset_id, raw_asset_type in cs_asset_matches:
                        logger.info(
                            f"Intercepted CS asset tag reference: ID='{asset_id}', type='{raw_asset_type}'"
                        )
                        try:
                            mapped_type = (
                                "uploaded"
                                if raw_asset_type == "source_asset"
                                else "generated"
                            )
                            ref = AssetRef(
                                id=asset_id,
                                asset_type=mapped_type,
                                workspace_id=workspace_id,
                            )
                            asset = await asset_service.get_asset(ref)
                            if asset:
                                logger.info(
                                    f"Successfully loaded CS asset: {asset.file_name} (ID: {asset_id})"
                                )
                                user_assets = dict(state.get("user_assets") or {})
                                metadata = getattr(asset, "generation_metadata", None)
                                prompt_desc = (
                                    getattr(metadata, "prompt", None)
                                    if metadata
                                    else None
                                )
                                if prompt_desc is None:
                                    gcs_uri = getattr(
                                        asset, "gcs_uri", None
                                    ) or getattr(
                                        getattr(asset, "current", None), "gcs_uri", None
                                    )
                                    prompt_desc = await generate_image_description(
                                        blob_data=None,
                                        mime_type=asset.mime_type,
                                        workspace_id=workspace_id,
                                        gcs_uri=gcs_uri,
                                    )

                                asset_key = f"{mapped_type}_{asset_id}"
                                user_assets[asset_key] = (
                                    f"(Original file: {asset_key}) {prompt_desc}"
                                )
                                state["user_assets"] = user_assets

                                asset_refs = dict(state.get("asset_refs") or {})
                                asset_refs[asset_key] = {
                                    "id": asset_id,
                                    "asset_type": mapped_type,
                                    "workspace_id": workspace_id,
                                }
                                state["asset_refs"] = asset_refs

                                note = f"\n(System note: Creative Studio asset '{asset_key}'.)"
                                if note not in clean_text:
                                    clean_text += note
                        except Exception as e:
                            logger.error(
                                f"Failed to resolve CS asset ID {asset_id}: {e}"
                            )

                    # Scenario D: Native session-service asset reference
                    # ("<asset://filename>"). FirestoreSessionService intercepts
                    # uploaded blobs, saves them as assets, and rewrites the
                    # message part to "<asset://filename>" text -- but it does NOT
                    # register them in user_assets/asset_refs. Without that mapping
                    # the storyboard agent has no assets to reference and
                    # generate_all_media's primary_product binding stays empty, so
                    # first frames are generated with no reference images. Recover
                    # the mapping here by looking each asset up by its filename.
                    native_asset_matches = re.findall(r"<asset://([^>]+)>", clean_text)
                    for raw_name in native_asset_matches:
                        file_name = raw_name.strip()
                        if not file_name:
                            continue
                        logger.info(
                            f"Intercepted native asset reference: '{file_name}'."
                        )
                        try:
                            asset = await asset_service.get_asset_by_file_name(
                                user_id=workspace_id, file_name=file_name
                            )
                            if not asset:
                                logger.warning(
                                    f"Native asset '{file_name}' not found by "
                                    "filename; skipping reference registration."
                                )
                                continue

                            # Key by the original filename so it aligns with how
                            # the brief references files, how the storyboard agent
                            # is told to use "the exact Filename from user_assets",
                            # and how generate_all_media detects the logo vs the
                            # primary product.
                            asset_key = file_name

                            # asset_refs is what scene resolution relies on --
                            # populate it first so a later description failure
                            # cannot leave the reference unusable.
                            asset_refs = dict(state.get("asset_refs") or {})
                            asset_refs[asset_key] = {
                                "id": asset.id,
                                "asset_type": "uploaded",
                                "workspace_id": workspace_id,
                            }
                            state["asset_refs"] = asset_refs

                            desc = f"Uploaded reference image '{file_name}'."
                            if str(getattr(asset, "mime_type", "") or "").startswith(
                                "image/"
                            ):
                                gcs_uri = getattr(
                                    getattr(asset, "current", None), "gcs_uri", None
                                )
                                try:
                                    desc = await generate_image_description(
                                        blob_data=None,
                                        mime_type=asset.mime_type,
                                        workspace_id=workspace_id,
                                        gcs_uri=gcs_uri,
                                    )
                                except Exception as desc_err:
                                    logger.warning(
                                        f"Description generation failed for "
                                        f"'{file_name}': {desc_err}"
                                    )

                            user_assets = dict(state.get("user_assets") or {})
                            user_assets[asset_key] = (
                                f"(Original file: {asset_key}) {desc}"
                            )
                            state["user_assets"] = user_assets

                            note = (
                                f"\n(System note: The file '{file_name}' is available "
                                f"as a reference asset for media generation using the "
                                f"ID: {asset_key})"
                            )
                            if note not in clean_text:
                                clean_text += note
                        except Exception as e:
                            logger.error(
                                f"Failed to resolve native asset '{file_name}': {e}"
                            )

                    part.text = clean_text

    return None
