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

"""Vertical Specific Ad Templates."""

from ..templates_model import (
    AdTemplate,
    SceneDefinition,
    CinematographyHints,
    AudioHints,
    TransitionHints,
)


def get_pet_companion() -> AdTemplate:
    """Template: Pet Companion (32s) - V7 Product Continuity"""
    return AdTemplate(
        template_name="Pet Companion",
        industry_type="Vertical-Specific",
        vertical_category="Pets",
        target_duration_seconds=32,  # Structure: 4+4+8+4+8+4
        description="A complete emotional arc: Curiosity -> Action -> Product -> Satisfaction -> Love.",
        brand_personality=["Playful", "Loyal", "Nurturing"],
        music_keywords=["Acoustic Guitar", "Whistling", "Upbeat Folk", "Warm"],
        scene_structure=[
            # --- SCENE 1: THE ANTICIPATION (4s) ---
            SceneDefinition(
                scene_id="hook",
                duration_seconds=4,
                purpose="The 'Nose Boop' Hook. Immediate intimacy.",
                asset_guidance="Extreme Close-Up (ECU) of the pet's nose/eyes, sniffing or staring intensely at the lens.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static, Center-framed 'Nose Boop' perspective",
                    lens_specification="100mm Macro Lens, extremely shallow depth of field (eyes in focus, ears blurred)",
                    lighting_description="Natural Window Light reflecting in eyes (Catchlights)",
                    mood=["Curious", "Adorable", "Intimate"],
                    color_anchors=["Natural Fur Tones", "Soft White", "Bright Eyes"],
                ),
            ),
            # --- SCENE 2: THE ACTIVITY (4s) ---
            SceneDefinition(
                scene_id="action",
                duration_seconds=4,
                purpose="High Energy / usage context.",
                asset_guidance="Low-angle action shot of the pet moving dynamically (running, jumping, or eating enthusiastically).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Low Angle 'Worm's Eye View', Fast Tracking/Gimbal movement following the pet",
                    lens_specification="16mm Wide Angle (GoPro style perspective)",
                    lighting_description="Bright Outdoor Sunlight or High-Key Indoor",
                    mood=["Energetic", "Happy", "Wild"],
                    color_anchors=[
                        "Vibrant Green (Grass)",
                        "Sky Blue",
                        "Saturated Colors",
                    ],
                ),
            ),
            # --- SCENE 3: THE PRODUCT HERO (8s) ---
            SceneDefinition(
                scene_id="product_int",
                duration_seconds=8,
                purpose="The Interaction. The Brand is the Hero.",
                asset_guidance="A seamless low-angle shot of the pet enthusiastically eating/using the product. The Product Packaging is clearly visible in the background (soft focus) but legible.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Smooth, slow sideways gliding movement (Truck Right) at eye-level with the product",
                    lens_specification="35mm Standard Lens (Natural Perspective)",
                    lighting_description="Golden Hour Backlighting (creating a halo on fur)",
                    mood=["Premium", "Safe"],
                    color_anchors=["Warm Gold", "Product Brand Color"],
                ),
            ),
            # --- SCENE 4: THE HAPPY SIGNAL (4s) ---
            SceneDefinition(
                scene_id="reaction",
                duration_seconds=4,
                purpose="The 'Happy Dance' triggered by the product.",
                asset_guidance="A medium-wide shot showing the whole pet's body language signaling happiness (tippy taps, happy dance, or zoomies). The Product is visible in the frame (e.g., sitting in the foreground or slightly to the side), linking the joy directly to the brand.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld, slightly shaky (to capture the vibration/energy)",
                    lens_specification="24mm Wide Angle Lens",
                    lighting_description="Warm ambient light",
                    mood=["Excited", "Joyful", "Satisfied"],
                    color_anchors=["Warm Fur Tones", "Soft Background"],
                ),
            ),
            # --- SCENE 5: THE BOND (8s) ---
            SceneDefinition(
                scene_id="connection",
                duration_seconds=8,
                purpose="Emotional Payoff enabled by the product.",
                asset_guidance="Medium shot of the Owner and Pet sharing a quiet moment (cuddling/petting). The Product is subtly placed in the scene (e.g. resting on the table or floor nearby), creating a subconscious link between the product and this peaceful moment.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static or very slow handheld sway, focus on the physical touch",
                    lens_specification="85mm f/1.4 Portrait Lens (Creamy Bokeh)",
                    lighting_description="Soft 'Blanket' Lighting, warm and cozy",
                    mood=["Peaceful", "Loved", "Content"],
                    color_anchors=["Pastel Tones", "Warm Skin", "Soft Beiges"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="Logo centered on a clean background with a subtle paw print design.",
                on_screen_text_hint="Give them the best.",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static with atmospheric bokeh",
                    lighting_description="Bright, happy colors, clean layout",
                    mood=["Trustworthy"],
                    velocity_hint="Atmospheric Drift",
                    color_anchors=["Brand Color", "White"],
                ),
            ),
        ],
    )


