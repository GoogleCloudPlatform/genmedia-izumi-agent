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

"""Tools to combine generated media into a final video using VideoStitchingService."""

from google.adk.tools import ToolContext

import mediagent_kit
from utils.adk import display_asset, get_user_id_from_context
from mediagent_kit.services import types

from ..utils import common_utils

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def stitch_final_video(tool_context: ToolContext) -> ToolResult:
    """Combines the generated media from the storyboard into a final video."""
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure(f"Missing {common_utils.STORYBOARD_KEY}")

    user_id = get_user_id_from_context(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()
    canvas_service = mediagent_kit.services.aio.get_canvas_service()
    video_stitching_service = mediagent_kit.services.aio.get_video_stitching_service()

    video_clips: list[types.VideoClip] = []
    audio_clips: list[types.AudioClip] = []
    transitions: list[types.Transition | None] = []

    total_duration_seconds = 0
    for index, scene in enumerate(storyboard["scenes"]):
        # Add scene video.
        first_frame_prompt = scene["first_frame_prompt"]
        first_frame_asset = await asset_service.get_asset_by_id(
            first_frame_prompt["asset_id"]
        )
        video_prompt = scene["video_prompt"]
        video_asset = await asset_service.get_asset_by_id(video_prompt["asset_id"])
        video_duration = video_asset.current.duration_seconds
        video_clips.append(
            types.VideoClip(asset=video_asset, first_frame_asset=first_frame_asset)
        )
        # Add scene voiceover.
        voiceover_prompt = scene["voiceover_prompt"]
        voiceover_asset = await asset_service.get_asset_by_id(
            voiceover_prompt["asset_id"]
        )
        voiceover_duration = voiceover_asset.current.duration_seconds
        speed = max(voiceover_duration, video_duration) / video_duration
        audio_clips.append(
            types.AudioClip(
                asset=voiceover_asset,
                start_at=types.AudioPlacement(video_clip_index=index),
                speed=speed,
            )
        )
        # Add a blank transition between scenes.
        if index > 0:
            transitions.append(None)
        total_duration_seconds += int(video_prompt["duration_seconds"])

    # Add background music.
    music_asset_id = storyboard["background_music_prompt"]["asset_id"]
    music_asset = await asset_service.get_asset_by_id(music_asset_id)
    audio_clips.append(
        types.AudioClip(
            asset=music_asset,
            start_at=types.AudioPlacement(video_clip_index=0),
            trim=types.Trim(duration_seconds=total_duration_seconds),
            fade_out_duration_seconds=1,
        )
    )

    # Construct VideoTimeline
    timeline = types.VideoTimeline(
        title="Final Video",
        video_clips=video_clips,
        audio_clips=audio_clips,
        transitions=transitions,
    )

    # Publish the timeline canvas
    await canvas_service.create_canvas(
        user_id=user_id, title=timeline.title, video_timeline=timeline
    )

    # Stitch the video
    stitched_asset = await video_stitching_service.stitch_video(
        user_id=user_id, timeline=timeline, output_filename="final_video.mp4"
    )
    result = await display_asset(tool_context=tool_context, asset_id=stitched_asset.id)
    if result.startswith("Error"):
        return tool_failure(result)
    return tool_success(result)
