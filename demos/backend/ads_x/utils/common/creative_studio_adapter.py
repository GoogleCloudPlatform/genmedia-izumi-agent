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
import httpx

from mediagent_kit.services import _get_service_factory
import mediagent_kit.services.aio
from . import common_utils

logger = logging.getLogger(__name__)


async def save_storyboard(config, auth_token: str, workspace_id: str, tool_context: Any, storyboard_dict: dict, parameters: dict) -> str | None:
    """Saves the storyboard to the Creative Studio backend. Transparently returns the storyboard ID."""
    if not config.use_creative_studio:
        logger.info("Creative Studio is disabled. Bypassing storyboard backend persistence.")
        return None

    backend_base_url = config.creative_studio_backend_url or "http://backend:8080"
    backend_url = f"{backend_base_url}/api/storyboards/"
    
    # Resolve storyboard_id if already exists in state
    storyboard_id = tool_context.state.get("current_storyboard_id") or parameters.get("storyboard_id")
    from utils.adk import get_session_id_from_context
    session_id = parameters.get("session_id") or tool_context.state.get("session_id") or get_session_id_from_context(tool_context)

    headers = {
        "X-User-Authorization": f"Bearer {auth_token}",
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
                "workspace_id": workspace_id,
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


async def get_storyboard(config, auth_token: str, storyboard_id: str) -> dict | None:
    """Queries the storyboard by ID from the Creative Studio backend."""
    if not config.use_creative_studio:
        logger.warning("Attempted to query remote storyboard with Creative Studio disabled.")
        return None

    backend_base_url = config.creative_studio_backend_url or "http://backend:8080"
    if not isinstance(backend_base_url, str):
        backend_base_url = str(backend_base_url)
    backend_url = f"{backend_base_url}/api/storyboards/{storyboard_id}"
    headers = {
        "X-User-Authorization": f"Bearer {auth_token}",
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


def with_creative_studio_adapter(func):
    """Decorator to inject request context and auto-save storyboard changes."""

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

        # Handle state dictionary from either ToolContext or ReadonlyContext
        state = {}
        if hasattr(context, "state"):
            state = context.state
        elif (
            hasattr(context, "_invocation_context")
            and context._invocation_context
            and context._invocation_context.session
        ):
            state = context._invocation_context.session.state

        # Extract workspace/token credentials from state
        workspace_id = state.get("workspace_id", 1) # Remove this hardcoded one afterwards this is only for testing
        user_auth_token_key = os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token")
        auth_token = state.get(user_auth_token_key)
        
        # Initialize creative studio asset cache in state
        if "_creative_studio_assets" not in state:
            state["_creative_studio_assets"] = {}
        if hasattr(context, "state"):
            context.state["_creative_studio_assets"] = state["_creative_studio_assets"]
            
        config = _get_service_factory().get_config()

        from mediagent_kit.utils.context import set_request_context, reset_request_context
        creds_token = set_request_context(
            user_auth_token=auth_token,
            workspace_id=workspace_id,
            transient_cache=state["_creative_studio_assets"]
        )
        
        # Snapshot storyboard state before tool execution
        old_storyboard = None
        if config.use_creative_studio and state and common_utils.STORYBOARD_KEY in state:
            old_storyboard = copy.deepcopy(state[common_utils.STORYBOARD_KEY])
            
        try:
            result = await func(*args, **kwargs)
            
            # Compare and auto-save after successful execution
            if config.use_creative_studio and auth_token and workspace_id and state and common_utils.STORYBOARD_KEY in state:
                current_storyboard = state[common_utils.STORYBOARD_KEY]
                if current_storyboard != old_storyboard:
                    logger.info("[STUDIO PERSISTENCE] Storyboard changes detected. Auto-synchronizing with backend...")
                    parameters = state.get(common_utils.PARAMETERS_KEY, {})
                    try:
                        storyboard_id = await save_storyboard(config, auth_token, str(workspace_id), context, current_storyboard, parameters)
                        if storyboard_id:
                            state["current_storyboard_id"] = storyboard_id
                            if isinstance(parameters, dict):
                                parameters["storyboard_id"] = storyboard_id
                    except Exception as save_err:
                        logger.error(f"[STUDIO PERSISTENCE] Auto-save failed: {save_err}")
                        
            return result
        finally:
            reset_request_context(creds_token)
    return wrapper


