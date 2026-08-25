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

"""Art direction presets for the storyboard agent.

This module holds two structures with distinct roles.

PRODUCTION_ENCYCLOPEDIA catalogues the available options, keyed by style mode
and then by axis (brand aesthetics, character, product macro, environment,
cinematography, illumination, sonic landscape, fidelity guards). It is never
sent to a model in full. It provides the set of valid values offered when a
reviewer edits a Look through `set_look`, and its FIDELITY_GUARDS entries are
copied into every recipe.

PRODUCTION_LOOKS defines curated combinations drawn from those axes. Each
Look's `recipe` selects one value per axis so that a campaign renders with a
consistent visual identity rather than an arbitrary mix of lens, lighting and
wardrobe. `tones` and `keywords` are used for matching only; `description` is
the text shown to the selector model.

A Look is applied as follows:

    recommend_production_recipe selects one Look per campaign
      -> its recipe is stored in state as `master_production_recipe`
      -> _build_art_direction_block appends the recipe's anchors to each
         scene's first-frame and video description
      -> enrichment renders those anchors as prose for Imagen and Veo

`sonic_landscape` is excluded from the art-direction block and supplies the
background music brief instead.

`product_mode` provides substitute styling for campaigns without a person on
screen. Omitting the character block alone is insufficient, because the
general styling may also assume a subject (butterfly lighting, catchlights,
sweat), which directs the renderer towards a face that is not in frame.
"""

from typing import Dict, Any

# --- PRODUCTION ENCYCLOPEDIA ---