def get_pet_companion_fast_pace() -> AdTemplate:
    """Template: Pet Companion (24s) - The Zoomies Arc"""
    return AdTemplate(
        template_name="Pet Companion (Fast)",
        industry_type="Vertical-Specific",
        vertical_category="Pets",
        target_duration_seconds=24,  # Structure: 2+2.5+3.5+3+3+3+3+4
        description="A high-energy 8-scene montage capturing the chaotic joy of pets, anchoring the energy to the product.",
        brand_personality=["Playful", "Energetic", "Happy", "Loyal"],
        music_keywords=[
            "Fast Acoustic Strumming",
            "Whistling",
            "Upbeat Folk",
            "Hand Claps",
        ],
        scene_structure=[
            # --- SCENE 1: THE NOSE (2s) ---
            SceneDefinition(
                scene_id="hook_nose",
                duration_seconds=2,
                purpose="Instant Hook. Sensory curiosity.",
                asset_guidance="Extreme Close-Up (ECU) of the pet's nose sniffing the camera lens rapidly. The nose twitches and fog appears on the glass, creating an immediate, cute connection.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static, Center-framed 'Nose Boop' perspective",
                    lens_specification="100mm Macro Lens (Fisheye distortion optional)",
                    lighting_description="Natural Window Light reflecting in eyes",
                    mood=["Curious", "Adorable"],
                    velocity_hint="Fast Twitch",
                ),
            ),
            # --- SCENE 2: THE ZOOMIES (2.5s) ---
            SceneDefinition(
                scene_id="action_run",
                duration_seconds=2.5,
                purpose="High Energy context. The 'Need'.",
                asset_guidance="Low-angle action shot of the pet sprinting directly towards the camera. The movement is continuous, linear, and unstoppable (no turning, lunging, or stopping). The camera tracks backwards rapidly, matching the pet's speed. Focus on the aerodynamic force: ears pinned back, paws blurring, and fur rippling with speed.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Low Angle 'Worm's Eye View', Fast Backward Tracking",
                    lens_specification="16mm Wide Angle (GoPro style)",
                    lighting_description="High-Key, Bright Sunlight",
                    mood=["Energetic", "Wild"],
                    velocity_hint="Linear High Speed",
                ),
            ),
            # --- SCENE 3: THE TRIGGER (3.5s) ---
            SceneDefinition(
                scene_id="product_quality",
                duration_seconds=3.5,
                purpose="The 'Why'. Visualizing the Motivation/Quality.",
                asset_guidance="A sharp, sensory cutaway revealing the 'Trigger' that attracts the pet. If Food: A luscious macro shot of fresh source ingredients (raw meat, fish, vegetables, etc.) or the texture of the food itself. If Hard Goods (Toys/Gear/etc.): A close-up of the material quality/durability. If Service: The iconic shipping box. This shot isolates the 'Object of Desire'.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Push-In or Static Macro",
                    lens_specification="85mm Telephoto (Food/Product spec)",
                    lighting_description="Studio 'Hero' Lighting. High contrast texture.",
                    mood=["Appetizing", "Premium", "Desirable"],
                    velocity_hint="Slow & Savory",
                ),
            ),
            # --- SCENE 4: THE ENGAGEMENT (3s) ---
            SceneDefinition(
                scene_id="product_use",
                duration_seconds=3,
                purpose="The Solution. Joyful Possession.",
                asset_guidance="A stable, happy shot of the pet engaging with the product in a way appropriate to the category. This could be rhythmically eating (Food), holding the item proudly in their mouth (Toy), resting comfortably upon it (Bed), or sitting confidently next to it (Gear/Care). The focus is on the pet's satisfaction and 'ownership' of the item, rather than chaotic action. The Brand Logo is clearly visible.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Eye-Level shot, focused on the face/expression",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Golden Hour Backlighting (Halo effect)",
                    mood=["Satisfying", "Content", "Proud"],
                    velocity_hint="Rhythmic Motion",
                ),
            ),
            # --- SCENE 5: THE HAPPY DANCE (3s) ---
            SceneDefinition(
                scene_id="happy_signal",
                duration_seconds=3,
                purpose="Visual Proof of Joy.",
                asset_guidance="A medium-wide shot of the pet doing a 'Happy Dance' (tippy taps, spinning, or play bow) right next to the Hero Product. The pet looks energetic and satisfied, linking the joy to the item.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld static shot, framed wide to capture full body movement",
                    lens_specification="24mm Wide Angle Lens",
                    lighting_description="Bright, even ambient light",
                    mood=["Joyful", "Satisfied"],
                    velocity_hint="Vibrating Energy",
                ),
            ),
            # --- SCENE 6: THE BOND (3s) ---
            SceneDefinition(
                scene_id="human_love",
                duration_seconds=3,
                purpose="Emotional Payoff.",
                asset_guidance="A warm moment between Owner and Pet. The owner hugs, pets, or praises the animal. The Hero Product is subtly visible in the foreground or background, acting as the facilitator of this love.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow handheld sway, focus on the physical touch",
                    lens_specification="85mm Portrait Lens (Soft Background)",
                    lighting_description="Soft 'Blanket' Lighting, warm and cozy",
                    mood=["Loved", "Thankful"],
                    velocity_hint="Gentle Motion",
                ),
            ),
            # --- SCENE 7: THE NAP (3s) ---
            SceneDefinition(
                scene_id="post_play_nap",
                duration_seconds=3,
                purpose="The Result: Satisfaction/Calm.",
                asset_guidance="Close-up of the pet in a state of total exhaustion/relaxation (sleeping, panting happily, or slow blinking) next to the product. A 'Breathing' zoom emphasizes the peace.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static shot with very slow, subtle zoom in",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Warm, low-contrast 'Nap' lighting",
                    mood=["Peaceful", "Dreamy"],
                    velocity_hint="Stillness",
                ),
            ),
            # --- SCENE 8: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The brand logo popping onto screen with a playful background.",
                on_screen_text_hint="[Playful Slogan] or 'Treat Them Best'",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Rapid Push-In (Crash Zoom) on static logo",
                    lighting_description="Studio Lighting",
                    mood=["Trustworthy"],
                    velocity_hint="Impact Zoom",
                    color_anchors=["Brand Color", "White"],
                ),
            ),
        ],
    )


