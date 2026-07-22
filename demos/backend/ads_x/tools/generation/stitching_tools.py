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
from typing import Any
import uuid
from google.adk.tools import ToolContext
import mediagent_kit
from mediagent_kit.services import types

from utils.adk import display_asset
from utils.adk import get_user_id_from_context
from utils.adk import get_session_id_from_context
from utils.adk import resolve_workspace_id

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

    workspace_id, ws_error = resolve_workspace_id(tool_context)
    if ws_error:
        return tool_failure(ws_error)

    current_sb_id = storyboard.get("storyboard_id") or storyboard.get("id")

    if isinstance(storyboard, dict):
        storyboard["session_id"] = session_id
        storyboard["workspace_id"] = workspace_id
    else:
        try:
            setattr(storyboard, "session_id", session_id)
            setattr(storyboard, "workspace_id", workspace_id)
        except Exception as attr_err:
            logger.warning(
                f"Could not directly set session_id/workspace_id on storyboard object: {attr_err}"
            )

    # Explicitly save latest storyboard to Creative Studio before timeline render
    try:
        storyboard_service = mediagent_kit.services.aio.get_storyboard_service()
        saved_sb = await storyboard_service.save_storyboard(storyboard)

        if hasattr(saved_sb, "storyboard_id") and saved_sb.storyboard_id:
            current_sb_id = str(saved_sb.storyboard_id)
        elif isinstance(saved_sb, dict) and (
            sb_id := saved_sb.get("storyboard_id") or saved_sb.get("id")
        ):
            current_sb_id = str(sb_id)

        if current_sb_id:
            tool_context.state["current_storyboard_id"] = current_sb_id
            # Save correct integer ID back into the session storyboard object for later updates
            if isinstance(storyboard, dict):
                storyboard["storyboard_id"] = current_sb_id
                tool_context.state[common_utils.STORYBOARD_KEY] = storyboard
            elif hasattr(storyboard, "storyboard_id"):
                setattr(storyboard, "storyboard_id", current_sb_id)
                tool_context.state[common_utils.STORYBOARD_KEY] = storyboard
    except Exception as sb_err:
        logger.warning(f"Explicit pre-stitch storyboard save bypassed/failed: {sb_err}")

    from mediagent_kit.services.types.common import AssetRef

    def _resolve_asset_ref(
        prompt_dict: dict[str, Any], default_ws: str
    ) -> AssetRef | None:
        if not prompt_dict:
            return None
        if "asset_ref" in prompt_dict and isinstance(prompt_dict["asset_ref"], dict):
            ref_data = prompt_dict["asset_ref"]
            return AssetRef(
                id=str(ref_data["id"]),
                asset_type=ref_data.get("asset_type", "generated"),
                workspace_id=str(ref_data.get("workspace_id") or default_ws),
            )
        logger.warning(
            f"Unable to resolve AssetRef: 'asset_ref' missing or invalid in prompt_dict: {prompt_dict}"
        )
        return None

    def _get_asset_duration(asset: Any) -> float | None:
        duration = getattr(asset, "duration_seconds", None)
        return float(duration) if isinstance(duration, (int, float)) else None

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
        first_frame_ref = _resolve_asset_ref(first_frame_prompt, workspace_id)

        # Robustness: Skip scenes that failed to generate any media
        if not first_frame_ref:
            logger.warning(
                f"Skipping scene {index} in final stitch because it has no asset_ref/asset_id (generation likely failed)."
            )
            continue

        # NOTE: Unified AssetServiceInterface adaptation.
        # This would break legacy version due to function signature and method name mismatch.
        first_frame_asset = await asset_service.get_asset(first_frame_ref)

        video_prompt = scene["video_prompt"]
        video_ref = _resolve_asset_ref(video_prompt, workspace_id)

        if video_ref:
            # NOTE: Unified AssetServiceInterface adaptation.
            # This would break legacy version due to function signature and method name mismatch.
            video_asset = await asset_service.get_asset(video_ref)
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

            group_audio_ref = _resolve_asset_ref(
                {"asset_ref": group.get("audio_asset_ref")},
                workspace_id,
            )

            if group_audio_ref:
                # NOTE: Unified AssetServiceInterface adaptation.
                # This would break legacy version due to function signature and method name mismatch.
                voiceover_asset = await asset_service.get_asset(group_audio_ref)
                if voiceover_asset:
                    speed = 1.0
                    vo_duration = _get_asset_duration(voiceover_asset)
                    if vo_duration and vo_duration > group_duration:
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
            vo_ref = _resolve_asset_ref(voiceover_prompt, workspace_id)

            if vo_ref:
                # NOTE: Unified AssetServiceInterface adaptation.
                # This would break legacy version due to function signature and method name mismatch.
                voiceover_asset = await asset_service.get_asset(vo_ref)

                if voiceover_asset:
                    speed = 1.0
                    vo_duration = _get_asset_duration(voiceover_asset)
                    if vo_duration and vo_duration > target_duration:
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
                video_ref = _resolve_asset_ref(video_prompt, workspace_id)
                if video_ref:
                    # NOTE: Unified AssetServiceInterface adaptation.
                    # This would break legacy version due to function signature and method name mismatch.
                    video_asset = await asset_service.get_asset(video_ref)
                    if video_asset and getattr(video_asset, "mime_type", "").startswith(
                        "video/"
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
    music_ref = _resolve_asset_ref(
        storyboard.get("background_music_prompt", {}), workspace_id
    )
    if music_ref:
        # NOTE: Unified AssetServiceInterface adaptation.
        # This would break legacy version due to function signature and method name mismatch.
        music_asset = await asset_service.get_asset(music_ref)
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

    config = mediagent_kit.services.aio.get_config()
    if config.use_creative_studio:
        from mediagent_kit.services.types.common import (
            AudioPlacement,
            GeneratedAsset,
            ScopedVideoTimeline,
            TimelineAudioClip,
            TimelineVideoClip,
            Transition as ScopedTransition,
            TransitionType as ScopedTransitionType,
            Trim as ScopedTrim,
        )

        scoped_video_clips = []
        for vc in video_clips:
            ref = None
            if vc.asset and vc.asset.id:
                ref = AssetRef(
                    id=str(vc.asset.id),
                    asset_type=(
                        "generated"
                        if isinstance(vc.asset, GeneratedAsset)
                        else "uploaded"
                    ),
                    workspace_id=workspace_id,
                )

            ff_ref = None
            if vc.first_frame_asset and vc.first_frame_asset.id:
                ff_ref = AssetRef(
                    id=str(vc.first_frame_asset.id),
                    asset_type=(
                        "generated"
                        if isinstance(vc.first_frame_asset, GeneratedAsset)
                        else "uploaded"
                    ),
                    workspace_id=workspace_id,
                )

            lf_ref = None
            if vc.last_frame_asset and vc.last_frame_asset.id:
                lf_ref = AssetRef(
                    id=str(vc.last_frame_asset.id),
                    asset_type=(
                        "generated"
                        if isinstance(vc.last_frame_asset, GeneratedAsset)
                        else "uploaded"
                    ),
                    workspace_id=workspace_id,
                )

            trim_obj = None
            if vc.trim:
                trim_obj = ScopedTrim(
                    offset_seconds=vc.trim.offset_seconds,
                    duration_seconds=vc.trim.duration_seconds,
                )

            scoped_video_clips.append(
                TimelineVideoClip(
                    asset_ref=ref,
                    trim=trim_obj,
                    volume=vc.volume,
                    speed=vc.speed,
                    first_frame_asset_ref=ff_ref,
                    last_frame_asset_ref=lf_ref,
                    placeholder=vc.placeholder,
                )
            )

        # HERE insert error
        if not scoped_video_clips:
            logger.error("No valid video clips found for final video stitching.")
            return tool_failure(
                "Final video stitching failed: no valid video clips were generated for any scene."
            )

        scoped_audio_clips = []
        for ac in audio_clips:
            ref = None
            if ac.asset and ac.asset.id:
                ref = AssetRef(
                    id=str(ac.asset.id),
                    asset_type=(
                        "generated"
                        if isinstance(ac.asset, GeneratedAsset)
                        else "uploaded"
                    ),
                    workspace_id=workspace_id,
                )

            start_at_obj = AudioPlacement(
                video_clip_index=ac.start_at.video_clip_index,
                offset_seconds=ac.start_at.offset_seconds,
            )

            trim_obj = None
            if ac.trim:
                trim_obj = ScopedTrim(
                    offset_seconds=ac.trim.offset_seconds,
                    duration_seconds=ac.trim.duration_seconds,
                )

            scoped_audio_clips.append(
                TimelineAudioClip(
                    start_at=start_at_obj,
                    asset_ref=ref,
                    trim=trim_obj,
                    volume=ac.volume,
                    speed=ac.speed,
                    fade_in_duration_seconds=ac.fade_in_duration_seconds,
                    fade_out_duration_seconds=ac.fade_out_duration_seconds,
                    placeholder=ac.placeholder,
                )
            )

        scoped_transitions = []
        for t in transitions:
            if t:
                t_type_val = t.type.value if hasattr(t.type, "value") else str(t.type)
                scoped_transitions.append(
                    ScopedTransition(
                        type=ScopedTransitionType(t_type_val),
                        duration_seconds=t.duration_seconds,
                    )
                )
            else:
                scoped_transitions.append(
                    ScopedTransition(
                        type=ScopedTransitionType("none"),
                        duration_seconds=0.0,
                    )
                )

        scoped_tl = ScopedVideoTimeline(
            workspace_id=workspace_id,
            session_id=session_id,
            storyboard_id=current_sb_id,
            title=f"Ads-X Template Final Video {uid}",
            video_clips=scoped_video_clips,
            audio_clips=scoped_audio_clips,
            transitions=scoped_transitions,
        )

        timeline_service = mediagent_kit.services.aio.get_video_timeline_service()
        created_tl = await timeline_service.create_timeline(
            workspace_id=workspace_id,
            session_id=session_id,
            storyboard_id=current_sb_id,
            title=f"Ads-X Template Final Video {uid}",
            timeline=scoped_tl,
        )
        tl_id = created_tl.timeline_id or "1"
        stitched_asset = await timeline_service.stitch_timeline(
            timeline_id=tl_id,
            output_filename=f"final_video_{uid}.mp4",
        )
    else:
        # Canvas Logic (native path: legacy CanvasService keyed by user_id)
        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas = await canvas_service.create_canvas(
            user_id=workspace_id,
            title=timeline.title,
            video_timeline=timeline,
        )
        tool_context.state["video_timeline_canvas_id"] = canvas.id

        # Stitch the video (native path: legacy stitcher keyed by user_id)
        stitched_asset = await video_stitching_service.stitch_video(
            user_id=workspace_id,
            timeline=timeline,
            output_filename=f"final_video_{uid}.mp4",
        )

    tool_context.state["final_video_asset_id"] = stitched_asset.id
    tool_context.state["final_video_asset_ref"] = {
        "id": stitched_asset.id,
        "asset_type": "generated",
        "workspace_id": workspace_id,
    }

    display_result = await display_asset(
        tool_context=tool_context, asset_id=stitched_asset.id
    )
    if display_result.startswith("Error"):
        return tool_failure(display_result)

    import os

    if config.use_creative_studio:
        cs_frontend_url = (config.cs_frontend_url or "http://localhost:4200").rstrip(
            "/"
        )

        cs_workbench_link = f"{cs_frontend_url}/workbench?timelineId={tl_id}&storyboardId={current_sb_id}&sessionId={session_id}"
        cs_asset_link = f"{cs_frontend_url}/gallery/{stitched_asset.id}"

        success_message = (
            f"🎬 **Video Production & Timeline Stitching Complete!**\n\n"
            f"- 🎬 [Open Timeline in Creative Studio Workbench]({cs_workbench_link})\n"
            f"- 🖼️ [View Final Rendered Video Asset]({cs_asset_link})"
        )
        return tool_success(success_message)

    IZUMI_BASE_URL = os.environ.get("IZUMI_STUDIO_URL")
    if not IZUMI_BASE_URL:
        # Fallback to backend service URL if in Cloud Run, otherwise Local
        IZUMI_BASE_URL = os.environ.get(
            "CLOUD_RUN_SERVICE_URL", "http://localhost:5173"
        )
    izumi_deep_link = f"{IZUMI_BASE_URL}/studio/#/project/{workspace_id}/chat/{session_id}?contentTab=canvas&canvasId={canvas.id}"
    success_message = f"[View Video Timeline in Izumi Studio]({izumi_deep_link})"

    return tool_success(success_message)
