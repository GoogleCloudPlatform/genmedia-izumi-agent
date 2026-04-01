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

"""
Pydantic models for the video generation agent's storyboard plan.

These models are used to define the structure and validate the JSON output
from the language model that generates the storyboard.

Note: Some of these models (e.g., AudioPlacement, Transition) are intentionally
redefined here, even though similar structures exist in `services.types`.
This is because the agent-facing models are Pydantic-based and tailored for
LLM output validation, while the service-facing models are dataclasses
designed for internal business logic and database serialization. This separation
of concerns prevents coupling the agent's data structures to the internal
service implementation.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Transition(BaseModel):
    type: Literal["fade", "none"]
    duration_seconds: float


class VideoClipPlan(BaseModel):
    clip_number: int
    description: str
    duration_seconds: float = Field(..., ge=2, le=8)
    image_prompt: str
    video_prompt: str
    narration: str | None = None
    elements: list[str] = Field(default_factory=list)
    image_file_name: str
    video_file_name: str
    speech_file_name: str | None = None


class ConsistentElement(BaseModel):
    id: str
    name: str
    description: str
    image_prompt: str | None = None
    file_name: str
    asset_id: str | None = None
    is_user_provided: bool = False


class AudioPlacement(BaseModel):
    video_clip_index: int
    offset_seconds: float = 0.0


class BackgroundMusicClipPlan(BaseModel):
    prompt: str
    file_name: str
    start_at: AudioPlacement
    duration_seconds: float = Field(le=30.0)
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0


class StoryboardPlan(BaseModel):
    title: str
    aspect_ratio: Literal["16:9", "9:16"]
    voice_gender: Literal["Male", "Female"]
    voice_name: Literal[
        "Achernar",
        "Aoede",
        "Autonoe",
        "Callirrhoe",
        "Despina",
        "Erinome",
        "Gacrux",
        "Kore",
        "Laomedeia",
        "Leda",
        "Pulcherrima",
        "Sulafat",
        "Vindemiatrix",
        "Zephyr",
        "Achird",
        "Algenib",
        "Algieba",
        "Alnilam",
        "Charon",
        "Enceladus",
        "Fenrir",
        "Iapetus",
        "Orus",
        "Puck",
        "Rasalgethi",
        "Sadachbia",
        "Sadaltager",
        "Schedar",
        "Umbriel",
        "Zubenelgenubi",
    ]
    video_clips: list[VideoClipPlan]
    transitions: list[Transition] = Field(default_factory=list)
    consistent_elements: list[ConsistentElement] = Field(default_factory=list)
    transition_in: Transition | None = None
    transition_out: Transition | None = None
    background_music_clips: list[BackgroundMusicClipPlan] = Field(default_factory=list)

    def get_clip_start_times(self) -> list[float]:
        """Calculates the start time of each video clip."""
        start_times = [0.0]
        if not self.video_clips:
            return []

        current_time = 0.0
        for i in range(len(self.video_clips) - 1):
            current_time += self.video_clips[i].duration_seconds
            if i < len(self.transitions):
                current_time -= self.transitions[i].duration_seconds
            start_times.append(current_time)
        return start_times

    def calculate_total_duration(self) -> float:
        """Calculates the total duration of the video timeline."""
        if not self.video_clips:
            return 0.0

        start_times = self.get_clip_start_times()
        last_clip_duration = self.video_clips[-1].duration_seconds
        return start_times[-1] + last_clip_duration