def get_apparel_style_showcase() -> AdTemplate:
    """Template: Style Showcase (32s) - V5 Framing-First Approach"""
    return AdTemplate(
        template_name="Style Showcase",
        industry_type="Vertical-Specific",
        vertical_category="Apparel",
        target_duration_seconds=32,  # Structure: 6+4+6+4+8+4
        description="A rhythmic interplay between 'Full Body Attitude' and 'Fabric Sensory Details'.",
        brand_personality=["Confident", "Stylish", "Trendsetting"],
        music_keywords=["Deep House", "Runway Beat", "Bass Heavy", "Vocal Chops"],
        scene_structure=[
            # --- SCENE 1: THE POWER WALK (6s) ---
            SceneDefinition(
                scene_id="hero_walk",
                duration_seconds=6,
                purpose="Establish the 'Look' and the Attitude.",
                asset_guidance="3/4 Profile Full Body shot of the model walking confidently diagonally past the camera (from mid-ground to foreground). They are looking ahead, not directly at the lens.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Low Angle, Trucking Shot moving alongside the subject at the same speed",
                    lens_specification="35mm Wide Angle Lens",
                    lighting_description="Natural 'Golden Hour' side-lighting (creating contrast/depth on the fabric)",
                    mood=["Confident", "Powerful", "Forward-Moving"],
                    color_anchors=["Sky Blue", "Warm Sun", "Outfit Color"],
                ),
            ),
            # --- SCENE 2: THE SENSORY MACRO (4s) ---
            SceneDefinition(
                scene_id="fabric_detail",
                duration_seconds=4,
                purpose="Sell the Quality (Materiality).",
                asset_guidance="A slow, detailed Macro pan traversing the surface of the Hero Product. The shot isolates the specific material texture (the weave of the fabric, the gloss of the frame, or the grain of the leather) to prove quality. No hands or external distractions—just the product material filling the frame.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, steady panning movement across the surface",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Neutral, High-Fidelity Studio Lighting to show true colors",
                    mood=["Tactile", "High-End", "Authentic"],
                    color_anchors=["Exact Product Color", "Monochromatic"],
                ),
            ),
            # --- SCENE 3: THE SPIN / FLOW (6s) ---
            SceneDefinition(
                scene_id="motion_showcase",
                duration_seconds=6,
                purpose="Show how it Fits in Motion.",
                asset_guidance="Medium shot of the model performing a dynamic movement to show the garment's flexibility and fit (e.g. a spin, a jump, or a sudden turn).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Motion (60fps), Camera orbits 180 degrees around subject",
                    lens_specification="50mm Standard Lens",
                    lighting_description="High Contrast Editorial Lighting (Studio or Sun)",
                    mood=["Energetic", "Free"],
                    color_anchors=["Vibrant", "Motion Blur"],
                ),
            ),
            # --- SCENE 4: THE ACCESSORY / ACCENT (4s) ---
            SceneDefinition(
                scene_id="detail_accent",
                duration_seconds=4,
                purpose="The Finishing Touch.",
                asset_guidance="Close-up detail shot of a specific design element (zipper, buttons, shoes, or logo).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Dutch Angle (tilted), fast whip-pan into focus",
                    lens_specification="85mm Telephoto",
                    lighting_description="Sharp, focused spotlight",
                    mood=["Edgy", "Sharp"],
                    color_anchors=["Metallic", "Contrast"],
                ),
            ),
            # --- SCENE 5: THE LIFESTYLE PORTRAIT (8s) ---
            SceneDefinition(
                scene_id="lifestyle_portrait",
                duration_seconds=8,
                purpose="The Identity (Face) + The Product (Body).",
                asset_guidance="A relaxed 'Lifestyle Portrait' where the model engages with the camera (smiling/confident). Crucial: The framing must be a 'Cowboy Shot' (Mid-Thigh Up) or wider to ensure the outfit is visible. Avoid tight headshots.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static or slight handheld sway. Composition must include torso and upper legs.",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Soft 'Beauty Dish' or Butterfly Lighting",
                    mood=["Cool", "Attractive", "Human"],
                    color_anchors=["Skin Tone", "Outfit Color", "Soft Background"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The brand logo overlaid on a moving abstract background (blur of the fabric color).",
                on_screen_text_hint="New Collection Out Now",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Abstract Light Leaks",
                    mood=["Stylish"],
                    velocity_hint="Slow Dolly Back",
                    color_anchors=["Brand Color"],
                ),
            ),
        ],
    )


def get_apparel_style_showcase_fast_pace() -> AdTemplate:
    """Template: Style Showcase (23s) - Commercial Realism"""
    return AdTemplate(
        template_name="Style Showcase (Fast)",
        industry_type="Vertical-Specific",
        vertical_category="Apparel",
        target_duration_seconds=23,  # Structure: 2+3+2.5+3+3+2.5+3+4
        description="A clean, realistic fashion montage focusing on fit, fabric, and natural movement without exaggerated effects.",
        brand_personality=["Confident", "Authentic", "Premium"],
        music_keywords=["Modern Lounge", "Rhythmic Bass", "Fashion Week", "Clean"],
        scene_structure=[
            # --- SCENE 1: THE ARRIVAL (2s) ---
            SceneDefinition(
                scene_id="environment_flash",
                duration_seconds=2,
                purpose="Establish Mood + Subject Presence.",
                asset_guidance="Wide shot. The model walks confidently into the frame from the background or side. CRITICAL: The model is GROUNDED with feet firmly touching the floor/pavement. They are walking, not jumping or running. The lighting establishes the atmospheric mood immediately.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera, Third-Person perspective",
                    lens_specification="35mm Wide Angle",
                    lighting_description="Natural Environmental Light",
                    mood=["Atmospheric", "Real"],
                    velocity_hint="Natural Walk",
                ),
            ),
            # --- SCENE 2: THE LOOK (3s) ---
            SceneDefinition(
                scene_id="hero_stance",
                duration_seconds=3,
                purpose="Establish the Look. Natural Confidence.",
                asset_guidance="Full body 'Fit Check'. The model stands confidently, shifting their weight from one leg to the other, or crossing their arms/adjusting their jacket. It is a natural, grounded pause that allows the viewer to see the full outfit clearly.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Push-In (Dolly Forward)",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Flattering Key Light",
                    mood=["Confident", "Stylish"],
                    velocity_hint="Gentle Movement",
                ),
            ),
            # --- SCENE 3: THE FABRIC (2.5s) ---
            SceneDefinition(
                scene_id="fabric_detail",
                duration_seconds=2.5,
                purpose="Sensory Quality. Materiality.",
                asset_guidance="A static, razor-sharp Macro close-up of the Hero Product's texture (weave/grain/gloss). The camera is Locked-Off. A soft beam of light moves slowly across the surface (Raking Light), revealing the depth of the texture through subtle shadows rather than harsh glare.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera (Locked-off)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Soft Side-Lighting (Raking Light) to reveal texture depth",
                    mood=["Tactile", "Expensive"],
                    velocity_hint="Shadow Shift",
                ),
            ),
            # --- SCENE 4: THE TOUCH (3s) ---
            SceneDefinition(
                scene_id="model_interact",
                duration_seconds=3,
                purpose="Usability/Feel. Visualizing comfort.",
                asset_guidance="Mid-shot of the model's hand gently brushing against or resting on the fabric of the Hero Product. This gesture highlights the tactile quality and comfort of the material without complex mechanical interactions.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Mid-Shot, focus on the hand/fabric",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Soft light emphasizing texture softness",
                    mood=["Comfortable", "High Quality"],
                    velocity_hint="Smooth Touch",
                ),
            ),
            # --- SCENE 5: THE MOVEMENT (3s) ---
            SceneDefinition(
                scene_id="motion_showcase",
                duration_seconds=3,
                purpose="Flexibility/Fit in Action.",
                asset_guidance="Dynamic movement appropriate to the specific item type. The model performs a single, grounded action to demonstrate fit or flow. If Bottoms/Shoes: A vertical 'Step Up' or 'Knee Bend' (keeps legs defined). If Tops/Jackets: A 'Shoulder Shrug', 'Arm Cross', or 'Collar Adjust' (shows fit). If Dress/Skirt: A 'Gentle Sway' or 'Forward Stride' (shows drape). If Accessories (Glasses/Jewelry): A 'Sharp Head Turn' or 'Tilt'. CRITICAL: Avoid side-lunges or fast spins to prevent mesh distortion.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera, framing optimized for the movement (Full body vs Mid-shot)",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Clear, Even Lighting",
                    mood=["Active", "Flexible", "Comfortable"],
                    velocity_hint="Controlled Motion",
                ),
            ),
            # --- SCENE 6: THE ACCENT (2.5s) ---
            SceneDefinition(
                scene_id="detail_accent",
                duration_seconds=2.5,
                purpose="Design Detail.",
                asset_guidance="A static, razor-sharp close-up of a specific design detail (waistband, logo, or zipper). The camera DOES NOT MOVE. A subtle reflection or 'High-Gloss' highlight travels smoothly across the detail, emphasizing the material quality without flashing.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Locked-off Macro",
                    lens_specification="85mm Telephoto",
                    lighting_description="Smooth, Continuous Highlight Roll",
                    mood=["Edgy", "Sharp"],
                    velocity_hint="Glint",
                ),
            ),
            # --- SCENE 7: THE POSE (3s) ---
            SceneDefinition(
                scene_id="lifestyle_portrait",
                duration_seconds=3,
                purpose="The Attitude. Face + Product.",
                asset_guidance="The 'Final Look'. The model strikes a confident, relaxed pose, looking directly at the lens. CRITICAL: The framing must be a 'Cowboy Shot' (Mid-Thigh Up) or wider to ensure the outfit is fully visible. The lighting is flattering and soft, making the skin and fabric look perfect.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static, slight handheld sway. Cowboy Shot framing.",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Soft 'Butterfly' Studio Lighting (Diffused)",
                    mood=["Cool", "Iconic"],
                    velocity_hint="Freeze Frame",
                ),
            ),
            # --- SCENE 8: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The brand logo overlaid on a moving abstract background (blur of the fabric color).",
                on_screen_text_hint="[Brand Slogan] or 'New Collection'",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Abstract Light Leaks",
                    mood=["Stylish"],
                    velocity_hint="Linear Slide (Truck)",
                    color_anchors=["Brand Color"],
                ),
            ),
        ],
    )


