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

"""Abstract service interfaces for the unified media-agent SDK.

These interfaces are the cross-backend contract described in
``unified_media_agent_interface_spec_v1.md §5``. Concrete
implementations live in per-backend submodules (``izumi/...``,
``creative_studio/...``) and are vended through ``AgentSession`` (see
``service_factory.py``).

The interfaces are added ALONGSIDE the existing concrete
``AssetService`` / ``CanvasService`` / ``MediaGenerationService`` /
``VideoStitchingService`` classes — they coexist rather than replace.
Concrete implementations of these interfaces will follow in later CLs
and incrementally retire the legacy concrete classes.

Contract notes that apply across the interfaces:
  * **Authorization is session-derived, not parameter-derived.** By-ID
    operations (``get_*``, ``update_*``, ``delete_*``,
    ``stitch_timeline``) take only the resource ID. The backend looks
    the resource up and authorizes it against the session identity;
    callers do not pass ``workspace_id`` / ``session_id`` to these.
    Scope inputs appear only at creation (``create_*``,
    ``upload_asset``).
  * **Terminal status for generations.** Every ``generate_*`` method
    and ``stitch_timeline`` MUST return a terminal ``GeneratedAsset``
    — ``status`` is ``"completed"`` or ``"failed"``, never
    ``"pending"``. Async backends are responsible for polling
    internally before returning.
  * **Error handling.** See ``errors.py`` for the typed exception
    taxonomy and the 5 routing rules.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union

from .types.common import (
    AssetRef,
    AssetType,
    Capability,
    GeneratedAsset,
    ScopedHtmlCanvas,
    ScopedVideoTimeline,
    UploadedAsset,
)
from .types.storyboard import Storyboard

# ---------------------------------------------------------------------------
# AssetService
# ---------------------------------------------------------------------------


class AssetServiceInterface(ABC):
    """Manages uploaded and generated files.

    Two distinct asset classes share this interface (see the
    uploaded-vs-generated separation in spec §3): callers distinguish
    by passing or receiving ``UploadedAsset`` vs ``GeneratedAsset``,
    and by the ``asset_type`` field on ``AssetRef``.
    """

    @abstractmethod
    async def upload_asset(
        self,
        workspace_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str,
        scope: str = "private",
        idempotency_key: Optional[str] = None,
    ) -> UploadedAsset:
        """Uploads a user-supplied file to the workspace.

        The owner identity is derived from the session — not passed in.
        ``scope`` is ``"private"`` (uploader-only within the workspace)
        or ``"system"`` (workspace-shared). Izumi Native ignores
        ``scope`` (single-user).

        ``idempotency_key`` (optional, recommended for retries): if the
        same key was used within the last 24h on the same workspace,
        the previously-created ``UploadedAsset`` is returned rather
        than creating a duplicate.
        """

    @abstractmethod
    async def get_asset(
        self, ref: AssetRef
    ) -> Optional[Union[UploadedAsset, GeneratedAsset]]:
        """Retrieves an asset by its composite reference.

        Returns ``None`` if the asset does not exist (backend 404 ->
        ``None``); see ``errors.py`` rule 1.
        """

    @abstractmethod
    async def search_assets(
        self,
        workspace_id: str,
        query: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Union[UploadedAsset, GeneratedAsset]]:
        """Lists assets in the workspace, optionally filtered by query
        string or asset type.

        Visibility is governed by the workspace scope and the session
        identity (plus each uploaded asset's ``scope``); there is no
        per-user filter parameter. Callers paginate by incrementing
        ``offset`` until a returned batch is shorter than ``limit``.
        """

    @abstractmethod
    async def download_asset_bytes(self, ref: AssetRef) -> bytes:
        """Downloads the raw byte stream of an asset."""

    @abstractmethod
    async def delete_asset(self, ref: AssetRef) -> None:
        """Deletes an asset and its underlying file."""


# ---------------------------------------------------------------------------
# HtmlCanvasService
# ---------------------------------------------------------------------------


class HtmlCanvasServiceInterface(ABC):
    """Manages HTML page layout templates (HTML canvases).

    Capability: ``Capability.HTML_CANVAS``. Backends that do not
    implement HTML canvas (e.g. Creative Studio) raise
    ``UnsupportedFeatureError`` from every method. Callers should check
    ``AgentSession.supports(Capability.HTML_CANVAS)`` before invoking.
    """

    @abstractmethod
    async def create_canvas(
        self,
        workspace_id: str,
        html_content: str,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        asset_references: Optional[list[AssetRef]] = None,
    ) -> ScopedHtmlCanvas:
        """Registers an HTML canvas bound to a workspace + optional
        session. Owner is derived from the session.
        """

    @abstractmethod
    async def get_canvas(self, canvas_id: str) -> Optional[ScopedHtmlCanvas]:
        """Returns the canvas, or ``None`` on 404."""

    @abstractmethod
    async def update_canvas(
        self,
        canvas_id: str,
        canvas_data: ScopedHtmlCanvas,
    ) -> None:
        """Replaces the canvas's content."""

    @abstractmethod
    async def delete_canvas(self, canvas_id: str) -> None:
        """Deletes the canvas."""


# ---------------------------------------------------------------------------
# VideoTimelineService
# ---------------------------------------------------------------------------


class VideoTimelineServiceInterface(ABC):
    """Manages NLE timelines and stitches them into final videos.

    Operates on ``ScopedVideoTimeline`` (the unified Pydantic model);
    distinct from the legacy ``timeline.VideoTimeline`` dataclass used
    by existing concrete services.
    """

    @abstractmethod
    async def create_timeline(
        self,
        workspace_id: str,
        session_id: Optional[str] = None,
        storyboard_id: Optional[str] = None,
        title: Optional[str] = None,
        timeline: Optional[ScopedVideoTimeline] = None,
    ) -> ScopedVideoTimeline:
        """Creates a timeline document. Owner is derived from the session."""

    @abstractmethod
    async def get_timeline(self, timeline_id: str) -> Optional[ScopedVideoTimeline]:
        """Returns the timeline, or ``None`` on 404."""

    @abstractmethod
    async def update_timeline(
        self,
        timeline_id: str,
        timeline: ScopedVideoTimeline,
    ) -> None:
        """Replaces the timeline's clips/transitions."""

    @abstractmethod
    async def stitch_timeline(
        self,
        timeline_id: str,
        output_filename: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Renders the timeline to a single video asset.

        MUST return a terminal asset (``status`` in {``"completed"``,
        ``"failed"``}). Async backends perform polling internally.
        """

    @abstractmethod
    async def delete_timeline(self, timeline_id: str) -> None:
        """Deletes the timeline document."""


# ---------------------------------------------------------------------------
# StoryboardService
# ---------------------------------------------------------------------------


class StoryboardServiceInterface(ABC):
    """Manages storyboard documents.

    M1 contract: the agent is the only writer; the frontend is
    read-only. ``save_storyboard`` is the explicit save service
    (decision 5 of the framing doc) that replaces the previous
    adapter-intercepted write pattern.

    The full M1 API is defined in ``storyboard_api_spec_m1.md``;
    scene-level CRUD (POST /scenes, PUT /scenes/{id}, etc.) is
    deferred to M2 and is not on this interface yet.
    """

    @abstractmethod
    async def save_storyboard(
        self,
        storyboard: Storyboard,
        idempotency_key: Optional[str] = None,
    ) -> Storyboard:
        """Persists the storyboard (create-or-replace).

        If ``storyboard.storyboard_id`` is ``None``, creates a new
        record. Otherwise, full-replaces the existing record.

        Returns the server-canonical ``Storyboard`` with assigned IDs
        and bumped ``updated_at``.

        On idempotent repeat (same ``idempotency_key`` within 24h),
        returns the previously-created storyboard rather than creating
        a duplicate. The agent typically uses ``session_id`` as the
        natural idempotency key.
        """

    @abstractmethod
    async def get_storyboard(self, storyboard_id: str) -> Optional[Storyboard]:
        """Returns the storyboard, or ``None`` on 404."""

    @abstractmethod
    async def list_storyboards(
        self,
        workspace_id: str,
        session_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Storyboard]:
        """Lists storyboards in the workspace (optionally scoped to a
        session)."""

    @abstractmethod
    async def delete_storyboard(self, storyboard_id: str) -> None:
        """Soft-deletes the storyboard."""


# ---------------------------------------------------------------------------
# MediaGenerationService
# ---------------------------------------------------------------------------


class MediaGenerationServiceInterface(ABC):
    """Model generations (text, image, video, speech, music).

    Contract: all media-producing methods (``generate_image``,
    ``generate_video``, ``generate_speech``, ``generate_music``, plus
    ``VideoTimelineService.stitch_timeline``) MUST return a TERMINAL
    ``GeneratedAsset`` — i.e. a ``GeneratedAsset`` whose ``status``
    is ``"completed"`` or ``"failed"``, never ``"pending"``. Backends
    that generate asynchronously are responsible for polling
    internally before returning. This keeps the abstraction honest
    across blocking (Izumi Native) and poll-based (Creative Studio)
    backends.

    ``generate_text`` is the one exception: it returns a bare ``str``,
    not a ``GeneratedAsset``, because text outputs are not persisted
    (they are consumed inline by callers for prompt rewriting,
    storyboard repair, parameter extraction, etc.). Asymmetric on
    purpose; the alternative (persisting every text generation as an
    asset) clutters the gallery with single-consumer artifacts that no
    one fetches later.
    """

    @abstractmethod
    async def generate_text(
        self,
        workspace_id: str,
        prompt: str,
        reference_assets: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Generates text and returns it inline.

        Unlike the other ``generate_*`` methods, this does NOT persist
        the result as an asset — callers consume the returned string
        directly. Use cases include prompt rewriting, storyboard
        repair, parameter extraction, and other intermediate-value
        text generations that no downstream consumer fetches as an
        asset.

        ``idempotency_key`` (optional): if supplied, the backend MAY
        cache the response for repeated calls within a short window
        to avoid duplicate generation costs on retry.
        """

    @abstractmethod
    async def generate_image(
        self,
        workspace_id: str,
        prompt: str,
        generation_model: str,
        aspect_ratio: str,
        resolution: str,
        file_name: str,
        reference_assets: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates a still image."""

    @abstractmethod
    async def generate_video(
        self,
        workspace_id: str,
        prompt: str,
        generation_model: str,
        aspect_ratio: str,
        duration_seconds: int,
        file_name: str,
        start_image: Optional[AssetRef] = None,
        end_image: Optional[AssetRef] = None,
        reference_videos: Optional[list[AssetRef]] = None,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates a video clip (text-to-video or image-to-video)."""

    @abstractmethod
    async def generate_speech(
        self,
        workspace_id: str,
        text: str,
        voice_name: str,
        language_code: str,
        file_name: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates TTS speech / voiceover."""

    @abstractmethod
    async def generate_music(
        self,
        workspace_id: str,
        prompt: str,
        model: str,
        duration_seconds: int,
        file_name: str,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedAsset:
        """Generates background music."""


# ---------------------------------------------------------------------------
# AgentSession (the request-scoped session that owns services)
# ---------------------------------------------------------------------------


class AgentSession(ABC):
    """A request-scoped session holding the caller's identity and per-
    request services.

    The ``ServiceFactory`` is a long-lived process singleton holding
    only context-free resources (config + connection pools).
    ``AgentSession`` is request-scoped and holds the identity (auth
    token, workspace) plus the services bound to that identity.

    Three rules every implementation MUST honor (see spec §6.2 and
    §6.3):
      1. **No process-global caching of context-dependent services.**
         The session may cache its own services internally (so callers
         can call ``get_*_service()`` multiple times cheaply), but those
         caches MUST NOT survive across requests.
      2. **Sub-services share THIS session's identity.** When the
         video timeline service needs the asset service to resolve
         clip refs, it MUST receive THIS session's asset service —
         never a globally cached one bound to a different identity.
      3. **Background jobs must capture the session explicitly.**
         ``contextvars`` propagation does not cross thread /
         ``BackgroundTasks`` boundaries. Workers dispatched from this
         session must capture the session (or at minimum the auth
         token + workspace) at submission time, not via ambient lookup.
    """

    @abstractmethod
    def get_asset_service(self) -> AssetServiceInterface: ...

    @abstractmethod
    def get_html_canvas_service(self) -> HtmlCanvasServiceInterface: ...

    @abstractmethod
    def get_video_timeline_service(self) -> VideoTimelineServiceInterface: ...

    @abstractmethod
    def get_storyboard_service(self) -> StoryboardServiceInterface: ...

    @abstractmethod
    def get_media_generation_service(self) -> MediaGenerationServiceInterface: ...

    @abstractmethod
    def supports(self, capability: Capability) -> bool:
        """Returns whether the backend supports the given capability.

        Callers wanting graceful degradation check this before
        invoking. Calls to an unsupported capability raise
        ``UnsupportedFeatureError`` rather than silently no-opping.

        Example::

            if session.supports(Capability.HTML_CANVAS):
                canvas = await session.get_html_canvas_service().create_canvas(...)
            else:
                # Fall back to a markdown summary, or skip.
                ...
        """


__all__ = [
    "AgentSession",
    "AssetServiceInterface",
    "HtmlCanvasServiceInterface",
    "MediaGenerationServiceInterface",
    "StoryboardServiceInterface",
    "VideoTimelineServiceInterface",
]
