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

import logging
import mediagent_kit
from mediagent_kit.services import types
import uuid
from google.adk.tools import ToolContext

from utils.adk import display_asset
from utils.adk import get_user_id_from_context
from utils.adk import get_session_id_from_context

from ...utils.common import common_utils
from ...utils.storyboard import template_library

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure


async def stitch_final_video(tool_context: ToolContext) -> ToolResult:
    """Combines the generated media from the storyboard into a final video."""
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `stitch_final_video` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    if (storyboard := tool_context.state.get(common_utils.STORYBOARD_KEY)) is None:
        return tool_failure(f"Missing {common_utils.STORYBOARD_KEY}")

    if (parameters := tool_context.state.get(common_utils.PARAMETERS_KEY)) is None:
        return tool_failure(f"Missing {common_utils.PARAMETERS_KEY}")

    user_id = get_user_id_from_context(tool_context)
    session_id = get_session_id_from_context(tool_context)

    asset_service = mediagent_kit.services.aio.get_asset_service()
    video_stitching_service = mediagent_kit.services.aio.get_video_stitching_service()

    # Identify if current run is UGC
    template_name = parameters.get("template_name", "Custom")
    template_obj = template_library.get_template_by_name(template_name)
    is_ugc = (
        (template_obj.industry_type == "Social Native")
        or (storyboard.get("campaign_theme") == "Social Native")
        or (parameters.get("vertical") in ["Social Native", "UGC"])
    )

    video_clips: list[types.VideoClip] = []
    audio_clips: list[types.AudioClip] = []
    transitions: list[types.Transition | None] = []

    total_duration_seconds = 0

    # Map original scene index to final clip index in VideoTimeline
    scene_to_clip_index: dict[int, int] = {}
    current_clip_idx = 0

    scenes = storyboard.get("scenes", [])
    if not scenes:
        return tool_failure(
            "Malformed storyboard: 'scenes' key is missing. Cannot stitch without scenes."
        )

    # 1. Build Video Track
    for index, scene in enumerate(scenes):
        # Add scene video.
        first_frame_prompt = scene["first_frame_prompt"]

        # Robustness: Skip scenes that failed to generate any media
        if not first_frame_prompt.get("asset_id"):
            logger.warning(
                f"Skipping scene {index} in final stitch because it has no asset_id (generation likely failed)."
            )
            continue

        first_frame_asset = await asset_service.get_asset_by_id(
            first_frame_prompt["asset_id"]
        )

        video_prompt = scene["video_prompt"]
        video_asset_id = video_prompt.get("asset_id")

        if video_asset_id:
            video_asset = await asset_service.get_asset_by_id(video_asset_id)
        else:
            # Fallback to first frame if video is missing
            video_asset = first_frame_asset

        # Apply trimming to match the exact storyboard pacing (e.g. 2s cut from a 4s generation)
        target_duration = video_prompt.get("duration_seconds", 4)

        video_clips.append(
            types.VideoClip(
                asset=video_asset,
                first_frame_asset=first_frame_asset,
                trim=types.Trim(duration_seconds=target_duration),
                volume=0.0,
            )
        )

        # Track that this original scene_index is now at current_clip_idx
        scene_to_clip_index[index] = current_clip_idx
        current_clip_idx += 1

        # Add transition from previous scene
        if index > 0:
            transition = None
            # Transitions are currently disabled to prevent potential ffmpeg issues
            transitions.append(transition)

        total_duration_seconds += video_prompt["duration_seconds"]

    # 2. Build Audio Track (Voiceover)
    voiceover_groups = storyboard.get("voiceover_groups", [])

    # THE UGC EXCEPTION: We never use grouped voiceover for UGC cases
    # to preserve lip-sync and per-scene timing.
    if voiceover_groups and not is_ugc:
        # STRATEGY A: Grouped Voiceover (Standard Templates)
        logger.info("Using Grouped Voiceover Strategy for final stitch.")
        current_audio_time = 0.0

        for group in voiceover_groups:
            group_start_time = current_audio_time
            group_duration = group.get("total_duration", 0.0)

            if group.get("audio_asset_id"):
                voiceover_asset = await asset_service.get_asset_by_id(
                    group["audio_asset_id"]
                )
                if voiceover_asset:
                    speed = 1.0
                    if voiceover_asset.current.duration_seconds:
                        vo_duration = voiceover_asset.current.duration_seconds
                        if vo_duration > group_duration:
                            speed = vo_duration / group_duration

                    # Map original scene index to the actual clip index
                    target_clip_idx = scene_to_clip_index.get(group["scene_indices"][0])
                    if target_clip_idx is not None:
                        audio_clips.append(
                            types.AudioClip(
                                asset=voiceover_asset,
                                start_at=types.AudioPlacement(
                                    video_clip_index=target_clip_idx
                                ),
                                speed=speed,
                            )
                        )
                    else:
                        logger.warning(
                            f"Skipping grouped voiceover for scene {group['scene_indices'][0]} because it was not included in the stitch."
                        )

            current_audio_time += group_duration

    else:
        # STRATEGY B: Per-Scene Voiceover (UGC or Legacy Fallback)
        logger.info(f"Using Per-Scene Voiceover Strategy (is_ugc={is_ugc}).")
        for index, scene in enumerate(scenes):
            voiceover_prompt = scene["voiceover_prompt"]
            video_prompt = scene["video_prompt"]
            target_duration = video_prompt.get("duration_seconds", 4)

            if voiceover_prompt.get("asset_id"):
                voiceover_asset = await asset_service.get_asset_by_id(
                    voiceover_prompt["asset_id"]
                )

                if voiceover_asset:
                    speed = 1.0
                    if voiceover_asset.current.duration_seconds:
                        vo_duration = voiceover_asset.current.duration_seconds
                        if vo_duration > target_duration:
                            speed = vo_duration / target_duration

                    # Map original scene index to the actual clip index
                    target_clip_idx = scene_to_clip_index.get(index)
                    if target_clip_idx is not None:
                        audio_clips.append(
                            types.AudioClip(
                                asset=voiceover_asset,
                                start_at=types.AudioPlacement(
                                    video_clip_index=target_clip_idx
                                ),
                                speed=speed,
                            )
                        )
                    else:
                        logger.warning(
                            f"Skipping per-scene voiceover for scene {index} because it was not included in the stitch."
                        )
            else:
                # UGC / Lip-Sync Logic: Add the video's own audio track
                video_asset_id = video_prompt.get("asset_id")
                if video_asset_id:
                    video_asset = await asset_service.get_asset_by_id(video_asset_id)
                    if (
                        video_asset.current.video_generate_config
                        and video_asset.current.video_generate_config.generate_audio
                    ):
                        target_clip_idx = scene_to_clip_index.get(index)
                        if target_clip_idx is not None:
                            audio_clips.append(
                                types.AudioClip(
                                    asset=video_asset,
                                    start_at=types.AudioPlacement(
                                        video_clip_index=target_clip_idx
                                    ),
                                    trim=types.Trim(duration_seconds=target_duration),
                                    volume=1.0,
                                )
                            )

    # 3. Build Audio Track (Background Music)
    music_asset_id = storyboard["background_music_prompt"].get("asset_id")
    if music_asset_id:
        music_asset = await asset_service.get_asset_by_id(music_asset_id)
        if music_asset:
            # Music always starts at the first AVAILABLE clip (index 0 of video_clips)
            if video_clips:
                audio_clips.append(
                    types.AudioClip(
                        asset=music_asset,
                        start_at=types.AudioPlacement(video_clip_index=0),
                        trim=types.Trim(duration_seconds=total_duration_seconds),
                        fade_out_duration_seconds=1,
                    )
                )

    uid = uuid.uuid4().hex[:4]
    timeline = types.VideoTimeline(
        title=f"Ads-X Template Final Video {uid}",
        video_clips=video_clips,
        audio_clips=audio_clips,
        transitions=transitions,
    )

    # Canvas Logic
    canvas_service = mediagent_kit.services.aio.get_canvas_service()
    canvas = await canvas_service.create_canvas(
        user_id=user_id,
        title=timeline.title,
        video_timeline=timeline,
    )
    tool_context.state["video_timeline_canvas_id"] = canvas.id

    # Stitch the video
    stitched_asset = await video_stitching_service.stitch_video(
        user_id=user_id, timeline=timeline, output_filename=f"final_video_{uid}.mp4"
    )

    tool_context.state["final_video_asset_id"] = stitched_asset.id

    display_result = await display_asset(
        tool_context=tool_context, asset_id=stitched_asset.id
    )
    if display_result.startswith("Error"):
        return tool_failure(display_result)

    import os

    IZUMI_BASE_URL = os.environ.get("IZUMI_STUDIO_URL")
    if not IZUMI_BASE_URL:
        # Fallback to backend service URL if in Cloud Run, otherwise Local
        IZUMI_BASE_URL = os.environ.get(
            "CLOUD_RUN_SERVICE_URL", "http://localhost:5173"
        )
    izumi_deep_link = f"{IZUMI_BASE_URL}/studio/#/project/{user_id}/chat/{session_id}?contentTab=canvas&canvasId={canvas.id}"
    success_message = f"[View Video Timeline in Izumi Studio]({izumi_deep_link})"

    return tool_success(success_message)