def get_beauty_routine() -> AdTemplate:
    """Template: Beauty Routine (32s) - V6 The Transfer of Glow"""
    return AdTemplate(
        template_name="Beauty Routine",
        industry_type="Vertical-Specific",
        vertical_category="Beauty",
        target_duration_seconds=32,  # Structure: 4+6+6+8+4+4
        description="A sensory-focused template emphasizing texture, application ritual, and the resulting 'Glow'.",
        brand_personality=["Luxurious", "Radiant", "Pure"],
        music_keywords=["Chill Lo-Fi", "Elegant Piano", "Soft House", "Water Sounds"],
        scene_structure=[
            # --- SCENE 1: THE ICON (4s) ---
            SceneDefinition(
                scene_id="hero_bottle",
                duration_seconds=4,
                purpose="Establish the Object of Desire.",
                asset_guidance="A studio beauty shot of the product packaging standing on a reflective surface (water or glass). A slow light sweep highlights the curve and logo.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static shot with moving light source (Light Sweep)",
                    lens_specification="85mm Telephoto (Flattering product compression)",
                    lighting_description="Soft, Pearlescent Studio Lighting with distinct Rim Light",
                    mood=["Luxurious", "Clean", "Premium"],
                    color_anchors=["Brand Color", "Pastel Background", "White"],
                ),
            ),
            # --- SCENE 2: THE TEXTURE SWATCH (6s) ---
            SceneDefinition(
                scene_id="texture_macro",
                duration_seconds=6,
                purpose="Sensory ASMR. Show the Viscosity/Pigment.",
                asset_guidance="Extreme Macro 'Swatch' shot. The product texture is smeared, dropped, or crushed onto a neutral glass or stone surface to show its richness and viscosity.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Top-down or 45-degree angle, Macro detail",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Backlit or Side-lit to reveal translucency and thickness",
                    mood=["Satisfying", "Rich"],
                    color_anchors=["Product Texture Color", "Neutral Surface"],
                ),
            ),
            # --- SCENE 3: THE GLIDING TRANSFER (6s) ---
            SceneDefinition(
                scene_id="application",
                duration_seconds=6,
                purpose="The Application in Motion (No 'Prep' steps).",
                asset_guidance="A smooth, flowing close-up of the application *in progress*. The applicator (eg, Model's Hand/Finger or a Brush/Wand, etc.) glides across the surface (Hair Strand/Cheek/Lips/etc.). CRITICAL: The shot highlights the 'Wet Trail' or 'Sheen' left behind by the movement, contrasting with the dry area ahead of it.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow tracking shot following the movement of the applicator",
                    lens_specification="85mm Portrait Lens (Focus on the contact point)",
                    lighting_description="Soft Front Lighting, positioned to catch the reflection of the wet product trail",
                    mood=["Gentle", "Nourishing"],
                    color_anchors=["Skin/Hair Tone", "Product Sheen"],
                ),
            ),
            # --- SCENE 4: THE GLOW REVEAL (8s) ---
            SceneDefinition(
                scene_id="result_glow",
                duration_seconds=8,
                purpose="The Result. Universal 'Sign of Quality'.",
                asset_guidance="A mesmerizing portrait of the model moving slowly to catch the light. The key visual is a 'Traveling Highlight'—a band of light that sweeps across the specific 'Hero Feature' (e.g. the gloss of the lips, the sheen of the cheek, the wave of the hair, or the glow of the shoulder) to prove the finish.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow motion movement (head turn or shoulder adjustment)",
                    lens_specification="85mm f/1.2 Portrait Lens (Dreamy Bokeh)",
                    lighting_description="High-Key, Ethereal Background. Soft diffuse light with distinct 'Specular Highlights' on the application area. Eyes have natural, subtle reflections only.",
                    mood=["Radiant", "Confident", "Glass-Like"],
                    color_anchors=["Glowing Skin", "Light Background", "Natural Tones"],
                ),
            ),
            # --- SCENE 5: THE INGREDIENT (4s) ---
            SceneDefinition(
                scene_id="ingredient_art",
                duration_seconds=4,
                purpose="The 'Why'. Nature/Science anchor.",
                asset_guidance="Artistic close-up of the key ingredient falling into water or floating in air (e.g., a flower, a water droplet, or gold particles).",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Phantom High-Speed (Slow Motion)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Bright, Fresh, Natural Light",
                    mood=["Pure", "Natural"],
                    color_anchors=["Ingredient Color", "Clear"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="The product centered on a soft pastel gradient background. The logo fades in elegantly.",
                on_screen_text_hint="Glow with [Brand Name]",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Soft Studio Lighting",
                    mood=["Luxurious"],
                    velocity_hint="Slow Shimmer/Glow",
                    color_anchors=["Brand Color", "Pastel"],
                ),
            ),
        ],
    )


