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

import json
import logging

from google.adk.tools import ToolContext

import mediagent_kit
from utils.adk import get_user_id_from_context

logger = logging.getLogger(__name__)


async def stitch_final_video(tool_context: ToolContext) -> str:
    """
    Stitches video and audio assets into a final video.
    The output filename is derived from the video timeline's title.
    """
    logger.info("Handing off to VideoStitchingService.")

    try:
        canvas_id = tool_context.state.get("video_timeline_canvas_id")
        if not canvas_id:
            raise ValueError("video_timeline_canvas_id not found in state.")

        canvas_service = mediagent_kit.services.aio.get_canvas_service()
        canvas = await canvas_service.get_canvas(canvas_id)
        if not canvas or not canvas.video_timeline:
            raise ValueError(
                f"Canvas with id {canvas_id} not found or has no timeline."
            )

        video_timeline = canvas.video_timeline
        user_id = get_user_id_from_context(tool_context)

        # Sanitize the title to create a valid filename.
        safe_title = "".join(
            c for c in video_timeline.title if c.isalnum() or c in (" ", "_")
        ).rstrip()
        output_filename = f"{safe_title.replace(' ', '_')}.mp4"

        stitching_service = mediagent_kit.services.aio.get_video_stitching_service()
        final_asset = await stitching_service.stitch_video(
            user_id=user_id, timeline=video_timeline, output_filename=output_filename
        )

        tool_context.state["final_video_asset"] = final_asset.to_firestore()
        tool_context.state["generation_stage"] = "STITCHING_VIDEO"
        logger.info(
            f"Successfully stitched and saved final video as {final_asset.file_name}"
        )

        return json.dumps(
            {"status": "success", "final_asset_name": final_asset.file_name}
        )

    except Exception as e:
        logger.error(f"Stitching failed: {e}", exc_info=True)
        return json.dumps({"status": "failure", "error_message": str(e)})
