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

"""Data types used by mediagent_kit services.

Two parallel layers coexist:

  * **Legacy dataclass-based types** (``Asset``, ``Canvas``,
    ``VideoTimeline``, ``Job``, etc.) — used by the existing concrete
    service classes (``AssetService``, ``CanvasService``,
    ``VideoStitchingService``, ...). Exported here from
    ``assets``, ``canvases``, ``jobs``, ``timeline``.

  * **Unified Pydantic models** (``UploadedAsset``, ``GeneratedAsset``,
    ``ScopedVideoTimeline``, ``ScopedHtmlCanvas``, ``Storyboard``,
    ``AssetRef``, ``GenerationMetadata``, ``Capability``) — used by
    the new abstract interfaces in ``mediagent_kit.services.interfaces``
    and their per-backend concrete implementations. Exported here
    from ``common`` and ``storyboard``.

The ``Scoped`` prefix on ``ScopedVideoTimeline`` / ``ScopedHtmlCanvas``
distinguishes the unified Pydantic models from the legacy
``VideoTimeline`` / ``Canvas`` types and avoids re-export collisions.
Inner unified clip types use a ``Timeline`` prefix
(``TimelineVideoClip``, ``TimelineAudioClip``) for the same reason.
Other unified inner types (``AssetRef``, ``GenerationMetadata``,
``AudioPlacement``, ``Trim``, ``Transition``, ``TransitionType``,
``UploadedAsset``, ``GeneratedAsset``, ...) reuse the legacy names
where the legacy module did not export them — see the per-symbol
notes below. Once the legacy concrete services are retired, the
``Scoped`` / ``Timeline`` prefixes can be dropped.
"""

# --- Legacy (dataclass-based) ---
from .assets import (
    Asset,
    AssetBlob,
    AssetVersion,
    ImageGenerateConfig,
    MusicGenerateConfig,
    SpeechGenerateConfig,
    TextGenerateConfig,
    VideoGenerateConfig,
)
from .canvases import Canvas, Html
from .jobs import Job, JobStatus, JobType

# Legacy timeline types — names UNCHANGED to preserve every existing
# caller. ``AudioPlacement``, ``Transition``, ``TransitionType``,
# ``Trim``, ``VideoClip``, ``AudioClip``, ``VideoTimeline`` continue
# to resolve to the dataclass variants (used by ads_x,
# ads_codirector, elements_to_video). The unified Pydantic variants
# share these conceptual names but live under DIFFERENT exported
# names (``TimelineAudioClip``, ``TimelineVideoClip``,
# ``ScopedVideoTimeline``) to avoid silent breakage. Inner shared
# types (``Trim``, ``Transition``, ``AudioPlacement``,
# ``TransitionType``) are intentionally NOT re-exported from
# ``common`` here; consumers of the Pydantic variants import them
# directly from ``mediagent_kit.services.types.common``.
from .timeline import (
    AudioClip,
    AudioPlacement,
    Transition,
    TransitionType,
    Trim,
    VideoClip,
    VideoTimeline,
)

# --- Unified (Pydantic) ---
#
# Note: ``AudioPlacement``, ``Transition``, ``TransitionType``,
# ``Trim`` are intentionally NOT re-exported here from ``common`` —
# they collide by name with the legacy dataclass variants above.
# Callers using the Pydantic variants import them explicitly:
#
#   from mediagent_kit.services.types.common import (
#       AudioPlacement, Transition, TransitionType, Trim,
#   )
#
# Once the legacy dataclass variants are retired this asymmetry
# disappears and we can re-export the Pydantic variants here.
from .common import (
    AssetRef,
    AssetStatus,
    AssetType,
    Capability,
    GeneratedAsset,
    GenerationMetadata,
    GenerationSource,
    ScopedHtmlCanvas,
    ScopedVideoTimeline,
    TimelineAudioClip,
    TimelineVideoClip,
    UploadedAsset,
)
from .storyboard import (
    AudioHints,
    CinematographyHints,
    ImagePrompt,
    MusicPrompt,
    NarrativeBlock,
    Scene,
    SpeechPrompt,
    Storyboard,
    TransitionHints,
    TransitionStyle,
    VideoPrompt,
    VoiceoverGroup,
)

__all__ = [
    # Legacy (dataclass-based) — names unchanged for backward compatibility
    "Asset",
    "AssetBlob",
    "AssetVersion",
    "AudioClip",
    "AudioPlacement",
    "Canvas",
    "Html",
    "ImageGenerateConfig",
    "Job",
    "JobStatus",
    "JobType",
    "MusicGenerateConfig",
    "SpeechGenerateConfig",
    "TextGenerateConfig",
    "Transition",
    "TransitionType",
    "Trim",
    "VideoClip",
    "VideoGenerateConfig",
    "VideoTimeline",
    # Unified — common (Pydantic). Inner types Trim/Transition/
    # TransitionType/AudioPlacement intentionally not re-exported
    # here to avoid name collision with the legacy variants above;
    # import them via ``mediagent_kit.services.types.common``.
    "AssetRef",
    "AssetStatus",
    "AssetType",
    "Capability",
    "GeneratedAsset",
    "GenerationMetadata",
    "GenerationSource",
    "ScopedHtmlCanvas",
    "ScopedVideoTimeline",
    "TimelineAudioClip",
    "TimelineVideoClip",
    "UploadedAsset",
    # Unified — storyboard
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