def get_beauty_routine_fast_pace() -> AdTemplate:
    """Template: Beauty Routine (25s) - Cleaned for Smart Enrichment"""
    return AdTemplate(
        template_name="Beauty Routine (Fast)",
        industry_type="Vertical-Specific",
        vertical_category="Beauty",
        target_duration_seconds=25,  # Structure: 4+4+3+3+4+3+4
        description="A high-velocity beauty montage starting with sensory texture and ending with the product reveal.",
        brand_personality=["Radiant", "Confident", "Instant"],
        music_keywords=[
            "Rhythmic House",
            "Water Drop Percussion",
            "Upbeat Fashion",
            "Snap",
        ],
        scene_structure=[
            # --- SCENE 1: THE TEXTURE HOOK (4s) ---
            SceneDefinition(
                scene_id="texture_impact",
                duration_seconds=4,
                purpose="Scroll Stopper. Instant Sensory Satisfaction.",
                asset_guidance="Extreme Macro Impact shot. A drop of serum, a dollop of cream, or a crush of powder impacts a neutral surface with high velocity. The texture splashes or smears on contact, looking wet, rich, and satisfying.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Macro with high-speed internal motion (Impact)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="High contrast, Backlit to show viscosity",
                    mood=["Satisfying", "Rich"],
                    velocity_hint="Impact / Splash",
                ),
            ),
            # --- SCENE 2: THE SWIPE (4s) ---
            SceneDefinition(
                scene_id="application_swipe",
                duration_seconds=4,
                purpose="The Transfer. Fast Action.",
                asset_guidance="A single, smooth 'Swipe' motion. The appropriate applicator (e.g., hand, brush, wand, etc.) glides across the target area (e.g., skin, hair, lips, etc.), leaving a distinct, glowing trail of product behind it. The focus is on the immediate transformation from dry to hydrated/shiny.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Tracking shot following the swipe speed",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Front light catching the wet trail",
                    mood=["Silky", "Smooth"],
                    velocity_hint="Fluid Motion",
                ),
            ),
            # --- SCENE 3: THE FLASH (3s) ---
            SceneDefinition(
                scene_id="glow_turn",
                duration_seconds=3,
                purpose="The Payoff. The 'Traveling Highlight'.",
                asset_guidance="The 'Money Shot'. A close-up portrait where the model turns their head quickly to catch the light. A 'Traveling Highlight' sweeps across the cheekbone, lips, or hair curve, creating a glass-like specular reflection.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast Head Turn (or Hair Flip) into a static lock",
                    lens_specification="85mm f/1.2 Portrait Lens (Bokeh)",
                    lighting_description="High-Key with specific Specular Highlights on the feature",
                    mood=["Radiant", "Glass-Like"],
                    velocity_hint="Dynamic Turn",
                ),
            ),
            # --- SCENE 4: THE INGREDIENT (3s) ---
            SceneDefinition(
                scene_id="science_splash",
                duration_seconds=3,
                purpose="The Science/Nature visualization.",
                asset_guidance="Artistic macro of the key ingredient (flower, water droplet, gold flake) falling into water or bursting in mid-air. A visual palate cleanser showing purity.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Phantom High-Speed (Slow motion capture of fast action)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Bright, Fresh",
                    mood=["Pure"],
                    velocity_hint="Explosive",
                ),
            ),
            # --- SCENE 5: THE ICON (4s) ---
            SceneDefinition(
                scene_id="hero_bottle",
                duration_seconds=4,
                purpose="The Solution Identified.",
                asset_guidance="Studio shot of the Product Packaging standing perfectly still. A sharp beam of light (Rim Light) scans rapidly across the logo and silhouette, revealing the shape.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Object, Moving Light Source",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Rim Lighting sweep",
                    mood=["Premium"],
                    velocity_hint="Light Sweep",
                ),
            ),
            # --- SCENE 6: THE CONFIDENCE (3s) ---
            SceneDefinition(
                scene_id="lifestyle_smile",
                duration_seconds=3,
                purpose="Emotional Validation.",
                asset_guidance="The model looks directly at the camera and breaks into a confident smile or gives a decisive nod. Wind blows their hair slightly. They look ready to take on the world.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld (subtle energy)",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Natural Daylight / Sun Flare",
                    mood=["Happy", "Confident"],
                    velocity_hint="Alive",
                ),
            ),
            # --- SCENE 7: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="Logo centered on a glowing background (matching the product texture).",
                on_screen_text_hint="[Short Brand Slogan] or 'Glow Instantly'",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Soft Studio Lighting",
                    mood=["Luxurious"],
                    velocity_hint="Pulse/Beat",
                    color_anchors=["Brand Color"],
                ),
            ),
        ],
    )


