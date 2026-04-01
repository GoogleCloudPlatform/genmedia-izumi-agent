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

import datetime
import enum
from typing import Optional

from pydantic import BaseModel, Field

from mediagent_kit.services.types.jobs import JobStatus, JobType

# Models from services/types.py, adapted for FastAPI


class ImageGenerateConfig(BaseModel):
    model: str | None = None
    prompt: str | None = None
    reference_images: list["Asset"] | None = None


class MusicGenerateConfig(BaseModel):
    model: str | None = None
    prompt: str | None = None


class VideoGenerateConfig(BaseModel):
    model: str | None = None
    prompt: str | None = None
    first_frame_asset: Optional["Asset"] = None
    last_frame_asset: Optional["Asset"] = None


class SpeechGenerateConfig(BaseModel):
    model: str | None = None
    prompt: str | None = None
    voice: str | None = None
    spoken_text: str | None = None


class AssetVersion(BaseModel):
    asset_id: str
    version_number: int
    gcs_uri: str
    create_time: datetime.datetime
    image_generate_config: ImageGenerateConfig | None = None
    music_generate_config: MusicGenerateConfig | None = None
    video_generate_config: VideoGenerateConfig | None = None
    speech_generate_config: SpeechGenerateConfig | None = None
    duration_seconds: float | None = None


class Asset(BaseModel):
    id: str
    user_id: str
    mime_type: str
    file_name: str
    current_version: int
    versions: list[AssetVersion]


class AssetUpdate(BaseModel):
    file_name: str | None = None


class Html(BaseModel):
    content: str
    asset_ids: list[str] = []


@enum.unique
class TransitionType(enum.StrEnum):
    NONE = "none"
    FADE = "fade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"


class Trim(BaseModel):
    offset_seconds: float = 0.0
    duration_seconds: float | None = None


class Transition(BaseModel):
    type: TransitionType
    duration_seconds: float


class VideoClip(BaseModel):
    asset: Asset | None = None
    trim: Trim | None = None
    volume: float = 1.0
    speed: float = 1.0
    first_frame_asset: Asset | None = None
    last_frame_asset: Asset | None = None
    placeholder: str | None = None


class AudioPlacement(BaseModel):
    video_clip_index: int
    offset_seconds: float = 0.0


class AudioClip(BaseModel):
    start_at: AudioPlacement
    asset: Asset | None = None
    trim: Trim | None = None
    volume: float = 1.0
    speed: float = 1.0
    fade_in_duration_seconds: float = 0.0
    fade_out_duration_seconds: float = 0.0
    placeholder: str | None = None


class VideoTimeline(BaseModel):
    title: str
    video_clips: list[VideoClip]
    transitions: list[Transition | None]
    audio_clips: list[AudioClip] = Field(default_factory=list)
    transition_in: Transition | None = None
    transition_out: Transition | None = None


class Canvas(BaseModel):
    id: str
    title: str
    user_id: str
    video_timeline: VideoTimeline | None = None
    html: Html | None = None


class CanvasInfo(BaseModel):
    id: str
    title: str
    user_id: str
    canvas_type: str


class CanvasUpdate(BaseModel):
    title: str | None = None
    video_timeline: VideoTimeline | None = None
    html: Html | None = None


@enum.unique
class ImagenModel(enum.StrEnum):
    IMAGEN_4_0_FAST_GENERATE_001 = "imagen-4.0-fast-generate-001"
    IMAGEN_4_0_GENERATE_001 = "imagen-4.0-generate-001"
    IMAGEN_4_0_ULTRA_GENERATE_001 = "imagen-4.0-ultra-generate-001"


@enum.unique
class ImagenAspectRatio(enum.StrEnum):
    RATIO_1_1 = "1:1"
    RATIO_3_4 = "3:4"
    RATIO_4_3 = "4:3"
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"


@enum.unique
class GeminiImageAspectRatio(enum.StrEnum):
    RATIO_1_1 = "1:1"
    RATIO_3_2 = "3:2"
    RATIO_2_3 = "2:3"
    RATIO_3_4 = "3:4"
    RATIO_4_3 = "4:3"
    RATIO_4_5 = "4:5"
    RATIO_5_4 = "5:4"
    RATIO_9_16 = "9:16"
    RATIO_16_9 = "16:9"
    RATIO_21_9 = "21:9"


