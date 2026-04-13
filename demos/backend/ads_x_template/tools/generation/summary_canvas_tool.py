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
from typing import Any
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
    :root {
        --primary: #1a73e8;
        --primary-light: #e8f0fe;
        --text-main: #202124;
        --text-muted: #5f6368;
        --bg-page: #f8f9fa;
        --bg-card: #ffffff;
        --border: #dadce0;
    }
    body { 
        font-family: 'Inter', 'Google Sans', sans-serif; 
        background: var(--bg-page); 
        color: var(--text-main); 
        padding: 32px; 
        line-height: 1.5;
    }
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 2px solid var(--border);
        padding-bottom: 16px;
        margin-bottom: 32px;
    }
    h1 { 
        color: var(--primary); 
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    .badge {
        background: var(--primary-light);
        color: var(--primary);
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 600;
    }
    .section { 
        background: var(--bg-card); 
        border-radius: 12px; 
        padding: 24px; 
        margin-bottom: 32px; 
        border: 1px solid var(--border);
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .section-title { 
        font-size: 20px; 
        font-weight: 700; 
        margin-bottom: 20px; 
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--primary);
    }
    .grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }
    .prompt-box { 
        background: #f1f3f4; 
        padding: 16px; 
        border-radius: 8px; 
        font-size: 14px;
        margin-bottom: 16px;
    }
    .prompt-box.highlight {
        background: var(--primary-light);
        border-left: 4px solid var(--primary);
    }
    .prompt-label { 
        font-weight: 700; 
        font-size: 12px; 
        color: var(--text-muted); 
        text-transform: uppercase;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }
    .prompt-value { 
        white-space: pre-wrap; 
        color: var(--text-main);
    }
    .scene-card { 
        display: flex; 
        flex-direction: column;
        gap: 24px; 
        border: 1px solid var(--border); 
        border-radius: 12px; 
        padding: 24px; 
        margin-bottom: 24px; 
        background: var(--bg-card); 
    }
    .scene-top-row {
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: 24px;
    }
    .col-header { 
        font-weight: 700; 
        color: var(--text-muted); 
        text-transform: uppercase; 
        font-size: 13px; 
        margin-bottom: 16px; 
        border-bottom: 1px solid var(--border);
        padding-bottom: 8px;
    }
    .cine-tag {
        display: inline-block;
        background: #e0e0e0;
        color: #333;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin: 2px;
        font-weight: 500;
    }
    video, img, audio { 
        max-width: 100%; 
        border-radius: 8px; 
        border: 1px solid var(--border); 
        margin-bottom: 12px;
    }
    .final-video-container {
        display: flex;
        justify-content: center;
        padding: 20px;
        background: #000;
        border-radius: 12px;
    }
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
        "<div class='header-container'>",
        f"<h1>✨ Campaign Orchestration Summary</h1>",
        f"<div class='badge'>Template: {template_name}</div>",
        "</div>",
    ]

    # --- Master Production Recipe Directive (High-End Dashboard Card) ---
    master_recipe = tool_context.state.get("master_production_recipe")
    if master_recipe:
        # Clean lists into beautiful comma-separated strings
        def _fmt(val: Any) -> str:
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)

        style_mode = _fmt(master_recipe.get("style_mode", "COMMERCIAL_PREMIUM"))
        brand_arch = _fmt(master_recipe.get("brand_archetype", ""))
        char = master_recipe.get("character", {})
        actor_vibe = _fmt(char.get("actor_vibe", ""))
        attire = _fmt(char.get("attire", ""))
        env = master_recipe.get("environment", {})
        temporal = _fmt(env.get("temporal", ""))

        cine = master_recipe.get("cinematography", {})
        optics = _fmt(cine.get("optics", ""))
        motion_texture = _fmt(cine.get("motion_texture", ""))

        illum = master_recipe.get("illumination", {})
        key_lighting = _fmt(illum.get("key_lighting", ""))

        sonic = _fmt(master_recipe.get("sonic_landscape", ""))

        html_parts.append(f"""
        <div class="section" style="background: linear-gradient(145deg, #f1f5f9, #e2e8f0); border-left: 6px solid #2563eb; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <div class="section-title" style="color: #1e40af; font-size: 1.4rem; display: flex; align-items: center; gap: 8px;">
                💎 Master Production Directive
            </div>
            <p style="color: #475569; font-size: 0.95rem; margin-bottom: 16px; font-style: italic;">
                Every visual and acoustic parameter generated in this campaign is anchored to these curated technical foundations.
            </p>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="background: #1e3a8a; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🏷️ Mode: {style_mode}
                </div>
                <div style="background: #3b82f6; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🎭 Archetype: {brand_arch}
                </div>
                <div style="background: #10b981; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    👤 Cast: {actor_vibe}
                </div>
                <div style="background: #059669; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    👗 Wardrobe: {attire}
                </div>
                <div style="background: #f59e0b; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🌅 Lighting: {temporal}
                </div>
                <div style="background: #d97706; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    💡 Key Light: {key_lighting}
                </div>
                <div style="background: #6366f1; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🔭 Optics: {optics}
                </div>
                <div style="background: #4f46e5; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🎥 Texture: {motion_texture}
                </div>
                <div style="background: #8b5cf6; color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600;">
                    🎵 Audio: {sonic}
                </div>
            </div>
        </div>
        """)

    # 1. Global Settings
    parameters = tool_context.state.get(common_utils.PARAMETERS_KEY, {})
    user_brief = parameters.get("campaign_brief", "Not captured")
    bg_music_prompt = storyboard.get("background_music_prompt", {})
    bg_music_id = bg_music_prompt.get("asset_id")
    bg_music_filename = await get_filename(bg_music_id)

    html_parts.append(
        '<div class="section"><div class="section-title">🎯 Global Strategy & Brief</div>'
    )

    html_parts.append('<div class="grid-2">')

    # Left Column: User Brief
    html_parts.append(
        f'<div><div class="prompt-box highlight"><div class="prompt-label">📝 User Campaign Brief</div>'
        f'<div class="prompt-value">{user_brief}</div></div></div>'
    )

    # Right Column: Template Context & Audio
    html_parts.append("<div>")
    if template_def:
        html_parts.append(
            f'<div class="prompt-box"><div class="prompt-label">📌 Strategic Context</div>'
            f'<div class="prompt-value"><b>Theme:</b> {template_def.description}<br>'
            f'<b>Tone & Voice:</b> {", ".join(template_def.brand_personality)}</div></div>'
        )

    html_parts.append(
        f'<div class="prompt-box"><div class="prompt-label">🎵 Background Music Prompt</div>'
        f'<div class="prompt-value">{bg_music_prompt.get("description", "None")}</div>'
    )
    if bg_music_filename:
        html_parts.append(
            f'<div style="margin-top:12px"><audio controls src="asset://{bg_music_filename}"></audio></div>'
        )
    html_parts.append("</div></div></div>")  # End prompt-box, right col, grid, section

    # 2. Scenes
    html_parts.append(
        '<div class="section"><div class="section-title">🎬 Storyboard Breakdown</div>'
    )

    for i, scene in enumerate(storyboard.get("scenes", [])):
        # Fetch Data
        vid_id = scene.get("video_prompt", {}).get("asset_id")
        img_id = scene.get("first_frame_prompt", {}).get("asset_id")
        aud_id = scene.get("voiceover_prompt", {}).get("asset_id")

        enrich_vid_id = scene.get("video_prompt", {}).get("enrichment_asset_id")
        enrich_img_id = scene.get("first_frame_prompt", {}).get("enrichment_asset_id")

        vid_file = await get_filename(vid_id)
        img_file = await get_filename(img_id)
        aud_file = await get_filename(aud_id)

        enrich_vid = await get_text_content(enrich_vid_id)
        enrich_img = await get_text_content(enrich_img_id)

        template_scene = None
        if template_def and i < len(template_def.scene_structure):
            template_scene = template_def.scene_structure[i]

        html_parts.append(f'<div class="scene-card">')

        # --- ROW 1: Dual Column (Strategy left, Assets right) ---
        html_parts.append(f'<div class="scene-top-row">')

        # Top Left: Strategy & Direction
        html_parts.append(
            f'<div class="col"><div class="col-header">🎯 Scene {i + 1}: Strategy & Direction</div>'
            f'<div style="font-weight:600; font-size:16px; margin-bottom:12px; color:var(--primary);">{scene.get("topic", "Untitled")}</div>'
        )

        if template_scene:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">📌 Strategy Mapping (Directive)</div>'
                f'<div class="prompt-value">{template_scene.asset_guidance}</div></div>'
            )

        # Final Cinematography (Formatted beautifully row-by-row)
        final_cine = scene.get("video_prompt", {}).get("cinematography", {})
        cine_html = ""

        def _clean(val: Any) -> str:
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)

        if isinstance(final_cine, dict):
            for k, v in final_cine.items():
                if v:
                    clean_v = _clean(v)
                    cine_html += f'<div style="background: #1e293b; color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; margin-bottom: 6px;"><b>{k}:</b> {clean_v}</div>'
        else:
            clean_cine = _clean(final_cine)
            cine_html = f'<div style="background: #1e293b; color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem;">{clean_cine}</div>'

        if cine_html:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">🎥 Cinematography Plan</div>'
                f'<div style="display:flex; flex-direction:column;">{cine_html}</div></div>'
            )

        html_parts.append(f"</div>")

        # Top Right: Generated Assets
        html_parts.append(
            '<div class="col"><div class="col-header">📦 Generated Assets</div>'
        )

        if vid_file:
            html_parts.append(
                f'<div class="prompt-label" style="margin-top:8px;">Video</div><video controls src="asset://{vid_file}"></video>'
            )
        else:
            html_parts.append(
                '<div class="prompt-box" style="text-align:center; color:var(--text-muted);">No Video Generated</div>'
            )

        if img_file:
            html_parts.append(
                f'<div class="prompt-label">First Frame</div><img src="asset://{img_file}">'
            )

        html_parts.append("</div></div>")  # End Top Right Col, End ROW 1

        # --- ROW 2: Full Width Prompts Footer ---
        html_parts.append(
            '<div class="col" style="border-top: 1px solid var(--border); padding-top: 20px; margin-top: 8px;">'
            '<div class="col-header">✨ Final Generation Prompts</div>'
        )

        if enrich_vid:
            html_parts.append(
                f'<div class="prompt-box highlight"><div class="prompt-label">🎬 Final Video Prompt (Enriched)</div>'
                f'<div class="prompt-value">{enrich_vid}</div></div>'
            )
        else:
            fallback_desc = scene.get("video_prompt", {}).get(
                "description", "Not available"
            )
            html_parts.append(
                f'<div class="prompt-box highlight"><div class="prompt-label">🎬 Final Video Prompt</div>'
                f'<div class="prompt-value">{fallback_desc}</div></div>'
            )

        img_desc = scene.get("first_frame_prompt", {}).get(
            "description", "Not available"
        )
        if enrich_img:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">🖼️ Final First-Frame Prompt (Enriched)</div>'
                f'<div class="prompt-value">{enrich_img}</div></div>'
            )
        else:
            html_parts.append(
                f'<div class="prompt-box"><div class="prompt-label">🖼️ Base First-Frame Prompt</div>'
                f'<div class="prompt-value">{img_desc}</div></div>'
            )

        html_parts.append("</div></div>")  # End Footer Col, End scene-card

    html_parts.append("</div>")  # End section

    # 3. Final Video
    if final_asset_id := tool_context.state.get("final_video_asset_id"):
        final_file = await get_filename(final_asset_id)
        if final_file:
            html_parts.append(
                f'<div class="section"><div class="section-title">🏆 Final Stitched Delivery</div>'
                f'<div class="final-video-container"><video controls src="asset://{final_file}" class="final-video" style="max-height:600px;"></video></div></div>'
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