def get_home_comfort() -> AdTemplate:
    """Template: Home Comfort (32s) - V2 The Day-to-Night Arc"""
    return AdTemplate(
        template_name="Home Comfort",
        industry_type="Vertical-Specific",
        vertical_category="Home",
        target_duration_seconds=32,  # Structure: 4+4+8+8+4+4
        description="A sensory journey showing the product transitioning from 'Airy Morning' to 'Cozy Evening'.",
        brand_personality=["Inviting", "Stylish", "Peaceful"],
        music_keywords=["Acoustic Piano", "Ambient", "Soft House", "Warm"],
        scene_structure=[
            # --- SCENE 1: THE MORNING BREATH (4s) ---
            SceneDefinition(
                scene_id="est_morning",
                duration_seconds=4,
                purpose="Establish the Space & 'Airiness'.",
                asset_guidance="Wide establishing shot of the room bathed in natural morning light. The Product is placed naturally in the center/foreground.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow, steady Push-In (Dolly Forward) establishing the space",
                    lens_specification="24mm Wide Angle Lens",
                    lighting_description="Soft Morning Sunlight (5600K), Volumetric Haze/Dust motes dancing in light",
                    mood=["Fresh", "Airy", "Awake"],
                    color_anchors=["White", "Soft Beige", "Pale Blue"],
                ),
            ),
            # --- SCENE 2: THE MATERIAL TOUCH (4s) ---
            SceneDefinition(
                scene_id="texture_detail",
                duration_seconds=4,
                purpose="Sensory Validation (Touch).",
                asset_guidance="Extreme Close-Up (Macro) of the product's texture. A hand gently grazes over the surface to show softness/quality.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Tracking shot following the hand movement",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Raking light to reveal texture depth and weave",
                    mood=["Tactile", "Soft", "High-Quality"],
                    color_anchors=["Material Color", "Warm Skin Tone"],
                ),
            ),
            # --- SCENE 3: THE LIVING MOMENT (8s) ---
            SceneDefinition(
                scene_id="lifestyle_day",
                duration_seconds=8,
                purpose="Usage in Context (Daytime).",
                asset_guidance="Medium shot of a person/family using the product casually in the bright daytime setting. Unposed, candid movement (e.g. reading a book, sipping coffee, or kids playing nearby).",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow sliding movement (Parallax effect) past a foreground xplant/chair",
                    lens_specification="35mm Standard Lens",
                    lighting_description="Natural Diffused Daylight (Window Light)",
                    mood=["Peaceful", "Lived-in", "Authentic"],
                    color_anchors=["Natural Tones", "Green (Plants)"],
                ),
            ),
            # --- SCENE 4: THE EVENING SHIFT (8s) ---
            SceneDefinition(
                scene_id="lifestyle_night",
                duration_seconds=8,
                purpose="The Atmosphere Shift (Cozy Night).",
                asset_guidance="The same room/product, but now at night. The main lights are off, lit only by warm lamps or candles. A person is winding down (relaxing/sleeping/watching TV).",
                transition_from_previous=TransitionHints(
                    type="dissolve",
                    description="Slow cross-dissolve to show time passing",
                ),
                cinematography_hints=CinematographyHints(
                    camera_description="Static, peaceful composition",
                    lens_specification="50mm Lens (Focus on the cozy atmosphere)",
                    lighting_description="Low-Key, Warm Practical Lighting (Lamps/Candles - 2700K), Deep Shadows",
                    mood=["Cozy", "Intimate", "Warm"],
                    color_anchors=["Amber", "Deep Orange", "Shadow Black"],
                ),
            ),
            # --- SCENE 5: THE PERFECT CORNER (4s) ---
            SceneDefinition(
                scene_id="hero_beauty",
                duration_seconds=4,
                purpose="The 'Magazine' Shot.",
                asset_guidance="A stylized 'Pinterest-worthy' vertical or square composition of the product in the evening light.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow vertical tilt-up or static beauty shot",
                    lens_specification="85mm Portrait Lens (Telephoto compression)",
                    lighting_description="Accent lighting spotlighting the product",
                    mood=["Stylish", "Desirable"],
                    color_anchors=["Warm Gold", "Rich Textures"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="Logo centered on a textured background (linen/fabric) that matches the product.",
                on_screen_text_hint="Make yourself at home.",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Soft Ambient Light",
                    mood=["Classy"],
                    velocity_hint="Slow Drift",
                    color_anchors=["Brand Color", "Cream/Beige"],
                ),
            ),
        ],
    )


