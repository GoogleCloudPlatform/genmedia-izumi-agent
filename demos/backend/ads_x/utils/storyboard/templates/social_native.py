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

"""UGC / Social Native Ad Templates."""

from ..templates_model import (
    AdTemplate,
    SceneDefinition,
    CinematographyHints,
    AudioHints,
    TransitionHints,
)


def get_ugc_first_impression() -> AdTemplate:
    """Template: UGC First Impression (32s) - The Discovery"""

    return AdTemplate(
        template_name="UGC First Impression",
        industry_type="Social Native",
        use_voiceover=False,
        generate_virtual_creator=True,
        veo_method="reference_to_video",
        target_duration_seconds=32,  # Structure: 8+8+8+8
        description="A flexible discovery template. Handles both small-item unboxings and large-item reveals (furniture, decor).",
        brand_personality=["Excited", "Authentic", "Fresh"],
        music_keywords=["Lo-Fi", "Beat", "Snap", "Fresh"],
        scene_structure=[
            # --- SCENE 1: THE DISCOVERY (8s) ---
            SceneDefinition(
                scene_id="ugc_discovery_hook",
                duration_seconds=8,
                purpose="Hook & Setup.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] [PRODUCT REQUIRED] The Creator (Selfie Mode). "
                    "Positioning: [IF SMALL PRODUCT]: Holding an opened shipping box with the item peeking out. "
                    "[IF LARGE PRODUCT]: Standing naturally next to the new item in its environment. "
                    "Action: Poised to speak. [OPTIONAL]: Visually reference a problem from the brief."
                ),
                on_screen_text_hint="[TEXT: Catchy discovery hook. Max 3 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld Selfie",
                    lens_specification="Phone Camera Wide",
                    lighting_description="Indoor Room Light",
                    mood=["Happy", "Authentic"],
                    velocity_hint="Stable",
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[HOOK: Express excitement about finally seeing the product. If brief mentioned a problem, mention it here. Max 24 words].",
                    dialogue_tone="Happy, authentic, casual",
                ),
            ),
            # --- SCENE 2: THE REVEAL/INTERACTION (8s) ---
            SceneDefinition(
                scene_id="ugc_reveal_action",
                duration_seconds=8,
                purpose="Direct Reveal & Usage.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] [PRODUCT REQUIRED] The Creator (SAME CHARACTER). "
                    "Action: [IF SMALL PRODUCT]: Pulling it fully out of the box and showing it to the camera. "
                    "[IF LARGE PRODUCT]: First time using/touching/sitting on the item. "
                    "Focus: A genuine 'Wow' expression. Text Overlay: '[REACTION TEXT]'."
                ),
                on_screen_text_hint="[TEXT: Reaction text + emoji. Max 4 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Stable Medium Shot, focus on interaction",
                    lens_specification="Phone Camera",
                    lighting_description="Window Light",
                    mood=["Impressed"],
                    velocity_hint="Slow Motion",
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[REACTION: Describe the 'Aha!' moment. Mention a primary USP from the brief. Max 24 words].",
                    dialogue_tone="Genuinely impressed",
                ),
            ),
            # --- SCENE 3: SENSORY QUALITY (8s) ---
            SceneDefinition(
                scene_id="ugc_detail_check",
                duration_seconds=8,
                purpose="Materiality & Tech Specs.",
                asset_guidance=(
                    "[PRODUCT ONLY] Extreme Close-Up (Macro). "
                    "Action: Slow camera glide over the material (weave, grain, shine). "
                    "Focus: Prove quality/durability mentioned in the brief. High stability. "
                    "Text Overlay: '[FEATURE TEXT]'."
                ),
                on_screen_text_hint="[TEXT: Highlight a specific feature. Max 3 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Macro glide / Dynamic Detail",
                    lens_specification="Phone Camera Macro",
                    lighting_description="Natural Light showing texture",
                    mood=["Tactile", "Satisfying"],
                    velocity_hint="Slow Motion",
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[QUALITY: Confirm the premium feel. Mention a technical detail or warranty from the brief. Max 24 words].",
                    dialogue_tone="Helpful, demonstrating",
                ),
            ),
            # --- SCENE 4: VERDICT (8s) ---
            SceneDefinition(
                scene_id="ugc_final_opinion",
                duration_seconds=8,
                purpose="Verdict & Call to Action.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] The Creator (SAME CHARACTER). "
                    "Action: Friendly nod or wave. Relaxed starting position. "
                    "If item is nearby, they point towards it. Text Overlay: '[CTA TEXT]'."
                ),
                on_screen_text_hint="[TEXT: Clear CTA. e.g. 'Shop now' or 'Check it out'. Max 3 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld Selfie, Stable",
                    lighting_description="Natural Light",
                    mood=["Friendly"],
                    color_anchors=["Neutral"],
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[VERDICT: Final summary. Justify price/value. Mention secondary USP (shipping/warranty). Max 24 words].",
                    dialogue_tone="Friendly, low pressure",
                ),
            ),
        ],
    )


