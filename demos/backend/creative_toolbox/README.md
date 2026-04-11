<div align="center">
  <h1>🎨 Creative Toolbox Agent</h1>
  <p><strong>The Freeform Multimodal Utility Workbench</strong></p>
</div>

---

## 📖 The "Unstructured" Agent

The **Creative Toolbox** is an agnostic, sandbox assistant designed for freeform media generation. 

Unlike the highly structured templates which orchestrate rigid, end-to-end commercial campaigns, the Creative Toolbox operates as a flexible utility workbench. It intentionally lacks an overarching storyboard or timeline, allowing developers and creatives to trigger discrete generation events on the fly.

## 🚀 Features

- **Unstructured Generation**: Chat naturally to generate a single image, manipulate a one-off video clip, synthesize audio, or transcribe speech natively.
- **Multimodal Output Capabilities**: Full, unfiltered access to the Vertex AI ecosystem:
  - **Imagen 3** (Image Generation & Iteration)
  - **Veo** (Physics-based Video Generation)
  - **Lyria** (High-fidelity Music Generation)
  - **Google Cloud TTS** (Text-to-Speech)
  - **Gemini** (Creative Copywriting & Multimodal Reasoning)

## 🧩 Architectural Role

- **When to invoke `ads_x_template`**: Use for end-to-end, multi-scene marketing campaign orchestration.
- **When to invoke `creative_toolbox`**: Use for rapid prototyping, generating single creative assets on demand, iterating a flawed concept, or experimenting with prompt engineering semantics before placing assets on a timeline.

## 🛠️ The Tools

The `tools/` directory contains isolated execution wrappers for every modality, securely managing the cloud authentication scopes required to invoke Google Cloud endpoints.
- `canvas_tools.py`: Manages the ephemeral session state, letting users iteratively reference their working "canvas" generation.
- `image_gen_tools.py`: Connects directly to the Imagen foundational models.
- `music_gen_tools.py` & `speech_gen_tools.py`: Connects to Lyria and TTS endpoints.

Because it leverages the exact same underlying `mediagent_kit` wrapper framework as the campaign agents, anything generated inside the Creative Toolbox retains identical production fidelity and seamlessly persists into the shared `asset_service` database for global use later.
