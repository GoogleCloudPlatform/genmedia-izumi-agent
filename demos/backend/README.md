<div align="center">
  <h1>Izumi Backend Engine ⚙️</h1>
  <p><strong>The Intelligence Layer of the Izumi Automated Ad Generation Platform</strong></p>
</div>

---

## 📖 Overview

The `backend` directory houses the core intelligence and orchestration pipelines for the Izumi open-source ecosystem. Built on **FastAPI** and the **Google Vertex AI Agent Development Kit (ADK)**, this environment translates natural language goals into fully orchestrated, multi-modal video advertisements.

It acts as a headless REST API that effortlessly interfaces with the standalone Vite React frontend or executes natively inside Google Cloud's Agent Engines.

## 🧩 The Agency

Izumi isn't a single monolithic script—it's a distributed suite of specialized AI Agents. This repository contains four discrete AI workspaces, each tuned for a specific creative workflow:

### 1. 🎬 [Ads-X Template](./ads_x_template) *(Flagship)*
Our most powerful enterprise orchestrator. `Ads-X Template` gives brands granular control over the timing, pacing, and visual progression of an ad. It operates in two modes:
- **Template Mode:** Adheres strictly to a pre-defined JSON skeleton (dictating exact clip lengths and transitions).
- **AI Director Mode:** Autonomously devises narrative pacing while enforcing brand guidelines.

### 2. 🚀 [Ads-X (Autonomous)](./ads_x)
The original fully-autonomous agent. Provide it a brand brief and a target demographic, and `Ads-X` handles the ideation, scriptwriting, storyboarding, and final rendering entirely on its own.

### 3. 🧬 [Elements to Video](./elements_to_video)
A specialized narrative chain workflow built explicitly to solve the "character consistency" problem in AI video. It anchors generation around persistent subjects (like a mascot or hero product) and drags them seamlessly through multiple generated clips and actions.

### 4. 🎨 [Creative Toolbox](./creative_toolbox)
An unstructured, conversational sandbox. When you don't need a full campaign, deploy the Creative Toolbox to chat naturally with the suite of Vertex AI models to generate one-off concept art, temporary voiceovers, or standalone Veo animations.

## ⚙️ Core Architecture

The backend leverages a standardized toolchain provided by the `mediagent_kit` wrapper, providing uniform access to:
- **Gemini Pro:** Copywriting, reasoning, and orchestration.
- **Imagen 3:** First-frame generation and storyboard composition.
- **Veo:** Cinematic video generation.
- **Lyria:** Dynamic background music composition.
- **Google Cloud TTS:** Studio-grade voiceovers.

### System Entry points
- **`main.py`**: The FastAPI root. Exposes all the autonomous agent endpoints.
- **`config.py`**: Mounts all Google Cloud credentials and environment bindings.

## 🚀 Quick Start (Local Development)

1. Ensure your `.env.dev` is configured with your Google Cloud credentials.
2. From the monorepo root, execute the backend startup script:
```bash
./scripts/start-local-server.sh
```
3. The API will spin up on `http://localhost:8000`. You can test endpoints natively using the FastAPI Swagger UI at `http://localhost:8000/docs`.
