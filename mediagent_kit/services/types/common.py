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

"""Unified domain models for the abstract service interfaces.

These models are the cross-backend data contracts described in
``unified_media_agent_interface_spec_v1.md §4``. They are NEW types added
alongside the existing ``Asset`` / ``Canvas`` / ``VideoTimeline`` types
in this package — they coexist rather than replace them. Concrete backend
implementations (``Izumi*Service``, ``CreativeStudio*Service``) translate
between these unified models and the backend-native representations.

Design notes:
  * Pydantic v2 throughout (existing ``Asset``/``Canvas`` use
    ``@dataclass``; the spec mandates Pydantic for the unified layer
    to get validation, JSON serialization, and FastAPI integration).
  * ``ConfigDict(extra="forbid")`` everywhere — strict schemas catch
    drift early. Backend-specific extension fields live in
    ``GenerationMetadata.raw``, not in arbitrary extra keys on every
    model.
  * IDs are always ``str`` in the unified models. Backends with
    integer PKs (e.g. Creative Studio) are responsible for casting on
    the wire and parsing back to ``str`` for these models. See spec
    §7.1.1.
  * ``Scoped*`` prefix is used where the unified concept exists
    alongside an older same-named concrete type to avoid import
    collisions (e.g. ``ScopedVideoTimeline`` vs the existing
    ``timeline.VideoTimeline``). The older types remain in use by
    existing concrete services; the ``Scoped*`` variants are what new
    interface-driven code consumes.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Asset references
# ---------------------------------------------------------------------------

AssetType = Literal["uploaded", "generated"]


class AssetRef(BaseModel):
    """Composite reference pointing to an asset across either backend.

    The ``(id, asset_type)`` pair is required because uploaded and
    generated assets do not share an ID space on Creative Studio
    (separate tables, each with its own auto-incrementing PK). On Izumi
    the IDs are globally unique Firestore string keys, but
    ``asset_type`` is still needed to route to the correct collection.

    ``workspace_id`` is included for the common case where the caller
    already has it; adapters MAY ignore it and resolve against the
    session's workspace instead. The session is the authoritative
    source of identity (see spec §7.4 — "Authorization is
    session-derived, not parameter-derived").
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    asset_type: AssetType
    workspace_id: str


# ---------------------------------------------------------------------------
# Uploaded assets (user-supplied files)
# ---------------------------------------------------------------------------


class UploadedAsset(BaseModel):
    """A file uploaded by a user (logo, reference image, brand-guidelines PDF, etc.).

    Distinct from ``GeneratedAsset`` to honor decision 1 in the unified
    spec: separating user-supplied content from AI-generated content
    enables different lifecycle / RBAC / quota policies on the backend
    without forcing the agent to know which is which.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    user_id: str  # uploader; backend-filled provenance, never a caller input
    scope: Literal["private", "system"] = "private"
    file_name: str
    gcs_uri: str
    mime_type: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Generated assets (model outputs) + provenance
# ---------------------------------------------------------------------------

AssetStatus = Literal["completed", "failed"]
GenerationSource = Literal["creative_studio", "izumi"]


class GenerationMetadata(BaseModel):
    """Generation provenance for a ``GeneratedAsset``.

    Hybrid model — lossless + partially unified:
      * The typed fields below are the common subset both backends
        populate, giving consumers a stable typed view.
      * ``raw`` carries each backend's full native record verbatim, so
        no information is lost regardless of which backend produced
        the asset.
          - Creative Studio: the ``media_items`` row
            (``original_prompt``, ``rewritten_prompt``, ``critique``,
            ``grounding_metadata``, ``audio_analysis``, ...).
          - Izumi Native: the ``AssetVersion.*_generate_config``
            object (``ImageGenerateConfig``, ``VideoGenerateConfig``,
            etc.).

    Common consumers read the typed fields; power users read ``raw``
    for full fidelity. ``source`` tells consumers how to interpret
    ``raw``.
    """

    model_config = ConfigDict(extra="forbid")

    source: GenerationSource
    model: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    references: list[AssetRef] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class GeneratedAsset(BaseModel):
    """A file produced by an AI model (Imagen image, Veo video, TTS, Lyria music).

    Terminal-only by contract: every ``generate_*`` interface method
    and ``stitch_timeline`` MUST return a ``GeneratedAsset`` with
    ``status`` in {``"completed"``, ``"failed"``}, never ``"pending"``.
    Async backends are responsible for polling internally before
    returning. See spec §5 ``MediaGenerationServiceInterface``
    contract note.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    file_name: str
    gcs_uri: str
    mime_type: str
    created_at: datetime
    status: AssetStatus
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    generation_metadata: Optional[GenerationMetadata] = None


# ---------------------------------------------------------------------------
# Video timeline (scoped variant)
# ---------------------------------------------------------------------------
#
# NOTE: there is an existing ``timeline.VideoTimeline`` dataclass in this
# package used by the legacy concrete services. The Pydantic models below
# are the unified-interface variants; the prefix is omitted on inner clip
# models (``TimelineVideoClip`` / ``TimelineAudioClip``) because they have
# no namespace collision, and kept on ``ScopedVideoTimeline`` because
# ``VideoTimeline`` does collide. When the legacy dataclass types are
# eventually retired, we can drop the ``Scoped`` prefix.


class TransitionType(str, Enum):
    FADE = "fade"
    NONE = "none"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"


class Trim(BaseModel):
    """Defines which slice of a media asset to use in a clip."""

    model_config = ConfigDict(extra="forbid")

    offset_seconds: float = 0.0
    duration_seconds: Optional[float] = None


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TransitionType
    duration_seconds: float


class TimelineVideoClip(BaseModel):
    """A single video clip in a scoped timeline.

    ``asset_ref`` is the rendered clip itself. ``first_frame_asset_ref``
    / ``last_frame_asset_ref`` are optional stills used by some
    rendering pipelines (e.g. Veo image-to-video). ``placeholder`` is a
    descriptive string used when a clip is being assembled but its
    asset is not yet generated.
    """

    model_config = ConfigDict(extra="forbid")

    asset_ref: Optional[AssetRef] = None
    trim: Optional[Trim] = None
    volume: float = 1.0
    speed: float = 1.0
    first_frame_asset_ref: Optional[AssetRef] = None
    last_frame_asset_ref: Optional[AssetRef] = None
    placeholder: Optional[str] = None


class AudioPlacement(BaseModel):
    """Anchors an audio clip relative to a specific video clip in the
    same timeline.

    Using a relative anchor (``video_clip_index`` + ``offset_seconds``)
    instead of an absolute offset makes timelines stable across video-
    clip duration changes — re-rendering a longer scene 2 does not
    require re-computing every downstream audio start time.
    """

    model_config = ConfigDict(extra="forbid")

    video_clip_index: int
    offset_seconds: float = 0.0


class TimelineAudioClip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: AudioPlacement
    asset_ref: Optional[AssetRef] = None
    trim: Optional[Trim] = None
    volume: float = 1.0
    speed: float = 1.0
    fade_in_duration_seconds: float = 0.0
    fade_out_duration_seconds: float = 0.0
    placeholder: Optional[str] = None


class ScopedVideoTimeline(BaseModel):
    """A track-based NLE timeline scoped to a workspace + optional session.

    Renamed from ``VideoTimeline`` to avoid collision with the existing
    ``timeline.VideoTimeline`` dataclass used by legacy concrete
    services. Once the legacy type is retired, the ``Scoped`` prefix
    can be dropped.

    Convention: ``transitions[i]`` is the transition BETWEEN
    ``video_clips[i]`` and ``video_clips[i + 1]``. Length:
    ``len(video_clips) - 1``. ``transition_in`` / ``transition_out``
    apply at the timeline boundaries.
    """

    model_config = ConfigDict(extra="forbid")

    timeline_id: Optional[str] = None
    workspace_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    video_clips: list[TimelineVideoClip]
    transitions: list[Optional[Transition]] = Field(default_factory=list)
    audio_clips: list[TimelineAudioClip] = Field(default_factory=list)
    transition_in: Optional[Transition] = None
    transition_out: Optional[Transition] = None


# ---------------------------------------------------------------------------
# HTML canvas (scoped variant)
# ---------------------------------------------------------------------------


class ScopedHtmlCanvas(BaseModel):
    """An HTML page layout scoped to a workspace + optional session.

    Renamed from ``HtmlCanvas`` to keep the namespace clear alongside
    the existing ``canvases.Canvas`` / ``canvases.Html`` legacy types.
    Once the legacy types are retired, the ``Scoped`` prefix can be
    dropped.
    """

    model_config = ConfigDict(extra="forbid")

    canvas_id: Optional[str] = None
    workspace_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    html_content: str
    asset_references: list[AssetRef] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Capabilities (for AgentSession.supports())
# ---------------------------------------------------------------------------


class Capability(str, Enum):
    """Named capabilities a backend may or may not support.

    Used by ``AgentSession.supports(capability)`` to enable graceful
    degradation. Calls to an unsupported capability raise
    ``UnsupportedFeatureError`` rather than silently no-opping (see
    spec §8.3).
    """

    HTML_CANVAS = "html_canvas"
    WORKSPACE_SHARING = "workspace_sharing"
    ASSET_VERSIONING = "asset_versioning"


__all__ = [
    "AssetRef",
    "AssetStatus",
    "AssetType",
    "AudioPlacement",
    "Capability",
    "GeneratedAsset",
    "GenerationMetadata",
    "GenerationSource",
    "ScopedHtmlCanvas",
    "ScopedVideoTimeline",
    "TimelineAudioClip",
    "TimelineVideoClip",
    "Transition",
    "TransitionType",
    "Trim",
    "UploadedAsset",
]
