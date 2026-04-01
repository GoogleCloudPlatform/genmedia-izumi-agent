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

"""Tools for generating all ad campaign media."""

import asyncio
from typing import Any

from google.adk.tools.tool_context import ToolContext

import mediagent_kit.services.aio
from utils.adk import get_user_id_from_context
from mediagent_kit.services.types import Asset

from ..utils import common_utils

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def generate_background_music(
    user_id: str, background_music_prompt: dict[str, Any]
) -> Asset:
    """Generates the background music for the campaign."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    music_prompt = background_music_prompt["description"]
    music_asset = await mediagen_service.generate_music_with_lyria(
        user_id=user_id, file_name="background_music.mp3", prompt=music_prompt
    )
    background_music_prompt["asset_id"] = music_asset.id
    return music_asset


async def generate_scene_voiceover(
    user_id: str, voiceover_prompt: dict[str, Any], index: int
) -> Asset:
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    voice_name = "Enceladus" if voiceover_prompt["gender"] == "male" else "Aoede"
    voiceover_asset = await mediagen_service.generate_speech_single_speaker(
        user_id=user_id,
        file_name=f"scene_{index}_voiceover.mp3",
        text=voiceover_prompt["text"],
        voice_name=voice_name,
        prompt=voiceover_prompt["description"],
    )
    voiceover_prompt["asset_id"] = voiceover_asset.id
    return voiceover_asset


async def generate_scene_first_frame(
    user_id: str, first_frame_prompt: dict[str, Any], index: int, aspect_ratio: str
) -> Asset:
    """Generates the first frame for one scene."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    first_frame_asset = await mediagen_service.generate_image_with_gemini(
        user_id=user_id,
        file_name=f"scene_{index}_first_frame.png",
        prompt=first_frame_prompt["description"],
        reference_image_filenames=first_frame_prompt["assets"],
        aspect_ratio=aspect_ratio,
    )
    first_frame_prompt["asset_id"] = first_frame_asset.id
    return first_frame_asset


async def generate_scene_video(
    user_id: str, scene: dict[str, Any], index: int, aspect_ratio: str
) -> list[Asset]:
    """Generates the video for one scene."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    first_frame_asset = await generate_scene_first_frame(
        user_id, scene["first_frame_prompt"], index, aspect_ratio
    )
    video_prompt = scene["video_prompt"]
    video_asset = await mediagen_service.generate_video_with_veo(
        user_id=user_id,
        file_name=f"scene_{index}_video.mp4",
        prompt=video_prompt["description"],
        duration_seconds=int(video_prompt["duration_seconds"]),
        aspect_ratio=aspect_ratio,
        generate_audio=False,
        first_frame_filename=first_frame_asset.file_name,
    )
    video_prompt["asset_id"] = video_asset.id
    return [first_frame_asset, video_asset]


async def generate_scene(
    user_id: str, scene: dict[str, Any], index: int, aspect_ratio: str
) -> list[Asset]:
    """Generates the media for one scene."""
    voiceover_task = generate_scene_voiceover(user_id, scene["voiceover_prompt"], index)
    video_task = generate_scene_video(user_id, scene, index, aspect_ratio)
    results = await asyncio.gather(voiceover_task, video_task, return_exceptions=True)
    assets = []
    for result in results:
        if isinstance(result, Exception):
            raise RuntimeError(f"Error generating scene {index}: {result}")
        assets.append(result)
    return assets


async def generate_all_media(tool_context: ToolContext) -> common_utils.ToolResult:
    """Generates the background music for the campaign."""
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure(f"Missing {common_utils.STORYBOARD_KEY}")
    if (parameters := tool_context.state.get(common_utils.PARAMETERS_KEY)) is None:
        return tool_failure(f"Missing {common_utils.PARAMETERS_KEY}")
    orientation = parameters.get("target_orientation", "landscape")
    aspect_ratio = "9:16" if orientation == "portrait" else "16:9"

    user_id = get_user_id_from_context(tool_context)
    music_task = generate_background_music(
        user_id, storyboard["background_music_prompt"]
    )
    scene_tasks = [
        generate_scene(user_id, scene, index, aspect_ratio)
        for index, scene in enumerate(storyboard["scenes"])
    ]

    results = await asyncio.gather(music_task, *scene_tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            return common_utils.tool_failure(f"Error generating media: {result}")

    return common_utils.tool_success("Generated all media.")
