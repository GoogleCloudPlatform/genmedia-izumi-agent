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

"""Data classes for representing video timelines."""

import dataclasses
import typing
from enum import Enum

if typing.TYPE_CHECKING:
    from ..asset_service import AssetService
    from .assets import Asset


class TransitionType(Enum):
    FADE = "fade"
    NONE = "none"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"


@dataclasses.dataclass
class Trim:
    """Defines which part of a media asset to use for a clip."""

    offset_seconds: float = 0.0
    duration_seconds: float | None = None

    def to_firestore(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_firestore(cls, data: dict) -> "Trim":
        return cls(**data)


@dataclasses.dataclass
class Transition:
    type: TransitionType
    duration_seconds: float

    def to_firestore(self) -> dict:
        return {"type": self.type.value, "duration_seconds": self.duration_seconds}

    @classmethod
    def from_firestore(cls, data: dict) -> "Transition":
        return cls(
            type=TransitionType(data["type"]),
            duration_seconds=data["duration_seconds"],
        )


@dataclasses.dataclass
class VideoClip:
    asset: "Asset | None" = None
    trim: Trim | None = None
    volume: float = 1.0
    speed: float = 1.0
    first_frame_asset: "Asset | None" = None
    last_frame_asset: "Asset | None" = None
    placeholder: str | None = None

    def to_firestore(self) -> dict:
        return {
            "asset_id": self.asset.id if self.asset else None,
            "trim": self.trim.to_firestore() if self.trim else None,
            "volume": self.volume,
            "speed": self.speed,
            "first_frame_asset_id": (
                self.first_frame_asset.id if self.first_frame_asset else None
            ),
            "last_frame_asset_id": (
                self.last_frame_asset.id if self.last_frame_asset else None
            ),
            "placeholder": self.placeholder,
        }

    @classmethod
    def from_firestore(cls, data: dict, asset_service: "AssetService") -> "VideoClip":
        asset = None
        asset_id = data.get("asset_id")
        if asset_id:
            asset = asset_service.get_asset_by_id(asset_id)

        first_frame_asset = None
        first_frame_asset_id = data.get("first_frame_asset_id")
        if first_frame_asset_id:
            first_frame_asset = asset_service.get_asset_by_id(first_frame_asset_id)

        last_frame_asset = None
        last_frame_asset_id = data.get("last_frame_asset_id")
        if last_frame_asset_id:
            last_frame_asset = asset_service.get_asset_by_id(last_frame_asset_id)

        return cls(
            asset=asset,
            trim=Trim.from_firestore(data["trim"]) if data.get("trim") else None,
            volume=data.get("volume", 1.0),
            speed=data.get("speed", 1.0),
            first_frame_asset=first_frame_asset,
            last_frame_asset=last_frame_asset,
            placeholder=data.get("placeholder"),
        )


@dataclasses.dataclass
class AudioPlacement:
    video_clip_index: int
    offset_seconds: float = 0.0

    def to_firestore(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_firestore(cls, data: dict) -> "AudioPlacement":
        return cls(**data)


@dataclasses.dataclass
class AudioClip:
    start_at: AudioPlacement
    asset: "Asset | None" = None
    trim: Trim | None = None
    volume: float = 1.0
    speed: float = 1.0
    fade_in_duration_seconds: float = 0.0
    fade_out_duration_seconds: float = 0.0
    placeholder: str | None = None

    def to_firestore(self) -> dict:
        return {
            "asset_id": self.asset.id if self.asset else None,
            "start_at": self.start_at.to_firestore(),
            "trim": self.trim.to_firestore() if self.trim else None,
            "volume": self.volume,
            "speed": self.speed,
            "fade_in_duration_seconds": self.fade_in_duration_seconds,
            "fade_out_duration_seconds": self.fade_out_duration_seconds,
            "placeholder": self.placeholder,
        }

    @classmethod
    def from_firestore(cls, data: dict, asset_service: "AssetService") -> "AudioClip":
        trim = None
        if "trim" in data and data["trim"] is not None:
            trim = Trim.from_firestore(data["trim"])
        elif (
            "timing" in data and data["timing"] is not None
        ):  # For backward compatibility
            trim = Trim.from_firestore(data["timing"])
        elif "asset_offset_seconds" in data:  # For backward compatibility
            trim = Trim(offset_seconds=data["asset_offset_seconds"])
        asset = None
        asset_id = data.get("asset_id")
        if asset_id:
            asset = asset_service.get_asset_by_id(asset_id)

        return cls(
            asset=asset,
            start_at=AudioPlacement.from_firestore(data["start_at"]),
            trim=trim,
            volume=data.get("volume", 1.0),
            speed=data.get("speed", 1.0),
            fade_in_duration_seconds=data.get("fade_in_duration_seconds", 0.0),
            fade_out_duration_seconds=data.get("fade_out_duration_seconds", 0.0),
            placeholder=data.get("placeholder"),
        )


@dataclasses.dataclass
class VideoTimeline:
    title: str
    video_clips: list[VideoClip]
    transitions: list[Transition | None]
    audio_clips: list[AudioClip] = dataclasses.field(default_factory=list)
    transition_in: Transition | None = None
    transition_out: Transition | None = None

    def __post_init__(self) -> None:
        if len(self.video_clips) > 1:
            if len(self.transitions) != len(self.video_clips) - 1:
                raise ValueError(
                    "The number of transitions must be one less than the number of video clips."
                )
        elif self.transitions:
            raise ValueError(
                "There should be no transitions if there is one or zero video clips."
            )

    def to_firestore(self) -> dict:
        return {
            "title": self.title,
            "video_clips": [c.to_firestore() for c in self.video_clips],
            "transitions": [t.to_firestore() if t else None for t in self.transitions],
            "audio_clips": [a.to_firestore() for a in self.audio_clips],
            "transition_in": (
                self.transition_in.to_firestore() if self.transition_in else None
            ),
            "transition_out": (
                self.transition_out.to_firestore() if self.transition_out else None
            ),
        }

    @classmethod
    def from_firestore(
        cls, data: dict, asset_service: "AssetService"
    ) -> "VideoTimeline":
        return cls(
            title=data["title"],
            video_clips=[
                VideoClip.from_firestore(c, asset_service)
                for c in data.get("video_clips", [])
            ],
            transitions=[
                Transition.from_firestore(t) if t else None
                for t in data.get("transitions", [])
            ],
            audio_clips=[
                AudioClip.from_firestore(a, asset_service)
                for a in data.get("audio_clips", [])
            ],
            transition_in=(
                Transition.from_firestore(data["transition_in"])
                if data.get("transition_in")
                else None
            ),
            transition_out=(
                Transition.from_firestore(data["transition_out"])
                if data.get("transition_out")
                else None
            ),
        )
