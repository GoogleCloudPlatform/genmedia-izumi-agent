<div align="center">
  <h1>🎬 Ads-X</h1>
  <p><strong>The Flagship Campaign Orchestrator</strong></p>
</div>

---

## 📖 What is Ads-X Agent?

The `ads_x` is Izumi's flagship, production-grade video orchestrator providing granular, enterprise-level pacing and structural constraints.

## 🎬 AI Director Mode

The agent architects the campaign itself. From a brief it decides what story the
product needs, how many scenes it takes and what each one has to accomplish,
then anchors every shot to a single coherent visual identity.

Two mechanisms keep that freedom from becoming inconsistency:

- **Pacing blueprints** resolve the requested duration to an exact scene count
  and an exact length per scene, computed before the model writes anything. Each
  scene runs a whole number of seconds between three and six, which is what the
  video model renders natively, so a scene reaches the final cut at exactly the
  length it was planned at.
- **Looks** supply the art direction. One Look is chosen per campaign and bound
  to every scene, so lens, lighting, colour, wardrobe and music come from the
  same coherent recipe rather than being sampled independently per shot.

The two are orthogonal: a blueprint governs structure and timing, a Look governs
how the result looks and sounds.
- Gemini operates purely as an art director, fleshing out visuals and copy to fit the predetermined time boxes.

## 🛠️ The Orchestration Workflow

1. **Parameters Initialization**: Captures user configurations, dimensions (e.g., Vertical 9:16), target demographic, and brand voice.
2. **Product Binding**: Extracts and secures any `asset_id` user-uploaded references (e.g., specific brand logos, actual product shots) using sanitized parsing.
3. **Template Fetching**: Pulls down the structural JSON scaffolding.
4. **Summary / Generation Canvas**: 
   - Uses `summary_canvas_tool.py` to draft the script and frame-by-frame intent.
   - Enriches the prompt using the `enrichment_utils.py` to guarantee "Invisible Camera" semantics and high-fidelity physics descriptions for Vertex AI targets.
5. **Generative Processing**: Kicks off asynchronous calls to:
   - **Gemini** (`gemini-3.1-flash-image`) for scene-setting first frames.
   - **Gemini Omni** for fluid, prompt-aligned action derived from those frames.
   - **Gemini TTS** and **Lyria** for auditory assembly.
6. **Timeline Stitching**: Renders the complete, composite MP4 payload to the user dashboard.

## 🚀 Purpose
The architecture is designed to yield consistently polished, broadcast-ready creative: the blueprint prevents structural meandering, and the Look holds every scene to one established cinematic paradigm.

---

## 🌟 Join the Open-Source Creative Community!

We believe the future of programmatic video advertising is **open and collaborative**. The Look library is the most approachable place to contribute: each Look is a single declarative recipe, and a new one extends the agent's reach to a vertical it does not yet serve well.

The library ships eleven Looks for produced commercial work and four for social-native creator content:

### 🎬 Commercial
*Produced, broadcast-oriented treatments.*

*   **Luxury Heritage** – Deep mahogany and brushed gold, moody chiaroscuro, portrait optics.
*   **Clean Tech Minimalism** – Monochromatic whites and greys, frosted glass, 70mm clarity.
*   **Nostalgic Warm Film** – Amber tones, film grain, golden-hour flares.
*   **Vibrant CPG Pop** – Saturated colour, punchy motion, playful energy.
*   **High-Octane Sports** – Hard light, aggressive movement, kinetic texture.
*   **Organic Wellness** – Earthy linens, diffused daylight, botanical macro.
*   **Home & Interior** – Oak, linen and wool under soft window light, unhurried dolly moves.
*   **Culinary Appetite** – Steam, gloss and sizzle under hard raking light, macro cross-sections.
*   **Pet Companion** – Golden domestic light, camera at paw height, unposed motion.
*   **Fashion Editorial** – Seamless backdrops, hard sculpted light, garment drape in motion.
*   **Outdoor Adventure** – Wide vistas, hard sun, dust and flare, gear in real use.

### 📱 Social Native
*Handheld, creator-style treatments.*

*   **Authentic Creator** – Unpolished, relatable, shot as if by the reviewer.
*   **Polished Creator** – Trendy and aspirational, but still handheld.
*   **Kitchen Culinary Native** – Homemade cooking shot over the shoulder.
*   **Street Vlog Energy** – Raw urban movement, run-and-gun framing.

### 🤝 How to Contribute Your Own:
A Look is one entry in `production_presets.py` carrying a recipe across eight axes — brand archetype, character, environment, cinematography, illumination, product mode and sonic landscape. Pick a vertical the library serves poorly, keep the tones distinct from the Looks already there, and open a Pull Request.

---

## 💡 Understanding the Izumi Studio Canvas

When the agent completes a creative run, it publishes its results to two distinct, read-only canvases in the Izumi Studio:

1.  **Campaign Summary Canvas** (Generated by `summary_canvas_tool.py`):
    *   **Master Production Directive**: Displays the core technical foundations (Style Mode, Archetype, Cast, Wardrobe, Lighting, Optics, Audio) that anchor the campaign.
    *   **Global Strategy & Brief**: Captures the original user brief, strategic context (theme, tone), and background music prompt.
    *   **Storyboard Breakdown**: A scene-by-scene card view showing strategy mapping, cinematography plans, final generation prompts (both base and enriched), and links to generated video/first-frame assets.

2.  **Video Timeline Canvas** (Generated by `stitching_tools.py`):
    *   **Multi-Track Timeline**: Visualizes the precise arrangement of video clips, audio tracks (voiceover and background music), and transitions.
    *   **Stitching Blueprint**: Serves as the input `VideoTimeline` object for the `VideoStitchingService` to produce the final rendered MP4.

These canvases serve as a transparent visual dashboard for reviewing both the strategy and the final cinematic assembly.

![Izumi Studio Canvas Placeholder]([Placeholder: Upload your screenshot and put path here])
