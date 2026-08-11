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

"""Creative Studio implementation of VideoTimelineServiceInterface."""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Optional

import httpx

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.creative_studio.cs_asset_service import CSAssetService
from mediagent_kit.services.errors import (
    AuthenticationError,
    AuthorizationError,
    BackendError,
    NotFoundError,
    ValidationError,
)
from mediagent_kit.services.interfaces import VideoTimelineServiceInterface
from mediagent_kit.services.types.common import (
    AssetRef,
    AudioPlacement,
    GeneratedAsset,
    GenerationMetadata,
    ScopedVideoTimeline,
    TimelineAudioClip,
    TimelineVideoClip,
    Transition,
    TransitionType,
    Trim,
)
from mediagent_kit.utils.auth import get_google_id_token
from mediagent_kit.utils.context import get_request_context

logger = logging.getLogger(__name__)


class CSTimelineService(VideoTimelineServiceInterface):
    """Creative Studio implementation of VideoTimelineServiceInterface."""

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

    def _convert_asset_ref_to_cs(
        self, ref: AssetRef | dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Converts SDK AssetRef to CS backend AssetRef format."""
        if not ref:
            return None
        if isinstance(ref, AssetRef):
            ref_id = ref.id
            asset_type = ref.asset_type
        elif isinstance(ref, dict):
            ref_id = ref.get("id")
            asset_type = ref.get("asset_type", "generated")
        else:
            return None

        if not ref_id:
            return None

        cs_type = (
            "media_item"
            if asset_type in ("generated", "media_item")
            else "source_asset"
        )
        return {
            "id": self._safe_int(ref_id) or str(ref_id),
            "type": cs_type,
        }

    def _convert_asset_ref_from_cs(
        self, ref_dict: dict[str, Any] | None, workspace_id: str
    ) -> AssetRef | None:
        """Converts CS backend AssetRef dict to SDK AssetRef model."""
        if not ref_dict or not isinstance(ref_dict, dict):
            return None
        raw_id = ref_dict.get("id")
        if not raw_id:
            return None

        cs_type = ref_dict.get("type", "media_item")
        sdk_type = "generated" if cs_type in ("media_item", "generated") else "uploaded"
        return AssetRef(
            id=str(raw_id),
            asset_type=sdk_type,
            workspace_id=workspace_id,
        )

    def _to_cs_payload(self, timeline: ScopedVideoTimeline) -> dict[str, Any]:
        """Converts ScopedVideoTimeline to Creative Studio backend payload."""
        ws_id = self._get_workspace_id(timeline.workspace_id)

        video_clips = []
        for vc in timeline.video_clips:
            clip_dict: dict[str, Any] = {
                "volume": vc.volume,
                "speed": vc.speed,
            }
            if vc.asset_ref:
                clip_dict["asset_ref"] = self._convert_asset_ref_to_cs(vc.asset_ref)
            if vc.trim:
                clip_dict["trim"] = {"offset_seconds": vc.trim.offset_seconds}
                if vc.trim.duration_seconds is not None:
                    clip_dict["trim"]["duration_seconds"] = vc.trim.duration_seconds
            if vc.first_frame_asset_ref:
                clip_dict["first_frame_asset_ref"] = self._convert_asset_ref_to_cs(
                    vc.first_frame_asset_ref
                )
            if vc.last_frame_asset_ref:
                clip_dict["last_frame_asset_ref"] = self._convert_asset_ref_to_cs(
                    vc.last_frame_asset_ref
                )
            if vc.placeholder:
                clip_dict["placeholder"] = vc.placeholder
            video_clips.append(clip_dict)

        audio_clips = []
        for ac in timeline.audio_clips:
            ac_dict: dict[str, Any] = {
                "start_at": {
                    "video_clip_index": ac.start_at.video_clip_index,
                    "offset_seconds": ac.start_at.offset_seconds,
                },
                "volume": ac.volume,
                "speed": ac.speed,
                "fade_in_duration_seconds": ac.fade_in_duration_seconds,
                "fade_out_duration_seconds": ac.fade_out_duration_seconds,
            }
            if ac.asset_ref:
                ac_dict["asset_ref"] = self._convert_asset_ref_to_cs(ac.asset_ref)
            if ac.trim:
                ac_dict["trim"] = {"offset_seconds": ac.trim.offset_seconds}
                if ac.trim.duration_seconds is not None:
                    ac_dict["trim"]["duration_seconds"] = ac.trim.duration_seconds
            if ac.placeholder:
                ac_dict["placeholder"] = ac.placeholder
            audio_clips.append(ac_dict)

        transitions = []
        for t in timeline.transitions:
            if t:
                transitions.append(
                    {
                        "type": (
                            t.type.value
                            if isinstance(t.type, TransitionType)
                            else str(t.type)
                        ),
                        "duration_seconds": t.duration_seconds,
                    }
                )
            else:
                transitions.append(None)

        payload: dict[str, Any] = {
            "workspace_id": self._safe_int(ws_id) or ws_id,
            "session_id": timeline.session_id,
            "storyboard_id": self._safe_int(timeline.storyboard_id)
            or timeline.storyboard_id,
            "title": timeline.title,
            "video_clips": video_clips,
            "audio_clips": audio_clips,
            "transitions": transitions,
        }
        if timeline.timeline_id:
            payload["timeline_id"] = (
                self._safe_int(timeline.timeline_id) or timeline.timeline_id
            )
        if timeline.transition_in:
            payload["transition_in"] = {
                "type": (
                    timeline.transition_in.type.value
                    if isinstance(timeline.transition_in.type, TransitionType)
                    else str(timeline.transition_in.type)
                ),
                "duration_seconds": timeline.transition_in.duration_seconds,
            }
        if timeline.transition_out:
            payload["transition_out"] = {
                "type": (
                    timeline.transition_out.type.value
                    if isinstance(timeline.transition_out.type, TransitionType)
                    else str(timeline.transition_out.type)
                ),
                "duration_seconds": timeline.transition_out.duration_seconds,
            }

        return payload

    def _from_cs_response(self, data: dict[str, Any]) -> ScopedVideoTimeline:
        """Parses Creative Studio backend response into ScopedVideoTimeline."""
        ws_id = str(data.get("workspace_id", self._workspace_id or "default"))

        video_clips = []
        for vc in data.get("video_clips", []):
            if not isinstance(vc, dict):
                continue
            trim_obj = None
            if isinstance(vc.get("trim"), dict):
                trim_obj = Trim(
                    offset_seconds=vc["trim"].get("offset_seconds", 0.0),
                    duration_seconds=vc["trim"].get("duration_seconds"),
                )
            video_clips.append(
                TimelineVideoClip(
                    asset_ref=self._convert_asset_ref_from_cs(
                        vc.get("asset_ref"), ws_id
                    ),
                    trim=trim_obj,
                    volume=float(vc.get("volume", 1.0)),
                    speed=float(vc.get("speed", 1.0)),
                    first_frame_asset_ref=self._convert_asset_ref_from_cs(
                        vc.get("first_frame_asset_ref"), ws_id
                    ),
                    last_frame_asset_ref=self._convert_asset_ref_from_cs(
                        vc.get("last_frame_asset_ref"), ws_id
                    ),
                    placeholder=vc.get("placeholder"),
                )
            )

        audio_clips = []
        for ac in data.get("audio_clips", []):
            if not isinstance(ac, dict):
                continue
            start_at_dict = ac.get("start_at", {})
            start_at = AudioPlacement(
                video_clip_index=start_at_dict.get("video_clip_index", 0),
                offset_seconds=float(start_at_dict.get("offset_seconds", 0.0)),
            )
            trim_obj = None
            if isinstance(ac.get("trim"), dict):
                trim_obj = Trim(
                    offset_seconds=ac["trim"].get("offset_seconds", 0.0),
                    duration_seconds=ac["trim"].get("duration_seconds"),
                )
            audio_clips.append(
                TimelineAudioClip(
                    start_at=start_at,
                    asset_ref=self._convert_asset_ref_from_cs(
                        ac.get("asset_ref"), ws_id
                    ),
                    trim=trim_obj,
                    volume=float(ac.get("volume", 1.0)),
                    speed=float(ac.get("speed", 1.0)),
                    fade_in_duration_seconds=float(
                        ac.get("fade_in_duration_seconds", 0.0)
                    ),
                    fade_out_duration_seconds=float(
                        ac.get("fade_out_duration_seconds", 0.0)
                    ),
                    placeholder=ac.get("placeholder"),
                )
            )

        transitions = []
        for t in data.get("transitions", []):
            if isinstance(t, dict) and t.get("type"):
                transitions.append(
                    Transition(
                        type=TransitionType(t["type"]),
                        duration_seconds=float(t.get("duration_seconds", 0.5)),
                    )
                )
            else:
                transitions.append(None)

        t_in = None
        if isinstance(data.get("transition_in"), dict) and data["transition_in"].get(
            "type"
        ):
            t_in = Transition(
                type=TransitionType(data["transition_in"]["type"]),
                duration_seconds=float(
                    data["transition_in"].get("duration_seconds", 0.5)
                ),
            )

        t_out = None
        if isinstance(data.get("transition_out"), dict) and data["transition_out"].get(
            "type"
        ):
            t_out = Transition(
                type=TransitionType(data["transition_out"]["type"]),
                duration_seconds=float(
                    data["transition_out"].get("duration_seconds", 0.5)
                ),
            )

        sb_id = data.get("storyboard_id")
        if sb_id is None:
            sb_id = data.get("storyboardId")
        sb_id_str = str(sb_id) if sb_id is not None else None

        return ScopedVideoTimeline(
            timeline_id=str(data.get("id") or data.get("timeline_id")),
            workspace_id=ws_id,
            user_id=str(data.get("user_id")) if data.get("user_id") else None,
            session_id=(
                str(data.get("session_id"))
                if data.get("session_id") is not None
                else None
            ),
            storyboard_id=sb_id_str,
            title=data.get("title", "Untitled Timeline"),
            video_clips=video_clips,
            audio_clips=audio_clips,
            transitions=transitions,
            transition_in=t_in,
            transition_out=t_out,
        )

    async def create_timeline(
        self,
        workspace_id: str,
        session_id: Optional[str] = None,
        storyboard_id: Optional[str] = None,
        title: Optional[str] = None,
        timeline: Optional[ScopedVideoTimeline] = None,
    ) -> ScopedVideoTimeline:
        """Creates a timeline document on Creative Studio backend."""
        token = self._get_user_auth_token()
        ws_id = self._get_workspace_id(workspace_id)
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/workbench/timelines"

        if timeline:
            initial_timeline = timeline
            if storyboard_id and not initial_timeline.storyboard_id:
                initial_timeline.storyboard_id = storyboard_id
        else:
            initial_timeline = ScopedVideoTimeline(
                workspace_id=ws_id,
                session_id=session_id,
                storyboard_id=storyboard_id,
                title=title or "Untitled Timeline",
                video_clips=[],
            )
        payload = self._to_cs_payload(initial_timeline)
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.is_error:
                self._handle_error_response(resp)
            data = resp.json()

        return self._from_cs_response(data)

    async def get_timeline(self, timeline_id: str) -> Optional[ScopedVideoTimeline]:
        """Returns the timeline by ID from Creative Studio backend."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/workbench/timelines/{timeline_id}"
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return None
            if resp.is_error:
                self._handle_error_response(resp)
            data = resp.json()

        return self._from_cs_response(data)

    async def update_timeline(
        self,
        timeline_id: str,
        timeline: ScopedVideoTimeline,
    ) -> None:
        """Replaces the timeline content on Creative Studio backend."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/workbench/timelines/{timeline_id}"

        payload = self._to_cs_payload(timeline)
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.put(url, json=payload, headers=headers)
            if resp.is_error:
                self._handle_error_response(resp)

    async def stitch_timeline(
        self,
        timeline_id: str,
        output_filename: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Renders the timeline to a single video asset using Creative Studio backend."""
        token = self._get_user_auth_token()
        ws_id = self._get_workspace_id()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/workbench/timelines/{timeline_id}/render"
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers)
            if resp.is_error:
                self._handle_error_response(resp)
            initial_data = resp.json()

            item_id = initial_data.get("id") or initial_data.get("asset_id")
            if not item_id:
                raise BackendError("No item ID returned from CS timeline render")

            # Polling loop
            poll_url = f"{backend_url}/api/gallery/item/{item_id}"
            start_time = time.time()
            curr_interval = 2.0
            timeout = 600

            while time.time() - start_time < timeout:
                poll_resp = await client.get(poll_url, headers=headers, timeout=30.0)
                poll_resp.raise_for_status()

                render_data = poll_resp.json()
                status = render_data.get("status")
                if status in ("completed", "failed"):
                    break

                import asyncio

                await asyncio.sleep(curr_interval)
                curr_interval = min(curr_interval * 1.5, 10.0)
            else:
                return GeneratedAsset(
                    id=str(item_id),
                    workspace_id=ws_id,
                    file_name=output_filename,
                    gcs_uri="",
                    mime_type="video/mp4",
                    created_at=datetime.now(timezone.utc),
                    status="failed",
                    error_message=f"Timeline rendering timed out after {timeout}s",
                    generation_metadata=GenerationMetadata(
                        source="creative_studio",
                        model="workbench_ffmpeg",
                        prompt=f"Rendered video timeline {timeline_id}",
                        raw={},
                    ),
                )

        asset_id = str(render_data.get("id") or render_data.get("asset_id", ""))
        gcs_uris = render_data.get("gcsUris", [])
        gcs_uri = gcs_uris[0] if gcs_uris else ""

        # Use CSAssetService to resolve hydrated asset details if available
        asset_service = CSAssetService(
            workspace_id=ws_id,
            user_auth_token=token,
            config=self._config,
        )
        ref = AssetRef(id=asset_id, asset_type="uploaded", workspace_id=ws_id)
        asset_info = await asset_service.get_asset(ref)

        if isinstance(asset_info, GeneratedAsset):
            return asset_info

        # Fallback to constructing terminal GeneratedAsset
        return GeneratedAsset(
            id=asset_id,
            workspace_id=ws_id,
            file_name=output_filename,
            gcs_uri=gcs_uri,
            mime_type="video/mp4",
            created_at=datetime.now(timezone.utc),
            status=render_data.get("status", "completed"),
            error_message=(
                render_data.get("errorMessage")
                if render_data.get("status") == "failed"
                else None
            ),
            generation_metadata=GenerationMetadata(
                source="creative_studio",
                model="workbench_ffmpeg",
                prompt=f"Rendered video timeline {timeline_id}",
                raw=render_data if isinstance(render_data, dict) else {},
            ),
        )

    async def delete_timeline(self, timeline_id: str) -> None:
        """Deletes the timeline document on Creative Studio backend."""
        token = self._get_user_auth_token()
        backend_url = (self._config.cs_backend_url or "http://backend:8080").rstrip("/")
        url = f"{backend_url}/api/workbench/timelines/{timeline_id}"
        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers)
            if resp.status_code == 404:
                return
            if resp.is_error:
                self._handle_error_response(resp)
