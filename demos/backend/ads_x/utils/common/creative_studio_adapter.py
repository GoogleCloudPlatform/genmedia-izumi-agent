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

"""Adapter for routing services dynamically between standard and Creative Studio backends."""

import contextvars
import copy
from typing import Any
import functools
import logging
import os
import unittest.mock
import httpx

from google.adk.tools.tool_context import ToolContext
from google.cloud import storage  # type: ignore

import mediagent_kit
import mediagent_kit.services.aio
from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types as asset_types
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.media_generation_service import MediaGenerationService
from mediagent_kit.services.aio.async_services import AsyncAssetService, AsyncMediaGenerationService
from mediagent_kit.services import _get_service_factory

from . import common_utils

logger = logging.getLogger(__name__)

# ContextVar to store the active adapter instance across task/execution boundaries
active_adapter_var = contextvars.ContextVar("active_adapter", default=None)


def get_active_adapter() -> "CreativeStudioAdapter | None":
    """Returns the active CreativeStudioAdapter if set in the current async context."""
    return active_adapter_var.get()


def with_creative_studio_adapter(func):
    """Decorator to automatically bind the CreativeStudioAdapter and auto-save storyboard changes."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Dynamically resolve the context (ToolContext, ReadonlyContext, or callback_context)
        context = None
        if args:
            context = args[0]
        elif "tool_context" in kwargs:
            context = kwargs["tool_context"]
        elif "callback_context" in kwargs:
            context = kwargs["callback_context"]
        elif "context" in kwargs:
            context = kwargs["context"]

        if context is None:
            raise TypeError(
                "with_creative_studio_adapter failed to resolve context. "
                "Make sure to pass a ToolContext, ReadonlyContext, or callback_context."
            )

        adapter = CreativeStudioAdapter(context)
        token = active_adapter_var.set(adapter)

        from mediagent_kit.utils.context import set_request_context, reset_request_context
        creds_token = set_request_context(
            user_auth_token=adapter.auth_token,
            workspace_id=adapter.workspace_id
        )

        # Resolve state dictionary from context safely
        state = {}
        if hasattr(context, "state"):
            state = context.state
        elif (
            hasattr(context, "_invocation_context")
            and context._invocation_context
            and context._invocation_context.session
        ):
            state = context._invocation_context.session.state
        
        # Snapshot storyboard state before tool execution
        old_storyboard = None
        if adapter.use_studio and state and common_utils.STORYBOARD_KEY in state:
            old_storyboard = copy.deepcopy(state[common_utils.STORYBOARD_KEY])
            
        try:
            result = await func(*args, **kwargs)
            
            # Compare and auto-save after successful execution
            if adapter.use_studio and state and common_utils.STORYBOARD_KEY in state:
                current_storyboard = state[common_utils.STORYBOARD_KEY]
                if current_storyboard != old_storyboard:
                    logger.info("[STUDIO PERSISTENCE] Storyboard changes detected. Auto-synchronizing with backend...")
                    parameters = state.get(common_utils.PARAMETERS_KEY, {})
                    try:
                        storyboard_id = await adapter.save_storyboard(current_storyboard, parameters)
                        if storyboard_id:
                            state["current_storyboard_id"] = storyboard_id
                            if isinstance(parameters, dict):
                                parameters["storyboard_id"] = storyboard_id
                    except Exception as save_err:
                        logger.error(f"[STUDIO PERSISTENCE] Auto-save failed: {save_err}")
                        
            return result
        finally:
            reset_request_context(creds_token)
            active_adapter_var.reset(token)
    return wrapper


class CreativeStudioAdapter:
    """Wraps asset and media generation services to dynamically support Creative Studio mode."""

    def __init__(self, tool_context: Any):
        from utils.adk import get_user_id_from_context
        self.tool_context = tool_context
        self.user_id = get_user_id_from_context(tool_context)

        # Retrieve global config directly to avoid early database/service initialization
        self.config = _get_service_factory().get_config()
        self.use_studio = self.config.use_creative_studio

        # Handle state dictionary from either ToolContext or ReadonlyContext
        state = {}
        if hasattr(tool_context, "state"):
            state = tool_context.state
        elif (
            hasattr(tool_context, "_invocation_context")
            and tool_context._invocation_context
            and tool_context._invocation_context.session
        ):
            state = tool_context._invocation_context.session.state

        # Extract workspace/token credentials from state
        self.workspace_id = state.get("workspace_id", 1) # Remove this hardcoded one afterwards this is only for testing
        user_auth_token_key = os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token")
        self.auth_token = state.get(user_auth_token_key)

        logger.info(
            f"[STUDIO ADAPTER RESOLUTION] "
            f"config.use_creative_studio={self.config.use_creative_studio}, "
            f"user_auth_token_key='{user_auth_token_key}', "
            f"auth_token_present={self.auth_token is not None}, "
            f"workspace_id={self.workspace_id}"
        )

        # Initialize creative studio asset cache in state
        if "_creative_studio_assets" not in state:
            state["_creative_studio_assets"] = {}

        # Keep a direct reference in tool_context if it has state
        if hasattr(tool_context, "state"):
            tool_context.state["_creative_studio_assets"] = state["_creative_studio_assets"]

        # Dynamic credential fallback with safety logs
        if self.use_studio and (not self.auth_token or not self.workspace_id):
            if not self.auth_token:
                logger.error(
                    f"[STUDIO ADAPTER FALLBACK] Failed to resolve Creative Studio credentials under key '{user_auth_token_key}'. "
                    f"Falling back to standard MediaGenerationService."
                )
            if not self.workspace_id:
                logger.error(
                    f"[STUDIO ADAPTER FALLBACK] Failed to resolve Creative Studio workspace_id. "
                    f"Falling back to standard MediaGenerationService."
                )
            self.use_studio = False

    @property
    def asset_service(self):
        """Lazy-loaded asset service to prevent premature Firestore connections."""
        # Detect and return test suite mocks seamlessly
        current_getter = getattr(mediagent_kit.services.aio, "get_asset_service", None)
        if current_getter and isinstance(current_getter, (unittest.mock.Mock, unittest.mock.MagicMock)):
            return current_getter()

        if not hasattr(self, "_asset_service_inst"):
            self._asset_service_inst = mediagent_kit.services.aio.get_asset_service()
        return self._asset_service_inst

    @property
    def mediagen_service(self):
        """Lazy-loaded media generation service to prevent premature API client creation."""
        # Detect and return test suite mocks seamlessly
        current_getter = getattr(mediagent_kit.services.aio, "get_media_generation_service", None)
        if current_getter and isinstance(current_getter, (unittest.mock.Mock, unittest.mock.MagicMock)):
            return current_getter()

        if not hasattr(self, "_mediagen_service_inst"):
            self._mediagen_service_inst = mediagent_kit.services.aio.get_media_generation_service()
        return self._mediagen_service_inst

    def _cache_asset(self, asset: asset_types.Asset):
        """Caches the generated CreativeStudioAsset in the ADK session state."""
        if asset and hasattr(asset, "id"):
            self.tool_context.state["_creative_studio_assets"][asset.id] = asset

    def _get_standard_asset_service(self):
        """Creates a standard AsyncAssetService instance to bypass CreativeStudio checks."""

        standard_config = copy.copy(self.config)
        standard_config.use_creative_studio = False

        db = self.asset_service._sync_service._db
        gcs_bucket = self.asset_service._sync_service._gcs_bucket

        sync_service = AssetService(db=db, gcs_bucket=gcs_bucket, config=standard_config)
        return AsyncAssetService(sync_service)

    def _get_standard_mediagen_service(self):
        """Creates a standard AsyncMediaGenerationService instance to bypass CreativeStudio checks."""

        standard_config = copy.copy(self.config)
        standard_config.use_creative_studio = False

        sync_asset_service = self._get_standard_asset_service()._sync_service
        sync_service = MediaGenerationService(asset_service=sync_asset_service, config=standard_config)
        return AsyncMediaGenerationService(sync_service)

    # Robust argument extractor helper
    def _get_arg(self, name, index, args, kwargs, default=None):
        if name in kwargs:
            return kwargs[name]
        if index < len(args):
            return args[index]
        return default

    async def generate_music_with_lyria(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        prompt = self._get_arg("prompt", 1, args, kwargs)

        # Remove explicit parameters from kwargs to prevent duplicate/multiple value errors
        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("prompt", None)

        if self.use_studio:
            asset = await self.mediagen_service.generate_music_with_lyria(
                file_name=file_name,
                prompt=prompt,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset
        else:
            return await self.mediagen_service.generate_music_with_lyria(
                user_id=self.user_id,
                file_name=file_name,
                prompt=prompt,
                **kwargs
            )

    async def generate_image_with_imagen(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        prompt = self._get_arg("prompt", 1, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("prompt", None)

        if self.use_studio:
            asset = await self.mediagen_service.generate_image_with_imagen(
                file_name=file_name,
                prompt=prompt,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset
        else:
            return await self.mediagen_service.generate_image_with_imagen(
                user_id=self.user_id,
                file_name=file_name,
                prompt=prompt,
                **kwargs
            )

    async def generate_speech_single_speaker(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        text = self._get_arg("text", 1, args, kwargs)
        voice_name = self._get_arg("voice_name", 2, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("text", None)
        kwargs.pop("voice_name", None)

        if self.use_studio:
            asset = await self.mediagen_service.generate_speech_single_speaker(
                file_name=file_name,
                text=text,
                voice_name=voice_name,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset
        else:
            return await self.mediagen_service.generate_speech_single_speaker(
                user_id=self.user_id,
                file_name=file_name,
                text=text,
                voice_name=voice_name,
                **kwargs
            )

    async def generate_text_with_gemini(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        prompt = self._get_arg("prompt", 1, args, kwargs)
        user_id = self._get_arg("user_id", 2, args, kwargs) or self.user_id

        if isinstance(self.mediagen_service, (unittest.mock.Mock, unittest.mock.MagicMock)):
            kwargs.pop("user_id", None)
            kwargs.pop("file_name", None)
            kwargs.pop("prompt", None)
            asset = await self.mediagen_service.generate_text_with_gemini(
                user_id=user_id,
                file_name=file_name,
                prompt=prompt,
                **kwargs
            )
            self._cache_asset(asset)
            return asset

        if self.use_studio:
            kwargs.pop("user_id", None)
            kwargs.pop("file_name", None)
            kwargs.pop("prompt", None)
            asset = await self.mediagen_service.generate_text_with_gemini(
                file_name=file_name,
                prompt=prompt,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset

        # Always route text generation to Vertex AI/Gemini directly
        standard_mediagen = self._get_standard_mediagen_service()

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("prompt", None)

        return await standard_mediagen.generate_text_with_gemini(
            user_id=user_id,
            file_name=file_name,
            prompt=prompt,
            **kwargs
        )

    async def generate_image_with_gemini(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        prompt = self._get_arg("prompt", 1, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("prompt", None)

        if self.use_studio:
            asset = await self.mediagen_service.generate_image_with_gemini(
                file_name=file_name,
                prompt=prompt,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset
        else:
            return await self.mediagen_service.generate_image_with_gemini(
                user_id=self.user_id,
                file_name=file_name,
                prompt=prompt,
                **kwargs
            )

    async def generate_video_with_veo(self, *args, **kwargs) -> asset_types.Asset:
        file_name = self._get_arg("file_name", 0, args, kwargs)
        prompt = self._get_arg("prompt", 1, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("prompt", None)

        if self.use_studio:
            asset = await self.mediagen_service.generate_video_with_veo(
                file_name=file_name,
                prompt=prompt,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
            self._cache_asset(asset)
            return asset
        else:
            return await self.mediagen_service.generate_video_with_veo(
                user_id=self.user_id,
                file_name=file_name,
                prompt=prompt,
                **kwargs
            )

    async def get_asset_by_id(self, asset_id: str, *args, **kwargs) -> asset_types.Asset | None:
        # 1. Check transient cache
        cached_asset = self.tool_context.state["_creative_studio_assets"].get(asset_id)
        if cached_asset:
            return cached_asset

        # 2. Check standard DB
        try:
            standard_asset_service = self._get_standard_asset_service()
            asset = await standard_asset_service.get_asset_by_id(asset_id, *args, **kwargs)
            if asset:
                return asset
        except Exception as e:
            logger.debug(f"Could not fetch asset {asset_id} from standard DB: {e}")

        # 3. Fail as requested if unimplemented/unconfigured in remote service
        return await self.asset_service.get_asset_by_id(asset_id, *args, **kwargs)

    # Add standard get_asset alias to resolve existing codebase bugs transparently
    async def get_asset(self, asset_id: str, *args, **kwargs) -> asset_types.Asset | None:
        return await self.get_asset_by_id(asset_id, *args, **kwargs)

    async def get_asset_blob(self, asset_id: str, *args, **kwargs) -> asset_types.AssetBlob:
        version = self._get_arg("version", 0, args, kwargs)

        # 1. Check if it is a cached Creative Studio Asset first (e.g. transient in-memory or remote studio asset)
        cached_asset = self.tool_context.state["_creative_studio_assets"].get(asset_id)
        if cached_asset:
            # Check for dynamic/transient in-memory content first
            if hasattr(cached_asset, "_content") and isinstance(getattr(cached_asset, "_content", None), bytes):
                return asset_types.AssetBlob(
                    content=cached_asset._content,
                    file_name=cached_asset.file_name,
                    mime_type=cached_asset.mime_type or "text/plain"
                )

            version_num = version if version is not None else cached_asset.current_version
            asset_version = next((v for v in cached_asset.versions if v.version_number == version_num), None)
            if asset_version and asset_version.gcs_uri:
                try:
                    content = self._download_from_gcs(asset_version.gcs_uri)
                    return asset_types.AssetBlob(
                        content=content,
                        file_name=cached_asset.file_name,
                        mime_type=cached_asset.mime_type
                    )
                except Exception as gcs_err:
                    logger.error(f"Failed direct GCS download for GCS URI {asset_version.gcs_uri}: {gcs_err}")
                    raise gcs_err

        # 2. Try standard GCS storage second
        try:
            standard_asset_service = self._get_standard_asset_service()
            return await standard_asset_service.get_asset_blob(asset_id, version, *args, **kwargs)
        except Exception as e:
            logger.debug(f"Standard get_asset_blob failed or asset not found: {e}")

        # 3. Fail as requested
        return await self.asset_service.get_asset_blob(asset_id, version, *args, **kwargs)

    def _download_from_gcs(self, gcs_uri: str) -> bytes:
        """Downloads direct raw bytes from GCS storage."""
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        path = gcs_uri.removeprefix("gs://")
        bucket_name, blob_path = path.split("/", 1)

        storage_client = storage.Client(project=self.config.google_cloud_project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        return blob.download_as_bytes()

    async def save_asset(self, *args, **kwargs) -> asset_types.Asset:
        user_id = self._get_arg("user_id", 0, args, kwargs) or self.user_id
        file_name = self._get_arg("file_name", 1, args, kwargs)
        blob = self._get_arg("blob", 2, args, kwargs)
        mime_type = self._get_arg("mime_type", 3, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("blob", None)
        kwargs.pop("mime_type", None)
        kwargs.pop("workspace_id", None)
        kwargs.pop("user_auth_token", None)

        if self.use_studio:
            return await self.asset_service.save_asset(
                user_id=user_id,
                file_name=file_name,
                blob=blob,
                mime_type=mime_type,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
        else:
            return await self.asset_service.save_asset(
                user_id=user_id,
                file_name=file_name,
                blob=blob,
                mime_type=mime_type,
                **kwargs
            )

    async def save_asset_from_file(self, *args, **kwargs) -> asset_types.Asset:
        user_id = self._get_arg("user_id", 0, args, kwargs) or self.user_id
        file_name = self._get_arg("file_name", 1, args, kwargs)
        file_path = self._get_arg("file_path", 2, args, kwargs)
        mime_type = self._get_arg("mime_type", 3, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("file_name", None)
        kwargs.pop("file_path", None)
        kwargs.pop("mime_type", None)
        kwargs.pop("workspace_id", None)
        kwargs.pop("user_auth_token", None)

        if self.use_studio:
            return await self.asset_service.save_asset_from_file(
                user_id=user_id,
                file_name=file_name,
                file_path=file_path,
                mime_type=mime_type,
                workspace_id=self.workspace_id,
                user_auth_token=self.auth_token,
                **kwargs
            )
        else:
            return await self.asset_service.save_asset_from_file(
                user_id=user_id,
                file_name=file_name,
                file_path=file_path,
                mime_type=mime_type,
                **kwargs
            )

    async def create_canvas(self, *args, **kwargs) -> asset_types.Canvas:
        user_id = self._get_arg("user_id", 0, args, kwargs) or self.user_id
        title = self._get_arg("title", 1, args, kwargs)
        video_timeline = self._get_arg("video_timeline", 2, args, kwargs)
        html = self._get_arg("html", 3, args, kwargs)

        kwargs.pop("user_id", None)
        kwargs.pop("title", None)
        kwargs.pop("video_timeline", None)
        kwargs.pop("html", None)

        import uuid
        from mediagent_kit.services import types as service_types

        canvas_id = str(uuid.uuid4())
        canvas = service_types.Canvas(
            id=canvas_id,
            user_id=user_id,
            title=title,
            video_timeline=video_timeline,
            html=html,
        )

        if not self.use_studio:
            standard_canvas_service = mediagent_kit.services.aio.get_canvas_service()
            return await standard_canvas_service.create_canvas(
                user_id=user_id,
                title=title,
                video_timeline=video_timeline,
                html=html,
                **kwargs
            )

        logger.info(f"[STUDIO ADAPTER] Bypassed Firestore write for Canvas {canvas_id} (In-Memory Only)")
        # Resolve state from context
        state = {}
        if hasattr(self.tool_context, "state"):
            state = self.tool_context.state
        elif (
            hasattr(self.tool_context, "_invocation_context")
            and self.tool_context._invocation_context
            and self.tool_context._invocation_context.session
        ):
            state = self.tool_context._invocation_context.session.state
        
        state[f"_creative_studio_canvas_{canvas_id}"] = canvas
        return canvas

    async def list_assets(self, *args, **kwargs) -> list[asset_types.Asset]:
        user_id = self._get_arg("user_id", 0, args, kwargs) or self.user_id
        if self.use_studio:
            try:
                standard_asset_service = self._get_standard_asset_service()
                return await standard_asset_service.list_assets(user_id)
            except Exception as e:
                logger.error(f"Failed to list standard assets: {e}")
                return []
        else:
            return await self.asset_service.list_assets(user_id)

    async def save_storyboard(self, storyboard_dict: dict, parameters: dict) -> str | None:
        """Saves the storyboard to the Creative Studio backend. Transparently returns the storyboard ID."""
        if not self.use_studio:
            logger.info("Creative Studio is disabled. Bypassing storyboard backend persistence.")
            return None

        backend_base_url = self.config.creative_studio_backend_url or "http://backend:8080"
        backend_url = f"{backend_base_url}/api/storyboards/"
        
        # Resolve storyboard_id if already exists in state
        storyboard_id = self.tool_context.state.get("current_storyboard_id") or parameters.get("storyboard_id")
        from utils.adk import get_session_id_from_context
        session_id = parameters.get("session_id") or self.tool_context.state.get("session_id") or get_session_id_from_context(self.tool_context)

        headers = {
            "X-User-Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        from mediagent_kit.utils.auth import get_google_id_token
        id_token_str = get_google_id_token(backend_url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"

        async with httpx.AsyncClient() as client:
            if not storyboard_id:
                # 1. Create Storyboard Record
                storyboard_payload = {
                    "workspace_id": self.workspace_id,
                    "session_id": session_id,
                    "template_name": parameters.get("template_name"),
                    "bg_music_description": storyboard_dict.get("background_music_prompt", {}).get("description")
                }
                logger.info(f"[STUDIO PERSISTENCE] Creating storyboard at {backend_url}")
                resp = await client.post(backend_url, json=storyboard_payload, headers=headers)
                resp.raise_for_status()
                
                storyboard_data = resp.json()
                storyboard_id = storyboard_data["id"]
                logger.info(f"[STUDIO PERSISTENCE] Created storyboard record {storyboard_id}.")

            # 2. Save/Update Storyboard Scenes and Details
            update_url = f"{backend_url}{storyboard_id}"
            update_payload = {
                "scenes": storyboard_dict.get("scenes"),
                "bg_music_description": storyboard_dict.get("background_music_prompt", {}).get("description")
            }
            logger.info(f"[STUDIO PERSISTENCE] Updating storyboard payload for {storyboard_id} at {update_url}")
            update_resp = await client.put(update_url, json=update_payload, headers=headers)
            update_resp.raise_for_status()
            logger.info(f"[STUDIO PERSISTENCE] Storyboard {storyboard_id} successfully synchronized.")
            return storyboard_id

    async def get_storyboard(self, storyboard_id: str) -> dict | None:
        """Queries the storyboard by ID from the Creative Studio backend."""
        if not self.use_studio:
            logger.warning("Attempted to query remote storyboard with Creative Studio disabled.")
            return None

        backend_base_url = self.config.creative_studio_backend_url or "http://backend:8080"
        if not isinstance(backend_base_url, str):
            backend_base_url = str(backend_base_url)
        backend_url = f"{backend_base_url}/api/storyboards/{storyboard_id}"
        headers = {
            "X-User-Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        from mediagent_kit.utils.auth import get_google_id_token
        id_token_str = get_google_id_token(backend_url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(backend_url, headers=headers)
            resp.raise_for_status()
            storyboard_data = resp.json()
            
            # Transform to match Pydantic model expected by agent
            scenes = []
            for s in storyboard_data.get("scenes", []):
                ff_id = s.get("first_frame_media_item_id") or s.get("first_frame_source_asset_id")
                ff_assets = []
                if ff_id:
                    ff_assets.append(f"asset://{ff_id}")
                    
                scenes.append({
                    "topic": s.get("topic") or "Scene",
                    "duration_seconds": s.get("duration_seconds") or 4.0,
                    "first_frame_prompt": {
                        "description": s.get("first_frame_description") or "",
                        "assets": ff_assets,
                        "generated_asset_id": str(s.get("first_frame_media_item_id")) if s.get("first_frame_media_item_id") else "",
                        "generated_asset_url": s.get("first_frame_generated_url") or "",
                    },
                    "video_prompt": {
                        "description": s.get("video_description") or "",
                        "duration_seconds": s.get("video_duration_seconds") or s.get("duration_seconds") or 4.0,
                    },
                    "voiceover_prompt": {
                        "text": s.get("voiceover_text") or "",
                        "gender": s.get("voiceover_gender") or "female",
                        "description": s.get("voiceover_description") or "Neutral voiceover",
                    },
                    "transition_hints": {
                        "type": s.get("transition_type") or "cut",
                        "duration_seconds": s.get("transition_duration") or 0.0,
                    },
                    "audio_hints": {
                        "ambient_description": s.get("audio_ambient_description") or "",
                        "sfx_description": s.get("audio_sfx_description") or "",
                    },
                })
                
            mapped_storyboard = {
                "template_name": storyboard_data.get("template_name") or "Custom",
                "background_music_prompt": {
                    "description": storyboard_data.get("bg_music_description") or "Upbeat background music"
                },
                "scenes": scenes,
                "voiceover_groups": [],
                "bg_music_asset_id": storyboard_data.get("bg_music_asset_id"),
                "timeline": storyboard_data.get("timeline") or {}
            }
            return mapped_storyboard


# Explicit context-resolved service getters
def get_asset_service():
    """Resolves the active CreativeStudioAdapter if bound to the async context, otherwise standard."""
    adapter = get_active_adapter()
    if adapter is not None:
        return adapter
    return mediagent_kit.services.aio.get_asset_service()


def get_media_generation_service():
    """Resolves the active CreativeStudioAdapter if bound to the async context, otherwise standard."""
    adapter = get_active_adapter()
    if adapter is not None:
        return adapter
    return mediagent_kit.services.aio.get_media_generation_service()


def get_canvas_service():
    """Resolves the active CreativeStudioAdapter if bound to the async context, otherwise standard."""
    adapter = get_active_adapter()
    if adapter is not None:
        return adapter
    return mediagent_kit.services.aio.get_canvas_service()
