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

"""Tool to generate an HTML Campaign Summary Canvas."""

import json
import mediagent_kit
from mediagent_kit.services import types
from google.adk.tools import ToolContext
from utils.adk import get_user_id_from_context
from ...utils.common import common_utils
from ...utils.storyboard import template_library

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Basic CSS for the report
CSS = """
<style>
    body { font-family: 'Google Sans', sans-serif; background: #f8f9fa; color: #3c4043; padding: 20px; }
    h1 { color: #1a73e8; }
    .section { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3); }
    .section-title { font-size: 1.2em; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    .scene-card { display: flex; gap: 20px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #fff; }
    .col { flex: 1; display: flex; flex-direction: column; gap: 10px; }
    .col-header { font-weight: bold; color: #5f6368; text-transform: uppercase; font-size: 0.8em; margin-bottom: 5px; }
    .prompt-box { background: #f1f3f4; padding: 10px; border-radius: 4px; font-size: 0.9em; }
    .prompt-box.enriched { background: #e8f0fe; border-left: 3px solid #1a73e8; }
    .prompt-label { font-weight: bold; font-size: 0.8em; color: #5f6368; margin-bottom: 3px; }
    .prompt-value { white-space: pre-wrap; }
    video, img, audio { max-width: 100%; border-radius: 4px; border: 1px solid #ddd; }
    .final-video { max-width: 800px; margin: 0 auto; display: block; }
    pre { white-space: pre-wrap; margin: 0; }
</style>
"""


