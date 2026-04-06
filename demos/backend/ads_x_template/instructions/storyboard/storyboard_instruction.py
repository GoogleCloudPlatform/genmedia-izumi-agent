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

"""Instructions for the storyboard agent."""

import json
import logging
from ...utils.common import common_utils

logger = logging.getLogger(__name__)
from ...utils.storyboard import storyboard_model
from ...utils.storyboard import template_library, pacing_blueprints
from google.adk.agents.readonly_context import ReadonlyContext


# --- DATA PREPARATION ---
def _get_templates_data():
    templates = template_library.get_all_templates()
    return json.dumps([t.model_dump() for t in templates], indent=2)


TEMPLATE_LIBRARY_JSON = _get_templates_data()
PACING_BLUEPRINTS_JSON = pacing_blueprints.get_pacing_options_json()


# --- STRATEGY A: TEMPLATED (Structured / Predictable) ---
def get_templated_instruction(ctx: ReadonlyContext) -> str:
    # Safely fetch state
    parameters = ctx.session.state.get("parameters", "[Not Yet Defined]")
    user_assets = ctx.session.state.get("user_assets", "[Not Yet Defined]")
    forced_metadata = ctx.session.state.get("forced_metadata", "[Not Yet Defined]")

    return f"""
Generate a JSON campaign breakdown (Storyboard) for the following video ad campaign.

**CORE INSTRUCTION:**
You are in **Templated Mode**. You must strictly follow the defined template structure.

**Campaign Parameters:**
{parameters}

**User Assets:**
{user_assets}

**Forced Metadata:**
{forced_metadata}

**Template Reference Library:**
{TEMPLATE_LIBRARY_JSON}

**Instructions:**
1.  **Identify Template:** Find the template definition in the Library that matches `parameters.template_name`.
2.  **Follow Structure:** You MUST strictly adhere to the `scene_structure` defined in that template.
    -   Create exactly the same number of scenes, in the same order.
    -   Use the exact `duration_seconds` and `topic` (or purpose) from the template.
    -   **CRITICAL DURATION RULE:** Many templates use fast pacing with decimal durations (e.g. 2.5s, 3.5s). You **MUST** copy these exact float values. **DO NOT** round them to the nearest integer. **DO NOT** default them to 4s.
    -   You MUST NOT change the scene durations or total duration, even if the user requested a specific duration (e.g. 30s). Strictly follow the template's timing to ensure optimal narrative flow.
3.  **Production Strategy (Tool-Based High-Fidelity):**
    -   You MUST call the `recommend_production_recipe` tool before generating your scenes.
    -   **Arguments**: Use `parameters.vertical`, `forced_metadata.campaign_theme`, and `forced_metadata.campaign_tone`.
    -   **TECHNICAL ANCHORS**: Use the technical anchors returned by the tool (Character, Environment, Cinematography, Illumination, Materiality, and Sonic Landscape) to hydrate your prompts in the next step.
4.  **Hydrate with Creativity:** For each scene, generate the detailed prompts:
    -   **`first_frame_prompt` & `video_prompt`**: Combine the template's `cinematography_hints` + `asset_guidance` + User Assets + **Technical Anchors** from the Production Recipe.
        -   **CRITICAL OVERRIDE RULE**: If the User's Campaign Brief explicitly requests a specific style, mood, or detail, you MUST **override** the template's default hint with the User's preference.
        -   **TEXT OVERLAY RULE**: If the template scene contains `on_screen_text_hint` (e.g. "Shop Now"), you MUST include a request for this text in the `first_frame_prompt.description` so it is rendered in the image.
        -   **MANDATORY ASSET TAGS**: 
            - If a scene features the primary product, you MUST include the string `[PRODUCT REQUIRED]` in the `first_frame_prompt.description`.
            - If a scene requires a character/person (especially for Virtual Creator campaigns), you MUST include the string `[CHARACTER REQUIRED]` in the `first_frame_prompt.description`.
        -   **NEGATIVE CONSTRAINT (IMPORTANT)**: DO NOT put `[PRODUCT REQUIRED]` or `[CHARACTER REQUIRED]` into the `assets` list (array of strings). These tags belong ONLY in the `description` text.
    -   **`voiceover_prompt`**: Write a script that matches the template's `audio_hints` (tone, dialogue) and the Campaign Brief.
        -   **BRIEF DOMINANCE RULE (UGC)**: For templates with `industry_type: 'Social Native'`, the `dialogue_hint` is a blueprint. You **MUST** hydrate it with specific details (product name, USPs, features) from the Campaign Brief. If the user explicitly mentioned a talking point (e.g., "Lifetime Warranty", "Titanium", "24h Battery"), it **MUST** appear in the dialogue.
    -   **`audio_hints` & `transition_hints`**: Copy from template.
5.  **Asset Integration:** Select appropriate asset IDs for scenes requiring products, logos, or characters.
    -   **Characters/Creators:** If a scene's `asset_guidance` is tagged as `[CHARACTER REQUIRED]`, you MUST look for an asset in `user_assets` whose filename starts with `virtual_creator_`. You MUST include that asset's ID (filename) in the `assets` list.
    -   **IMPORTANT:** The `user_assets` variable is a dictionary where the **Key** is the Filename (Asset ID) and the **Value** is the description.
    -   **The Asset ID IS the Filename.** (e.g., "smartwater_logo.png").
    -   **NEVER** invent a UUID (e.g., "18c949c8...").
    -   **NEVER** invent a filename based on the description (e.g., "smartwater_from_work_to_workout.png").
    -   You **MUST** use the exact Filename string from the `user_assets` keys provided in the context. If the key is "smartwater_1.png", use "smartwater_1.png".
6.  **Music Selection:** Use the **SONIC_LANDSCAPE** description returned by the `recommend_production_recipe` tool to populate the `background_music_prompt`.
7.  **Asset Usage (Maximize):**
    -   **Goal:** Showcase the user's product.
    -   **Rule:** You MUST incorporate **as many User Assets as possible**.
    -   **Target:** Aim for **80%+ of scenes** to feature an uploaded asset (using `first_frame_prompt.assets`).
    -   Do not hallucinate new products if the user provided images.

**CRITICAL CONSTRAINTS (Best Practices):**
1.  **Brand Name Safety (CRITICAL - SPLIT RULE):**
    -   **For `first_frame_prompt` (Image):** You **SHOULD** use the specific Brand Name and Product Name (e.g. "Dior Foundation", "Chewy Box") to ensure the generated image looks exactly like the product.
    -   **For `video_prompt` (Video):** You **MUST NOT** use specific Brand Names. Use generic terms like "the product", "the bottle", "the logo".
2.  **CTA Distortion Safety (End Scene):**
    -   For the **CTA / Brand Seal** scene, you MUST specify **Subtle Motion** only (e.g. "Slow Push-In", "Static with floating particles"). Fast motion distorts text rendering.

**OUTPUT RULE (PIPELINE MODE):**
- You must output the valid JSON object exactly matching this schema:
{storyboard_model.DESCRIPTION}
- **CRITICAL**: The `scenes` array MUST NOT BE EMPTY. You must populate it with exactly the number of scenes dictated by the blueprint.
- After successfully calling the `finalize_and_persist_storyboard` tool, do NOT provide a long celebratory summary.
- Simply output: `🎬 **Creative Perspective Synced!** Storyboard generated and ready for media production.`

**FINAL STEP (CRITICAL):**
Once you have generated the JSON object, you MUST call the `finalize_and_persist_storyboard` tool.
"""


