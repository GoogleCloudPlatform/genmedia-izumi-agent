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
import re
from typing import Any

from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import ValidationError

import mediagent_kit
from config import settings
from utils.adk import get_user_id_from_context

from .. import types as video_gen_types
from ..instructions import storyboard as storyboard_instruction

logger = logging.getLogger(__name__)


def _initialize_project(
    tool_context: ToolContext,
    user_idea: str,
    aspect_ratio: str,
    consistent_elements_str: str = "",
):
    """Saves the initial project configuration to the session state."""
    logger.info(f"Initializing project for: {user_idea}")

    tool_context.state["user_idea"] = user_idea
    tool_context.state["aspect_ratio"] = aspect_ratio

    if consistent_elements_str:
        tool_context.state["consistent_elements"] = json.loads(consistent_elements_str)
    else:
        tool_context.state["consistent_elements"] = []

    tool_context.state["generation_stage"] = "WRITING_STORYBOARD"


def _format_storyboard_for_display(storyboard_json: dict[str, Any]) -> str:
    """Formats a storyboard JSON object into a human-readable string."""
    lines = []
    voice_name = storyboard_json.get("voice_name", "N/A")
    voice_gender = storyboard_json.get("voice_gender", "N/A")
    lines.append(f"**Narration Voice:** {voice_name} ({voice_gender})")
    lines.append("")  # Add an empty line for spacing
    consistent_elements_map = {
        el["id"]: el for el in storyboard_json.get("consistent_elements", [])
    }

    if consistent_elements_map:
        lines.append("**Consistent Elements:**")
        for el in consistent_elements_map.values():
            lines.append(f"- **{el.get('id')} {el.get('name', '')}:**")
            lines.append(f"  - **Description:** {el.get('description', '')}")
            lines.append(f"  - **File Name:** {el.get('file_name', 'N/A')}")

    lines.append("\n**Video Clips:**")
    for clip in storyboard_json.get("video_clips", []):
        lines.append(
            f"\n**Clip {clip.get('clip_number')}:** ({clip.get('duration_seconds')}s)"
        )
        lines.append(f'*   **Description:** "{clip.get("description", "")}"')
        narration_value = clip.get("narration", "")
        formatted_narration = (
            f'"{narration_value}"' if narration_value != "None" else narration_value
        )
        lines.append(f"*   **Narration:** {formatted_narration}")

        element_details = []
        for el_id in clip.get("elements", []):
            element = consistent_elements_map.get(el_id)
            if element:
                element_details.append(
                    f"{element.get('name', el_id)} (file: {element.get('file_name', 'N/A')})"
                )
            else:
                element_details.append(el_id)

        if element_details:
            lines.append(f"*   **Elements:** {', '.join(element_details)}")
        else:
            lines.append("*   **Elements:** None")

    if storyboard_json.get("transitions"):
        lines.append("\n**Transitions:**")
        for i, transition in enumerate(storyboard_json["transitions"]):
            if transition:
                lines.append(
                    f"- **Between Clip {i + 1} and {i + 2}:** {transition.get('type')} ({transition.get('duration_seconds')}s)"
                )
            else:
                lines.append(f"- **Between Clip {i + 1} and {i + 2}:** No transition")

    if storyboard_json.get("background_music_clips"):
        lines.append("\n**Background Music:**")
        for i, music_clip in enumerate(storyboard_json["background_music_clips"]):
            start_at = music_clip.get("start_at", {})
            lines.append(
                f"- **Track {i + 1}:** Starts at clip {start_at.get('video_clip_index', 0) + 1}, offset {start_at.get('offset_seconds', 0)}s. ({music_clip.get('duration_seconds')}s)"
            )
            lines.append(f'  - **Prompt:** "{music_clip.get("prompt", "")}"')
            lines.append(
                f"  - **Fade In:** {music_clip.get('fade_in_seconds', 0)}s, **Fade Out:** {music_clip.get('fade_out_seconds', 0)}s"
            )

    return "\n".join(lines)


def _adjust_music_duration(
    storyboard_plan: video_gen_types.StoryboardPlan,
) -> video_gen_types.StoryboardPlan:
    """Adjusts the duration of the last music clip to match the video length."""
    if not storyboard_plan.background_music_clips:
        return storyboard_plan

    total_video_duration = storyboard_plan.calculate_total_duration()
    clip_start_times = storyboard_plan.get_clip_start_times()

    # Find the last music clip
    last_music_clip = None
    latest_start_time = -1.0

    for music_clip in storyboard_plan.background_music_clips:
        start_time = (
            clip_start_times[music_clip.start_at.video_clip_index]
            + music_clip.start_at.offset_seconds
        )
        if start_time > latest_start_time:
            latest_start_time = start_time
            last_music_clip = music_clip

    if last_music_clip:
        # Adjust duration
        new_duration = total_video_duration - latest_start_time
        if new_duration > 0:
            last_music_clip.duration_seconds = min(new_duration, 30)

    return storyboard_plan


