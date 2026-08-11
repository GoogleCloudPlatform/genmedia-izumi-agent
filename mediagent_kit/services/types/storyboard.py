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

"""Wire-format DTOs for the Storyboard resource.

These models are the cross-team contract described in
``storyboard_api_spec_m1.md``. They mirror the Izumi-internal
``Storyboard`` Pydantic model (``demos/backend/ads_x/utils/storyboard/
storyboard_model.py``) with intentional differences called out below.

Why a separate wire model rather than reusing the agent's internal one?
  * The internal model uses ``extra="allow"`` to accommodate LLM
    output drift. The wire format uses ``extra="forbid"`` to catch
    schema drift across teams loudly rather than silently.
  * The internal model uses positional ``scene_indices`` in
    ``VoiceoverGroup``. The wire format uses stable ``scene_ids`` so
    the M2 reorder feature does not silently corrupt voiceover-to-
    scene alignment. (See spec §2.3 and the Izumi commitment in
    ``storyboard_collaboration_framing.md``.)
  * The wire format uses typed ``AssetRef`` for asset references; the
    internal model uses raw ID strings.

Translation between the two lives in the SDK adapter layer, not in
this module.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import AssetRef

# ---------------------------------------------------------------------------
# Inner building blocks
# ---------------------------------------------------------------------------


class SpeechPrompt(BaseModel):
    """Prompt for TTS voiceover generation."""

    model_config = ConfigDict(extra="forbid")

    text: str
    gender: Literal["female", "male"]
    description: str
    style: str = "Natural"


class MusicPrompt(BaseModel):
    """Prompt for background music generation."""

    model_config = ConfigDict(extra="forbid")

    description: str


class CinematographyHints(BaseModel):
    """Visual / camera direction for an image or video generation.

    Drives prompt enrichment in the agent's generation tools. Preserving
    these across storyboard round-trips is non-negotiable: regenerating
    a scene without them produces a visually different result and breaks
    continuity.
    """

    model_config = ConfigDict(extra="forbid")

    camera: Optional[str] = None
    lens: Optional[str] = None
    lighting: Optional[str] = None
    mood: list[str] = Field(default_factory=list)
    color_anchors: list[str] = Field(default_factory=list)
    velocity_hint: Optional[str] = None


class AudioHints(BaseModel):
    """Ambient / SFX / dialogue tone direction for a scene."""

    model_config = ConfigDict(extra="forbid")

    dialogue_hint: Optional[str] = None
    dialogue_tone: Optional[str] = None
    ambient_description: Optional[str] = None
    sfx_description: Optional[str] = None


TransitionStyle = Literal["cut", "crossfade", "fade", "wipe_left", "wipe_right"]


class TransitionHints(BaseModel):
    """How a scene transitions IN from the previous scene."""

    model_config = ConfigDict(extra="forbid")

    type: TransitionStyle = "cut"
    duration_seconds: float = 0.0


class ImagePrompt(BaseModel):
    """Prompt to generate a still image (typically a scene's first frame)."""

    model_config = ConfigDict(extra="forbid")

    description: str
    assets: list[AssetRef] = Field(
        default_factory=list,
        description="Reference assets (e.g. brand logo, product shot) to incorporate.",
    )
    cinematography: CinematographyHints = Field(default_factory=CinematographyHints)
    generated_asset: Optional[AssetRef] = Field(
        default=None,
        description="The generated image asset (populated after generation).",
    )


class VideoPrompt(BaseModel):
    """Prompt to generate a video clip from a first-frame image."""

    model_config = ConfigDict(extra="forbid")

    description: str
    duration_seconds: float
    assets: list[AssetRef] = Field(default_factory=list)
    cinematography: CinematographyHints = Field(default_factory=CinematographyHints)
    generated_asset: Optional[AssetRef] = Field(
        default=None,
        description="The generated video asset (populated after generation).",
    )


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class Scene(BaseModel):
    """A single scene in the storyboard.

    ``scene_id`` is mandatory and stable for the lifetime of the
    storyboard. Reordering scenes does NOT change any ``scene_id``;
    only ``order`` changes. This is the M2-enabling invariant — without
    it, ``VoiceoverGroup.scene_ids`` would corrupt on reorder.

    ``order`` is the 0-indexed position. We store it explicitly (rather
    than relying on array position) so that JSON-patch-style edits in
    M2 produce unambiguous results when scenes are added, removed, or
    reordered.
    """

    model_config = ConfigDict(extra="forbid")

    scene_id: str  # stable UUID, immutable across the storyboard's lifetime
    order: int = Field(ge=0)
    topic: str
    duration_seconds: float = Field(default=4.0, gt=0.0)
    first_frame_prompt: ImagePrompt
    video_prompt: VideoPrompt
    voiceover_prompt: SpeechPrompt
    transition_hints: TransitionHints = Field(default_factory=TransitionHints)
    audio_hints: AudioHints = Field(default_factory=AudioHints)
    narrative_action: Optional[str] = None
    establishment_shot: Optional[str] = None


# ---------------------------------------------------------------------------
# VoiceoverGroup
# ---------------------------------------------------------------------------

NarrativeBlock = Literal["START", "BODY", "CTA"]


class VoiceoverGroup(BaseModel):
    """A sequence of scenes sharing one voiceover asset.

    References scenes by stable ``scene_ids``, NOT positional indices.
    This is the M2-enabling change relative to the current Izumi
    internal model.

    Business rules (enforced by ``StoryboardService``, not by Pydantic):
      * Every entry in ``scene_ids`` must reference an existing
        ``Scene.scene_id`` in the same storyboard.
      * No two ``VoiceoverGroup``s in the same storyboard may have
        overlapping ``scene_ids`` (each scene belongs to at most one
        group).
    """

    model_config = ConfigDict(extra="forbid")

    group_id: str
    scene_ids: list[str] = Field(min_length=1)
    total_duration: float = Field(gt=0.0)
    original_scripts: list[str]
    rewritten_script: str = ""
    audio_asset: Optional[AssetRef] = None
    narrative_block: NarrativeBlock


# ---------------------------------------------------------------------------
# Top-level Storyboard
# ---------------------------------------------------------------------------


class Storyboard(BaseModel):
    """The full storyboard document.

    Server-assigned fields (``storyboard_id``, ``created_at``,
    ``updated_at``) are ``None`` on initial POST and populated on the
    create response. Agents track ``storyboard_id`` after creation to
    issue subsequent updates as PUTs rather than POSTs (matches the
    pattern agreed for ``VideoTimeline`` integration).

    M1 invariant: ``scenes`` is non-empty. The agent always produces
    at least one scene.
    """

    model_config = ConfigDict(extra="forbid")

    # Server-assigned (None on initial POST)
    storyboard_id: Optional[str] = None
    workspace_id: str
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Agent-authored campaign metadata
    template_name: str = "Custom"
    campaign_title: Optional[str] = None
    campaign_theme: Optional[str] = None
    campaign_tone: Optional[str] = None
    concept_description: Optional[str] = None
    key_message: Optional[str] = None
    global_visual_style: Optional[str] = None
    global_setting: Optional[str] = None
    target_audience_profile: Optional[str] = None

    # Background music
    background_music_prompt: MusicPrompt
    background_music_asset: Optional[AssetRef] = None

    # Scenes + voiceover groups
    scenes: list[Scene] = Field(min_length=1)
    voiceover_groups: list[VoiceoverGroup] = Field(default_factory=list)


__all__ = [
    "AudioHints",
    "CinematographyHints",
    "ImagePrompt",
    "MusicPrompt",
    "NarrativeBlock",
    "Scene",
    "SpeechPrompt",
    "Storyboard",
    "TransitionHints",
    "TransitionStyle",
    "VideoPrompt",
    "VoiceoverGroup",
]