def get_home_comfort_fast_pace() -> AdTemplate:
    """Template: Home Comfort (24s) - High Velocity Rhythm"""
    return AdTemplate(
        template_name="Home Comfort (Fast)",
        industry_type="Vertical-Specific",
        vertical_category="Home",
        target_duration_seconds=24,  # Structure: 3+3+2+3+3+3+3+4
        description="A rapid-fire 8-scene montage compressing the sensory experience of 'Home' into micro-moments.",
        brand_personality=["Inviting", "Stylish", "Peaceful", "Modern"],
        music_keywords=["Lo-Fi Beat", "Rhythmic Percussion", "Snap Transition", "Warm"],
        scene_structure=[
            # --- SCENE 1: THE WAKE UP (3s) ---
            SceneDefinition(
                scene_id="light_burst",
                duration_seconds=3,
                purpose="Instant Energy. The start of the day.",
                asset_guidance="A rapid time-lapse light burst. High-contrast morning sunlight sweeps aggressively across the Hero Product, instantly banishing the shadows.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera",
                    lens_specification="35mm Wide Angle",
                    lighting_description="Transition from Shadow to Blinding High Key",
                    mood=["Awake", "Fresh"],
                    velocity_hint="Light Burst",
                ),
            ),
            # --- SCENE 2: THE SPACE (3s) ---
            SceneDefinition(
                scene_id="room_expand",
                duration_seconds=3,
                purpose="Establish Context fast.",
                asset_guidance="A fast 'Snap Zoom Out' (Pull Back) starting from a tight detail of the Hero Product and widening to reveal the entire beautiful room around it.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast Zoom Out from Close to Wide (Center-locked)",
                    lens_specification="24mm Wide Angle",
                    lighting_description="Bright, Airy",
                    mood=["Spacious"],
                    velocity_hint="Fast Reveal",
                ),
            ),
            # --- SCENE 3: THE TOUCH (2s) ---
            SceneDefinition(
                scene_id="tactile_macro",
                duration_seconds=2,
                purpose="Sensory: Softness/Texture.",
                asset_guidance="Extreme Macro. A hand interacts firmly with the material. If soft (fabric/foam), the hand pushes down to show compression. If hard (wood/metal), the hand glides smoothly to show finish quality.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Macro Handheld",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Side lighting for texture contrast",
                    mood=["Soft", "High-Quality"],
                    velocity_hint="Active Touch",
                ),
            ),
            # --- SCENE 4: THE DETAIL (3s) ---
            SceneDefinition(
                scene_id="design_accent",
                duration_seconds=3,
                purpose="Sensory: Design/Craftsmanship.",
                asset_guidance="A static, crystal-clear Macro close-up of a specific design detail. The camera remains completely still (Locked-off). A focused beam of light sweeps rapidly across the surface, causing a 'Glint' or shifting shadows that reveal the depth and texture of the material.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Camera (Locked-off)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Dynamic Moving Light Source (Rim light sweep), High Contrast",
                    mood=["Premium", "Sleek"],
                    velocity_hint="Light Flash",
                ),
            ),
            # --- SCENE 5: THE LIVE (3s) ---
            SceneDefinition(
                scene_id="day_action",
                duration_seconds=3,
                purpose="Human Connection (Day).",
                asset_guidance="Dynamic physics test. A relevant accessory (e.g., a fluffy pillow, a folded blanket, or a pair of slippers) is suspended in mid-air above the Hero Product. It drops, impacts the surface, and settles. Focus on the 'Squish' and 'Rebound' of the Hero Product to prove its softness and quality.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Wide Shot",
                    lens_specification="35mm Standard Lens",
                    lighting_description="Natural Day Light, High Shutter Speed",
                    mood=["Playful", "Soft", "Satisfying"],
                    velocity_hint="Impact Bounce",
                ),
            ),
            # --- SCENE 6: THE SNAP (3s) ---
            SceneDefinition(
                scene_id="night_switch",
                duration_seconds=3,
                purpose="The Day-to-Night Contrast.",
                asset_guidance="A hard cut to Night Mode. The room is now dark and lit by warm lamps, but the composition remains identical. The person is already present and visible in the static frame, resting in the same position on the product, breathing gently in the stillness.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Lock-off",
                    lens_specification="50mm Lens",
                    lighting_description="Dark, Warm Tungsten (2700K), Lamp light",
                    mood=["Cozy", "Intimate"],
                    velocity_hint="Stillness",
                ),
            ),
            # --- SCENE 7: THE ZEN (3s) ---
            SceneDefinition(
                scene_id="cozy_moment",
                duration_seconds=3,
                purpose="The Result: Peace.",
                asset_guidance="Close-up of a Person or the Hero Product in a resting state. A hand resting on the fabric, or a person reading quietly in the warm light. A very slow, subtle zoom in (Breathing) to emphasize the stillness.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static shot with subtle 'Breathing' zoom",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Cozy Backlight (Halo)",
                    mood=["Peaceful", "Dreamy"],
                    velocity_hint="Slow Motion",
                ),
            ),
            # --- SCENE 8: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Brand Anchor.",
                asset_guidance="Logo centered on a warm, textured home background.",
                on_screen_text_hint="[Brand Slogan] / 'Upgrade Your Space' / 'Make Yourself at Home' / etc.",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Soft Ambient Light",
                    mood=["Classy"],
                    velocity_hint="Slow Drift",
                    color_anchors=["Brand Color", "Cream/Beige"],
                ),
            ),
        ],
    )


def get_meal_prep() -> AdTemplate:
    """Template: Meal Prep Made Easy (32s) - V3 Sensory Kitchen"""
    return AdTemplate(
        template_name="Meal Prep Made Easy",
        industry_type="Vertical-Specific",
        vertical_category="Food & Beverage",
        target_duration_seconds=32,  # Structure: 4+4+8+8+4+4
        description="A sensory-driven journey from 'Organized Ingredients' to 'Restaurant Quality Taste'.",
        brand_personality=["Delicious", "Fresh", "Convenient"],
        music_keywords=[
            "Upbeat Jazz",
            "Percussive Cooking Sounds",
            "Bright",
            "Acoustic",
        ],
        scene_structure=[
            # --- SCENE 1: THE SATISFYING UNBOX (4s) ---
            SceneDefinition(
                scene_id="unboxing_knoll",
                duration_seconds=4,
                purpose="Organized Potential. The 'Fresh Start' feeling.",
                asset_guidance="Top-Down 'Flat Lay' (Knolling) view. The box opens (stop motion style) and the ingredients arrange themselves neatly on the counter. It looks abundant and organized.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Strict Top-Down (Bird's Eye View), 90-degree angle",
                    lens_specification="35mm Wide Angle (to fit everything)",
                    lighting_description="Bright, Even Kitchen Daylight (High Key)",
                    mood=["Organized", "Fresh", "Exciting"],
                    color_anchors=["Fresh Green", "Bright Orange", "White Counter"],
                ),
            ),
            # --- SCENE 2: THE FRESHNESS MACRO (4s) ---
            SceneDefinition(
                scene_id="ingredient_macro",
                duration_seconds=4,
                purpose="Proof of Quality (Sensory).",
                asset_guidance="Extreme Close-Up (Macro) of the hero ingredient. Focus on texture: Water droplets on fresh produce, the grain of spice, or the marbling of protein.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Macro shot, focus shifting (Rack Focus) from front to back",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Backlit by window light to make moisture/droplets sparkle",
                    mood=["Crisp", "Raw", "Natural"],
                    color_anchors=["Vibrant", "Glistening"],
                ),
            ),
            # --- SCENE 3: THE KINETIC PREP (8s) ---
            SceneDefinition(
                scene_id="cooking_action",
                duration_seconds=8,
                purpose="The Process. Fast & Easy.",
                asset_guidance="A dynamic montage of the transformation. The food hitting the hot pan (sizzle), the knife slicing cleanly, or the blender swirling. Focus on the energy/heat.",
                transition_from_previous=TransitionHints(type="dissolve"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow Motion (60fps) to capture steam/splash, Low Angle near the pan",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Directional 'Rembrandt' lighting to emphasize steam and smoke",
                    mood=["Appetizing", "Hot"],
                    color_anchors=["Warm Orange (Fire/Heat)", "Steel"],
                ),
            ),
            # --- SCENE 4: THE PLATING REVEAL (8s) ---
            SceneDefinition(
                scene_id="hero_plate",
                duration_seconds=8,
                purpose="The Result. 'Restaurant Quality'.",
                asset_guidance="The 'Money Shot'. The finished dish is plated. A final garnish is sprinkled, or sauce is drizzled. Steam rises gracefully. The lighting shifts to warm evening vibes.",
                on_screen_text_hint="Chef Quality. Home Cooked.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Slow 360-degree Orbit (Turntable style) or slow push-in",
                    lens_specification="85mm Telephoto (Food Photography standard)",
                    lighting_description="Warm, Golden 'Candlelight' or Restaurant Ambience",
                    mood=["Delicious", "Cozy", "Accomplished"],
                    color_anchors=["Golden Brown", "Rich Red", "Warm Yellow"],
                ),
            ),
            # --- SCENE 5: THE TASTE TEST (4s) ---
            SceneDefinition(
                scene_id="human_reaction",
                duration_seconds=4,
                purpose="The Payoff. Visual Validation.",
                asset_guidance="Close-up of a person taking the first bite/sip. Their eyes widen in delight, and they nod. Pure satisfaction.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld, slightly shaky (authentic)",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Natural Interior Light",
                    mood=["Happy", "Satisfied"],
                    color_anchors=["Skin Tone", "Smile"],
                ),
            ),
            # --- SCENE 6: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Conversion.",
                asset_guidance="The discount code overlaying a background of the delicious food texture (blurred).",
                on_screen_text_hint="50% Off First Box",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Bright/High Contrast",
                    mood=["Urgent"],
                    velocity_hint="Slow Dolly In",
                    color_anchors=["Brand Color", "White Text"],
                ),
            ),
        ],
    )


