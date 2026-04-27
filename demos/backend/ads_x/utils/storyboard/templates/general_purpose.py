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

"""General Purpose Ad Templates."""

from ..templates_model import (
    AdTemplate,
    SceneDefinition,
    CinematographyHints,
    AudioHints,
    TransitionHints,
)


def get_general_purpose_problem_solution() -> AdTemplate:
    """Template: Problem/Solution Highlight (32s) - V7 Density & Payoff"""
    return AdTemplate(
        template_name="Problem/Solution Highlight",
        industry_type="General Purpose",
        target_duration_seconds=32,  # Structure: 4+4+8+6+6+4
        description="High information density: Problem -> Reveal -> Flow -> Tech Spec -> Living the Benefit.",
        brand_personality=["Refreshment", "Clarity", "Premium"],
        music_keywords=["Minimal", "Rhythmic", "Bright", "Pop"],
        scene_structure=[
            # --- SCENE 1: THE STAGNATION (4s) ---
            SceneDefinition(
                scene_id="problem_state",
                duration_seconds=4,
                purpose="Establish the 'Unresolved State'.",
                asset_guidance="A static, slightly dull shot of the problem state (e.g. empty room, messy desk, blank screen).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Completely Static (Tripod Lock-off)",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Flat, low-contrast lighting",
                    mood=["Boring", "Cold", "Waiting"],
                    color_anchors=["Cool Grey", "Desaturated Colors"],
                ),
            ),
            # --- SCENE 2: THE CATALYST (4s) ---
            SceneDefinition(
                scene_id="solution_reveal",
                duration_seconds=4,
                purpose="The Product breaks the stagnation.",
                asset_guidance="The Product cuts in, centered, bursting with light or motion.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Push-In (Dolly Forward)",
                    lens_specification="35mm Lens",
                    lighting_description="Bright 'Hero' Lighting, High Contrast",
                    mood=["Relieved", "Fresh", "New"],
                    color_anchors=["Brand Color", "Bright White"],
                ),
            ),
            # --- SCENE 3: THE FLOW (8s) ---
            SceneDefinition(
                scene_id="demo_action",
                duration_seconds=8,
                purpose="The 'Effortless' Process (Broad Action).",
                asset_guidance="A continuous, smooth motion shot of the product performing its function effortlessly (cleaning, pouring, or processing).",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Smooth tracking movement following the leading edge of the action",
                    lens_specification="50mm Standard Lens",
                    lighting_description="High-Key Commercial Lighting",
                    mood=["Satisfying", "Effortless"],
                    color_anchors=["Vibrant", "Clear"],
                ),
            ),
            # --- SCENE 4: THE TECH FLEX (6s) ---
            SceneDefinition(
                scene_id="tech_detail",
                duration_seconds=6,
                purpose="The 'Mechanism'. Prove why it works.",
                asset_guidance="Extreme Close-Up (Macro) of the specific mechanism, ingredient, or feature that drives the result. Highlighting precision.",
                on_screen_text_hint="Precision Technology.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Macro shot with internal movement (e.g. spinning, glowing, clicking)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Sharp, Contrast-heavy 'Tech' lighting (Blue/White accents)",
                    mood=["Innovative", "Smart", "Powerful"],
                    color_anchors=["Metallic", "Light Blue", "Silver"],
                ),
            ),
            # --- SCENE 5: THE LIFESTYLE PAYOFF (6s) ---
            SceneDefinition(
                scene_id="lifestyle_result",
                duration_seconds=6,
                purpose="The 'Living the Dream' State. (Environment + Human).",
                asset_guidance="A wide, atmospheric shot showing the User RELAXING in the fully resolved environment. They are enjoying the result, not working.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Pull-Back (Dolly Out) revealing the person situated in the beautiful space",
                    lens_specification="24mm Wide Angle Lens",
                    lighting_description="Natural Sunlight, Airy, 'Golden Hour' spilling into the room",
                    mood=["Pristine", "Happy", "Relieved"],
                    color_anchors=["Warm Skin Tones", "Sunlight", "White"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The product centered on a clean background with the logo. A perfect static layout.",
                on_screen_text_hint="Shop Now",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, smooth Push-In (Dolly Forward) on the static graphic",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Clean Studio Gradient",
                    mood=["Professional"],
                    velocity_hint="Smooth Linear Motion (No Morphing)",
                    color_anchors=["Brand Color"],
                ),
            ),
        ],
    )


