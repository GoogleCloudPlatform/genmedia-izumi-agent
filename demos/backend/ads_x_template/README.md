<div align="center">
  <h1>🎬 Ads-X Template</h1>
  <p><strong>The Flagship Campaign Orchestrator</strong></p>
</div>

---

## 📖 What is the Template Agent?

The `ads_x_template` is Izumi's flagship, production-grade video orchestrator providing granular, enterprise-level pacing and structural constraints.

The defining characteristic of this agent is its capacity to run in two distinct operational profiles tailored for different marketing needs: **Template Mode** and **AI Director Mode**.

## 🔄 Dual Operating Modes

### 1. Template Mode (Rigid Framework)
In Template Mode, the AI must conform to an overarching JSON pacing document. The user supplies the core template (e.g., "The 15s UGC Feature", "The 8s Explainer"), and the AI simply populates that heavily constrained skeleton with generated media.
- Total video duration is strictly enforced.
- Scene cuts, audio transitions, and frame layouts are explicitly blocked out before generation begins.
- Gemini operates purely as an art director, fleshing out visuals and copy to fit the predetermined time boxes.

### 2. AI Director Mode (Bespoke Generation)
In AI Director Mode, the template guardrails are removed. The agent dynamically decides how many scenes the brief requires, how long they should run, and the pacing of the background music. 
- It retains the high-quality orchestration pipelines of the template engine, but operates with the freedom to invent custom structural formats.

## 🛠️ The Orchestration Workflow

1. **Parameters Initialization**: Captures user configurations, dimensions (e.g., Vertical 9:16), target demographic, and brand voice.
2. **Product Binding**: Extracts and secures any `asset_id` user-uploaded references (e.g., specific brand logos, actual product shots) using sanitized parsing.
3. **Template Fetching**: Pulls down the structural JSON scaffolding.
4. **Summary / Generation Canvas**: 
   - Uses `summary_canvas_tool.py` to draft the script and frame-by-frame intent.
   - Enriches the prompt using the `enrichment_utils.py` to guarantee "Invisible Camera" semantics and high-fidelity physics descriptions for Vertex AI targets.
5. **Generative Processing**: Kicks off asynchronous calls to:
   - **Gemini (Imagen 3)** for scene-setting first frames.
   - **Veo** for fluid, prompt-aligned action derived from those frames.
   - **Google Cloud TTS** and **Lyria** for auditory assembly.
6. **Timeline Stitching**: Renders the complete, composite MP4 payload to the user dashboard.

## 🚀 Purpose
The Template architecture is designed to yield consistently polished, broadcast-ready creative by preventing AI hallucinatory meandering, forcing all output to bend to established cinematic paradigms.

---

## 🌟 Join the Open-Source Creative Community!

We believe the future of programmatic video advertising is **open and collaborative**. We strongly encourage marketing developers and cinematic engineers across GitHub to design, test, and submit their own high-converting JSON template architectures to our open-source library!

To help you get started, we are sharing our flagship collection of **broadcast-proven marketing structures** that are already integrated and ready for your immediate production use:

### ⚡ Fast-Paced Frameworks (High Energy, Quick Cuts)
*Perfect for social media feeds, disruptive hooks, and high-velocity engagement.*

*   **Problem/Solution (24s)** – Disrupt a 'Problem' state with a dynamic 'Solution'.
*   **Feature Spotlight (23s)** – Rhythmic tabletop montage: materials, physics, & presence.
*   **Pet Companion (24s)** – Chaotic joy of pets, anchoring energy to the product.
*   **Style Showcase (23s)** – Clean fashion montage focusing on fit, fabric, & movement.
*   **Beauty Routine (25s)** – High-velocity texture & product reveal montage.
*   **Home Comfort (24s)** – Rapid-fire sensory home moments.
*   **Meal Prep Made Easy (20s)** – High-octane cooking sizzle reel.

### 🎬 Standard Pacing (Cinematic, Detailed Narrative)
*Designed for premium storytelling, immersive product demonstrations, and emotional arcs.*

*   **Problem/Solution Highlight (32s)** – Full Arc: Problem → Reveal → Flow → Payoff.
*   **Feature Spotlight (32s)** – High-end 'Tabletop' commercial: materials & physics.
*   **Pet Companion (32s)** – Emotional Arc: Curiosity → Action → Love.
*   **Style Showcase (32s)** – Rhythmic interplay of attitude & fabric details.
*   **Beauty Routine (32s)** – Sensory ritual, texture, and resulting 'Glow'.
*   **Home Comfort (32s)** – Sensory journey: Airy Morning → Cozy Evening.
*   **Meal Prep Made Easy (32s)** – Organized ingredients to restaurant quality.
*   **UGC First Impression (32s)** – Unboxing & genuine discovery (Creator style).
*   **UGC Honest Opinion (32s)** – Trust-focused lifestyle review (Creator style).

### 🤝 How to Contribute Your Own:
Have a brilliant structural idea for a **15-second teaser** or a **6-second unskippable bumper**? Simply format your scene timing in standard JSON, open a Pull Request, and help us expand the world's first open-source generative media orchestrator!

---

## 💡 Understanding the Izumi Studio Canvas

When the agent completes a creative run, it publishes its results to two distinct, read-only canvases in the Izumi Studio:

1.  **Video Timeline Canvas**:
    *   **Media Player**: Preview the stitched video or individual audio tracks.
    *   **Multi-Track Timeline**: Visualize the precise arrangement of video clips, audio tracks, and cinematic transitions.
    *   **Inspection Panel**: View specific clip details (duration, offsets) and the exact AI parameters (Generation Config) used for each asset.

2.  **Campaign Summary Canvas**:
    *   **Strategic Overview**: An interactive HTML report detailing the campaign's target demographics, creative tone, and stylistic alignment.

These canvases serve as a transparent visual dashboard for reviewing both the strategy and the final cinematic assembly.

![Izumi Studio Canvas Placeholder]([Placeholder: Upload your screenshot and put path here])
