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

"""Data classes for representing canvases."""

import dataclasses
import typing

if typing.TYPE_CHECKING:
    from ..asset_service import AssetService
    from .timeline import VideoTimeline


@dataclasses.dataclass
class Html:
    content: str
    asset_ids: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Canvas:
    id: str
    title: str
    user_id: str
    video_timeline: "VideoTimeline | None" = None
    html: Html | None = None

    def __post_init__(self) -> None:
        if self.video_timeline is None and self.html is None:
            raise ValueError("Either video_timeline or html must be set.")
        if self.video_timeline is not None and self.html is not None:
            raise ValueError("Only one of video_timeline or html can be set.")

    @classmethod
    def from_firestore(cls, doc: dict, asset_service: "AssetService") -> "Canvas":
        from .timeline import VideoTimeline

        if not doc:
            raise ValueError("Cannot create Canvas from empty document.")
        video_timeline_data = doc.get("video_timeline")
        video_timeline = (
            VideoTimeline.from_firestore(video_timeline_data, asset_service)
            if video_timeline_data
            else None
        )

        html_data = doc.get("html")
        html = Html(**html_data) if html_data else None

        return cls(
            id=doc["id"],
            title=doc["title"],
            user_id=doc["user_id"],
            video_timeline=video_timeline,
            html=html,
        )

    def to_firestore(self) -> dict:
        video_timeline_dict = (
            self.video_timeline.to_firestore() if self.video_timeline else None
        )
        html_dict = dataclasses.asdict(self.html) if self.html else None

        return {
            "id": self.id,
            "title": self.title,
            "user_id": self.user_id,
            "video_timeline": video_timeline_dict,
            "html": html_dict,
        }