async def create_campaign_summary(tool_context: ToolContext) -> ToolResult:
    """Generates a visual HTML summary of the campaign and saves it as a Canvas."""
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        "⭐⭐⭐ [NATIVE TOOL INVOCATION] `create_campaign_summary` WAS SUCCESSFULLY TRIGGERED ⭐⭐⭐"
    )
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not storyboard:
        return tool_failure("No storyboard found in state.")

    user_id = get_user_id_from_context(tool_context)
    asset_service = mediagent_kit.services.aio.get_asset_service()
    canvas_service = mediagent_kit.services.aio.get_canvas_service()

    # Get Template Definition
    template_name = storyboard.get("template_name", "Custom")
    template_def = None
    if template_name and template_name != "Custom":
        template_def = template_library.get_template_by_name(template_name)

    # Helper to resolve asset ID to filename (for asset:// URI)
    async def get_filename(asset_id):
        if not asset_id:
            return None
        try:
            asset = await asset_service.get_asset_by_id(asset_id)
            return asset.file_name if asset else None
        except:
            return None

    # Helper to fetch text content from asset ID
    async def get_text_content(asset_id):
        if not asset_id:
            return None
        try:
            blob = await asset_service.get_asset_blob(asset_id)
            return blob.content.decode("utf-8")
        except:
            return None

    # --- Build HTML ---
    html_parts = [
        "<html><head>",
        CSS,
        "</head><body>",
        f"<h1>Campaign Summary: {template_name}</h1>",
    ]

    # 1. Global Settings
    parameters = tool_context.state.get(common_utils.PARAMETERS_KEY, {})
    user_brief = parameters.get("campaign_brief", "Not captured")
    bg_music_prompt = storyboard.get("background_music_prompt", {})
    bg_music_id = bg_music_prompt.get("asset_id")
    bg_music_filename = await get_filename(bg_music_id)

    html_parts.append(
        '<div class="section"><div class="section-title">Global Settings</div>'
    )

    # User Brief
    html_parts.append(
        f'<div class="prompt-box"><div class="prompt-label">User Campaign Brief</div>'
        f'<div class="prompt-value">{user_brief}</div></div>'
    )

    # Template Metadata
    if template_def:
        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">Description</div><div class="prompt-value">{template_def.description}</div></div>'
            f'<div class="prompt-box"><div class="prompt-label">Brand Personality</div><div class="prompt-value">{", ".join(template_def.brand_personality)}</div></div>'
            f'<div class="prompt-box"><div class="prompt-label">Music Keywords</div><div class="prompt-value">{", ".join(template_def.music_keywords)}</div></div>'
        )

    html_parts.append(
        f'<div class="prompt-box"><div class="prompt-label">Background Music Prompt</div>'
        f'<div class="prompt-value">{bg_music_prompt.get("description", "None")}</div></div>'
    )
    if bg_music_filename:
        html_parts.append(
            f'<div style="margin-top:10px"><audio controls src="asset://{bg_music_filename}"></audio></div>'
        )
    html_parts.append("</div>")

    # 2. Scenes
    html_parts.append(
        '<div class="section"><div class="section-title">Storyboard Scenes</div>'
    )

    for i, scene in enumerate(storyboard.get("scenes", [])):
        # IDs for Media
        vid_id = scene.get("video_prompt", {}).get("asset_id")
        img_id = scene.get("first_frame_prompt", {}).get("asset_id")
        aud_id = scene.get("voiceover_prompt", {}).get("asset_id")

        # IDs for Enrichment Text
        enrich_vid_id = scene.get("video_prompt", {}).get("enrichment_asset_id")
        enrich_img_id = scene.get("first_frame_prompt", {}).get("enrichment_asset_id")

        # Fetch Data
        vid_file = await get_filename(vid_id)
        img_file = await get_filename(img_id)
        aud_file = await get_filename(aud_id)

        enrich_vid = await get_text_content(enrich_vid_id)
        enrich_img = await get_text_content(enrich_img_id)

        # Template Guidance
        template_scene = None
        if template_def and i < len(template_def.scene_structure):
            template_scene = template_def.scene_structure[i]

        html_parts.append(f'<div class="scene-card">')

        # Col 1: The Plan & Template
        html_parts.append(
            f'<div class="col"><div class="col-header">Scene {i + 1}: {scene.get("topic", "Untitled")}</div>'
        )

        if template_scene:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">Template Requirement (Source)</div>'
                f'<div class="prompt-value">{template_scene.asset_guidance}</div></div>'
            )

        # Final Cinematography (What the agent actually used)
        final_cine = scene.get("video_prompt", {}).get("cinematography", {})
        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">Final Cinematography</div>'
            f'<div class="prompt-value"><pre>{json.dumps(final_cine, indent=2)}</pre></div></div>'
        )

        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">Voiceover Script</div>'
            f'<div class="prompt-value">"{scene.get("voiceover_prompt", {}).get("text", "")}"</div></div>'
            f"</div>"
        )

        # Col 2: Prompts (Base vs Enriched)
        html_parts.append('<div class="col"><div class="col-header">Prompts</div>')

        # Video Prompt
        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">Hydrated Guidance (Agent Output)</div><div class="prompt-value">{scene.get("video_prompt", {}).get("description", "")}</div></div>'
        )
        if enrich_vid:
            html_parts.append(
                f'<div class="prompt-box enriched"><div class="prompt-label">Enriched Video Prompt</div><div class="prompt-value">{enrich_vid}</div></div>'
            )
        else:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">Enriched Video Prompt</div><div class="prompt-value">Not found</div></div>'
            )

        # Image Prompt
        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">Base Image Prompt</div><div class="prompt-value">{scene.get("first_frame_prompt", {}).get("description", "")}</div></div>'
        )
        if enrich_img:
            html_parts.append(
                f'<div class="prompt-box enriched"><div class="prompt-label">Enriched Image Prompt</div><div class="prompt-value">{enrich_img}</div></div>'
            )

        html_parts.append("</div>")

        # Col 3: The Result
        html_parts.append(
            '<div class="col"><div class="col-header">Generated Assets</div>'
        )

        if vid_file:
            html_parts.append(
                f'<div class="prompt-label">Video</div><video controls src="asset://{vid_file}"></video>'
            )
        else:
            html_parts.append('<div class="prompt-box">No Video</div>')

        if img_file:
            html_parts.append(
                f'<div class="prompt-label">First Frame</div><img src="asset://{img_file}">'
            )

        if aud_file:
            html_parts.append(
                f'<div class="prompt-label">Voiceover</div><audio controls src="asset://{aud_file}"></audio>'
            )

        html_parts.append("</div></div>")  # End col, end card

    html_parts.append("</div>")  # End section

    # 3. Final Video
    if final_asset_id := tool_context.state.get("final_video_asset_id"):
        final_file = await get_filename(final_asset_id)
        if final_file:
            html_parts.append(
                f'<div class="section"><div class="section-title">Final Output</div>'
                f'<video controls src="asset://{final_file}" class="final-video"></video></div>'
            )

    html_parts.append("</body></html>")
    full_html = "".join(html_parts)

    # Collect IDs for permission (using all asset references)
    all_asset_ids = []
    if bg_music_id:
        all_asset_ids.append(bg_music_id)
    for s in storyboard.get("scenes", []):
        if vid := s.get("video_prompt", {}).get("asset_id"):
            all_asset_ids.append(vid)
        if img := s.get("first_frame_prompt", {}).get("asset_id"):
            all_asset_ids.append(img)
        if aud := s.get("voiceover_prompt", {}).get("asset_id"):
            all_asset_ids.append(aud)
        if evid := s.get("video_prompt", {}).get("enrichment_asset_id"):
            all_asset_ids.append(evid)
        if eimg := s.get("first_frame_prompt", {}).get("enrichment_asset_id"):
            all_asset_ids.append(eimg)

    if final_asset_id := tool_context.state.get("final_video_asset_id"):
        all_asset_ids.append(final_asset_id)

    html_obj = types.Html(content=full_html, asset_ids=all_asset_ids)

    canvas = await canvas_service.create_canvas(
        user_id=user_id, title=f"Campaign Summary - {template_name}", html=html_obj
    )

    tool_context.state["summary_canvas_id"] = canvas.id

    # Construct Deep Link
    from utils.adk import get_session_id_from_context

    session_id = get_session_id_from_context(tool_context)

    # TODO: Replace with the actual deployment URL of your Izumi UI
    import os

    IZUMI_BASE_URL = os.environ.get("IZUMI_STUDIO_URL")
    if not IZUMI_BASE_URL:
        # Fallback to backend service URL if in Cloud Run, otherwise Local
        IZUMI_BASE_URL = os.environ.get(
            "CLOUD_RUN_SERVICE_URL", "http://localhost:5173"
        )

    izumi_deep_link = f"{IZUMI_BASE_URL}/studio/#/project/{user_id}/chat/{session_id}?contentTab=canvas&canvasId={canvas.id}"

    # Return ONLY the link for cleaner composition
    return tool_success(f"[View Campaign Summary in Izumi Studio]({izumi_deep_link})")