def get_general_purpose_problem_solution_fast_pace() -> AdTemplate:
    """Template: Problem/Solution (24s) - The Disruption Arc"""
    return AdTemplate(
        template_name="Problem/Solution (Fast)",
        industry_type="General Purpose",
        target_duration_seconds=24,  # Structure: 2+3.5+3+3.5+3+2.5+2.5+4
        description="A high-velocity 8-scene arc that disrupts a static 'Problem' state with a dynamic 'Solution', emphasizing mechanism and payoff.",
        brand_personality=["Efficient", "Innovative", "Premium", "Clear"],
        music_keywords=["Modern Pop", "Rhythmic Bass", "Snap Transition", "Upbeat"],
        scene_structure=[
            # --- SCENE 1: THE STASIS (2s) ---
            SceneDefinition(
                scene_id="problem_static",
                duration_seconds=2,
                purpose="Establish the Need. The 'Before' state.",
                asset_guidance="A completely static, slightly dull shot of the 'Unresolved State'. The lighting is flat or dim. Nothing is moving. It visually represents the problem (e.g., clutter, dullness, or waiting) effectively.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Lock-off",
                    lens_specification="35mm Wide Angle",
                    lighting_description="Flat, Low-Contrast, Desaturated",
                    mood=["Boring", "Stuck", "Waiting"],
                    velocity_hint="Zero Motion",
                ),
            ),
            # --- SCENE 2: THE ARRIVAL (3.5s) ---
            SceneDefinition(
                scene_id="solution_entry",
                duration_seconds=3.5,
                purpose="The Catalyst. Disruption.",
                asset_guidance="Visual Disruption. The Hero Product is ALREADY centered and dominant in the frame from the very first millisecond. The action is a violent 'Light Blast' or 'Crash Zoom' that hits the product, instantly shifting the atmosphere from the previous scene's dullness to high-energy brightness. The product itself stays planted; the energy comes from the camera and light.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast Crash Zoom onto the Static Product",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Sudden Flash / Spot Light turning on",
                    mood=["Energetic", "New", "Powerful"],
                    velocity_hint="Impact Zoom",
                ),
            ),
            # --- SCENE 3: THE ACTION (3s) ---
            SceneDefinition(
                scene_id="demo_flow",
                duration_seconds=3,
                purpose="The Transformation. Seeing it work.",
                asset_guidance="A smooth, satisfying motion of the product performing its primary function. It glides, wipes, or processes effortlessly, leaving a clear trail of 'Success' (e.g., a clean path, a hydrated glow, or a completed task) behind it.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Tracking Shot following the leading edge of the action",
                    lens_specification="50mm Standard Lens",
                    lighting_description="High-Key, Clear Commercial Lighting",
                    mood=["Satisfying", "Effortless"],
                    velocity_hint="Fluid Motion",
                ),
            ),
            # --- SCENE 4: THE TECH FLEX (3.5s) ---
            SceneDefinition(
                scene_id="tech_macro",
                duration_seconds=3.5,
                purpose="The Mechanism. Authority/Science.",
                asset_guidance="Extreme Macro close-up of the specific internal mechanism or ingredient that makes the product work. Focus on the precision of the technology or the purity of the material (e.g., a laser beam, a digital chip, a water droplet, or a specific texture).",
                on_screen_text_hint="Precision Tech",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Macro with internal motion (spinning/glowing)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Sharp, Contrast-heavy 'Tech' lighting",
                    mood=["Innovative", "Smart"],
                    velocity_hint="Active Tech",
                ),
            ),
            # --- SCENE 5: THE AESTHETIC ANCHOR (3s) ---
            SceneDefinition(
                scene_id="product_hero_context",
                duration_seconds=3,
                purpose="The 'Job Done' Hero Shot. Product beauty.",
                asset_guidance="A static 'Beauty Shot' of the Hero Product sitting perfectly in the resolved/clean environment. The product looks triumphant and sleek. A subtle light flare or reflection moves across its surface, emphasizing that the work is finished and the product is the star.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Low Angle, Static Hero Shot",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Hero Lighting (Backlight/Rim light)",
                    mood=["Triumphant", "Sleek"],
                    velocity_hint="Stillness",
                ),
            ),
            # --- SCENE 6: THE WIDE RESULT (2.5s) ---
            SceneDefinition(
                scene_id="result_wide",
                duration_seconds=2.5,
                purpose="The Outcome. The 'After' state.",
                asset_guidance="Wide shot of the fully resolved state. The chaos from Scene 1 is gone, replaced by order, brightness, and space (e.g., a sparkling room, a glowing face, or a completed project board). The environment feels airy and complete.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Dolly Out (Pull Back) to reveal the perfection",
                    lens_specification="24mm Wide Angle",
                    lighting_description="Natural Sunlight / Airy / Fresh",
                    mood=["Pristine", "Complete"],
                    velocity_hint="Smooth Reveal",
                ),
            ),
            # --- SCENE 7: THE LIVING PROOF (2.5s) ---
            SceneDefinition(
                scene_id="human_payoff",
                duration_seconds=2.5,
                purpose="Emotion + Lifestyle combined.",
                asset_guidance="A focused Close-Up or Mid-Close-Up capturing a specific gesture of satisfaction. Instead of full-body movement, focus on a 'Micro-Action' that proves the result. Examples: A genuine smile breaking out, a slow exhale of relief, hands clapping dust off, a thumbs-up, or eyes closing to savor the moment. The movement is contained and intimate.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera, Shallow Depth of Field (Bokeh)",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Warm, Inviting Natural Light (Golden Hour or Soft Window)",
                    mood=["Happy", "Free", "Relieved"],
                    velocity_hint="Human Reaction",
                ),
            ),
            # --- SCENE 8: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The product centered on a clean background with the logo. A perfect static layout.",
                on_screen_text_hint="[Brand Slogan] or 'Upgrade Today'",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, smooth Push-In (Dolly Forward) on the static graphic",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Clean Studio Gradient",
                    mood=["Professional"],
                    velocity_hint="Smooth Linear Motion (No Morphing)",
                    color_anchors=["Brand Color"],
                ),
            ),
        ],
    )


