# Copyright 2026 Google LLC
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

"""Creative Studio implementation of StoryboardServiceInterface."""

import logging
from typing import Any, Optional, Union

import httpx

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.errors import (
    AuthenticationError,
    AuthorizationError,
    BackendError,
    NotFoundError,
    ValidationError,
)
from mediagent_kit.services.interfaces import StoryboardServiceInterface
from mediagent_kit.services.types.storyboard import Storyboard
from mediagent_kit.utils.auth import get_google_id_token
from mediagent_kit.utils.context import get_request_context

logger = logging.getLogger(__name__)


class CSStoryboardService(StoryboardServiceInterface):
    """Creative Studio implementation of StoryboardServiceInterface."""

    def __init__(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
        config: MediagentKitConfig | None = None,
    ):
        self._workspace_id = workspace_id
        self._user_auth_token = user_auth_token
        self._config = config or MediagentKitConfig()

    def _safe_int(self, val: Any) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _normalize_prompt(
        self, prompt_dict: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Normalizes prompt dict to strictly separate media_item_id (generated) vs asset_id (uploaded).

        Explicitly returns an updated dictionary rather than mutating references in-place.
        """
        if not prompt_dict or not isinstance(prompt_dict, dict):
            return prompt_dict

        res = dict(prompt_dict)
        ref = res.get("asset_ref")
        if isinstance(ref, dict) and ref.get("id"):
            ref_id = str(ref["id"])
            asset_type = ref.get("asset_type", "generated")
            int_id = self._safe_int(ref_id)
            if asset_type in ("generated", "media_item"):
                res["media_item_id"] = int_id
            elif asset_type in ("uploaded", "source_asset"):
                res["source_asset_id"] = int_id

        return res

    def _get_workspace_id(self, override: str | None = None) -> str:
        ctx = get_request_context() or {}
        ws_id = override or ctx.get("workspace_id") or self._workspace_id
        if not ws_id or not str(ws_id).isdigit():
            raise ValidationError(
                f"Invalid workspace_id: '{ws_id}'. Workspace ID must be a non-empty numeric string."
            )
        return str(ws_id)

    def _get_user_auth_token(self) -> str:
        ctx = get_request_context()
        if ctx:
            token_key = self._config.cs_user_auth_token_key or "user_auth_token"
            token = ctx.get(token_key) or ctx.get("user_auth_token")
            if token:
                return str(token)
        if self._user_auth_token:
            return self._user_auth_token
        raise ValueError("user_auth_token is required")

    def _get_headers(
        self,
        token: str,
        url: str,
        content_type: str | None = "application/json",
    ) -> dict[str, str]:
        headers = {
            "X-User-Authorization": f"Bearer {token}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        id_token_str = get_google_id_token(url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"
        return headers

    def _handle_error_response(self, response: httpx.Response) -> None:
        status_code = response.status_code
        try:
            error_json = response.json()
            message = error_json.get("message") or response.text
        except Exception:
            message = response.text or f"HTTP error {status_code}"

        if status_code == 401:
            raise AuthenticationError(message, status_code=status_code)
        if status_code == 403:
            raise AuthorizationError(message, status_code=status_code)
        if status_code == 404:
            raise NotFoundError(message, status_code=status_code)
        if status_code in (400, 422):
            raise ValidationError(message, status_code=status_code)
        raise BackendError(message, status_code=status_code)

    async def save_storyboard(
        self,
        storyboard: Union[Storyboard, dict[str, Any]],
        idempotency_key: Optional[str] = None,
    ) -> Union[Storyboard, dict[str, Any]]:
        """Persists the storyboard (create-or-replace) to Creative Studio backend."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        endpoint = f"{backend_url}/api/storyboards/"

        # Handle Pydantic Storyboard model vs dict
        if isinstance(storyboard, Storyboard):
            sb_dict = storyboard.model_dump()
            storyboard_id = storyboard.storyboard_id
            workspace_id = storyboard.workspace_id
            session_id = getattr(storyboard, "session_id", None) or getattr(
                storyboard, "sessionId", None
            )
            template_name = storyboard.template_name
            bg_music_desc = (
                storyboard.background_music_prompt.description
                if storyboard.background_music_prompt
                else None
            )
            bg_music_id = (
                storyboard.background_music_asset.id
                if storyboard.background_music_asset
                else None
            )
        else:
            sb_dict = dict(storyboard)
            storyboard_id = (
                sb_dict.get("storyboard_id")
                or sb_dict.get("id")
                or sb_dict.get("current_storyboard_id")
            )
            workspace_id = sb_dict.get("workspace_id")
            session_id = sb_dict.get("session_id") or sb_dict.get("sessionId")
            template_name = sb_dict.get("template_name", "Custom")
            bg_music_prompt = sb_dict.get("background_music_prompt", {})
            bg_music_desc = (
                bg_music_prompt.get("description")
                if isinstance(bg_music_prompt, dict)
                else None
            )
            bg_music_asset = sb_dict.get("background_music_asset")
            bg_music_id = (
                bg_music_asset.get("id")
                if isinstance(bg_music_asset, dict)
                else sb_dict.get("bg_music_asset_id")
            )
            if not bg_music_id and isinstance(bg_music_prompt, dict):
                ref = bg_music_prompt.get("asset_ref")
                if isinstance(ref, dict):
                    bg_music_id = ref.get("id")

        # Normalize all scene prompts for backend media_item_id vs source_asset_id separation
        scenes = sb_dict.get("scenes", [])
        if isinstance(scenes, list):
            new_scenes = []
            for idx, scene in enumerate(scenes):
                if isinstance(scene, dict):
                    sc = dict(scene)
                    sc["order"] = idx
                    sc["first_frame_prompt"] = self._normalize_prompt(
                        sc.get("first_frame_prompt")
                    )
                    sc["video_prompt"] = self._normalize_prompt(sc.get("video_prompt"))
                    sc["voiceover_prompt"] = self._normalize_prompt(
                        sc.get("voiceover_prompt")
                    )
                    new_scenes.append(sc)
            sb_dict["scenes"] = new_scenes

        ws_id = self._get_workspace_id(workspace_id)
        headers = self._get_headers(token, endpoint)

        async with httpx.AsyncClient() as client:
            # 1. Create record if not yet assigned
            if not storyboard_id:
                create_payload = {
                    "workspace_id": self._safe_int(ws_id) or ws_id,
                    "session_id": session_id,
                    "template_name": template_name,
                    "bg_music_description": bg_music_desc,
                    "bg_music_asset_id": self._safe_int(bg_music_id),
                }
                logger.info(f"Creating new storyboard record at {endpoint}")
                resp = await client.post(endpoint, json=create_payload, headers=headers)
                if resp.is_error:
                    self._handle_error_response(resp)
                created_data = resp.json()
                storyboard_id = str(created_data.get("id"))
                logger.info(f"Created storyboard record with ID {storyboard_id}")

                # Update sb_dict and model immediately so step 2 sends the correct ID
                sb_dict["storyboard_id"] = storyboard_id
                if isinstance(storyboard, Storyboard):
                    storyboard.storyboard_id = storyboard_id

            # 2. Synchronize full payload via PUT /api/storyboards/{id}
            update_url = f"{endpoint}{storyboard_id}"
            update_headers = self._get_headers(token, update_url)
            update_payload = {
                "workspace_id": self._safe_int(ws_id) or ws_id,
                "session_id": session_id,
                "template_name": template_name,
                "bg_music_description": bg_music_desc,
                "bg_music_asset_id": self._safe_int(bg_music_id),
                "storyboard": sb_dict,
            }
            logger.info(
                f"Synchronizing storyboard {storyboard_id} payload at {update_url}"
            )
            resp = await client.put(
                update_url, json=update_payload, headers=update_headers
            )
            if resp.is_error:
                self._handle_error_response(resp)

        # Update ID fields on original input structure
        if isinstance(storyboard, Storyboard):
            storyboard.storyboard_id = storyboard_id
            storyboard.workspace_id = ws_id
            return storyboard

        sb_dict["storyboard_id"] = storyboard_id
        return sb_dict

    async def get_storyboard(
        self, storyboard_id: str
    ) -> Optional[Union[Storyboard, dict[str, Any]]]:
        """Returns the storyboard by ID from Creative Studio backend, fully hydrated with AssetRefs."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/storyboards/{storyboard_id}"
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return None
            if resp.is_error:
                self._handle_error_response(resp)
            data = resp.json()

        if not isinstance(data, dict):
            return data

        ws_id = str(data.get("workspace_id", self._workspace_id or "default"))

        # Hydrate backend response scenes into canonical ads_x storyboard format
        raw_scenes = data.get("scenes", [])
        hydrated_scenes = []
        for s in raw_scenes:
            if not isinstance(s, dict):
                continue

            ff_media_id = s.get("first_frame_media_item_id")
            ff_source_id = s.get("first_frame_source_asset_id")
            ff_id = ff_media_id or ff_source_id
            ff_type = (
                "generated" if ff_media_id else ("uploaded" if ff_source_id else None)
            )
            ff_ref = (
                {
                    "id": str(ff_id),
                    "asset_type": ff_type,
                    "workspace_id": ws_id,
                }
                if ff_id
                else None
            )

            v_media_id = s.get("video_media_item_id")
            v_source_id = s.get("video_source_asset_id")
            v_id = v_media_id or v_source_id
            v_type = (
                "generated" if v_media_id else ("uploaded" if v_source_id else None)
            )
            v_ref = (
                {
                    "id": str(v_id),
                    "asset_type": v_type,
                    "workspace_id": ws_id,
                }
                if v_id
                else None
            )

            vo_media_id = s.get("voiceover_media_item_id")
            vo_source_id = s.get("voiceover_source_asset_id")
            vo_id = vo_media_id or vo_source_id
            vo_type = (
                "generated" if vo_media_id else ("uploaded" if vo_source_id else None)
            )
            vo_ref = (
                {
                    "id": str(vo_id),
                    "asset_type": vo_type,
                    "workspace_id": ws_id,
                }
                if vo_id
                else None
            )

            ff_prompt: dict[str, Any] = {
                "description": s.get("first_frame_description") or "",
                "asset_ref": ff_ref,
                "generated_url": s.get("first_frame_generated_url"),
            }
            if ff_media_id:
                ff_prompt["media_item_id"] = str(ff_media_id)
            elif ff_source_id:
                ff_prompt["asset_id"] = str(ff_source_id)
                ff_prompt["source_asset_id"] = str(ff_source_id)

            v_prompt: dict[str, Any] = {
                "description": s.get("video_description") or "",
                "duration_seconds": s.get("video_duration_seconds")
                or s.get("duration_seconds")
                or 4.0,
                "asset_ref": v_ref,
                "generated_url": s.get("video_generated_url"),
            }
            if v_media_id:
                v_prompt["media_item_id"] = str(v_media_id)
            elif v_source_id:
                v_prompt["asset_id"] = str(v_source_id)
                v_prompt["source_asset_id"] = str(v_source_id)

            vo_prompt: dict[str, Any] = {
                "text": s.get("voiceover_text") or "",
                "gender": s.get("voiceover_gender") or "female",
                "description": s.get("voiceover_description") or "Voiceover",
                "asset_ref": vo_ref,
            }
            if vo_media_id:
                vo_prompt["media_item_id"] = str(vo_media_id)
            elif vo_source_id:
                vo_prompt["asset_id"] = str(vo_source_id)
                vo_prompt["source_asset_id"] = str(vo_source_id)

            scene_entry = {
                "id": str(s.get("id")) if s.get("id") else None,
                "order": s.get("order", len(hydrated_scenes)),
                "topic": s.get("topic") or "Scene",
                "duration_seconds": s.get("duration_seconds") or 4.0,
                "first_frame_prompt": ff_prompt,
                "video_prompt": v_prompt,
                "voiceover_prompt": vo_prompt,
                "transition_hints": {
                    "type": s.get("transition_type"),
                    "duration": s.get("transition_duration"),
                },
                "audio_hints": {
                    "ambient_sound": s.get("audio_ambient_description"),
                    "sfx": s.get("audio_sfx_description"),
                },
            }
            hydrated_scenes.append(scene_entry)

        data["storyboard_id"] = str(data.get("id"))
        data["scenes"] = hydrated_scenes
        if "voiceover_groups" not in data:
            data["voiceover_groups"] = []
        return data

    async def list_storyboards(
        self,
        workspace_id: str,
        session_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Union[Storyboard, dict[str, Any]]]:
        """Lists storyboards in the workspace."""
        token = self._get_user_auth_token()
        ws_id = self._get_workspace_id(workspace_id)
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/storyboards"
        params: dict[str, Any] = {
            "workspace_id": ws_id,
            "limit": limit,
            "offset": offset,
        }
        if session_id:
            params["session_id"] = session_id

        headers = self._get_headers(token, url)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.is_error:
                self._handle_error_response(resp)
            items = resp.json()
            if isinstance(items, list):
                return items
            if isinstance(items, dict) and "items" in items:
                return items["items"]
            return []

    async def delete_storyboard(self, storyboard_id: str) -> None:
        """Deletes the storyboard from Creative Studio backend."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/storyboards/{storyboard_id}"
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers)
            if resp.status_code == 404:
                return
            if resp.is_error:
                self._handle_error_response(resp)
