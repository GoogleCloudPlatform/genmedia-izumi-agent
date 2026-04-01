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

import asyncio
import json
import logging

from google.adk.tools import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context
from mediagent_kit.services import types as asset_types
from mediagent_kit.services.media_generation_service import MediaGenerationService

from .. import types as video_gen_types

logger = logging.getLogger(__name__)


async def _generate_consistent_element_image(
    media_generation_service: MediaGenerationService,
    user_id: str,
    element: dict,
    aspect_ratio: str,
) -> dict:
    """Generates an image for a consistent element."""
    prompt = element.get("image_prompt")
    element_id = element.get("id")
    file_name = element.get("file_name")
    if not prompt or not element_id or not file_name:
        raise ValueError(
            f"Consistent element is missing id, prompt, or file_name: {element}"
        )

    logger.info(
        f"Generating image for consistent element '{element_id}' with prompt: '{prompt}'"
    )

    asset = await media_generation_service.generate_image_with_gemini(
        user_id=user_id,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        file_name=file_name,
        reference_image_filenames=[],  # No reference for the base element
    )

    if not asset:
        raise Exception(f"Image generation failed for consistent element {element_id}")

    logger.info(
        f"Successfully generated image asset for consistent element {element_id}: {asset.file_name}"
    )
    updated_element = element.copy()
    updated_element["asset_id"] = asset.id
    return updated_element


async def _generate_single_image(
    media_generation_service: MediaGenerationService,
    user_id,
    clip_plan: video_gen_types.VideoClipPlan,
    aspect_ratio,
    consistent_elements_map,
):
    """Generates a single image for a clip using MediaGenerationService."""
    prompt_text = clip_plan.image_prompt
    reference_image_filenames = []
    asset_service = mediagent_kit.services.aio.get_asset_service()

    # Find and append consistent element assets
    reference_names = []
    for element_id in clip_plan.elements:
        element = consistent_elements_map.get(element_id)
        if element and element.get("asset_id"):
            asset = await asset_service.get_asset_by_id(element["asset_id"])
            if asset:
                reference_image_filenames.append(asset.file_name)
                reference_names.append(element.get("name", element_id))

    # Add reference information to the prompt
    if reference_names:
        prompt_text += "\n\n---"
        prompt_text += "\nREFERENCE INSTRUCTIONS:"
        for name in reference_names:
            prompt_text += f"\nFor the character/element '{name}', use the provided reference image."

    file_name = clip_plan.image_file_name
    if not file_name:
        raise ValueError(
            f"Clip plan for clip {clip_plan.clip_number} is missing image_file_name."
        )

    logger.info(
        json.dumps(
            {
                "message": "Calling MediaGenerationService for image generation",
                "clip_number": clip_plan.clip_number,
                "prompt": prompt_text,
                "aspect_ratio": aspect_ratio,
                "referenced_elements": clip_plan.elements,
            }
        )
    )

    asset = await media_generation_service.generate_image_with_gemini(
        user_id=user_id,
        prompt=prompt_text,
        aspect_ratio=aspect_ratio,
        file_name=file_name,
        reference_image_filenames=reference_image_filenames,
    )

    if not asset:
        raise Exception(f"Image generation failed for clip {clip_plan.clip_number}")

    logger.info(
        f"Successfully generated image asset for clip {clip_plan.clip_number}: {asset.file_name}"
    )
    return clip_plan.clip_number, asset