def get_feature_spotlight() -> AdTemplate:
    """Template: Feature Spotlight (32s) - V4 Cinematic Engineering"""
    return AdTemplate(
        template_name="Feature Spotlight",
        industry_type="General Purpose",
        target_duration_seconds=32,  # Structure: 4+6+6+6+6+4
        description="A high-end 'Tabletop' commercial template focusing on materials, physics, and architectural presence.",
        brand_personality=["Premium", "Innovative", "Precision"],
        music_keywords=["Deep Bass", "Rhythmic", "Minimal", "Industrial", "Clockwork"],
        scene_structure=[
            # --- SCENE 1: THE GLANCING LIGHT (4s) ---
            SceneDefinition(
                scene_id="tease",
                duration_seconds=4,
                purpose="The Mystery Hook. Form over Function.",
                asset_guidance="The product in deep shadow. A sharp, narrow beam of light (rim light) travels slowly along the edge or profile of the object, revealing its sleek silhouette and material reflectivity.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static camera, subject is back-lit",
                    lens_specification="85mm Telephoto (flattens perspective)",
                    lighting_description="Moving 'Rim Light' only. High contrast, Deep Blacks, Bright Edges",
                    mood=["Mysterious", "Premium", "Sleek"],
                    color_anchors=["Black", "Metallic Silver/Gold/Glass"],
                ),
            ),
            # --- SCENE 2: THE TACTILE MACRO (6s) ---
            SceneDefinition(
                scene_id="texture_macro",
                duration_seconds=6,
                purpose="Sensory Validation. The 'Touch' Test.",
                asset_guidance="Extreme Macro shot traversing the product's primary surface. Focus is strictly on the *micro-texture* to prove build quality. No background visible.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, steady panning shot across the surface (Scanner style)",
                    lens_specification="100mm Macro Lens, Focus distance < 5cm",
                    lighting_description="Hard 'Raking Light' from the side to reveal surface bumps/grain",
                    mood=["Tactile", "High-End", "Industrial"],
                    color_anchors=["Material Color", "Highlight Sheen"],
                ),
            ),
            # --- SCENE 3: THE PHYSICS ENGINE (6s) ---
            SceneDefinition(
                scene_id="action_function",
                duration_seconds=6,
                purpose="Energy & Physics. The 'Alive' Moment.",
                asset_guidance="Super Slow Motion (High Speed) shot. EITHER: The product performing a mechanical action (clicking, opening, spraying) OR: An element interacting with the product (water splash, smoke stream, or light flare) to show resistance and durability.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Phantom High-Speed Camera (1000fps), Frozen in time",
                    lens_specification="50mm Standard Lens",
                    lighting_description="High-Key Strobe Lighting (Freezes motion, crisp edges)",
                    mood=["Dynamic", "Powerful", "Engineering"],
                    color_anchors=["Sharp Details", "Crystal Clear"],
                ),
            ),
            # --- SCENE 4: THE JIB REVEAL (6s) ---
            SceneDefinition(
                scene_id="context_wide",
                duration_seconds=6,
                purpose="Scale & Dominance. The 'Monument' Shot.",
                asset_guidance="A wide, establishing shot of the product placed in a stunning, minimalist architectural environment. The camera rises slowly (Jib Up), revealing the product as the centerpiece of the space.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow 'Jib Up' (Boom Up) movement, rising from floor level to eye level",
                    lens_specification="24mm Wide Angle (To show the environment)",
                    lighting_description="Soft, diffused Architectural Lighting (Window light or Softbox)",
                    mood=["Sophisticated", "Belonging", "Grand"],
                    color_anchors=["Neutral Background", "Complementary Tones"],
                ),
            ),
            # --- SCENE 5: THE MONOLITH (6s) ---
            SceneDefinition(
                scene_id="full_reveal",
                duration_seconds=6,
                purpose="The Hero. Authority.",
                asset_guidance="The 'Hero Shot'. A low-angle view looking up at the product, making it look larger than life. The lighting shifts to a dramatic 'God Ray' or Volumetric backlight.",
                on_screen_text_hint="Precision Engineered.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Low Angle (Hero Perspective), slight push-in",
                    lens_specification="35mm Wide-Standard",
                    lighting_description="Volumetric Backlighting (God Rays) creating a halo effect",
                    mood=["Confident", "Perfect", "Dominant"],
                    color_anchors=["Brand Colors", "Glow"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The logo embossed/floating on a surface matching the product's primary material. A perfect static layout.",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, majestic Pull-Back (Dolly Out) revealing the texture",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Dramatic Spotlights",
                    mood=["Final"],
                    velocity_hint="Atmospheric Drift (No Morphing)",
                    color_anchors=["Dark", "Gold/Silver/Brand Color"],
                ),
            ),
        ],
    )