def get_ugc_honest_opinion() -> AdTemplate:
    """Template: UGC Honest Opinion (32s) - The Trust Builder"""

    return AdTemplate(
        template_name="UGC Honest Opinion",
        industry_type="Social Native",
        use_voiceover=False,
        generate_virtual_creator=True,
        veo_method="reference_to_video",
        target_duration_seconds=32,  # Structure: 8+8+8+8
        description="A long-term trust-focused review. High conversion for lifestyle products.",
        brand_personality=["Honest", "Direct", "Experienced"],
        music_keywords=["Chill", "Lo-Fi", "Talk", "Authentic"],
        scene_structure=[
            # --- SCENE 1: THE REALITY CHECK (8s) ---
            SceneDefinition(
                scene_id="ugc_reality_hook",
                duration_seconds=8,
                purpose="Credibility & Timeline.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] [PRODUCT REQUIRED] The Creator (Selfie Mode). "
                    "They are sitting comfortably with the product in a real room. "
                    "Action: Thoughtful expression, poised to speak. Text Overlay: '[TIMELINE TEXT]'."
                ),
                on_screen_text_hint="[TEXT: Time spent with product. e.g. '7 Days Later'. Max 3 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld Selfie, Stable",
                    lens_specification="Phone Camera",
                    lighting_description="Natural Window Light",
                    mood=["Serious", "Approachable"],
                    color_anchors=["Natural"],
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[HOOK: Establish timeline and admit an initial hesitation or doubt from the brief. Max 24 words].",
                    dialogue_tone="Direct, honest, conversational",
                ),
            ),
            # --- SCENE 2: THE FEATURE PROOF (8s) ---
            SceneDefinition(
                scene_id="ugc_performance_demo",
                duration_seconds=8,
                purpose="Action Proof.",
                asset_guidance=(
                    "[PRODUCT ONLY] Mid-shot or POV. "
                    "The product in use in its natural environment (e.g. skin absorbing cream, sofa being sat on). "
                    "Action: Clear functional demonstration of the main USP from the brief."
                ),
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Stable shot, focus on function",
                    lens_specification="Phone Camera",
                    lighting_description="Ambient Room Light",
                    mood=["Functional", "Satisfied"],
                    velocity_hint="Action",
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[PROOF: Describe how well it actually works in real life. Use specific brief details. Max 24 words].",
                    dialogue_tone="Impressed, proving a point",
                ),
            ),
            # --- SCENE 3: LIFESTYLE FIT (8s) ---
            SceneDefinition(
                scene_id="ugc_daily_routine",
                duration_seconds=8,
                purpose="Routine Integration & Surprise Detail.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] [PRODUCT REQUIRED] The Creator (SAME CHARACTER). "
                    "Close up. They show a secondary detail that surprised them (e.g. easy cleaning, warranty, portability). "
                    "Action: Showing the specific detail while speaking."
                ),
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld Selfie, Close up",
                    lens_specification="Phone Camera",
                    lighting_description="Natural Light",
                    mood=["Confidential"],
                    velocity_hint="Stable",
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[VALUE: Mention the secondary USP or integration into daily life. Confirm if worth the price. Max 24 words].",
                    dialogue_tone="Confidential, advice",
                ),
            ),
            # --- SCENE 4: CTA (8s) ---
            SceneDefinition(
                scene_id="ugc_opinion_cta",
                duration_seconds=8,
                purpose="Final Verdict.",
                asset_guidance=(
                    "[CHARACTER REQUIRED] The Creator (SAME CHARACTER). "
                    "Action: Casual wave or pointing to a link. Friendly sign-off. "
                    "Text Overlay: '[FINAL TEXT]'."
                ),
                on_screen_text_hint="[TEXT: Casually encouraging CTA. Max 3 words]",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld Selfie",
                    lighting_description="Natural Light",
                    mood=["Friendly"],
                    color_anchors=["Neutral"],
                ),
                audio_hints=AudioHints(
                    dialogue_hint="[CTA: Casual sign-off and recommendation. Catch you in the next one! Max 24 words].",
                    dialogue_tone="Friendly, sign-off",
                ),
            ),
        ],
    )