# --- STRATEGY B: AI DIRECTOR (Creative / Custom / Freeform) ---
def get_ai_director_instruction(ctx: ReadonlyContext) -> str:
    # Safely fetch state securely. State might be a DictProxy, string, or dict.
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        f"🚨 [DEEP DEBUG DOWNSTREAM] All keys in ctx.session.state: {list(ctx.session.state.keys())}"
    )

    parameters = ctx.session.state.get("parameters", {})
    logger.warning(
        f"🚨 [DEEP DEBUG DOWNSTREAM] Extracted parameters type: {type(parameters)}"
    )
    logger.warning(
        f"🚨 [DEEP DEBUG DOWNSTREAM] Extracted parameters repr: {repr(parameters)}"
    )

    if isinstance(parameters, str):
        import json

        try:
            parameters = json.loads(parameters)
        except Exception:
            parameters = {}

    # Ensure it's safe to call .get()
    if not hasattr(parameters, "get"):
        parameters = {}

    target_duration_str = parameters.get("target_duration", "12s")
    try:
        target_secs = float(str(target_duration_str).replace("s", "").strip())
    except ValueError:
        target_secs = 12.0

    logger.info(
        f"🎬 [AI DIRECTOR PACING] State target_duration: '{target_duration_str}', Resolved Float: {target_secs}s"
    )

    # Pre-calculate the exact rigorous pacing array beforehand using Python
    blueprint_array = pacing_blueprints.get_random_blueprint_for_duration(target_secs)
    expected_scene_count = len(blueprint_array)

    # Convert state to strings for prompt
    parameters_str = ctx.session.state.get("parameters", "[Not Yet Defined]")
    user_assets = ctx.session.state.get("user_assets", "[Not Yet Defined]")
    forced_metadata = ctx.session.state.get("forced_metadata", "[Not Yet Defined]")

    return f"""
Generate a JSON campaign breakdown (Storyboard) for the following video ad campaign.

**CORE INSTRUCTION:**
You are an expert **AI Creative Director**. You are responsible for architecting a cinematic narrative structure.

**Campaign Parameters:**
{parameters_str}

**User Assets:**
{user_assets}

**Forced Metadata:**
{forced_metadata}

**Instructions:**

1.  **Hierarchy of Structural Truth (Rule of Adherence):**
    -   **Level 1 (Highest Priority):** If the User's Campaign Brief provides a **specific scene breakdown** (e.g., "Scene 1: Hook, 5s...", "1. Logo intro 3s, 2. Feature demo 7s..."), you MUST strictly follow the user's defined structure and durations.
    -   **Level 2 (Target Duration Enforcement):** If the user ONLY specifies a total duration or provides no structure, you MUST STRICTLY execute the following Python-calculated scene blueprint:
        -   **EXTRACTED TARGET DURATION:** {target_secs}s
        -   **REQUIRED SCENE COUNT:** {expected_scene_count} scenes.
        -   **REQUIRED PACING ARRAY:** {blueprint_array}
        -   **RULE:** You MUST generate EXACTLY {expected_scene_count} scenes. The `duration_seconds` for each scene MUST exactly match the values in the pacing array in sequence (e.g., Scene 1 is {blueprint_array[0]}s). You MUST populate the `scenes` JSON array with exactly these {expected_scene_count} scene objects. It MUST NEVER be empty.

2.  **Invent the Narrative Narrative (Blueprint Mapping):**
    -   Map the chosen structure (either user-defined or library-preset) to a high-fidelity narrative blueprint:
        -   **Hook**: Attention grabber.
        -   **Body**: Demonstration, Benefits, Social Proof.
        -   **Resolution**: CTA and Brand Identity.

3.  **Production Strategy (Tool-Based High-Fidelity):**
    -   You MUST call the `recommend_production_recipe` tool before generating your first scene.
    -   **Arguments**: Use `parameters.vertical`, `forced_metadata.campaign_theme`, and `forced_metadata.campaign_tone`.
    -   **RECIPE CONSUMPTION**: You MUST strictly use the technical anchors returned by the tool (Character, Environment, Cinematography, Illumination, and Sonic Landscape) to hydrate your prompts.
    -   **MANDATORY ASSET TAGS**: 
        - Include `[PRODUCT REQUIRED]` for product shots.
        - Include `[CHARACTER REQUIRED]` for scenes with people or characters.
    -   **NEGATIVE CONSTRAINT (IMPORTANT)**: DO NOT put `[PRODUCT REQUIRED]` or `[CHARACTER REQUIRED]` into any `assets` array. These tags belong ONLY in the `description` text.

4.  **Strategic Alignment (CRITICAL):**
    -   Use `forced_metadata` values to populate global fields: `campaign_title`, `campaign_theme`, `campaign_tone`, `global_visual_style`, `global_setting`, `concept_description`, `key_message`, `target_audience_profile`.
    -   **Music**: Use the **SONIC_LANDSCAPE** description from the Production Recipe for `background_music_prompt`.

5.  **Asset Integration:**
    -   **Asset IDs:** Use the exact Filename from `user_assets`. Look for `virtual_creator_` for digital influencers.
    -   **FORBIDDEN FILENAMES:** Do NOT use `input_file_0.png`. Use the exact keys from `user_assets`.

**CINEMATIC FIDELITY (HIGH QUALITY):**
-   **Detail is Everything:** Be specific (lens, lighting, textures).
-   **Technical Precision:** Always include a lighting style and a camera lens/movement (e.g., '35mm anamorphic, slow dolly in').

**Output Format (PIPELINE MODE):**
1. Report the storyboard as the following JSON object:
{storyboard_model.DESCRIPTION}
- **CRITICAL**: The `scenes` array MUST NOT BE EMPTY. You must populate it with exactly the mapped scene objects.

2. After successfully calling the `finalize_and_persist_storyboard` tool, do NOT provide a long celebratory summary.
3. Simply output: `🎬 **Creative Perspective Synced!** Storyboard generated and ready for media production.`

**FINAL STEP (CRITICAL):**
Once you have generated the JSON object, you MUST call the `finalize_and_persist_storyboard` tool.
"""


# --- SPECIALIZED ROUTER INSTRUCTION ---
def get_router_instruction(ctx: ReadonlyContext) -> str:
    # Safely fetch state
    parameters = ctx.session.state.get("parameters", {})
    template_name = parameters.get("template_name", "Custom")

    return f"""
You are the **Storyboard Router**. Your job is to decide which specialized agent should perform the final storyboard creation.

**Current Campaign Context:**
- Template Name: {template_name}
- Parameters: {parameters}

**Routing Rules:**
- **IF** `template_name` is 'Custom' (or 'Creative', 'Freeform', 'No Template'):
    -   Call the `storyboard_agent_creative` tool.
- **ELSE** (If `template_name` is a specific template like 'Pet Companion' or 'Feature Spotlight'):
    -   Call the `storyboard_agent_templated` tool.

**CRITICAL RULE FOR AVOIDING CRASHES**:
When calling either storyboard tool, you MUST call it with a simple context string (e.g., `request="Please create the storyboard for this campaign using the parameters in the shared state."`). DO NOT pass the massive parameters dictionary or JSON strings into the tool arguments, as this will crash the system.


**Output Rule:**
Once you have called the specialized agent, your job is done. 
Simply report the success message from the sub-agent.
"""