@enum.unique
class GeminiImageModel(enum.StrEnum):
    GEMINI_2_5_FLASH_IMAGE = "gemini-2.5-flash-image"
    GEMINI_3_PRO_IMAGE = "gemini-3-pro-image-preview"


@enum.unique
class LyriaModel(enum.StrEnum):
    LYRIA_002 = "lyria-002"


@enum.unique
class SpeechModel(enum.StrEnum):
    GEMINI_2_5_FLASH_TTS = "gemini-2.5-flash-tts"
    GEMINI_2_5_PRO_TTS = "gemini-2.5-pro-tts"


@enum.unique
class SpeechVoice(enum.StrEnum):
    ACHERNAR = "Achernar"
    ACHIRD = "Achird"
    ALGENIB = "Algenib"
    ALGIEBA = "Algieba"
    ALNILAM = "Alnilam"
    AOEDE = "Aoede"
    AUTONOE = "Autonoe"
    CALLIRRHOE = "Callirrhoe"
    CHARON = "Charon"
    DESPINA = "Despina"
    ENCELADUS = "Enceladus"
    ERINOME = "Erinome"
    FENRIR = "Fenrir"
    GACRUX = "Gacrux"
    IAPETUS = "Iapetus"
    KORE = "Kore"
    LAOMEDEIA = "Laomedeia"
    LEDA = "Leda"
    ORUS = "Orus"
    PULCHERRIMA = "Pulcherrima"
    PUCK = "Puck"
    RASALGETHI = "Rasalgethi"
    SADACHBIA = "Sadachbia"
    SADALTAGER = "Sadaltager"
    SCHEDAR = "Schedar"
    SULAFAT = "Sulafat"
    UMBRIEL = "Umbriel"
    VINDEMIATRIX = "Vindemiatrix"
    ZEPHYR = "Zephyr"
    ZUBENELGENUBI = "Zubenelgenubi"


@enum.unique
class VeoModel(enum.StrEnum):
    VEO_3_0_FAST_GENERATE_001 = "veo-3.0-fast-generate-001"
    VEO_3_0_GENERATE_001 = "veo-3.0-generate-001"
    VEO_3_1_GENERATE_001 = "veo-3.1-generate-001"


@enum.unique
class VeoAspectRatio(enum.StrEnum):
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"


@enum.unique
class VeoDuration(enum.IntEnum):
    SECONDS_4 = 4
    SECONDS_6 = 6
    SECONDS_8 = 8


@enum.unique
class VeoResolution(enum.StrEnum):
    RESOLUTION_720P = "720p"
    RESOLUTION_1080P = "1080p"


# --- Request Models ---


class GenerateMusicRequest(BaseModel):
    prompt: str
    file_name: str
    model: LyriaModel
    negative_prompt: str | None = None


class GenerateImageWithImagenRequest(BaseModel):
    prompt: str
    aspect_ratio: ImagenAspectRatio
    model: ImagenModel
    file_name: str


class GenerateImageWithGeminiRequest(BaseModel):
    prompt: str
    aspect_ratio: GeminiImageAspectRatio
    file_name: str
    model: GeminiImageModel = GeminiImageModel.GEMINI_2_5_FLASH_IMAGE
    reference_image_filenames: list[str] = Field(default_factory=list)


class GenerateSpeechSingleSpeakerRequest(BaseModel):
    prompt: str
    text: str
    model: SpeechModel
    voice_name: SpeechVoice
    file_name: str


class GenerateVideoRequest(BaseModel):
    prompt: str
    file_name: str
    model: VeoModel
    first_frame_filename: str | None = None
    last_frame_filename: str | None = None
    aspect_ratio: VeoAspectRatio
    duration_seconds: VeoDuration
    resolution: VeoResolution | None = None
    generate_audio: bool = False


# --- Job Models ---


class Job(BaseModel):
    id: str
    user_id: str
    job_type: JobType
    status: JobStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    job_input: dict | None = None
    result_asset_id: str | None = None
    result_asset: Asset | None = None
    error_message: str | None = None