def get_feature_spotlight_fast_pace() -> AdTemplate:
    """Template: Feature Spotlight (Fast) - The Engineering Beat"""
    return AdTemplate(
        template_name="Feature Spotlight (Fast)",
        industry_type="General Purpose",
        target_duration_seconds=23,  # Structure: 2.5+2.5+2.5+3+3+2.5+3+4
        description="A high-velocity, rhythmic tabletop montage focusing on materials, physics, and architectural presence.",
        brand_personality=["Premium", "Innovative", "Precision"],
        music_keywords=["Deep Bass", "Clockwork Percussion", "Glitch", "Industrial"],
        scene_structure=[
            # --- SCENE 1: THE SILHOUETTE (2.5s) ---
            SceneDefinition(
                scene_id="tease_silhouette",
                duration_seconds=2.5,
                purpose="The Mystery Hook. Form over Function.",
                asset_guidance="The Hero Product is shrouded in darkness. A sharp, narrow beam of light (Rim Light) travels rapidly along the edge or profile, briefly illuminating the silhouette before vanishing. It teases the shape without revealing the details.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera",
                    lens_specification="85mm Telephoto (flattens perspective)",
                    lighting_description="Moving 'Rim Light' only. High contrast, Deep Blacks.",
                    mood=["Mysterious", "Sleek"],
                    velocity_hint="Light Sweep",
                ),
            ),
            # --- SCENE 2: THE SURFACE (2.5s) ---
            SceneDefinition(
                scene_id="texture_scan",
                duration_seconds=2.5,
                purpose="Sensory Validation. The 'Touch' Test.",
                asset_guidance="Extreme Macro shot traversing the product's primary surface. The camera or light scans across the material (e.g., brushed metal, grain leather, or mesh) to reveal the micro-texture quality.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast panning shot across the surface",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Raking Light to reveal texture bumps/grain",
                    mood=["Tactile", "High-End"],
                    velocity_hint="Fast Scan",
                ),
            ),
            # --- SCENE 3: THE COMPONENT (2.5s) ---
            SceneDefinition(
                scene_id="detail_component",
                duration_seconds=2.5,
                purpose="Precision Engineering. The 'Jewel'.",
                asset_guidance="A static, razor-sharp close-up of a specific engineering detail (e.g., a camera lens, a watch dial, a hinge, or a button). A 'Strobe Light' or rapid lighting shift highlights the machined edges or precise assembly.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Locked-off Macro",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Strobe / Flash Lighting",
                    mood=["Industrial", "Precise"],
                    velocity_hint="Light Pulse",
                ),
            ),
            # --- SCENE 4: THE PHYSICS (3s) ---
            SceneDefinition(
                scene_id="action_physics",
                duration_seconds=3,
                purpose="Energy & Durability. The 'Alive' Moment.",
                asset_guidance="Super Slow Motion shot of an interaction. EITHER the product performing a function (e.g., opening, clicking) OR an element interacting with it (e.g., water splashing, smoke swirling, or light flaring). Focus on the 'Zero Motion Blur' clarity of the high-speed capture.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Phantom High-Speed Camera (1000fps)",
                    lens_specification="50mm Standard Lens",
                    lighting_description="High-Key Strobe Lighting (Freezes motion)",
                    mood=["Dynamic", "Powerful"],
                    velocity_hint="Frozen Action",
                ),
            ),
            # --- SCENE 5: THE JIB REVEAL (3s) ---
            SceneDefinition(
                scene_id="context_grand",
                duration_seconds=3,
                purpose="Scale & Dominance. The 'Monument' Shot.",
                asset_guidance="A wide establishing shot. The camera rises (Jib Up) from a low position to a high position, revealing the product sitting like a monument in a minimalist architectural space.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast 'Jib Up' movement",
                    lens_specification="24mm Wide Angle",
                    lighting_description="Soft Architectural Lighting",
                    mood=["Grand", "Sophisticated"],
                    velocity_hint="Vertical Reveal",
                ),
            ),
            # --- SCENE 6: THE MONOLITH (2.5s) ---
            SceneDefinition(
                scene_id="hero_angle",
                duration_seconds=2.5,
                purpose="The Hero. Authority.",
                asset_guidance="Low-angle 'Hero Shot' looking up at the product. It dominates the frame. A Volumetric 'God Ray' or backlight shifts behind it, creating a halo effect.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Low Angle",
                    lens_specification="35mm Standard Lens",
                    lighting_description="Volumetric Backlighting (God Rays)",
                    mood=["Dominant", "Perfect"],
                    velocity_hint="Light Shift",
                ),
            ),
            # --- SCENE 7: THE LIFESTYLE GLIMPSE (3s) ---
            SceneDefinition(
                scene_id="human_touch",
                duration_seconds=3,
                purpose="Human Connection (Optional but recommended).",
                asset_guidance="A stylized, anonymous human interaction. A hand reaches in to touch, hold, or use the product. The focus remains on the product's reaction to the touch (e.g., screen lighting up, button depressing, or just the fit in the hand).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Mid-Shot",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Natural Light",
                    mood=["Desirable", "Usable"],
                    velocity_hint="Gentle Interaction",
                ),
            ),
            # --- SCENE 8: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Seal.",
                asset_guidance="The logo embossed or floating on a surface matching the product's primary material. A perfect static layout.",
                on_screen_text_hint="[Brand Slogan] or 'Engineered for [Use Case]'",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, majestic Pull-Back (Dolly Out) revealing the texture",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Dramatic Spotlights",
                    mood=["Final"],
                    velocity_hint="Atmospheric Drift (No Morphing)",
                    color_anchors=["Dark", "Gold/Silver/Brand Color"],
                ),
            ),
        ],
    )