PRODUCTION_ENCYCLOPEDIA: Dict[str, Any] = {
    "COMMERCIAL_PREMIUM": {
        "BRAND_AESTHETICS": {
            "luxury_heritage": "Deep mahogany, brushed gold, velvet textures, low-key lighting, timeless elegance.",
            "tech_minimalism": "Monochromatic whites/greys, frosted glass, blue-tinted shadows, ultra-clean surfaces.",
            "vibrant_cpg": "High-saturation pops, playful shadows, rhythmic editing, 'color-block' styling.",
            "organic_wellness": "Earthy linens, diffused sunlight, botanical greens, raw wood, 'no-makeup' makeup look.",
            "high_octane_sports": "High contrast, grit, sweat-sheen, aggressive motion blur, anamorphic flares.",
            "urban_street_luxe": "Raw concrete, metallic silver chrome, high-contrast neon, oversized silhouettes, graffiti-inspired textures.",
            "avant_garde_fashion": "Structural silhouettes, monochromatic black/gold, high-gloss leather, surrealist lighting.",
            "nostalgic_vintage": "Warm amber tones, film grain, soft lens flares, 70s-style typography, rich filmic saturation.",
        },
        "CHARACTER_DETAILS": {
            "primary_actors": [
                "The 'Aspirant': flawless skin, symmetrical features, direct but soft eye contact",
                "The 'Tech-Visionary': focused, illuminated by screen-glow, minimalist attire",
                "The 'Craftsman': macro focus on hands, dust motes in hair, rugged linen apron",
                "The 'Modern Athlete': hyper-defined muscle tension, micro-droplets of sweat, explosive power",
                "The 'Connoisseur': refined features, calm and deliberate movement, looking at product with admiration",
                "The 'Dynamic Explorer': weathered skin textures, wind-swept hair, looking towards the horizon",
                "The 'Creative Radical': bold colored hair, strike makeup, confident artistic posture",
                "The 'Zen Practitioner': closed eyes, relaxed facial muscles, luminous and hydrated skin",
            ],
            "attire_styling": [
                "Textural Luxury: heavy-gauge cashmere, raw silk, bespoke structured wool",
                "Technical Performance: laser-cut seams, matte-finish synthetics, iridescent fibers",
                "Avant-Garde Editorial: structural silhouettes, high-gloss leather, metallic accents",
                "Minimalist Sophistication: tailored linen, high-thread-count cotton, understated luxury",
                "Vintage Filmic: textured corduroy, worn leather, high-waisted tailoring",
                "Industrial Utility: heavy canvas, technical straps, metallic hardware, matte black finish",
                "Fluid Ethereal: flowing chiffon, sheer layers, translucent fabrics that catch the light",
                "Street-Style High-Fashion: oversized hoodies, reflective fabrics, contrast stitching",
            ],
            "visage_grooming": [
                "Glass Skin: hyper-hydrated, reflective highlights on cheekbones",
                "Precision Grooming: sharp beard lines, matte-finish hair styling",
                "Editorial Statement: graphic eyeliner, wet-look hair, high-fashion structuralism",
                "Raw Authenticity: visible skin textures, natural freckles, 'no-makeup' makeup look",
                "Saturated Pop: vibrant eyeshadow, bold matte lips, playful color accents",
                "Sun-kissed Glow: bronzed skin, scattered freckles, wind-tossed hair",
                "High-Contrast Shadow: dramatic eye-makeup, sharp contours, mysterious gaze",
                "Dewy Botanical: soft floral tones, luminous highlights, flushed cheeks",
            ],
        },
        "PRODUCT_MACRO": {
            "liquid_physics": "Slow-motion condensation beads, viscous pouring (honey/oil), explosive splash (4k droplets)",
            "textile_detail": "Micro-weave patterns, individual thread fibers, soft fabric ripple in slow-motion",
            "tech_surface": "Subsurface scattering on matte plastic, brushed aluminum grain, laser-etched logos",
            "culinary_hero": "Steam tendrils, caramelizing textures, glistening glaze, internal heat glow",
            "metallic_oxidation": "High-detail macro on brushed titanium, shifting light on chrome surfaces, iridescent carbon-fiber",
            "geological_texture": "Raw stone grain, crystalline structures, microscopic dust particles catching the light",
            "organic_macro": "Detailed plant veins, soft botanical fuzz, microscopic pollen, translucent leaves",
            "cosmetic_viscosity": "Rich cream texture, shimmering micro-particles, smooth applicator gliding through liquid",
        },
        "ENVIRONMENT": {
            "spatial_context": [
                "Brutalist Concrete Atrium: scale-play, dramatic shadows, floor-to-ceiling glass",
                "Hyper-Modern Lab: glowing recessed lights, liquid-nitrogen vapor, stainless steel",
                "Zen Sanctuary: raked sand, slate stone, reflecting pools, bonsai silhouettes",
                "Infinite Abstract: soft-gradient 'limbo' space, floating geometric shapes, volumetric fog",
                "Abandoned Luxury Ballroom: peeling gold leaf, dusty chandeliers, shafts of window light",
                "Pristine Arctic Expanse: white-on-white, blue shadows, distant snowy horizons",
                "Neon Sky-Bridge: glowing foundations, city-lights below, futuristic glass architecture",
                "Mediterranean Cliffside: limestone textures, deep blue sea, sun-bleached wood",
            ]
        },
        "CINEMATOGRAPHY": {
            "optical_specs": [
                "Master Prime 100mm Macro: extreme shallow depth, razor-sharp focus on texture",
                "Anamorphic 35mm: horizontal blue lens flares, oval bokeh, wide cinematic 'squeeze'",
                "Probe Lens: immersive 'through-the-object' perspective, wide-angle macro shots",
                "70mm IMAX: immense scale, zero distortion, hyper-real clarity",
                "Tilt-Shift Lens: miniature-effect selective focus, surreal depth perception",
                "Vintage Kowa Anamorphic: warm flares, high-character distortion, soft edges",
                "Fisheye 8mm: extreme peripheral distortion, immersive 'center-of-world' feel",
                "T2.8 Portrait Prime: soft background separation, dreamy bokeh, flattering skin tones",
            ],
            "dynamic_motion": [
                "SnorriCam: camera locked to the actor for a disorienting, immersive feel",
                "Circular Orbit: 360-degree high-speed rotation around the hero product",
                "Crash Zoom: sudden, rhythmic zoom-in for high energy",
                "Parallax Slide: foreground elements moving faster than background for depth",
                "Slow-Motion Reveal: 120fps dolly-out from a macro detail to full character",
                "Whip-Pan Transition: fast-paced kinetic blur connecting two different locations",
                "Steady-Cam Chase: low-angle, smooth tracking behind an athlete",
                "Handheld Shiver: subtle vibrating movement to evoke intensity or anxiety",
            ],
        },
        "ILLUMINATION": {
            "aesthetic_vibe": [
                "Butterfly Lighting: flattering high-contrast for beauty shots",
                "Rembrandt Lighting: classic mood with the signature 'triangle' cheek highlight",
                "Neon Cyber-Noir: dual-tone rim lighting (Magenta/Cyan), high-gloss reflections",
                "Golden Hour Backlighting: warm, soft flares, volumetric sunbeams",
                "High-Key Commercial: bright, clean, shadow-less, premium vibe",
                "Moody Chiaroscuro: high contrast, deep shadows, single theatrical source",
                "Bioluminescent Glow: soft internal light sources, glowing product features",
                "Motivated Candle-light: flickering warm tones, soft shadows, intimate feel",
            ],
            "tonal_highlights": [
                "Caustic light reflections through water",
                "Soft-box pearlescent sheen on surfaces",
                "Edge-glow rim lighting (separating subject from dark background)",
                "Volumetric dust-motes in a window beam",
                "Subtle prism rainbow flares on the lens edge",
                "OLED blue screen-glow spill on subject face",
                "Metallic specular highlights (sparkling micro-points)",
                "Soft rim-lighting on hair/textures",
            ],
        },
        "SONIC_LANDSCAPE": {
            "composition_styles": [
                "Industrial Minimalist: rhythmic metallic pings, deep sub-bass pulses, clean silence",
                "Modern Orchestral: soaring staccato strings, cinematic brass swells, hybrid synth",
                "Lo-Fi Luxury: vinyl crackle, soulful Rhodes piano, laid-back jazzy percussion",
                "ASMR Soundscape: crisp fabric rustles, liquid pours, hyper-detailed foley",
                "Cyberpunk Synth-wave: high-energy arpeggios, analog distortion, heavy percussion",
                "Ethereal Ambient: slow-moving pads, shimmering chimes, vast reverb tails",
                "Aggressive Trap-Hybrid: heavy 808s, distorted vocals, fast-paced hi-hats",
                "Nostalgic Folk: acoustic guitar, natural environment sounds, warm vocals",
            ]
        },
        "FIDELITY_GUARDS": [
            "No motion artifacts in high-speed splashes",
            "Text on products must be legible or stylized blur, no 'gibberish' characters",
            "Maintain perfect 'Golden Hour' color temperature if outdoors",
            "Skin texture must remain visible (no 'plastic' AI face smoothing)",
            "Ensure 'Product-as-Hero' logic: the product is always the brightest/sharpest point",
            "No floating objects or gravity-defying hair unless explicitly requested",
            "Temporal consistency: wardrobe must not change between matching scenes",
            "Lighting direction must remain consistent within a narrative sequence",
        ],
    },
    "SOCIAL_NATIVE": {
        "BRAND_AESTHETICS": {
            "ugc_authentic": "Natural lighting, slightly messy backgrounds, direct Eye-contact, relatable environment.",
            "creator_premium": "Ring lighting, clean aesthetics, trending color palettes, high-energy editing cues.",
            "street_vlog": "Raw handheld movement, urban sidewalk sounds, casual direct-to-camera address.",
            "home_wellness": "Diffused window light, soft linens, plant-filled domestic spaces, tranquil mood.",
            "tech_influencer": "Multiple monitor glow, desk setup aesthetic, high-quality audio equipment visible.",
            "fitness_native": "Gym environment, high-key overhead light, dynamic movement, high motivation.",
            "culinary_vibe": "Close-up food prep, overhead tripod shots, messy but tasty application, ASMR sounds.",
            "luxury_lifestyle": "High-end car interior, designer accessories, hotel lobby aesthetic, aspirational but raw.",
        },
        "CHARACTER_DETAILS": {
            "primary_actors": [
                "The 'Real User': relatable, expressive, comfortable in a home setting",
                "The 'Expert Hobbyist': focused, using product in context",
                "The 'Vibe Curator': high energy, trendy attire, direct address",
                "The 'Satisfied Customer': genuine smile, relaxed posture, authentic delight",
                "The 'DIY Creator': messy hands, focused gaze on the task",
                "The 'Busy Professional': multi-tasking, on-the-go, relatable stress",
                "The 'Fitness Enthusiast': active movement, expressive exertion, high energy",
                "The 'Tech-Savvy Youth': fast-paced gestures, phone-in-hand, high energy",
            ],
            "attire_styling": [
                "Lived-in Casual: comfort-first, standard household textiles",
                "Active Everyday: functional athletic wear",
                "Smart-Casual Home: neat sweater, denim, relatable style",
                "Streetwear: oversized hoodies, beanies, sneakers",
                "Professional Uniform: apron, scrubs, or business-casual",
                "Sleepwear: cozy pajamas, soft robes, morning look",
                "Traveler Gear: backpack, weatherproof jacket, layered look",
                "Trendy Lifestyle: high-saturation colors, current fashion trends",
            ],
            "visage_grooming": [
                "Everyday Natural: minimal makeup, real skin textures",
                "Fresh-Faced: clear skin, light gloss, soft highlights",
                "Groomed Casual: neat beard, simple hair styling",
                "Workout Glow: slight sweat, bun-tied hair, natural skin",
                "Trending Glam: defined brows, lash extensions, lip gloss",
                "Relaxed Home-look: messy bun, 'no-care' grooming",
                "Urbane Grooming: sharp haircut, well-maintained beard",
                "Playful Color: bright nail polish, fun hair clips, youthful energy",
            ],
        },
        "PRODUCT_MACRO": {
            "unboxing_tactile": "Focus on opening packaging, textured cardstock, satisfied peeling sounds",
            "real_world_use": "Direct interaction, product gripped by hand, messy but honest application",
            "handheld_closeup": "Product held towards the lens, shallow depth focusing on label",
            "texture_smear": "Cream or liquid spread on skin, macro focus on consistency",
            "swatch_test": "Makeup or color applied to arm, high-detail macro",
            "tech_interaction": "Finger swiping screen, clicking buttons, LED indicators flashing",
            "crunch_snap": "Food being bitten into or broken, macro focus on internal texture",
            "fabric_feel": "Hand brushing over soft fabric, close-up on weave",
        },
        "ENVIRONMENT": {
            "spatial_context": [
                "Domestic Kitchen: relatable clutter, warm wood, fridge magnets",
                "Sunlit Bedroom: unmade bed, soft morning light, plant on nightstand",
                "In-car Vlog: driver/passenger seat view, passing city motion",
                "Urban Street Walk-and-talk: sidewalk, shop-windows in background",
                "Home Gym: yoga mat, dumbbell rack, neutral walls",
                "Coffee Shop: blurred patrons, steam machine, wooden table",
                "Cozy Living Room: soft sofa, pillows, television glow",
                "Modern Home Office: laptop, monitors, coffee mug, bookshelf",
            ]
        },
        "CINEMATOGRAPHY": {
            "optical_specs": [
                "Smartphone Vertical 24mm: standard social media perspective",
                "Front-facing Selfie Cam: authentic distortion, relatable look",
                "Handheld Main Sensor: sharp detail, wide-angle POV",
                "Over-the-shoulder POV: immersive user-perspective",
            ],
            "dynamic_motion": [
                "Handheld Shake: authentic movement to evoke realness",
                "Snap-zoom: quick rhythmic zoom into product",
                "Quick Cuts: fast-paced jumping between angles",
                "Screen-recording Overlays: digital UI appearing over the shot",
                "Circular Hand-Pan: camera rotation to reveal environment",
                "Camera Drop: mimicking setting the phone down on a table",
                "Walking Tracking: bobbing motion of a walking creator",
                "Mirror Reveal: camera move from subject to their reflection",
            ],
        },
        "ILLUMINATION": {
            "aesthetic_vibe": [
                "Natural Window Light: soft directional shadows",
                "Overhead Warm Domestic: standard yellowish room light",
                "Electronic Screen Glow: cool blue light from a monitor/phone",
                "Outdoor Golden Hour: warm sunset glow, lens flares",
                "Soft Ring Light: circular reflection in eyes, even beauty lighting",
                "Harsh Midday Sun: high contrast, authentic feeling",
                "String/Fairy Lights: soft bokeh background, cozy evening feel",
                "Dusk Street-light: orange sodium glow, moody urban look",
            ],
            "tonal_highlights": [
                "Natural sun-flares across the lens",
                "Incidental shadows on the background",
                "Reflection of the phone screen in a surface",
                "Soft glow on the creator's face from the window",
                "Hard shadows from bright indoor light",
                "Glitter or shimmering product details catching the light",
            ],
        },
        "SONIC_LANDSCAPE": {
            "composition_styles": [
                "Trending Audio Bed: high-energy, familiar beats",
                "Upbeat Lo-Fi: chill, modern, non-distracting backgrounds",
                "Raw Environment Sounds (Ambient): street noise, home birds, wind",
                "Direct Voiceover (ASMR): whispered or very close mic-ing",
                "Hyper-fast Cuts Audio: rhythmic sync to visual jumps",
                "Soft Acoustic: intimate, guitar or piano focused",
                "Synth-Pop: energetic, colorful, youthful energy",
                "Muted Muffled: high-frequency roll-off to sound like a distant speaker",
            ]
        },
        "FIDELITY_GUARDS": [
            "Maintain 'Handheld' feel to ensure authenticity",
            "Background must remain recognizable (avoid unrealistic blurring)",
            "Stay consistent with the character's creator identity",
            "No cinematic 'over-grading'—maintain Rec.709 look",
            "Ensure on-screen text is in social-native fonts/styles",
            "Foley sounds must feel incidental and real (not studio-perfect)",
            "Lighting must match the environment (e.g. no ring light in a forest)",
            "Clothing should remain consistent for the character",
        ],
    },
}


