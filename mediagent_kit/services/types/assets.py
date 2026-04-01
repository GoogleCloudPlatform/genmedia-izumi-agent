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

"""Data classes for representing assets."""

import dataclasses
import datetime
import typing

if typing.TYPE_CHECKING:
    from ..asset_service import AssetService


@dataclasses.dataclass(frozen=True, kw_only=True)
class TextGenerateConfig:
    """Configuration for generating text.

    Attributes:
        model: The text generation model to use.
        prompt: The prompt used for text generation.
        reference_images: A list of reference images used for text generation.
    """

    model: str | None = None
    prompt: str | None = None
    reference_images: list["Asset"] | None = None


@dataclasses.dataclass
class ImageGenerateConfig:
    """Configuration for generating an image.

    Attributes:
        model: The image generation model to use.
        prompt: The prompt used for image generation.
        aspect_ratio: The aspect ratio of the generated image (e.g., "1:1", "16:9").
        reference_images: A list of reference images used for image generation.
    """

    model: str | None = None
    prompt: str | None = None
    aspect_ratio: str | None = None
    reference_images: list["Asset"] | None = None


@dataclasses.dataclass
class MusicGenerateConfig:
    """Configuration for generating music.

    Attributes:
        model: The music generation model to use.
        prompt: The prompt used for music generation.
        negative_prompt: An optional negative prompt to guide music generation away from certain characteristics.
    """

    model: str | None = None
    prompt: str | None = None
    negative_prompt: str | None = None


@dataclasses.dataclass
class VideoGenerateConfig:
    """Configuration for generating a video.

    Attributes:
        model: The video generation model to use.
        prompt: The prompt used for video generation.
        aspect_ratio: The aspect ratio of the generated video (e.g., "1:1", "16:9").
        duration_seconds: The duration of the video in seconds.
        resolution: The resolution of the video (e.g., "720p", "1080p").
        generate_audio: Whether to generate audio for the video.
        first_frame_asset: The asset to use as the first frame of the video.
        last_frame_asset: The asset to use as the last frame of the video.
    """

    model: str | None = None
    prompt: str | None = None
    aspect_ratio: str | None = None
    duration_seconds: int | None = None
    resolution: str | None = None
    generate_audio: bool | None = None
    first_frame_asset: typing.Optional["Asset"] = None
    last_frame_asset: typing.Optional["Asset"] = None


@dataclasses.dataclass
class SpeechGenerateConfig:
    """Configuration for generating speech.

    Attributes:
        model: The speech generation model to use.
        prompt: The prompt used for speech generation.
        voice: The voice to use for speech generation.
        spoken_text: The text to be spoken.
    """

    model: str | None = None
    prompt: str | None = None
    voice: str | None = None
    spoken_text: str | None = None


