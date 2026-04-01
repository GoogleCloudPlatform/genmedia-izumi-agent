<div align="center">
  <h1>🚀 Ads-X Autonomous Orchestrator</h1>
  <p><strong>End-to-End AI Campaign Generation</strong></p>
</div>

---

## 📖 What is Ads-X?

The **Ads-X Orchestrator** is an autonomous, multi-agent pipeline designed to ingest a simple brand brief and output a fully assembled, broadcast-ready digital advertisement.

It requires minimal human intervention, relying on heavily engineered prompting architectures to construct logical storyboards before spinning up worker threads to generate the required media.

## 🔄 The Pipeline Architecture

When triggered, the Ads-X agent executes a rigorous, multi-stage generation sequence:

1. **Brief Ingestion & Strategy**: Analyzes the raw prompt, identifying the product, target audience, and ideal emotional tone.
2. **Storyboard Generation (Gemini)**: Deconstructs the strategy into a JSON-enforced storyboard. It plans camera angles, lighting, on-screen text, and voiceover scripts for every discrete scene.
3. **Audio Mapping (Lyria & TTS)**: Generates a pacing track. Uses Lyria to compose thematic background music and Google Cloud TTS to synthesize the voiceover dialogue matching the sentiment.
4. **Visual Generation (Imagen & Veo)**: 
   - Uses **Imagen 3** to construct pixel-perfect "first frames" matching the storyboard.
   - Hands those pristine frames off to **Veo**, dictating the physical physics and kinetic motion required to bring the frame to life.
5. **Final Stitching**: Merges the generated video clips, syncs the voiceover tracks to specific scenes, layers the Lyria music track underneath, and burns in the requested on-screen text.

## 🛠️ Modularity & Tools

The `tools/` directory contains all the specialized modules that the central `agent.py` brain invokes during its lifecycle.
- `generation_tools.py`: Wraps the parallel asynchronous calls to the media generation endpoints.
- `stitching_tools.py`: Handles the final FFmpeg-style compilation array.
- `user_assets_tools.py`: Safely extracts and mounts user-uploaded product descriptions into the generation sequence.

## 🎯 Best Use Case
Ads-X is best utilized for rapid A/B testing, bulk content creation, and entirely autonomous ideation where the specific frame-by-frame pacing is less critical than the overall thematic execution. For rigid, time-constrained outputs, refer to the **Ads-X Template** agent.
