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

"""This package contains the data types used by the services."""

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
from .timeline import (
    AudioClip,
    AudioPlacement,
    Transition,
    TransitionType,
    Trim,
    VideoClip,
    VideoTimeline,
)

__all__ = [
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
]