@dataclasses.dataclass
class AssetVersion:
    """Represents a specific version of an asset.

    Attributes:
        asset_id: The ID of the parent asset.
        version_number: The version number of this asset.
        gcs_uri: The Google Cloud Storage URI where the asset blob is stored.
        create_time: The timestamp when this version was created.
        text_generate_config: The configuration used to generate text for this version, if applicable.
        image_generate_config: The configuration used to generate an image for this version, if applicable.
        music_generate_config: The configuration used to generate music for this version, if applicable.
        video_generate_config: The configuration used to generate a video for this version, if applicable.
        speech_generate_config: The configuration used to generate speech for this version, if applicable.
    """

    asset_id: str
    version_number: int
    gcs_uri: str
    create_time: datetime.datetime
    text_generate_config: TextGenerateConfig | None = None
    image_generate_config: ImageGenerateConfig | None = None
    music_generate_config: MusicGenerateConfig | None = None
    video_generate_config: VideoGenerateConfig | None = None
    speech_generate_config: SpeechGenerateConfig | None = None
    duration_seconds: float | None = None

    def to_firestore(self) -> dict:
        """Converts the AssetVersion object to a Firestore-compatible dictionary without deep recursion."""
        data = {
            "asset_id": self.asset_id,
            "version_number": self.version_number,
            "gcs_uri": self.gcs_uri,
            "create_time": self.create_time,
            "duration_seconds": self.duration_seconds,
        }

        if self.text_generate_config:
            text_config = {
                "model": self.text_generate_config.model,
                "prompt": self.text_generate_config.prompt,
            }
            if self.text_generate_config.reference_images:
                text_config["reference_image_ids"] = [
                    img.id for img in self.text_generate_config.reference_images
                ]
            data["text_generate_config"] = text_config

        if self.image_generate_config:
            image_config = {
                "model": self.image_generate_config.model,
                "prompt": self.image_generate_config.prompt,
                "aspect_ratio": self.image_generate_config.aspect_ratio,
            }
            if self.image_generate_config.reference_images:
                image_config["reference_image_ids"] = [
                    img.id for img in self.image_generate_config.reference_images
                ]
            data["image_generate_config"] = image_config

        if self.music_generate_config:
            data["music_generate_config"] = {
                "model": self.music_generate_config.model,
                "prompt": self.music_generate_config.prompt,
                "negative_prompt": self.music_generate_config.negative_prompt,
            }

        if self.video_generate_config:
            video_config = {
                "model": self.video_generate_config.model,
                "prompt": self.video_generate_config.prompt,
                "aspect_ratio": self.video_generate_config.aspect_ratio,
                "duration_seconds": self.video_generate_config.duration_seconds,
                "resolution": self.video_generate_config.resolution,
                "generate_audio": self.video_generate_config.generate_audio,
            }
            if self.video_generate_config.first_frame_asset:
                video_config["first_frame_asset_id"] = self.video_generate_config.first_frame_asset.id
            if self.video_generate_config.last_frame_asset:
                video_config["last_frame_asset_id"] = self.video_generate_config.last_frame_asset.id
            data["video_generate_config"] = video_config

        if self.speech_generate_config:
            data["speech_generate_config"] = {
                "model": self.speech_generate_config.model,
                "prompt": self.speech_generate_config.prompt,
                "voice": self.speech_generate_config.voice,
                "spoken_text": self.speech_generate_config.spoken_text,
            }

        return data