# --- CURATED "LOOKS" ---
# A Look is a single, internally-coherent art-direction bundle: every field is
# chosen to reinforce the others. This is the opposite of sampling each field
# independently (which produces clashing combinations like "intimate candlelight"
# + "aggressive trap" + "tilt-shift miniature"). recommend_production_recipe
# selects ONE Look for the brief and binds it to every scene. Each Look carries
# selection metadata (tier / tones / keywords / description) used by the LLM
# selector, plus a `recipe` payload in the exact shape the storyboard and
# generation pipeline already consume.
#
# Tones are selection signal and are kept disjoint within a tier. A tone listed
# by several Looks does not discriminate between them and biases the selector
# toward whichever carries the most of them, irrespective of category.

PRODUCTION_LOOKS: list[Dict[str, Any]] = [
    # ---------------- COMMERCIAL (premium, produced) ----------------
    {
        "name": "Luxury Heritage",
        "tier": "commercial",
        "tones": ["premium", "elegant", "timeless", "sophisticated", "emotional"],
        "keywords": [
            "luxury",
            "heritage",
            "watch",
            "jewelry",
            "spirits",
            "leather",
            "finance",
            "automotive",
            "fragrance",
        ],
        "description": (
            "Timeless luxury — deep mahogany and brushed gold, moody chiaroscuro, "
            "portrait optics. Aspirational, refined, emotional."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Deep mahogany, brushed gold, velvet textures, low-key lighting, timeless elegance.",
            "character": {
                "actor_vibe": "The 'Connoisseur': refined features, calm and deliberate movement, admiring the product",
                "attire": "Textural Luxury: heavy-gauge cashmere, raw silk, bespoke structured wool",
                "grooming": "Precision Grooming: sharp lines, matte-finish styling",
                "motion": "Slow, deliberate, poised movement",
            },
            "environment": {
                "spatial_context": "Abandoned Luxury Ballroom: peeling gold leaf, dusty chandeliers, shafts of window light",
                "temporal": "Moody Chiaroscuro: high contrast, deep shadows, single theatrical source",
            },
            "cinematography": {
                "optics": "T2.8 Portrait Prime: soft background separation, dreamy bokeh, flattering tones",
                "movement": "Slow-Motion Reveal: 120fps dolly-out from a macro detail to the full subject",
                "motion_texture": "Master Prime 100mm Macro: razor-sharp focus on texture",
            },
            "illumination": {
                "vibe": "Moody Chiaroscuro: high contrast, deep shadows, single theatrical source",
                "chromatic_scheme": "Warm amber and gold against deep shadow",
                "key_lighting": "Rembrandt Lighting: classic 'triangle' cheek highlight",
                "highlights": "Soft edge-glow rim lighting separating subject from dark background",
            },
            # Substituted when the ad has no on-screen person. Portrait optics
            # ask the renderer for a face that is not in the shot; macro optics
            # deliver the same shallow-depth look aimed at the product.
            "product_mode": {
                "optics": "T2.8 Macro Prime: soft background separation, dreamy bokeh, warm tones",
            },
            "sonic_landscape": "Modern Orchestral: soaring staccato strings, cinematic brass swells, hybrid synth",
        },
    },
    {
        "name": "Clean Tech Minimalism",
        "tier": "commercial",
        "tones": ["modern", "precise", "innovative", "cool", "minimal", "technical"],
        "keywords": [
            "tech",
            "gadget",
            "saas",
            "app",
            "device",
            "appliance",
            "electronics",
            "ai",
            "software",
            "fintech",
        ],
        "description": (
            "Modern tech minimalism — monochrome whites and frosted glass, high-key "
            "clean light, IMAX clarity. Precise, innovative, cool."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Monochromatic whites/greys, frosted glass, blue-tinted shadows, ultra-clean surfaces.",
            "character": {
                "actor_vibe": "The 'Tech-Visionary': focused, minimalist attire, calm confidence",
                "attire": "Technical Performance: laser-cut seams, matte-finish synthetics",
                "grooming": "Precision Grooming: sharp lines, matte-finish styling",
                "motion": "Deliberate, precise, minimal gestures",
            },
            "environment": {
                "spatial_context": "Hyper-Modern Lab: glowing recessed lights, stainless steel, ultra-clean surfaces",
                "temporal": "High-Key Commercial: bright, clean, shadow-less, premium",
            },
            "cinematography": {
                "optics": "70mm IMAX: immense clarity, zero distortion, hyper-real detail",
                "movement": "Circular Orbit: smooth 360-degree rotation around the hero product",
                "motion_texture": "Probe Lens: immersive through-the-object macro perspective",
            },
            "illumination": {
                "vibe": "High-Key Commercial: bright, clean, shadow-less, premium",
                "chromatic_scheme": "Cool monochrome whites with blue-tinted shadow",
                "key_lighting": "Butterfly Lighting: even, flattering, high-clarity",
                "highlights": "Metallic specular highlights (sparkling micro-points)",
            },
            "product_mode": {
                "key_lighting": "Even Overhead Key: shadow-less, high-clarity across the surface",
            },
            "sonic_landscape": "Industrial Minimalist: rhythmic metallic pings, deep sub-bass pulses, clean silence",
        },
    },
    {
        "name": "Nostalgic Warm Film",
        "tier": "commercial",
        "tones": ["warm", "nostalgic", "cozy", "authentic", "emotional", "artisan"],
        "keywords": [
            "food",
            "coffee",
            "snacks",
            "bakery",
            "home",
            "family",
            "craft",
            "comfort",
            "restaurant",
            "beverage",
        ],
        "description": (
            "Warm nostalgic film — amber tones, film grain, golden-hour flares, "
            "vintage anamorphic. Cozy, authentic, heartfelt."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Warm amber tones, film grain, soft lens flares, 70s-style typography, rich filmic saturation.",
            "character": {
                "actor_vibe": "The 'Craftsman': macro focus on hands, dust motes in hair, rugged linen apron",
                "attire": "Vintage Filmic: textured corduroy, worn leather, high-waisted tailoring",
                "grooming": "Sun-kissed Glow: bronzed skin, scattered freckles, wind-tossed hair",
                "motion": "Gentle, unhurried, human",
            },
            "environment": {
                "spatial_context": "Sun-drenched artisan interior: warm wood, soft window light, lived-in warmth",
                "temporal": "Golden Hour Backlighting: warm, soft flares, volumetric sunbeams",
            },
            "cinematography": {
                "optics": "Vintage Kowa Anamorphic: warm flares, high-character distortion, soft edges",
                "movement": "Parallax Slide: foreground moving faster than background for depth",
                "motion_texture": "Anamorphic 35mm: oval bokeh, filmic organic texture",
            },
            "illumination": {
                "vibe": "Golden Hour Backlighting: warm, soft flares, volumetric sunbeams",
                "chromatic_scheme": "Rich warm amber and honey tones",
                "key_lighting": "Motivated Candle-light: flickering warm tones, soft shadows, intimate feel",
                "highlights": "Volumetric dust-motes in a window beam",
            },
            "sonic_landscape": "Nostalgic Folk: instrumental acoustic guitar, natural environment sounds, warm and unhurried",
        },
    },
    {
        "name": "Vibrant CPG Pop",
        "tier": "commercial",
        "tones": ["playful", "energetic", "vibrant", "fun", "youthful", "bold"],
        "keywords": [
            "snacks",
            "candy",
            "beverage",
            "cpg",
            "kids",
            "fun",
            "retail",
            "soda",
            "fashion",
            "toys",
        ],
        "description": (
            "Vibrant CPG pop — high-saturation color-block, punchy high-key light, "
            "crash zooms. Playful, energetic, fun."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "High-saturation color pops, playful shadows, rhythmic editing, bold color-block styling.",
            "character": {
                "actor_vibe": "The 'Creative Radical': confident, expressive, playful energy",
                "attire": "Street-Style High-Fashion: bold color-block, contrast stitching, statement pieces",
                "grooming": "Saturated Pop: vibrant color accents, bold matte lips, playful styling",
                "motion": "Snappy, energetic, rhythmic",
            },
            "environment": {
                "spatial_context": "Infinite Abstract: soft-gradient color 'limbo' space, floating geometric shapes",
                "temporal": "High-Key Commercial: bright, clean, punchy, premium",
            },
            "cinematography": {
                "optics": "Probe Lens: immersive wide-angle macro, dynamic product-hero perspective",
                "movement": "Crash Zoom: sudden, rhythmic zoom-in for high energy",
                "motion_texture": "Tilt-Shift Lens: playful selective focus",
            },
            "illumination": {
                "vibe": "High-Key Commercial: bright, clean, punchy color, premium",
                "chromatic_scheme": "Bold saturated primary color-block palette",
                "key_lighting": "Butterfly Lighting: bright, even, poppy",
                "highlights": "Soft-box pearlescent sheen on surfaces",
            },
            "product_mode": {
                "key_lighting": "Even Overhead Key: bright, punchy, shadow-less",
            },
            "sonic_landscape": "Upbeat Pop-Electronic: bright synths, punchy claps, playful bassline, high-energy hooks",
        },
    },
    {
        "name": "High-Octane Sports",
        "tier": "commercial",
        "tones": ["dynamic", "powerful", "intense", "energetic", "bold", "athletic"],
        "keywords": [
            "sports",
            "fitness",
            "athletic",
            "energy",
            "automotive",
            "gaming",
            "performance",
            "outdoor",
            "adventure",
        ],
        "description": (
            "High-octane sports — grit and sweat-sheen, anamorphic flares, "
            "chase cameras, aggressive rhythm. Powerful and intense."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "High contrast, grit, sweat-sheen, aggressive motion blur, anamorphic flares.",
            "character": {
                "actor_vibe": "The 'Modern Athlete': hyper-defined muscle tension, micro-droplets of sweat, explosive power",
                "attire": "Technical Performance: laser-cut seams, matte synthetics, iridescent fibers",
                "grooming": "High-Contrast Shadow: sharp contours, intense focused gaze",
                "motion": "Explosive, powerful, kinetic",
            },
            "environment": {
                "spatial_context": "Brutalist Concrete Atrium: scale-play, dramatic shadows, raw texture",
                "temporal": "Moody Chiaroscuro: high contrast, deep shadows, dramatic source",
            },
            "cinematography": {
                "optics": "Anamorphic 35mm: horizontal blue lens flares, oval bokeh, cinematic squeeze",
                "movement": "Steady-Cam Chase: low-angle, smooth tracking behind the athlete",
                "motion_texture": "Master Prime 100mm Macro: razor-sharp texture on sweat and fabric",
            },
            "illumination": {
                "vibe": "Moody Chiaroscuro: high contrast, deep shadows, dramatic single source",
                "chromatic_scheme": "High-contrast steel with cyan/magenta rim",
                "key_lighting": "Neon Cyber-Noir: dual-tone rim lighting (magenta/cyan), high-gloss",
                "highlights": "Metallic specular highlights and edge-glow rim",
            },
            "product_mode": {
                "brand_archetype": "High contrast, grit, condensation sheen, aggressive motion blur, anamorphic flares.",
                "motion_texture": "Master Prime 100mm Macro: razor-sharp texture on material grain and edges",
            },
            "sonic_landscape": "Aggressive Trap-Hybrid: heavy 808s, distorted textures, fast-paced hi-hats",
        },
    },
    {
        "name": "Organic Wellness",
        "tier": "commercial",
        "tones": ["calm", "natural", "serene", "soothing", "wholesome", "pure"],
        "keywords": [
            "wellness",
            "beauty",
            "skincare",
            "health",
            "spa",
            "organic",
            "botanical",
            "sustainable",
            "cosmetics",
        ],
        "description": (
            "Organic wellness — earthy linens, diffused daylight, botanical macro, "
            "ethereal ambient. Calm, natural, serene."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Earthy linens, diffused sunlight, botanical greens, raw wood, 'no-makeup' makeup look.",
            "character": {
                "actor_vibe": "The 'Zen Practitioner': relaxed facial muscles, luminous hydrated skin",
                "attire": "Fluid Ethereal: flowing chiffon, sheer layers, light-catching fabrics",
                "grooming": "Dewy Botanical: soft floral tones, luminous highlights, flushed cheeks",
                "motion": "Serene, flowing, unhurried",
            },
            "environment": {
                "spatial_context": "Zen Sanctuary: raked sand, slate stone, reflecting pools, botanical silhouettes",
                "temporal": "Golden Hour Backlighting: warm, soft, diffused daylight",
            },
            "cinematography": {
                "optics": "T2.8 Portrait Prime: soft separation, dreamy bokeh, flattering skin",
                "movement": "Slow-Motion Reveal: gentle 120fps dolly across botanical detail",
                "motion_texture": "Master Prime 100mm Macro: detailed plant veins and soft botanical fuzz",
            },
            "illumination": {
                "vibe": "Golden Hour Backlighting: warm, soft, diffused daylight",
                "chromatic_scheme": "Soft earthy greens and warm neutrals",
                "key_lighting": "Soft window key with gentle wraparound",
                "highlights": "Caustic light reflections through water",
            },
            # Substituted when the ad has no on-screen person: the wellness
            # aesthetic survives, but skin and make-up references do not.
            "product_mode": {
                "brand_archetype": "Earthy linens, diffused sunlight, botanical greens, raw wood, natural matte finishes.",
                "optics": "T2.8 Macro Prime: soft separation, dreamy bokeh, warm natural tones",
            },
            "sonic_landscape": "Ethereal Ambient: slow-moving pads, shimmering chimes, vast reverb tails",
        },
    },
    {
        "name": "Home & Interior",
        "tier": "commercial",
        "tones": ["inviting", "restful", "homely", "textural", "spacious"],
        "keywords": [
            "furniture",
            "sofa",
            "mattress",
            "bedding",
            "interior",
            "decor",
            "rug",
            "lawn",
            "garden",
            "homeware",
        ],
        "description": (
            "Lived-in interiors — oak, linen and wool under soft window light, "
            "unhurried dolly moves. Inviting, restful, textural."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Warm neutral palette, oiled oak, stonewashed linen, boucle wool, brushed brass, layered textiles.",
            "character": {
                "actor_vibe": "The 'Homemaker': unhurried, settling into the space as if it were their own",
                "attire": "Soft Domestic: oversized knitwear, relaxed cotton, bare feet",
                "grooming": "Effortless and undone, as at home on a slow morning",
                "motion": "Unhurried, settling, weight sinking into furniture",
            },
            "environment": {
                "spatial_context": "Sunlit Apartment: sheer curtains, plastered walls, potted greenery, mid-century furniture",
                "temporal": "Late Morning Window Light: soft, directional, slowly drifting",
            },
            "cinematography": {
                "optics": "T2.0 Spherical Prime: gentle falloff, honest geometry, no distortion",
                "movement": "Slow Lateral Dolly: a patient glide past furniture at seated height",
                "motion_texture": "Master Prime 100mm Macro: weave of linen, grain of oak, pile of wool",
            },
            "illumination": {
                "vibe": "Soft Window Daylight: broad, wrapping, gently directional",
                "chromatic_scheme": "Warm neutrals, oatmeal and clay against muted green",
                "key_lighting": "Large north-facing window key with bounced fill",
                "highlights": "Soft sheen along brass edges and polished wood",
            },
            "sonic_landscape": "Warm Acoustic Minimal: felted piano, soft upright bass, unhurried brushed percussion",
        },
    },
    {
        "name": "Culinary Appetite",
        "tier": "commercial",
        "tones": ["appetizing", "hearty", "indulgent", "savory", "abundant"],
        "keywords": [
            "food",
            "meal",
            "recipe",
            "kitchen",
            "snack",
            "frozen",
            "sauce",
            "blender",
            "ingredients",
            "grocery",
        ],
        "description": (
            "Appetite-forward food commercial — steam, gloss and sizzle, hard "
            "raking light, macro cross-sections. Hearty, indulgent, abundant."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Saturated food colour, glossy sauces, rising steam, cast iron and butcher block, scattered raw ingredients.",
            "character": {
                "actor_vibe": "The 'Home Cook': confident hands working the pan, absorbed in the task",
                "attire": "Working Kitchen: rolled sleeves, linen apron, simple dark cotton",
                "grooming": "Unfussed and practical, sleeves pushed back",
                "motion": "Purposeful, tactile, hands leading the frame",
            },
            "environment": {
                "spatial_context": "Warm Working Kitchen: butcher block, cast iron, hanging copper, flour dust in the air",
                "temporal": "Low Raking Sidelight: hard, warm, carving texture out of shadow",
            },
            "cinematography": {
                "optics": "T2.8 Macro Prime: shallow plane on a single glistening detail",
                "movement": "Fast Push-In on the Pour: an accelerating move onto the moment of contact",
                "motion_texture": "Probe Lens Macro: syrup thread, cheese pull, crumb structure at 240fps",
            },
            "illumination": {
                "vibe": "Hard Raking Sidelight: strong single source skimming the surface",
                "chromatic_scheme": "Deep caramel, burnt orange and cream against dark wood",
                "key_lighting": "Hard backlight through rising steam with a warm bounce return",
                "highlights": "Wet specular glints on sauce, glaze and rendered fat",
            },
            "sonic_landscape": "Rhythmic Kitchen Percussion: warm marimba, plucked upright bass, brushed snare, playful woodblock",
        },
    },
    {
        "name": "Pet Companion",
        "tier": "commercial",
        "tones": ["affectionate", "loyal", "spirited", "tender", "joyful"],
        "keywords": [
            "pet",
            "dog",
            "cat",
            "puppy",
            "kitten",
            "kibble",
            "treats",
            "veterinary",
            "leash",
            "companion",
        ],
        "description": (
            "The bond with an animal — golden domestic light, camera at paw "
            "height, unposed motion. Affectionate, loyal, spirited."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Golden domestic warmth, worn rugs and sunlit floorboards, soft blankets, scattered toys, honest household clutter.",
            "character": {
                "actor_vibe": "The 'Devoted Owner': crouching to the animal's level, laughing without performing",
                "attire": "Weekend Domestic: soft flannel, worn denim, thick socks",
                "grooming": "Casual and unstyled, as on an ordinary Saturday",
                "motion": "Kneeling, reaching, playful and reactive",
            },
            "environment": {
                "spatial_context": "Sunlit Living Room: worn rug, low couch, scattered toys, garden visible through glass",
                "temporal": "Late Afternoon Sun: long warm shafts across the floor",
            },
            "cinematography": {
                "optics": "T2.0 Spherical Prime: low at paw height, generous depth, honest perspective",
                "movement": "Handheld Follow: a low tracking chase keeping pace with the animal",
                "motion_texture": "Master Prime 100mm Macro: individual guard coat strands, wet nose, paw pads at 120fps",
            },
            "illumination": {
                "vibe": "Warm Domestic Afternoon: low golden sun through a window",
                "chromatic_scheme": "Honeyed golds and soft greens against warm neutrals",
                "key_lighting": "Low sun raking across the floor with soft ambient fill",
                "highlights": "Backlit rim glow through a raised ear and coat edge",
            },
            "sonic_landscape": "Playful Acoustic Folk: fingerpicked guitar, hand claps, glockenspiel, light shaker",
        },
    },
    {
        "name": "Fashion Editorial",
        "tier": "commercial",
        "tones": ["stylish", "editorial", "sculpted", "urbane", "poised"],
        "keywords": [
            "fashion",
            "apparel",
            "knitwear",
            "eyewear",
            "sunglasses",
            "accessories",
            "clothing",
            "footwear",
            "boutique",
            "jewellery",
        ],
        "description": (
            "Editorial fashion — seamless backdrops, hard sculpted light, "
            "garment drape in motion. Stylish, sculpted, poised."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Seamless paper backdrops, sculptural silhouettes, restrained palette, matte and sheen played against each other.",
            "character": {
                "actor_vibe": "The 'Editorial Model': composed, still, weight held on one hip",
                "attire": "Directional Tailoring: sharp shoulders, fluid drape, considered proportion",
                "grooming": "Sculpted and deliberate, styled to the garment",
                "motion": "Deliberate, held poses breaking into a single fluid turn",
            },
            "environment": {
                "spatial_context": "Seamless Studio Cyclorama: infinite backdrop, polished concrete, a single sculptural plinth",
                "temporal": "Controlled Studio Time: no exterior reference, light entirely built",
            },
            "cinematography": {
                "optics": "T2.8 Anamorphic: oval bokeh, horizontal flare, sculpted separation",
                "movement": "Orbiting Arc: a slow circular track around the subject",
                "motion_texture": "Master Prime 100mm Macro: knit loops, weave slub and stitch at 120fps",
            },
            "illumination": {
                "vibe": "Hard Sculpted Key: single crisp source with deep controlled shadow",
                "chromatic_scheme": "Monochrome base with one saturated accent",
                "key_lighting": "Hard fresnel key at 45 degrees with black negative fill",
                "highlights": "Crisp edge separation along shoulder and hem",
            },
            # The general styling is built around a worn garment; a product-only
            # cut swaps to the garment itself as the sculptural subject.
            "product_mode": {
                "brand_archetype": "Seamless paper backdrops, sculptural garment forms on invisible support, restrained palette, matte against sheen.",
                "motion_texture": "Probe Lens Macro: knit loops, weave slub and stitched seams in raking light",
            },
            "sonic_landscape": "Minimal Electronic Runway: sparse four-on-the-floor kick, filtered synth stabs, tape hiss",
        },
    },
    {
        "name": "Outdoor Adventure",
        "tier": "commercial",
        "tones": ["rugged", "expansive", "adventurous", "sunlit", "freewheeling"],
        "keywords": [
            "camping",
            "hiking",
            "trail",
            "backyard",
            "grill",
            "campsite",
            "cooler",
            "portable",
            "gear",
            "ridgeline",
        ],
        "description": (
            "Open air and open road — wide vistas, hard sun, dust and flare, "
            "gear in real use. Rugged, expansive, adventurous."
        ),
        "recipe": {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Sun-bleached landscape, anodised metal and ripstop nylon, dust in the air, honest wear and scuffs.",
            "character": {
                "actor_vibe": "The 'Explorer': weathered, capable, scanning the horizon",
                "attire": "Technical Outdoor: ripstop shells, worn boots, layered fleece",
                "grooming": "Windblown and unstyled, earned rather than arranged",
                "motion": "Purposeful stride, loading gear, riding through frame",
            },
            "environment": {
                "spatial_context": "Open Trailhead: scrub grass, gravel, distant ridgeline, wide unbroken sky",
                "temporal": "Hard Midday Sun: bright, high contrast, short crisp shadows",
            },
            "cinematography": {
                "optics": "T2.8 Wide Spherical: deep focus, expansive field, natural perspective",
                "movement": "Tracking Vehicle Follow: a low fast parallel move alongside the action",
                "motion_texture": "Probe Lens Macro: grit on tread, dust plume and knurled metal at 120fps",
            },
            "illumination": {
                "vibe": "Hard Natural Sun: unmodified daylight, deep contrast",
                "chromatic_scheme": "Sun-bleached ochre and dust against deep sky blue",
                "key_lighting": "Direct overhead sun with a large silver bounce return",
                "highlights": "Anamorphic sun flare across the lens and hot metal glints",
            },
            "sonic_landscape": "Driving Indie Rock: gritty baritone guitar, four-on-the-floor drums, handclap stomps",
        },
    },
    # ---------------- SOCIAL NATIVE / UGC (authentic, handheld) ----------------
    {
        "name": "Authentic Creator",
        "tier": "ugc",
        "tones": ["authentic", "relatable", "genuine", "warm", "casual"],
        "keywords": [
            "ugc",
            "review",
            "testimonial",
            "lifestyle",
            "everyday",
            "home",
            "unboxing",
            "haul",
        ],
        "description": (
            "Authentic creator — natural window light, cozy home, handheld selfie. "
            "Relatable and genuine."
        ),
        "recipe": {
            "style_mode": "SOCIAL_NATIVE",
            "brand_archetype": "Natural lighting, slightly messy backgrounds, direct eye-contact, relatable environment.",
            "character": {
                "actor_vibe": "The 'Real User': relatable, expressive, comfortable at home",
                "attire": "Lived-in Casual: comfort-first, standard household textiles",
                "grooming": "Everyday Natural: minimal makeup, real skin textures",
                "motion": "Relaxed, natural, handheld",
            },
            "environment": {
                "spatial_context": "Cozy Living Room: soft sofa, pillows, relatable lived-in warmth",
                "temporal": "Natural Window Light: soft directional shadows",
            },
            "cinematography": {
                "optics": "Front-facing Selfie Cam: authentic distortion, relatable look",
                "movement": "Handheld Shake: subtle authentic movement",
                "motion_texture": "Handheld Main Sensor: sharp, real, wide POV",
            },
            "illumination": {
                "vibe": "Natural Window Light: soft directional shadows",
                "chromatic_scheme": "Neutral warm domestic tones",
                "key_lighting": "Soft window key on the face",
                "highlights": "Soft glow on the creator's face from the window",
            },
            "sonic_landscape": "Upbeat Lo-Fi: chill, modern, non-distracting background",
            # Substituted when the ad has no on-screen person: a key light aimed
            # at a face that is not in the shot just confuses the renderer.
            "product_mode": {
                "key_lighting": "Soft window key across the product",
            },
        },
    },
    {
        "name": "Polished Creator",
        "tier": "ugc",
        "tones": ["trendy", "clean", "energetic", "aspirational", "youthful"],
        "keywords": [
            "beauty",
            "skincare",
            "fashion",
            "creator",
            "influencer",
            "haul",
            "trending",
            "makeup",
        ],
        "description": (
            "Polished creator — ring-light glow, trendy bright bedroom, snappy "
            "zooms. Clean, aspirational, native."
        ),
        "recipe": {
            "style_mode": "SOCIAL_NATIVE",
            "brand_archetype": "Ring lighting, clean aesthetics, trending color palettes, high-energy editing cues.",
            "character": {
                "actor_vibe": "The 'Vibe Curator': high energy, trendy attire, direct address",
                "attire": "Trendy Lifestyle: high-saturation colors, current fashion trends",
                "grooming": "Trending Glam: defined brows, lash extensions, lip gloss",
                "motion": "High-energy, snappy, expressive",
            },
            "environment": {
                "spatial_context": "Sunlit Bedroom: bright, clean, soft morning light, trendy decor",
                "temporal": "Soft Ring Light: circular catchlight, even beauty lighting",
            },
            "cinematography": {
                "optics": "Smartphone Vertical 24mm: standard social-media perspective",
                "movement": "Snap-zoom: quick rhythmic zoom into product",
                "motion_texture": "Handheld Main Sensor: sharp, crisp detail",
            },
            "illumination": {
                "vibe": "Soft Ring Light: circular catchlight, even beauty lighting",
                "chromatic_scheme": "Bright clean trending palette",
                "key_lighting": "Soft ring key with even wraparound",
                "highlights": "Glitter or shimmering product details catching the light",
            },
            "product_mode": {
                "brand_archetype": "Clean aesthetics, trending color palettes, high-energy editing cues, crisp product staging.",
                "vibe": "Soft Ring Light: even wraparound illumination, clean highlights on the product",
            },
            "sonic_landscape": "Trending Audio Bed: high-energy, familiar beats",
        },
    },
    {
        "name": "Kitchen Culinary Native",
        "tier": "ugc",
        "tones": ["cozy", "tasty", "warm", "homemade", "satisfying"],
        "keywords": [
            "food",
            "cooking",
            "recipe",
            "kitchen",
            "snacks",
            "culinary",
            "home",
            "baking",
        ],
        "description": (
            "Kitchen culinary native — warm domestic kitchen, overhead handheld, "
            "crunchy macro. Cozy and tasty."
        ),
        "recipe": {
            "style_mode": "SOCIAL_NATIVE",
            "brand_archetype": "Close-up food prep, overhead tripod shots, messy-but-tasty application, ASMR sounds.",
            "character": {
                "actor_vibe": "The 'DIY Creator': messy hands, focused gaze on the task",
                "attire": "Professional Uniform: apron, relatable home-cook style",
                "grooming": "Groomed Casual: neat, simple styling",
                "motion": "Focused hands, natural handheld",
            },
            "environment": {
                "spatial_context": "Domestic Kitchen: relatable clutter, warm wood, homely detail",
                "temporal": "Overhead Warm Domestic: warm inviting room light",
            },
            "cinematography": {
                "optics": "Handheld Main Sensor: sharp detail, wide-angle POV",
                "movement": "Circular Hand-Pan: rotation to reveal the dish",
                "motion_texture": "Crunch/Snap Macro: internal food texture in close-up",
            },
            "illumination": {
                "vibe": "Overhead Warm Domestic: warm inviting room light",
                "chromatic_scheme": "Warm appetizing golden tones",
                "key_lighting": "Soft window key with warm fill",
                "highlights": "Glossy food sheen catching the light",
            },
            "sonic_landscape": "Soft Acoustic: intimate, warm, guitar-focused",
        },
    },
    {
        "name": "Street Vlog Energy",
        "tier": "ugc",
        "tones": ["raw", "urban", "energetic", "youthful", "bold"],
        "keywords": [
            "streetwear",
            "sneakers",
            "tech",
            "gaming",
            "urban",
            "vlog",
            "youth",
            "music",
        ],
        "description": (
            "Street vlog energy — raw handheld walk-and-talk, dusk city glow, "
            "synth-pop. Urban and high-energy."
        ),
        "recipe": {
            "style_mode": "SOCIAL_NATIVE",
            "brand_archetype": "Raw handheld movement, urban sidewalk sounds, casual direct-to-camera address.",
            "character": {
                "actor_vibe": "The 'Tech-Savvy Youth': fast-paced gestures, high energy",
                "attire": "Streetwear: oversized hoodies, beanies, sneakers",
                "grooming": "Urbane Grooming: sharp haircut, well-maintained look",
                "motion": "Walking, fast, kinetic",
            },
            "environment": {
                "spatial_context": "Urban Street Walk-and-talk: sidewalk, shop-windows, city motion",
                "temporal": "Dusk Street-light: orange sodium glow, moody urban look",
            },
            "cinematography": {
                "optics": "Handheld Main Sensor: wide-angle POV, real detail",
                "movement": "Walking Tracking: authentic bobbing motion of a walking creator",
                "motion_texture": "Over-the-shoulder POV: immersive user perspective",
            },
            "illumination": {
                "vibe": "Dusk Street-light: orange sodium glow, moody urban look",
                "chromatic_scheme": "Neon-lit urban palette with warm sodium glow",
                "key_lighting": "Available city light with neon accents",
                "highlights": "Neon reflections and incidental street shadows",
            },
            "product_mode": {
                "brand_archetype": "Raw handheld movement, urban sidewalk sounds, casual street-level product framing.",
            },
            "sonic_landscape": "Synth-Pop: energetic, colorful, youthful",
        },
    },
]


def get_looks_for_tier(tier: str) -> list[Dict[str, Any]]:
    """Returns the curated Looks for a tier ('commercial' or 'ugc')."""
    looks = [look for look in PRODUCTION_LOOKS if look.get("tier") == tier]
    return looks or PRODUCTION_LOOKS


def get_look_by_name(name: str) -> Dict[str, Any] | None:
    """Case-insensitive lookup of a Look by its name."""
    if not name:
        return None
    target = name.strip().lower()
    for look in PRODUCTION_LOOKS:
        if look.get("name", "").strip().lower() == target:
            return look
    return None
