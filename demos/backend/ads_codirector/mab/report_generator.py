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

import base64
import json
import logging
import re

from ..utils import common_utils

logger = logging.getLogger(__name__)


def _format_markdown(text: str) -> str:
    """Very basic markdown-to-HTML formatter (bold and newlines)."""
    if not isinstance(text, str):
        return str(text)
    # Handle bold **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # Handle newlines
    text = text.replace("\n", "<br>")
    return text


def generate_html_report(
    user_prompt: str,
    mab_state: dict,
    local_artifact_dirs: dict,
    output_path: str,
    use_asset_uris: bool = False,
):
    """
    Generates a comprehensive HTML report from the ads_x_mab run state and artifacts.
    """
    try:
        iterations = mab_state.get("iterations", [])
        if not iterations:
            logger.warning("No iterations found in MAB state. Cannot generate report.")
            return

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Report</title>
            <style>
                :root {{
                    --primary: #5c67f2;
                    --primary-hover: #4a54d1;
                    --bg: #f4f7fa;
                    --card-bg: #ffffff;
                    --text: #2d3436;
                    --text-muted: #636e72;
                    --border: #dfe6e9;
                    --shadow: 0 4px 6px rgba(0,0,0,0.05);
                }}
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 2em;
                    background-color: var(--bg); 
                    color: var(--text); 
                    line-height: 1.6;
                }}
                .container {{ max-width: 1100px; margin: auto; }}
                
                h1, h2, h3, h4 {{ color: var(--text); margin-top: 0; }}
                h1 {{ font-size: 2.2em; border-bottom: 3px solid var(--primary); padding-bottom: 0.5em; margin-bottom: 1em; }}
                
                /* Cards & Sections */
                .report-card {{
                    background: var(--card-bg);
                    border-radius: 8px;
                    box-shadow: var(--shadow);
                    margin-bottom: 1.5em;
                    border: 1px solid var(--border);
                    overflow: hidden;
                }}
                .card-header {{
                    padding: 12px 20px;
                    background: #f8f9fa;
                    border-bottom: 1px solid var(--border);
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: background 0.2s;
                    user-select: none;
                }}
                .card-header:hover {{ background: #f1f3f5; }}
                .card-header h3, .card-header h4 {{ margin: 0; font-size: 1.1em; color: var(--text); font-weight: 600; }}
                .card-header .toggle-icon {{ 
                    font-size: 0.8em; 
                    transition: transform 0.3s; 
                    color: var(--text-muted);
                }}
                .card-content {{
                    padding: 20px;
                    display: none; /* Hidden by default */
                }}
                .card-content.active {{ display: block; }}
                .card-header.active .toggle-icon {{ transform: rotate(180deg); }}

                /* Iteration Hero Styles */
                .iteration-header {{
                    background: var(--primary);
                    color: white;
                    padding: 15px 25px;
                    border-radius: 8px 8px 0 0;
                    margin-top: 2em;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .iteration-header h2 {{ color: white; margin: 0; font-size: 1.5em; }}
                .mab-score-pill {{
                    background: rgba(255,255,255,0.2);
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 0.9em;
                }}

                /* Video Container */
                .video-hero {{
                    background: #000;
                    padding: 0;
                    border-radius: 0 0 8px 8px;
                    margin-bottom: 2em;
                    box-shadow: var(--shadow);
                    overflow: hidden;
                    text-align: center;
                }}
                video {{ max-width: 100%; display: block; margin: auto; max-height: 600px; }}

                /* Typography & Elements */
                pre {{ 
                    white-space: pre-wrap; 
                    word-wrap: break-word; 
                    background: #2d2d2d; 
                    color: #f1f1f1; 
                    padding: 1.2em; 
                    border-radius: 6px;
                    font-size: 0.9em;
                    margin: 0;
                }}
                .feedback-pane {{ background-color: #f0f4ff; border-left: 4px solid var(--primary); padding: 15px; margin-top: 10px; border-radius: 4px; }}
                
                /* Tables */
                .feedback-table {{ width: 100%; border-collapse: collapse; margin-top: 0.5em; }}
                .feedback-table th, .feedback-table td {{ border: 1px solid var(--border); padding: 12px; text-align: left; font-size: 0.9em; }}
                .feedback-table th {{ background-color: #f8f9fa; font-weight: 600; color: var(--text-muted); }}

                /* Gallery & Assets */
                .user-asset-gallery {{ display: flex; flex-wrap: wrap; gap: 1em; margin-top: 1em; }}
                .user-asset {{ 
                    border: 1px solid var(--border); 
                    border-radius: 6px; 
                    padding: 10px; 
                    background: #fff; 
                    max-width: 250px;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .user-asset:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .user-asset img {{ max-width: 100%; border-radius: 4px; }}
                
                .attempt-gallery {{ display: flex; flex-wrap: wrap; gap: 1em; margin-top: 1em; overflow-x: auto; padding-bottom: 10px; }}
                .attempt {{ border: 1px solid var(--border); border-radius: 6px; padding: 10px; background: #fcfcfc; min-width: 200px; max-width: 280px; flex-shrink: 0; }}
                .attempt img {{ max-width: 100%; border-radius: 4px; border: 1px solid #eee; }}
                
                .badge {{ font-size: 0.7em; padding: 2px 8px; border-radius: 10px; color: white; vertical-align: middle; text-transform: uppercase; font-weight: bold; }}
                .badge-regen {{ background-color: #eb4d4b; }}
                .badge-retained {{ background-color: #6ab04c; }}

                .efficacy-card {{ background: white; border: 1px solid var(--border); border-radius: 6px; padding: 15px; margin-bottom: 12px; }}
                .efficacy-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
                .efficacy-title {{ font-weight: 600; color: var(--primary); }}
                .efficacy-score {{ background: var(--primary); color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold; }}
                
                /* Helper classes */
                .mt-10 {{ margin-top: 10px; }}
                .mb-10 {{ margin-bottom: 10px; }}
                .text-muted {{ color: var(--text-muted); font-size: 0.9em; }}
                .bold {{ font-weight: 600; }}
            </style>
            <script>
                function toggleSection(header) {{
                    const content = header.nextElementSibling;
                    header.classList.toggle('active');
                    content.classList.toggle('active');
                }}
                
                function toggleSubSection(id) {{
                    const el = document.getElementById(id);
                    if (el) el.classList.toggle('active');
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>Report</h1>
                
                <div class="report-card">
                    <div class="card-header active" onclick="toggleSection(this)">
                        <h3>User Prompt</h3>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content active">
                        <pre>{user_prompt}</pre>
                    </div>
                </div>
        """

        # 3. Campaign Constraints
        constraints = mab_state.get("structured_constraints", {})
        if constraints:
            html_content += """
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h3>Campaign Constraints</h3>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                        <table class="feedback-table">
            """
            for k, v in constraints.items():
                if v and k != "campaign_brief":
                    friendly_key = k.replace("_", " ").title()
                    html_content += f"<tr><td class='bold' style='width:30%;'>{friendly_key}</td><td>{v}</td></tr>"
            html_content += "</table></div></div>"

        # User Assets
        user_assets_from_log = (
            mab_state.get(common_utils.ANNOTATED_REFERENCE_VISUALS_KEY)
            or mab_state.get(common_utils.USER_ASSETS_KEY)
            or {}
        )
        if user_assets_from_log:
            html_content += """
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h3>Annotated User Assets</h3>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                        <div class="user-asset-gallery">
            """
            user_asset_paths = local_artifact_dirs.get("user_asset_paths", {})
            for i, (filename, annotation) in enumerate(user_assets_from_log.items()):
                if filename.startswith("iter_") or filename.startswith("scene_"): continue
                description = annotation.get("caption", "") if isinstance(annotation, dict) else str(annotation)
                role = annotation.get("semantic_role", "N/A") if isinstance(annotation, dict) else "N/A"
                
                img_src = ""
                if use_asset_uris: img_src = f"asset://{filename}"
                else:
                    path = user_asset_paths.get(filename)
                    if path and path.is_file():
                        img_src = f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"

                if img_src:
                    html_content += f"""
                    <div class="user-asset">
                        <img src="{img_src}" alt="{filename}">
                        <div class="text-muted mt-10 bold" style="text-align:center;">{role.upper()}</div>
                        <div style="font-size:0.75em; color:#666; margin-top:5px; line-height:1.2;">{description}</div>
                        <div style="font-size:0.7em; color:#999; margin-top:8px; text-align:center; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; border-top:1px solid #eee; padding-top:4px;">{filename}</div>
                    </div>
                    """
            html_content += "</div></div></div>"

        # ITERATIONS
        for iteration in sorted(iterations, key=lambda x: x["iteration_num"]):
            iter_num = iteration["iteration_num"]
            iter_index = iter_num - 1
            storyboard = iteration.get("storyboard", {})
            iteration_artifacts = local_artifact_dirs.get(iter_index, {})
            local_dir = iteration_artifacts.get("dir_path")
            verifier_results = iteration.get("verifier_results", {})
            video_score = verifier_results.get("score", 0)

            # Iteration Hero
            html_content += f"""
            <div class="iteration-header">
                <h2>Iteration {iter_num}</h2>
                <div class="mab-score-pill">Score: {video_score}/100</div>
            </div>
            """

            # Final Video - Hero Placement
            final_video_filename = f"iter_{iter_index}_final_video.mp4"
            video_src = f"asset://{final_video_filename}" if use_asset_uris else ""
            if not use_asset_uris and local_dir:
                vp = local_dir / final_video_filename
                if vp.is_file():
                    video_src = f"data:video/mp4;base64,{base64.b64encode(vp.read_bytes()).decode()}"
            
            html_content += f"""
            <div class="video-hero">
                <video controls src="{video_src}"></video>
            </div>
            """

            # 1. Creative Configuration Card
            arms_selected = iteration.get("arms_selected", {})
            warm_start = mab_state.get("warm_start") if iter_num == 1 else None
            
            html_content += f"""
            <div class="report-card">
                <div class="card-header" onclick="toggleSection(this)">
                    <h4>1. Creative Configuration</h4>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="card-content">
                    <div class="mb-10">
                        <span class="bold">Selection Logic:</span> 
                        {_format_markdown(warm_start.get('reasoning')) if warm_start else "UCB1-based selection (Exploration vs Exploitation)"}
                    </div>
                    <table class="feedback-table">
            """
            for k, v in arms_selected.items():
                html_content += f"<tr><td class='bold' style='width:30%;'>{k.replace('_', ' ').title()}</td><td>{v}</td></tr>"
            html_content += "</table></div></div>"

            # 2. Creative Brief Card
            brief = iteration.get("creative_brief")
            if brief:
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>2. Creative Brief</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                        <div style="font-size:0.95em;">{_format_markdown(brief)}</div>
                    </div>
                </div>
                """

            # 3. System-Generated Visual Assets Card (Casting)
            collage_id = iteration.get("character_collage_asset_id")
            casting_specs = iteration.get("character_casting", {})
            if collage_id or casting_specs:
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>3. System-Generated Visual Assets</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                """
                if collage_id:
                    c_name = f"iter_{iter_index}_character_collage.png"
                    c_src = f"asset://{c_name}" if use_asset_uris else ""
                    if not use_asset_uris:
                        cp = iteration_artifacts.get("character_collage_path")
                        if cp and cp.is_file():
                            c_src = f"data:image/png;base64,{base64.b64encode(cp.read_bytes()).decode()}"
                    
                    if c_src:
                        html_content += f"""
                        <div style="display: flex; gap: 2em; align-items: flex-start; margin-bottom:1.5em;">
                            <img src="{c_src}" style="max-width: 300px; border-radius: 8px; border: 1px solid var(--border);">
                            <div style="flex:1;">
                                <div class="bold mb-10">Character Specs:</div>
                                <ul style="font-size:0.9em; padding-left:20px;">
                                    <li><span class="bold">Profile:</span> {casting_specs.get('character_profile', 'N/A')}</li>
                                    <li><span class="bold">Wardrobe:</span> {casting_specs.get('wardrobe_description', 'N/A')}</li>
                                </ul>
                                <div class="mt-10 bold">Collage Prompt:</div>
                                <pre style="font-size:0.85em; margin-top:5px;">{casting_specs.get('collage_prompt', 'N/A')}</pre>
                            </div>
                        </div>
                        """
                html_content += "</div></div>"

            # 4. Storyline Card
            storyline_history = iteration.get("storyline_refinement_history")
            if storyline_history:
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>4. Storyline & Refinement</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                """
                for attempt in storyline_history:
                    att_num = attempt.get("attempt", 0)
                    att_score = attempt.get("score", 0)
                    eval_data = attempt.get("evaluation", {})
                    output = attempt.get("output", {})
                    
                    html_content += f"""
                    <div style="border-bottom: 1px solid var(--border); margin-bottom: 15px; padding-bottom: 15px;">
                        <div class="bold" style="display:flex; justify-content:space-between;">
                            <span>Attempt {att_num}</span>
                            <span style="color:var(--primary);">{att_score}/100</span>
                        </div>
                        <div class="mt-10" style="font-size:0.9em;">
                    """
                    scenes_list = output.get("scenes") or output.get("script") or output.get("storyline", {}).get("scenes")
                    if isinstance(scenes_list, list):
                        for s_idx, scn in enumerate(scenes_list):
                            desc = scn.get('action') or scn.get('visual_description') or "N/A"
                            html_content += f"<div class='mb-10'><span class='bold'>Scene {s_idx+1}:</span> {desc}</div>"
                    
                    html_content += f"""
                        </div>
                        <div class="feedback-pane">
                            <div class="bold" style="font-size:0.85em;">Refinement Feedback:</div>
                            <div style="font-size:0.85em; color:var(--text-muted);">{eval_data.get('feedback', 'N/A')}</div>
                            <div class="bold mt-10" style="font-size:0.85em; color:#eb4d4b;">Actionable Guidance:</div>
                            <div style="font-size:0.85em; color:#eb4d4b;">{eval_data.get('actionable_feedback', 'N/A')}</div>
                        </div>
                    </div>
                    """
                html_content += "</div></div>"

            # 5. Global Audio Card
            html_content += f"""
            <div class="report-card">
                <div class="card-header" onclick="toggleSection(this)">
                    <h4>5. Global Audio Track</h4>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="card-content">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            """
            for a_type in [("Background Music", "background_music"), ("Voiceover", "voiceover")]:
                label, key = a_type
                p_key = f"{key}_prompt"
                h_key = f"{key}_generation_history"
                prompt_data = storyboard.get(p_key, {})
                history = storyboard.get(h_key, [])
                
                html_content += f"""
                <div style="background:#f8f9fa; padding:15px; border-radius:6px; border:1px solid var(--border);">
                    <h5 class="mb-10">{label}</h5>
                    <div class="bold" style="font-size:0.8em; margin-bottom:4px;">PROMPT:</div>
                    <pre style="font-size:0.8em; margin-bottom:15px;">{prompt_data.get('description', 'N/A')}</pre>
                """
                if history:
                    for h_idx, att in enumerate(history):
                        fname = att.get("asset", {}).get("file_name")
                        src = ""
                        if use_asset_uris: src = f"asset://{fname}"
                        elif local_dir and fname:
                            ap = local_dir / fname
                            if ap.is_file(): src = f"data:audio/mp3;base64,{base64.b64encode(ap.read_bytes()).decode()}"
                        
                        if src:
                            html_content += f"""
                            <div class="mt-10">
                                <div style="font-size:0.75em; color:var(--text-muted);">Attempt {h_idx+1}:</div>
                                <audio controls src="{src}" style="width:100%; height:32px;"></audio>
                            </div>
                            """
                html_content += "</div>"
            html_content += "</div></div></div>"

            # 6. Evaluation Results Card
            if verifier_results:
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>6. Video Evaluation Results</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                        <div style="display: flex; gap: 2em; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 300px;">
                                <h5 class="mb-10">Execution Breakdown:</h5>
                """
                breakdown = verifier_results.get("breakdown", {})
                for k, v in breakdown.items():
                    html_content += f"""
                    <div class="efficacy-card" style="padding:10px; margin-bottom:8px;">
                        <div class="efficacy-header" style="margin-bottom:0;">
                            <span class="efficacy-title" style="font-size:0.9em;">{k.replace('_', ' ').title()}</span>
                            <span class="efficacy-score" style="font-size:0.75em;">{v}/20</span>
                        </div>
                    </div>
                    """
                html_content += f"""
                            <div class="efficacy-card" style="margin-top:10px;">
                                <div class="bold mb-10">Critic Feedback:</div>
                                <div style="font-size:0.9em;">{_format_markdown(verifier_results.get('feedback', 'N/A'))}</div>
                            </div>
                        </div>
                        <div style="flex: 1; min-width: 300px;">
                            <h5 class="mb-10">Factorized Rewards:</h5>
                """
                eff_scores = verifier_results.get("mab_efficacy_scores", {})
                eff_justs = verifier_results.get("mab_efficacy_justifications", {})
                for dim, score in eff_scores.items():
                    just = eff_justs.get(dim, "N/A") if isinstance(eff_justs, dict) else str(eff_justs)
                    html_content += f"""
                    <div class="efficacy-card">
                        <div class="efficacy-header">
                            <span class="efficacy-title">{dim.replace('_', ' ').title()}</span>
                            <span class="efficacy-score">{score}/100</span>
                        </div>
                        <div style="font-size:0.8em; color:var(--text-muted);">{_format_markdown(just)}</div>
                    </div>
                    """
                html_content += "</div></div></div></div>"

            # 7. Scene Breakdown Card
            if storyboard.get("scenes"):
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>7. Scene-by-Scene Breakdown</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                """
                # Gapless Strip
                html_content += '<div style="display: flex; width: 100%; gap: 0; margin-bottom: 2em; overflow: hidden; border-radius: 8px; border: 1px solid var(--border);">'
                for s_idx, scene in enumerate(storyboard.get("scenes", [])):
                    fname = f"iter_{iter_index}_scene_{s_idx}_final_frame.png"
                    hist = scene.get("first_frame_generation_history", [])
                    if hist and (h_name := hist[-1].get("asset", {}).get("file_name")): fname = h_name
                    
                    src = ""
                    if use_asset_uris: src = f"asset://{fname}"
                    elif local_dir:
                        fp = local_dir / fname
                        if fp.is_file(): src = f"data:image/png;base64,{base64.b64encode(fp.read_bytes()).decode()}"
                    
                    if src:
                        html_content += f'<img src="{src}" style="flex: 1; min-width: 0; display: block; width: 100%; border-right: 1px solid rgba(255,255,255,0.1);" title="Scene {s_idx+1}">'
                html_content += "</div>"

                for i, scene in enumerate(storyboard.get("scenes", [])):
                    html_content += f"""
                    <div style="border: 1px solid var(--border); border-radius:6px; margin-bottom:15px; overflow:hidden;">
                        <div class="card-header" style="background:#fcfcfc; padding:8px 15px;" onclick="toggleSection(this)">
                            <h5 style="margin:0;">Scene {i+1}: {scene.get('topic', 'N/A')}</h5>
                            <span class="toggle-icon">▼</span>
                        </div>
                        <div class="card-content" style="padding:15px;">
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:15px;">
                                <div><div class="bold" style="font-size:0.8em;">KEYFRAME PROMPT:</div><pre style="font-size:0.75em; margin-top:5px;">{scene.get('first_frame_prompt', {}).get('description')}</pre></div>
                                <div><div class="bold" style="font-size:0.8em;">VIDEO PROMPT:</div><pre style="font-size:0.75em; margin-top:5px;">{scene.get('video_prompt', {}).get('description')}</pre></div>
                            </div>
                            <div class="bold mb-10" style="font-size:0.85em;">Refinement History:</div>
                            <div class="attempt-gallery">
                    """
                    for attempt in scene.get("first_frame_generation_history", []):
                        cyc = attempt.get("cycle", 0)
                        is_reg = attempt.get("regenerated", False)
                        f_name = attempt.get("asset", {}).get("file_name")
                        b_cls = "badge-regen" if is_reg else "badge-retained"
                        b_txt = "REGEN" if is_reg else "KEEP"
                        
                        a_src = ""
                        if use_asset_uris: a_src = f"asset://{f_name}"
                        elif local_dir and f_name:
                            ap = local_dir / f_name
                            if ap.is_file(): a_src = f"data:image/png;base64,{base64.b64encode(ap.read_bytes()).decode()}"
                        
                        v_res = attempt.get("joint_verification", {})
                        html_content += f"""
                        <div class="attempt">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <span class="bold" style="font-size:0.8em;">Cycle {cyc+1}</span>
                                <span class="badge {b_cls}">{b_txt}</span>
                            </div>
                            <img src="{a_src}">
                            <div style="font-size:0.75em; margin-top:8px;">
                                <div class="bold" style="color:var(--primary);">Score: {v_res.get('score', 0)}/100</div>
                                <div class="text-muted mt-10">{v_res.get('feedback', 'N/A')}</div>
                            </div>
                        </div>
                        """
                    html_content += "</div></div></div>"
                html_content += "</div></div>"

            # 8. MAB Arm Stats Card
            arm_stats = iteration.get("arm_stats") or mab_state.get("arm_stats", {})
            if arm_stats:
                html_content += f"""
                <div class="report-card">
                    <div class="card-header" onclick="toggleSection(this)">
                        <h4>8. MAB Arm Statistics</h4>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="card-content">
                        <table class="feedback-table">
                            <thead><tr><th>Dimension</th><th>Arm</th><th style="text-align:center;">Pulls</th><th style="text-align:center;">Avg Reward</th></tr></thead>
                            <tbody>
                """
                for dim, stats in arm_stats.items():
                    arms = list(stats.items())
                    for idx, (arm, data) in enumerate(arms):
                        p = data.get("pulls", 0)
                        r = data.get("total_reward", 0) / p if p > 0 else 0
                        html_content += "<tr>"
                        if idx == 0: html_content += f'<td rowspan="{len(arms)}" class="bold" style="background:#f8f9fa;">{dim.replace("_"," ").title()}</td>'
                        html_content += f"<td>{arm}</td><td style='text-align:center;'>{p}</td><td style='text-align:center;'>{r:.2f}</td></tr>"
                html_content += "</tbody></table></div></div>"

        html_content += "</div></body></html>"

        if output_path:
            with open(output_path, "w") as f: f.write(html_content)
            logger.info(f"Successfully generated HTML report at {output_path}")
        return html_content
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
        raise