@dataclasses.dataclass
class Asset:
    """Represents a digital asset, which can have multiple versions.

    Attributes:
        id: The unique identifier for the asset.
        user_id: The ID of the user who owns this asset.
        mime_type: The MIME type of the asset (e.g., "image/png", "audio/mp3").
        file_name: The original file name of the asset.
        current_version: The version number of the currently active asset version.
        versions: A list of all versions of this asset.
    """

    id: str
    user_id: str
    mime_type: str
    file_name: str
    current_version: int
    versions: list[AssetVersion]

    @classmethod
    def from_firestore(
        cls, doc: dict, asset_service: "AssetService", fetch_references: bool = True
    ) -> "Asset":
        """Creates an Asset object from a Firestore document.

        Args:
            doc: The Firestore document data as a dictionary.
            asset_service: The AssetService instance to use for fetching referenced assets.
            fetch_references: Whether to fetch referenced assets (e.g. parent images).
                Defaults to True. If False, referenced assets will be None.
                This is to prevent infinite recursion.

        Returns:
            An Asset object populated with data from the Firestore document.
        """
        versions_data = doc.get("versions", [])
        versions = []
        for v_data in versions_data:
            text_config = None
            image_config = None
            music_config = None
            video_config = None
            speech_config = None
            reference_images: list[Asset] | None = None  # Declare once per loop

            if text_config_data := v_data.get("text_generate_config"):
                if fetch_references and (
                    reference_image_ids := text_config_data.get("reference_image_ids")
                ):
                    fetched_assets = (
                        asset_service.get_asset_by_id(asset_id, fetch_references=False)
                        for asset_id in reference_image_ids
                    )
                    reference_images = list(filter(None, fetched_assets))
                text_config = TextGenerateConfig(
                    model=text_config_data.get("model"),
                    prompt=text_config_data.get("prompt"),
                    reference_images=reference_images,
                )

            if image_config_data := v_data.get("image_generate_config"):
                if fetch_references and (
                    reference_image_ids := image_config_data.get("reference_image_ids")
                ):
                    fetched_assets = (
                        asset_service.get_asset_by_id(asset_id, fetch_references=False)
                        for asset_id in reference_image_ids
                    )
                    reference_images = list(filter(None, fetched_assets))

                image_config = ImageGenerateConfig(
                    model=image_config_data.get("model"),
                    prompt=image_config_data.get("prompt"),
                    aspect_ratio=image_config_data.get("aspect_ratio"),
                    reference_images=reference_images,
                )

            music_config_data = v_data.get("music_generate_config")
            music_config = (
                MusicGenerateConfig(**music_config_data) if music_config_data else None
            )

            video_config_data = v_data.get("video_generate_config")
            video_config = None
            if video_config_data:
                first_frame_asset = None
                if fetch_references and video_config_data.get("first_frame_asset_id"):
                    first_frame_asset = asset_service.get_asset_by_id(
                        video_config_data.get("first_frame_asset_id"),
                        fetch_references=False,
                    )

                last_frame_asset = None
                if fetch_references and video_config_data.get("last_frame_asset_id"):
                    last_frame_asset = asset_service.get_asset_by_id(
                        video_config_data.get("last_frame_asset_id"),
                        fetch_references=False,
                    )
                video_config = VideoGenerateConfig(
                    model=video_config_data.get("model"),
                    prompt=video_config_data.get("prompt"),
                    aspect_ratio=video_config_data.get("aspect_ratio"),
                    duration_seconds=video_config_data.get("duration_seconds"),
                    resolution=video_config_data.get("resolution"),
                    generate_audio=video_config_data.get("generate_audio"),
                    first_frame_asset=first_frame_asset,
                    last_frame_asset=last_frame_asset,
                )

            speech_config_data = v_data.get("speech_generate_config")
            speech_config = (
                SpeechGenerateConfig(**speech_config_data)
                if speech_config_data
                else None
            )

            versions.append(
                AssetVersion(
                    asset_id=v_data["asset_id"],
                    version_number=v_data["version_number"],
                    gcs_uri=v_data["gcs_uri"],
                    create_time=v_data["create_time"],
                    text_generate_config=text_config,
                    image_generate_config=image_config,
                    music_generate_config=music_config,
                    video_generate_config=video_config,
                    speech_generate_config=speech_config,
                    duration_seconds=v_data.get("duration_seconds"),
                )
            )

        if not fetch_references:
            versions = []

        return cls(
            id=doc["id"],
            user_id=doc["user_id"],
            mime_type=doc["mime_type"],
            file_name=doc["file_name"],
            current_version=doc["current_version"],
            versions=versions,
        )

    def to_firestore(self) -> dict:
        """Converts the Asset object to a Firestore-compatible dictionary.

        Returns:
            A dictionary representation of the asset, suitable for Firestore.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mime_type": self.mime_type,
            "file_name": self.file_name,
            "current_version": self.current_version,
            "versions": [v.to_firestore() for v in self.versions],
        }

    @property
    def current(self) -> AssetVersion:
        """Returns the current asset version."""
        for version in self.versions:
            if version.version_number == self.current_version:
                return version
        raise ValueError(
            f"Could not find the current version of asset {self.file_name}"
        )


@dataclasses.dataclass
class AssetBlob:
    """Represents the binary content of an asset along with its metadata.

    Attributes:
        content: The binary content of the asset.
        file_name: The file name of the asset.
        mime_type: The MIME type of the asset.
    """

    content: bytes
    file_name: str
    mime_type: str
