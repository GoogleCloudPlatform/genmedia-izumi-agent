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

"""Storyboard object for ads_x agent."""

from typing import Any, Literal

import pydantic

from . import common_utils


class SpeechPrompt(pydantic.BaseModel):
    """Prompt to generate a speech."""

    text: str = pydantic.Field(description="Text to be spoken.")
    gender: Literal["female", "male"] = pydantic.Field(
        description="Gender of the voice (one of 'female' or 'male').",
    )
    description: str = pydantic.Field(
        description="Detailed description of the style of speaking."
    )


class MusicPrompt(pydantic.BaseModel):
    """Prompt to generate music."""

    description: str = pydantic.Field(
        description=(
            "Detailed description of the music to generate,"
            " describing the mood, genre, and instruments."
        )
    )


class ImagePrompt(pydantic.BaseModel):
    """Prompt to generate an image."""

    description: str = pydantic.Field(
        description=(
            "Detailed description of the image to generate. "
            "Do NOT include literal filenames (e.g., .png) in this field. "
            "Use natural descriptions of the objects instead."
        )
    )
    assets: list[str] = pydantic.Field(
        default_factory=list,
        description="List of asset filenames to show in the image.",
    )


class VideoPrompt(pydantic.BaseModel):
    """Prompt to generate a video."""

    description: str = pydantic.Field(
        description=(
            "Detailed description of the video to generate given the first frame. "
            "Do NOT include literal filenames (e.g., .png) in this field. "
            "Use natural descriptions of the actions instead."
        )
    )
    assets: list[str] = pydantic.Field(
        default_factory=list,
        description="List of asset filenames to show in the video.",
    )
    duration_seconds: Literal["4", "6", "8"] = pydantic.Field(
        description="Desired video length in seconds (one of '4', '6', or '8')"
    )


class Scene(pydantic.BaseModel):
    """A single scene in the storyboard."""

    topic: str = pydantic.Field(
        description="A short, descriptive topic for this scene."
    )
    first_frame_prompt: ImagePrompt = pydantic.Field(
        description="Prompt to generate the first frame for this scene.",
    )
    video_prompt: VideoPrompt = pydantic.Field(
        description="Prompt to generate the scene video from the first frame.",
    )
    first_frame_generation_history: list[dict[str, Any]] = pydantic.Field(
        default_factory=list,
        description="Log of all generation attempts for this scene's first frame.",
    )


class Storyboard(pydantic.BaseModel):
    """A structured representation of a MediaGen video storyboard."""

    voiceover_prompt: SpeechPrompt = pydantic.Field(
        description="Single unified voiceover for the entire campaign."
    )
    background_music_prompt: MusicPrompt = pydantic.Field(
        description="Prompt to generate background music for the video."
    )
    scenes: list[Scene] = pydantic.Field(
        default_factory=list,
        description="The sequence of scenes comprising the final video.",
    )
    voiceover_generation_history: list[dict[str, Any]] = pydantic.Field(
        default_factory=list,
        description="Log of all generation attempts for the unified voiceover.",
    )
    background_music_generation_history: list[dict[str, Any]] = pydantic.Field(
        default_factory=list,
        description="Log of all generation attempts for the background music.",
    )
    final_video_asset_id: str | None = pydantic.Field(
        default=None, description="The asset ID of the final stitched video."
    )
    final_video_asset_version: int | None = pydantic.Field(
        default=None, description="The asset version of the final stitched video."
    )


DESCRIPTION = common_utils.describe_pydantic_model(Storyboard)