def get_meal_prep_fast_pace() -> AdTemplate:
    """Template: Meal Prep Made Easy (21s) - Fast Rhythm"""
    return AdTemplate(
        template_name="Meal Prep Made Easy (Fast)",
        industry_type="Vertical-Specific",
        vertical_category="Food & Beverage",
        target_duration_seconds=20,  # Structure: 2.5+2.5+3+3+3+3+4
        description="A high-octane 'Sizzle Reel' that compresses the cooking journey into 20 seconds of rhythmic visual beats.",
        brand_personality=["Delicious", "Fresh", "Convenient", "Energetic"],
        music_keywords=[
            "Percussive Kitchen Sounds",
            "Upbeat Funk",
            "Fast Jazz",
            "Bright",
        ],
        scene_structure=[
            # --- SCENE 1: THE POP (2.5s) ---
            SceneDefinition(
                scene_id="unboxing_burst",
                duration_seconds=2.5,
                purpose="Instant Hook. Explosion of potential.",
                asset_guidance="Top-Down (Bird's Eye) view. The box/packaging bursts open (Stop Motion style), and ingredients visually 'pop' into an organized arrangement.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static Top-Down, High shutter speed (Stop Motion feel)",
                    lens_specification="35mm Wide Angle",
                    lighting_description="Bright, Even Kitchen Daylight (High Key)",
                    mood=["Excited", "Organized"],
                    velocity_hint="Immediate / Burst",
                ),
            ),
            # --- SCENE 2: THE WASH (2.5s) ---
            SceneDefinition(
                scene_id="freshness_splash",
                duration_seconds=2.5,
                purpose="Sensory Detail. Water = Freshness.",
                asset_guidance="Extreme Macro shot of water splashing onto the hero ingredient. Focus on the collision of liquid and texture.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Macro, High-Speed (Slow Motion capture of the splash)",
                    lens_specification="100mm Macro Lens",
                    lighting_description="Backlit to make water droplets sparkle",
                    mood=["Fresh", "Crisp"],
                    velocity_hint="Explosive Liquid",
                ),
            ),
            # --- SCENE 3: THE CHOP (3s) ---
            SceneDefinition(
                scene_id="prep_rhythm",
                duration_seconds=3,
                purpose="The Prep. Rhythmic action.",
                asset_guidance="Low-angle dynamic shot of the 'Prep Action'. Fast, rhythmic movement (chopping/blending/shaking) with motion blur emphasizing speed.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld 'Crash Zoom' into the action",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Directional lighting to catch movement",
                    mood=["Active", "Efficient"],
                    velocity_hint="Fast / Rhythmic",
                ),
            ),
            # --- SCENE 4: THE HEAT (3s) ---
            SceneDefinition(
                scene_id="cooking_transform",
                duration_seconds=3,
                purpose="The Transformation. Heat/Physics.",
                asset_guidance="Close-up of the 'Thermal Transformation'. Food hitting the heat (sizzle/steam) or liquids merging. Heavy emphasis on steam or particles rising.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static camera, focused on the physics (steam/bubbles)",
                    lens_specification="85mm Telephoto",
                    lighting_description="Warm 'Rembrandt' lighting (High Contrast)",
                    mood=["Hot", "Appetizing"],
                    velocity_hint="Dynamic Physics",
                ),
            ),
            # --- SCENE 5: THE REVEAL (3s) ---
            SceneDefinition(
                scene_id="hero_plate_spin",
                duration_seconds=3,
                purpose="The Result. Beauty Shot.",
                asset_guidance="The finished product spins rapidly into a locked position (Whip-Pan transition). It stops perfectly plated, glistening under warm light.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Fast Whip-Pan ending in a steady lock-off",
                    lens_specification="50mm Standard Lens",
                    lighting_description="Restaurant Ambience (Warm/Golden)",
                    mood=["Delicious", "Ready"],
                    velocity_hint="Fast Entry -> Dead Stop",
                ),
            ),
            # --- SCENE 6: THE YUM (3s) ---
            SceneDefinition(
                scene_id="reaction_bite",
                duration_seconds=3,
                purpose="Human Validation.",
                asset_guidance="Tight close-up of a person taking a bite/sip and immediately smiling/nodding. Instant satisfaction.",
                transition_from_previous=TransitionHints(type="cut"),
                cinematography_hints=CinematographyHints(
                    camera_description="Handheld, intimate proximity",
                    lens_specification="85mm Portrait Lens",
                    lighting_description="Soft Interior Light",
                    mood=["Satisfied", "Happy"],
                    velocity_hint="Natural / Reactive",
                ),
            ),
            # --- SCENE 7: CTA (4s) ---
            SceneDefinition(
                scene_id="cta",
                duration_seconds=4,
                purpose="Conversion.",
                asset_guidance="Brand logo pulsating on top of a blurred, appetizing background texture.",
                on_screen_text_hint="50% Off / Order Now / [Brand Slogan] / Shop at [Brand Website]/ etc.",
                transition_from_previous=TransitionHints(type="fade"),
                cinematography_hints=CinematographyHints(
                    camera_description="Static",
                    lighting_description="Clean/Bold",
                    mood=["Urgent"],
                    velocity_hint="Rhythmic Pulse (Light Only)",
                    color_anchors=["Brand Color", "White Text"],
                ),
            ),
        ],
    )