async def generate_images_for_storyboard(tool_context: ToolContext) -> str:
    """
    Generates consistent element images first, then generates images for all clips
    in a storyboard in parallel.
    """
    logger.info("Starting image generation for storyboard.")
    try:
        storyboard_plan_dict = tool_context.state.get("storyboard_plan")
        if not storyboard_plan_dict:
            raise ValueError("storyboard_plan not found in state.")
        storyboard_plan = video_gen_types.StoryboardPlan(**storyboard_plan_dict)

        aspect_ratio = tool_context.state["aspect_ratio"]
        consistent_elements = tool_context.state.get("consistent_elements", [])
        user_id = get_user_id_from_context(tool_context)

        media_generation_service = (
            mediagent_kit.services.aio.get_media_generation_service()
        )

        # Generate consistent element images first
        logger.info("Generating consistent element images.")
        consistent_elements_map = {el["id"]: el for el in consistent_elements}

        consistent_element_tasks = [
            _generate_consistent_element_image(
                media_generation_service,
                user_id,
                element,
                aspect_ratio,
            )
            for element in consistent_elements
            if not element.get("is_user_provided") and element.get("image_prompt")
        ]

        if consistent_element_tasks:
            updated_elements_results = await asyncio.gather(
                *consistent_element_tasks, return_exceptions=True
            )
            for result in updated_elements_results:
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to generate a consistent element image: {result}"
                    )
                else:
                    consistent_elements_map[result["id"]] = result
            tool_context.state["consistent_elements"] = list(
                consistent_elements_map.values()
            )
        logger.info("Finished generating consistent element images.")

        # Now generate clip images using the consistent elements
        tasks = [
            _generate_single_image(
                media_generation_service,
                user_id,
                clip_plan,
                aspect_ratio,
                consistent_elements_map,
            )
            for clip_plan in storyboard_plan.video_clips
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        generated_assets = {}
        failed_clips = []
        for i, result in enumerate(results):
            clip_plan = storyboard_plan.video_clips[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to generate image for a clip: {result}")
                failed_clips.append(clip_plan.clip_number)
            else:
                clip_num, asset = result
                generated_assets[clip_num] = asset

        # Create asset_types objects from the plan
        video_clips = []
        for clip_plan in storyboard_plan.video_clips:
            image_asset = generated_assets.get(clip_plan.clip_number)
            placeholder_text = None
            if not image_asset:
                placeholder_text = (
                    f"Image generation failed for prompt: {clip_plan.image_prompt}"
                )

            duration_seconds = clip_plan.duration_seconds or 5.0

            clip = asset_types.VideoClip(
                asset=None,
                trim=asset_types.Trim(duration_seconds=duration_seconds),
                first_frame_asset=image_asset,
                placeholder=placeholder_text,
            )
            video_clips.append(clip)

        transitions = []
        if storyboard_plan.transitions:
            for t_plan in storyboard_plan.transitions:
                if t_plan:
                    try:
                        transition_type = asset_types.TransitionType(t_plan.type)
                        transitions.append(
                            asset_types.Transition(
                                type=transition_type,
                                duration_seconds=t_plan.duration_seconds,
                            )
                        )
                    except ValueError:
                        transitions.append(None)
                else:
                    transitions.append(None)

        transition_in = None
        if storyboard_plan.transition_in:
            transition_in = asset_types.Transition(
                type=asset_types.TransitionType(storyboard_plan.transition_in.type),
                duration_seconds=storyboard_plan.transition_in.duration_seconds,
            )

        transition_out = None
        if storyboard_plan.transition_out:
            transition_out = asset_types.Transition(
                type=asset_types.TransitionType(storyboard_plan.transition_out.type),
                duration_seconds=storyboard_plan.transition_out.duration_seconds,
            )

        video_timeline_obj = asset_types.VideoTimeline(
            title=storyboard_plan.title,
            video_clips=video_clips,
            transitions=transitions,
            transition_in=transition_in,
            transition_out=transition_out,
        )

        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas = await canvas_service.create_canvas(
            user_id=user_id,
            title=video_timeline_obj.title,
            video_timeline=video_timeline_obj,
        )
        tool_context.state["video_timeline_canvas_id"] = canvas.id
        tool_context.state["generation_stage"] = "IMAGES_REVIEW"

        logger.info("Finished image generation for storyboard.")
        return json.dumps(
            {
                "status": "success",
                "message": "Image generation complete.",
                "failed_clips": failed_clips,
            }
        )

    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        return json.dumps({"status": "failure", "error_message": str(e)})


async def _generate_single_video(
    media_generation_service: MediaGenerationService,
    user_id,
    clip_plan: video_gen_types.VideoClipPlan,
    image_asset: asset_types.Asset,
    aspect_ratio,
):
    """Generates a single video for a clip using MediaGenerationService."""
    if not image_asset:
        raise ValueError(f"Clip {clip_plan.clip_number} is missing an image_asset")

    model_name = "veo-3.1-generate-001"
    file_name = clip_plan.video_file_name
    if not file_name:
        raise ValueError(
            f"Clip plan for clip {clip_plan.clip_number} is missing video_file_name."
        )

    logger.info(
        json.dumps(
            {
                "message": "Calling MediaGenerationService for video generation",
                "model": model_name,
                "clip_number": clip_plan.clip_number,
                "prompt": clip_plan.video_prompt,
                "reference_image": image_asset.file_name,
            }
        )
    )

    requested_duration = clip_plan.duration_seconds
    veo_supported_durations = [4, 6, 8]
    generation_duration = 8  # default to longest
    for d in sorted(veo_supported_durations):
        if d >= requested_duration:
            generation_duration = d
            break

    asset = await media_generation_service.generate_video_with_veo(
        user_id=user_id,
        prompt=clip_plan.video_prompt,
        file_name=file_name,
        model=model_name,
        first_frame_filename=image_asset.file_name,
        last_frame_filename=None,
        aspect_ratio=aspect_ratio,
        duration_seconds=generation_duration,
        resolution="720p",
        generate_audio=False,
    )

    if not asset:
        raise Exception(f"Video generation failed for clip {clip_plan.clip_number}")

    logger.info(
        f"Successfully generated video asset for clip {clip_plan.clip_number}: {asset.file_name}"
    )
    return clip_plan.clip_number, asset


async def _generate_single_speech(
    media_generation_service: MediaGenerationService,
    user_id,
    clip_plan: video_gen_types.VideoClipPlan,
    voice_name: str,
):
    """Generates a single speech audio file for a clip's narration using MediaGenerationService."""
    narration = clip_plan.narration
    if not narration:
        return None

    model_name = "gemini-2.5-flash-tts"
    file_name = clip_plan.speech_file_name
    if not file_name:
        raise ValueError(
            f"Clip plan for clip {clip_plan.clip_number} has narration but is missing speech_file_name."
        )

    logger.info(
        json.dumps(
            {
                "message": "Calling MediaGenerationService for speech generation",
                "model": model_name,
                "voice": voice_name,
                "clip_number": clip_plan.clip_number,
                "text": narration,
            }
        )
    )

    asset = await media_generation_service.generate_speech_single_speaker(
        user_id=user_id,
        prompt="",
        text=narration,
        model=model_name,
        voice_name=voice_name,
        file_name=file_name,
    )

    if not asset:
        raise Exception(f"Speech generation failed for clip {clip_plan.clip_number}")

    logger.info(
        f"Successfully generated speech asset for clip {clip_plan.clip_number}: {asset.file_name}"
    )
    return clip_plan.clip_number, asset


async def _generate_single_music(
    media_generation_service: MediaGenerationService,
    user_id: str,
    music_plan: video_gen_types.BackgroundMusicClipPlan,
) -> tuple[video_gen_types.BackgroundMusicClipPlan, asset_types.Asset]:
    """Generates a single music clip."""
    logger.info(f"Generating music with prompt: '{music_plan.prompt}'")

    asset = await media_generation_service.generate_music_with_lyria(
        user_id=user_id,
        prompt=music_plan.prompt,
        file_name=music_plan.file_name,
        model="lyria-002",
    )

    if not asset:
        raise Exception(f"Music generation failed for prompt: {music_plan.prompt}")

    logger.info(f"Successfully generated music asset: {asset.file_name}")
    return music_plan, asset


async def generate_videos_and_speech_for_storyboard(tool_context: ToolContext) -> str:
    """
    Generates videos and speech for all clips in a storyboard in parallel.
    """
    logger.info("Starting video and speech generation for storyboard.")
    try:
        canvas_id = tool_context.state.get("video_timeline_canvas_id")
        if not canvas_id:
            raise ValueError("video_timeline_canvas_id not found in state.")

        storyboard_plan_dict = tool_context.state.get("storyboard_plan")
        if not storyboard_plan_dict:
            raise ValueError("storyboard_plan not found in state.")
        storyboard_plan = video_gen_types.StoryboardPlan(**storyboard_plan_dict)
        voice_name = storyboard_plan.voice_name

        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas = await canvas_service.get_canvas(canvas_id)
        if not canvas or not canvas.video_timeline:
            raise ValueError(f"Canvas with id {canvas_id} not found.")

        video_timeline = canvas.video_timeline
        aspect_ratio = tool_context.state["aspect_ratio"]
        user_id = get_user_id_from_context(tool_context)

        media_generation_service = (
            mediagent_kit.services.aio.get_media_generation_service()
        )

        tasks = {}
        for i, (clip_plan, video_clip) in enumerate(
            zip(storyboard_plan.video_clips, video_timeline.video_clips, strict=False)
        ):
            clip_id = f"clip_{i}"

            if video_clip.first_frame_asset:
                logger.info(f"Queueing video generation for {clip_id}")
                tasks[f"{clip_id}_video"] = _generate_single_video(
                    media_generation_service,
                    user_id,
                    clip_plan,
                    video_clip.first_frame_asset,
                    aspect_ratio,
                )
            else:
                logger.warning(
                    f"Skipping video generation for {clip_id} because first_frame_asset is missing."
                )

            if clip_plan.narration:
                logger.info(f"Queueing speech generation for {clip_id}")
                tasks[f"{clip_id}_speech"] = _generate_single_speech(
                    media_generation_service,
                    user_id,
                    clip_plan,
                    voice_name,
                )

        for i, music_plan in enumerate(storyboard_plan.background_music_clips):
            music_id = f"music_{i}"
            logger.info(f"Queueing music generation for {music_id}")
            tasks[music_id] = _generate_single_music(
                media_generation_service,
                user_id,
                music_plan,
            )

        if not tasks:
            return json.dumps(
                {"status": "success", "message": "No video or speech tasks to run."}
            )

        task_coroutines = tasks.values()
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        results_map = dict(zip(tasks.keys(), results, strict=False))

        failed_clips = {"video": [], "speech": []}
        audio_clips = video_timeline.audio_clips or []
        for i, (clip_plan, video_clip) in enumerate(
            zip(storyboard_plan.video_clips, video_timeline.video_clips, strict=False)
        ):
            clip_id = f"clip_{i}"

            video_res = results_map.get(f"{clip_id}_video")
            if video_res:
                if isinstance(video_res, Exception):
                    logger.error(
                        f"Failed to generate video for clip {i}",
                        exc_info=video_res,
                    )
                    video_clip.placeholder = (
                        f"Video generation failed: {clip_plan.video_prompt}"
                    )
                    failed_clips["video"].append(clip_plan.clip_number)
                else:
                    _, asset = video_res
                    video_clip.asset = asset

            speech_res = results_map.get(f"{clip_id}_speech")
            if speech_res:
                if isinstance(speech_res, Exception):
                    logger.error(
                        f"Failed to generate speech for clip {i}",
                        exc_info=speech_res,
                    )
                    audio_clips.append(
                        asset_types.AudioClip(
                            asset=None,
                            start_at=asset_types.AudioPlacement(
                                video_clip_index=i, offset_seconds=0
                            ),
                            trim=asset_types.Trim(
                                duration_seconds=clip_plan.duration_seconds or 5.0
                            ),
                            placeholder=f"Speech generation failed for: {clip_plan.narration}",
                        )
                    )
                    failed_clips["speech"].append(clip_plan.clip_number)
                else:
                    _, asset = speech_res
                    audio_duration = clip_plan.duration_seconds or 5.0
                    audio_clips.append(
                        asset_types.AudioClip(
                            asset=asset,
                            start_at=asset_types.AudioPlacement(
                                video_clip_index=i, offset_seconds=0
                            ),
                            trim=asset_types.Trim(duration_seconds=audio_duration),
                        )
                    )

        for i in range(len(storyboard_plan.background_music_clips)):
            music_id = f"music_{i}"
            music_res = results_map.get(music_id)
            if music_res:
                if isinstance(music_res, Exception):
                    logger.error(
                        f"Failed to generate music clip {i}",
                        exc_info=music_res,
                    )
                    # TODO: Add placeholder for failed music
                else:
                    music_plan, asset = music_res
                    audio_clips.append(
                        asset_types.AudioClip(
                            asset=asset,
                            start_at=asset_types.AudioPlacement(
                                video_clip_index=music_plan.start_at.video_clip_index,
                                offset_seconds=music_plan.start_at.offset_seconds,
                            ),
                            trim=asset_types.Trim(
                                duration_seconds=music_plan.duration_seconds
                            ),
                            fade_in_duration_seconds=music_plan.fade_in_seconds,
                            fade_out_duration_seconds=music_plan.fade_out_seconds,
                        )
                    )

        video_timeline.audio_clips = audio_clips
        await canvas_service.update_canvas(canvas_id, video_timeline=video_timeline)
        tool_context.state["generation_stage"] = "VIDEO_SPEECH_REVIEW"

        logger.info("Finished video and speech generation.")
        return json.dumps(
            {
                "status": "success",
                "message": "Video and speech generation complete.",
                "failed_clips": failed_clips,
            }
        )

    except Exception as e:
        logger.error(f"Video/speech generation failed: {e}", exc_info=True)
        return json.dumps({"status": "failure", "error_message": str(e)})


async def regenerate_assets(
    tool_context: ToolContext,
    clip_numbers: list[int],
    asset_types: list[str],
) -> str:
    """
    Regenerates specific assets for given clip numbers.

    Args:
        tool_context: The tool context.
        clip_numbers: A list of clip numbers to regenerate assets for.
        asset_types: A list of asset types to regenerate, e.g., ["image", "video", "speech"].
    """
    logger.info(f"Regenerating assets for clips {clip_numbers}, types {asset_types}")
    try:
        canvas_id = tool_context.state.get("video_timeline_canvas_id")
        if not canvas_id:
            raise ValueError("video_timeline_canvas_id not found in state.")

        storyboard_plan_dict = tool_context.state.get("storyboard_plan")
        if not storyboard_plan_dict:
            raise ValueError("storyboard_plan not found in state.")
        storyboard_plan = video_gen_types.StoryboardPlan(**storyboard_plan_dict)
        voice_name = storyboard_plan.voice_name

        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas = await canvas_service.get_canvas(canvas_id)
        if not canvas or not canvas.video_timeline:
            raise ValueError(f"Canvas with id {canvas_id} not found.")

        video_timeline = canvas.video_timeline
        aspect_ratio = tool_context.state["aspect_ratio"]
        user_id = get_user_id_from_context(tool_context)
        media_generation_service = (
            mediagent_kit.services.aio.get_media_generation_service()
        )
        consistent_elements = tool_context.state.get("consistent_elements", [])
        consistent_elements_map = {el["id"]: el for el in consistent_elements}

        tasks = {}
        for clip_num in clip_numbers:
            clip_plan = next(
                (c for c in storyboard_plan.video_clips if c.clip_number == clip_num),
                None,
            )
            if not clip_plan:
                logger.warning(f"Clip plan for clip number {clip_num} not found.")
                continue

            video_clip = video_timeline.video_clips[clip_num - 1]

            for asset_type in asset_types:
                task_id = f"clip_{clip_num}_{asset_type}"
                if asset_type == "image":
                    tasks[task_id] = _generate_single_image(
                        media_generation_service,
                        user_id,
                        clip_plan,
                        aspect_ratio,
                        consistent_elements_map,
                    )
                elif asset_type == "video":
                    if video_clip.first_frame_asset:
                        tasks[task_id] = _generate_single_video(
                            media_generation_service,
                            user_id,
                            clip_plan,
                            video_clip.first_frame_asset,
                            aspect_ratio,
                        )
                    else:
                        logger.warning(
                            f"Skipping video regeneration for clip {clip_num} due to missing image asset."
                        )
                elif asset_type == "speech":
                    if clip_plan.narration:
                        tasks[task_id] = _generate_single_speech(
                            media_generation_service,
                            user_id,
                            clip_plan,
                            voice_name,
                        )

        if not tasks:
            return json.dumps(
                {"status": "success", "message": "No assets to regenerate."}
            )

        task_coroutines = tasks.values()
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        results_map = dict(zip(tasks.keys(), results, strict=False))

        for task_id, result in results_map.items():
            _, clip_num_str, asset_type = task_id.split("_")
            clip_num = int(clip_num_str)
            video_clip = video_timeline.video_clips[clip_num - 1]

            if isinstance(result, Exception):
                logger.error(
                    f"Failed to regenerate {asset_type} for clip {clip_num}",
                    exc_info=result,
                )
                if asset_type == "image":
                    video_clip.placeholder = "Image regeneration failed."
                elif asset_type == "video":
                    video_clip.placeholder = "Video regeneration failed."
            else:
                _, asset = result
                if asset_type == "image":
                    video_clip.first_frame_asset = asset
                    video_clip.placeholder = None
                elif asset_type == "video":
                    video_clip.asset = asset
                    video_clip.placeholder = None
                elif asset_type == "speech":
                    # Find the corresponding audio clip and update it
                    for i, audio_clip in enumerate(video_timeline.audio_clips):
                        if audio_clip.start_at.video_clip_index == (
                            clip_num - 1
                        ) and "Speech generation failed" in (
                            audio_clip.placeholder or ""
                        ):
                            video_timeline.audio_clips[i].asset = asset
                            video_timeline.audio_clips[i].placeholder = None
                            break

        await canvas_service.update_canvas(canvas_id, video_timeline=video_timeline)

        return json.dumps(
            {
                "status": "success",
                "message": f"Asset regeneration complete for clips {clip_numbers}.",
            }
        )

    except Exception as e:
        logger.error(f"Asset regeneration failed: {e}", exc_info=True)
        return json.dumps({"status": "failure", "error_message": str(e)})
