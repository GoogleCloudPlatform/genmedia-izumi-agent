<div align="center">
  <h1>🧬 Elements-to-Video Agent</h1>
  <p><strong>The Character Consistency Orchestrator</strong></p>
</div>

---

## 📖 Overview

The **Elements to Video** agent is a highly specialized narrative orchestrator designed to solve one of the most difficult challenges in generative AI video: **visual consistency**.

It is constructed to perfectly maintain the identity of a specific character, mascot, or object ("The Element") across multiple generated video clips, regardless of the prompt variations or background shifts.

## 🚀 The Pipeline Flow

Unlike the traditional `ads_x` pipeline which generates independent scenes based off a conceptual brief, this module uses a heavy "Reference-to-Video" pipeline locked to a user's defined subject.

### 1. Consistent Elements Definition
The user explicitly defines or uploads a set of core assets dictating the anchor (e.g., an uploaded headshot, a 3D model, or a descriptive prompt like "A 3D stylized golden retriever with a red collar").

### 2. Target Storyboarding
The agent breaks the overarching narrative into discrete, continuous clips. However, instead of prompting those scenes holistically, the agent strictly references the designated Consistent Elements via local IDs for every shot in the `clip_plan`.

### 3. Progressive Media Generation 
   - **The Anchor Image**: First, the agent employs **Imagen 3** to generate pristine, static images (`image_file_name`) isolating the element in the exact starting state required for the specific clip.
   - **The Motion Execution**: Next, it feeds that high-fidelity anchor frame directly into **Veo** (`video_file_name`) using the Image-to-Video modality, animating the scene while definitively dragging the character's geometry and texturing intact through time.

### 4. Continuous Stitching
Finally, the disparate, identity-consistent clips are automatically concatenated (`stitching_tool.py`) alongside synthesized audio tracks into a single unified video file.

## 🛠️ Modularity

- `tools/generation_tools.py`: Orchestrates the complex hand-off logic between the starting anchors, the Imagen validation steps, and the final Veo renders.
- `tools/storyboard_tool.py`: Enforces the stateful constraints defining exactly which elements persist in which shots across the timeline matrix.

By shifting the generation burden towards stateful image referencing rather than relying entirely on text prompts, the Elements-to-Video module yields robust, cinematic consistency for character-driven campaigns.
