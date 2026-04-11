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
