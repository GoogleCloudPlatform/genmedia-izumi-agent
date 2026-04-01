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

import pydantic
from typing import List
from ..common import common_utils
from .templates_model import CinematographyHints, AudioHints, TransitionHints


class SpeechPrompt(pydantic.BaseModel):
    """Prompt to generate a speech."""
    model_config = pydantic.ConfigDict(extra='allow')

    text: str = pydantic.Field(description="Text to be spoken.")
    gender: str = pydantic.Field(
        description="Gender of the voice (one of 'female' or 'male').",
    )
    description: str = pydantic.Field(
        description="Detailed description of the style of speaking."
    )
    style: str = pydantic.Field(
        default="Natural",
        description="A specific vibe or tone (e.g. 'Energetic', 'Empathetic')."
    )


class MusicPrompt(pydantic.BaseModel):
    """Prompt to generate music."""
    model_config = pydantic.ConfigDict(extra='allow')

    description: str = pydantic.Field(
        description=(
            "Detailed description of the music to generate,"
            " describing the mood, genre, and instruments."
        )
    )


class ImagePrompt(pydantic.BaseModel):
    """Prompt to generate an image."""
    model_config = pydantic.ConfigDict(extra='allow')

    description: str = pydantic.Field(
        description=(
            "Detailed description of the image to generate,"
            " incorporating the featured asset(s)."
        )
    )
    assets: list[str] = pydantic.Field(
        default_factory=list,
        description="List of asset IDs to show in the image.",
    )
    # Added fields to support template richness
    cinematography: CinematographyHints = pydantic.Field(
        default_factory=CinematographyHints,
        description="Technical visual details for the image generation",
    )


class VideoPrompt(pydantic.BaseModel):
    """Prompt to generate a video."""
    model_config = pydantic.ConfigDict(extra='allow')

    description: str = pydantic.Field(
        description=(
            "Detailed description of the video to generate given the first frame,"
            " depicting the action and referencing the featured assets."
        )
    )
    duration_seconds: float = pydantic.Field(
        description="The exact duration of the final video cut in seconds. Can be a decimal value (e.g., 2.5, 3.5) to match fast-paced template timings."
    )
    assets: list[str] = pydantic.Field(
        default_factory=list,
        description="List of asset IDs used in this video generation.",
    )
    # Added fields to support template richness
    cinematography: CinematographyHints = pydantic.Field(
        default_factory=CinematographyHints,
        description="Technical visual details for the video generation",
    )


class Scene(pydantic.BaseModel):
    """A single scene in the storyboard."""
    model_config = pydantic.ConfigDict(extra='allow')

    topic: str = pydantic.Field(
        description="A short, descriptive topic for this scene."
    )
    first_frame_prompt: ImagePrompt = pydantic.Field(
        description="Prompt to generate the first frame for this scene.",
    )
    video_prompt: VideoPrompt = pydantic.Field(
        description="Prompt to generate the scene video from the first frame.",
    )
    voiceover_prompt: SpeechPrompt = pydantic.Field(
        description="Prompt to generate the voiceover for this scene."
    )

    # New fields from Template design
    transition_hints: TransitionHints = pydantic.Field(
        default_factory=TransitionHints,
        description="How to transition into this scene.",
    )
    audio_hints: AudioHints = pydantic.Field(
        default_factory=AudioHints, description="Ambient sound and SFX details."
    )
    duration_seconds: float = pydantic.Field(
        default=4, description="Target duration for this scene in seconds. Can be a decimal value (e.g., 2.5, 3.5) to match fast-paced template timings."
    )
    narrative_action: str | None = pydantic.Field(
        default=None,
        description="Specific character or object action for this scene."
    )
    establishment_shot: str | None = pydantic.Field(
        default=None,
        description="A description of the opening context for the scene (e.g. 'EXT. PARK - DAY')."
    )


class VoiceoverGroup(pydantic.BaseModel):
    """Represents a sequence of scenes sharing a single voiceover asset."""
    model_config = pydantic.ConfigDict(extra='allow')
    
    group_id: str = pydantic.Field(description="Unique ID for this group.")
    scene_indices: List[int] = pydantic.Field(description="Indices of the scenes included in this group.")
    total_duration: float = pydantic.Field(description="Total duration of all scenes in this group.")
    original_scripts: List[str] = pydantic.Field(description="Original script snippets for each scene.")
    rewritten_script: str = pydantic.Field(default="", description="The LLM-rewritten, flowing script.")
    audio_asset_id: str = pydantic.Field(default="", description="ID of the generated audio asset.")
    narrative_block: str = pydantic.Field(description="The narrative block this group belongs to (START, BODY, CTA).")


class Storyboard(pydantic.BaseModel):
    """A structured representation of a MediaGen video storyboard."""
    model_config = pydantic.ConfigDict(extra='allow')

    template_name: str = pydantic.Field(
        default="Custom", description="Name of the template used, if any."
    )
    background_music_prompt: MusicPrompt = pydantic.Field(
        default_factory=lambda: MusicPrompt(description="A cinematic and inspiring background score for an advertising campaign."),
        description="Prompt to generate background music for the video."
    )
    scenes: list[Scene] = pydantic.Field(
        min_length=1,
        description="The sequence of scenes comprising the final video. This array MUST NEVER BE EMPTY.",
    )
    voiceover_groups: list[VoiceoverGroup] = pydantic.Field(
        default_factory=list,
        description="Grouped voiceover segments for better prosody and flow.",
    )

    # Global Campaign Metadata (Rich Brief)
    campaign_title: str | None = None
    campaign_theme: str | None = None
    campaign_tone: str | None = None
    concept_description: str | None = None
    key_message: str | None = None
    global_visual_style: str | None = None
    global_setting: str | None = None
    target_audience_profile: str | None = None


DESCRIPTION = common_utils.describe_pydantic_model(Storyboard)