async def create_storyboard(
    tool_context: ToolContext,
    *,
    user_idea: str = "",
    aspect_ratio: str = "",
    consistent_elements_str: str = "",
) -> str:
    """
    Initializes a project and/or generates/refines a storyboard using the Gemini model.

    If a `user_idea` is provided, it's used to initialize the project (if new)
    or to update the existing idea for refinement.
    """
    # Initialize project or update idea
    if user_idea:
        if "user_idea" not in tool_context.state:
            if not aspect_ratio:
                return json.dumps(
                    {
                        "status": "failure",
                        "error_message": "aspect_ratio is required to start a new project.",
                    }
                )
            _initialize_project(
                tool_context, user_idea, aspect_ratio, consistent_elements_str
            )
        else:
            # This is a subsequent call with a new idea/feedback, so update the state
            tool_context.state["user_idea"] = user_idea

    current_user_idea = tool_context.state.get("user_idea")
    if not current_user_idea:
        return json.dumps(
            {
                "status": "failure",
                "error_message": "User idea not found in state. Please provide a user_idea.",
            }
        )

    logger.info(f"Starting storyboard creation for: {current_user_idea}")

    project = settings.GOOGLE_CLOUD_PROJECT
    region = settings.GOOGLE_CLOUD_LOCATION
    client = genai.Client(vertexai=True, project=project, location=region)
    model = "gemini-2.5-pro"

    current_aspect_ratio = tool_context.state.get("aspect_ratio", "16:9")
    consistent_elements = tool_context.state.get("consistent_elements", [])
    previous_storyboard_plan = tool_context.state.get("storyboard_plan")

    # --- New Multimodal Logic ---
    image_parts = []
    prompt_addition = ""
    filenames_in_prompt = re.findall(
        r"\b\w+\.(?:png|jpg|jpeg|webp)\b", current_user_idea, re.IGNORECASE
    )

    if filenames_in_prompt:
        asset_service = mediagent_kit.services.aio.get_asset_service()
        user_id = get_user_id_from_context(tool_context)

        for filename in set(filenames_in_prompt):
            try:
                asset = await asset_service.get_asset_by_file_name(
                    user_id=user_id, file_name=filename
                )
                if asset:
                    asset_blob = await asset_service.get_asset_blob(asset_id=asset.id)
                    if asset_blob:
                        image_parts.append(
                            types.Part.from_bytes(
                                data=asset_blob.content, mime_type=asset_blob.mime_type
                            )
                        )
                        logger.info(
                            f"Found and loaded user asset '{filename}' to send to LLM."
                        )
            except Exception as e:
                logger.warning(
                    f"Could not load asset '{filename}' mentioned in prompt: {e}"
                )

        if image_parts:
            prompt_addition = (
                "\n\nYou have been provided with one or more images for user-provided assets. "
                "Use these images to understand the visual details of the characters or elements "
                "and reflect that understanding in your descriptions and prompts."
            )

    prompt_parts = [
        f"Aspect Ratio: {current_aspect_ratio}",
        f"Core Idea: {current_user_idea}",
    ]
    if prompt_addition:
        prompt_parts.append(prompt_addition)

    if consistent_elements:
        prompt_parts.append("\nHere are the consistent elements to use:")
        prompt_parts.append(json.dumps(consistent_elements))

    if previous_storyboard_plan:
        prompt_parts.append(
            "\nPlease revise the following storyboard based on the Core Idea provided above."
        )
        prompt_parts.append(
            f"\nHere is the previous storyboard JSON to revise:\n{json.dumps(previous_storyboard_plan)}"
        )

    full_prompt = "\n".join(prompt_parts)
    contents = [*image_parts, full_prompt]

    generation_config = types.GenerateContentConfig(
        system_instruction=storyboard_instruction.INSTRUCTION,
        temperature=1.0,
        response_mime_type="application/json",
    )

    logger.info(
        json.dumps(
            {
                "message": "Calling Gemini API for storyboard creation",
                "model": model,
                "prompt": full_prompt,
                "temperature": generation_config.temperature,
                "response_mime_type": generation_config.response_mime_type,
            }
        )
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=generation_config,
        )

        storyboard_json = json.loads(response.text)
        storyboard_plan = video_gen_types.StoryboardPlan(**storyboard_json)

        asset_service = mediagent_kit.services.aio.get_asset_service()
        user_id = get_user_id_from_context(tool_context)

        for element in storyboard_plan.consistent_elements:
            if element.is_user_provided and element.file_name and not element.asset_id:
                try:
                    asset = await asset_service.get_asset_by_file_name(
                        user_id=user_id, file_name=element.file_name
                    )
                    if asset:
                        element.asset_id = asset.id
                        logger.info(
                            f"Resolved user-provided asset '{element.file_name}' to asset_id '{asset.id}'."
                        )
                    else:
                        logger.warning(
                            f"Could not find user-provided asset with filename: '{element.file_name}'"
                        )
                except Exception as e:
                    logger.error(
                        f"Error resolving asset for filename {element.file_name}: {e}"
                    )

        storyboard_plan = _adjust_music_duration(storyboard_plan)

        tool_context.state["storyboard_plan"] = storyboard_plan.model_dump()

        tool_context.state["generation_stage"] = "STORYBOARD_REVIEW"

        if storyboard_plan.consistent_elements:
            existing_element_ids = {el.get("id") for el in consistent_elements}
            new_elements = [
                el.model_dump()
                for el in storyboard_plan.consistent_elements
                if el.id not in existing_element_ids
            ]
            if new_elements:
                tool_context.state["consistent_elements"] = (
                    consistent_elements + new_elements
                )

        storyboard_text_for_display = _format_storyboard_for_display(storyboard_json)
        tool_context.state["storyboard_text"] = storyboard_text_for_display

        logger.info("Successfully generated and parsed storyboard.")
        return json.dumps(
            {"status": "success", "storyboard_text": storyboard_text_for_display}
        )

    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse storyboard from LLM response: {e}")
        return json.dumps({"status": "failure", "error_message": str(e)})
    except Exception as e:
        logger.error(f"Failed to generate storyboard: {e}")
        return json.dumps({"status": "failure", "error_message": str(e)})
