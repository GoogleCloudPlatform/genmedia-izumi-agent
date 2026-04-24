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

"""Tools to combine generated media into a final video with Global Audio sync."""

import logging

from google.adk.tools import ToolContext

import mediagent_kit
from mediagent_kit.services import types
from utils.adk import display_asset, get_user_id_from_context

from ..utils import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def stitch_final_video(tool_context: ToolContext) -> ToolResult:
    """Combines the generated media into a final video with unified Global Audio."""
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure(f"Missing {common_utils.STORYBOARD_KEY}")

    user_id = get_user_id_from_context(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()
    video_stitching_service = mediagent_kit.services.aio.get_video_stitching_service()
    iteration_num = tool_context.state.get("mab_iteration", 0)

    video_clips: list[types.VideoClip] = []
    audio_clips: list[types.AudioClip] = []
    transitions: list[types.Transition | None] = []

    total_duration_seconds = 0

    # 1. Process Video Clips and calculate total duration
    for index, scene in enumerate(storyboard["scenes"]):
        first_frame_asset = await asset_service.get_asset_by_id(
            scene["first_frame_prompt"]["asset_id"]
        )
        video_asset_id = scene["video_prompt"].get("asset_id")

        if video_asset_id:
            video_asset = await asset_service.get_asset_by_id(video_asset_id)
            logger.info(f"Adding video clip for scene {index}: {video_asset.file_name}")
        else:
            # FALLBACK: Use static image if video failed
            video_asset = first_frame_asset
            logger.warning(
                f"Scene {index} has no video asset. Using static fallback: {video_asset.file_name}"
            )

        video_clips.append(
            types.VideoClip(asset=video_asset, first_frame_asset=first_frame_asset)
        )

        # Handle Stage 3 Fallback: Static Logo Hold
        if hold_id := scene.get("last_frame_hold_asset_id"):
            hold_duration = scene.get("last_frame_hold_duration", 2.0)
            hold_asset = await asset_service.get_asset_by_id(hold_id)
            logger.info(
                f"Adding static logo hold for scene {index}: {hold_asset.file_name} ({hold_duration}s)"
            )
            video_clips.append(
                types.VideoClip(
                    asset=hold_asset,
                    trim=types.Trim(duration_seconds=float(hold_duration)),
                )
            )
            total_duration_seconds += float(hold_duration)

        if index > 0:
            transitions.append(None)
            # If we added a hold clip, we need an extra transition (None)
            if scene.get("last_frame_hold_asset_id"):
                transitions.append(None)

        total_duration_seconds += int(scene["video_prompt"]["duration_seconds"])

    # 2. Process Global Voiceover (Unified)
    vo_prompt = storyboard.get("voiceover_prompt", {})
    if vo_asset_id := vo_prompt.get("asset_id"):
        vo_asset = await asset_service.get_asset_by_id(vo_asset_id)
        vo_duration = vo_asset.versions[-1].duration_seconds

        # Calculate speed multiplier to fit VO into the total video length.
        # Clamp speed between 0.8 and 2.0 to maintain intelligibility.
        # If VO is shorter than video, ratio < 1.0 (slowing down).
        # If VO is longer than video, ratio > 1.0 (speeding up).
        speed = max(0.8, min(2.0, vo_duration / float(total_duration_seconds)))

        audio_clips.append(
            types.AudioClip(
                asset=vo_asset,
                start_at=types.AudioPlacement(video_clip_index=0),
                speed=speed,
            )
        )
        logger.info(
            f"Adding unified voiceover: {vo_duration:.2f}s adjusted by {speed:.2f}x to fit {total_duration_seconds}s"
        )
    else:
        logger.warning("No global voiceover asset found for stitching.")

    # 3. Add Background Music
    music_prompt = storyboard.get("background_music_prompt", {})
    if music_asset_id := music_prompt.get("asset_id"):
        music_asset = await asset_service.get_asset_by_id(music_asset_id)
        audio_clips.append(
            types.AudioClip(
                asset=music_asset,
                start_at=types.AudioPlacement(video_clip_index=0),
                trim=types.Trim(duration_seconds=total_duration_seconds),
                fade_out_duration_seconds=1,
            )
        )
    else:
        logger.warning("No background music asset found for stitching.")

    # 4. Construct VideoTimeline
    timeline = types.VideoTimeline(
        title=f"Iteration {iteration_num} Final Video",
        video_clips=video_clips,
        audio_clips=audio_clips,
        transitions=transitions,
    )

    # 5. Final Assembly
    output_filename = f"iter_{iteration_num}_final_video.mp4"
    stitched_asset = await video_stitching_service.stitch_video(
        user_id=user_id, timeline=timeline, output_filename=output_filename
    )

    storyboard["final_video_asset_id"] = stitched_asset.id
    storyboard["final_video_asset_version"] = stitched_asset.current_version
    tool_context.state[common_utils.STORYBOARD_KEY] = storyboard

    result = await display_asset(tool_context=tool_context, asset_id=stitched_asset.id)
    if result.startswith("Error"):
        return tool_failure(result)
    return tool_success(result)
