<div align="center">
  <h1>Izumi Backend Engine ⚙️</h1>
  <p><strong>The Intelligence Layer of the Izumi Automated Ad Generation Platform</strong></p>
  <p align="center">
    <img src="https://img.shields.io/badge/🐍Python-3.12-00d9ff?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e">
    <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white">
    <img src="https://img.shields.io/badge/Vertex AI-ADK-blue?style=for-the-badge">
  </p>
</div>

---

## 📖 Overview

The `backend` directory houses the core intelligence and orchestration pipelines for the Izumi open-source ecosystem. Built on **FastAPI** and the **Google Vertex AI Agent Development Kit (ADK)**, this environment translates natural language goals into fully orchestrated, multi-modal video advertisements.

It acts as a headless REST API that effortlessly interfaces with the standalone Vite React frontend or executes natively inside Google Cloud's Agent Engines.

## 🧩 The Specialized Agents

Izumi isn't a single monolithic script—it's a distributed suite of specialized AI Agents. Here is a quick comparison to help you choose the right agent for your workflow:

| Agent | Best For | Control Level | Key Tech |
| :--- | :--- | :--- | :--- |
| **🎬 [Ads-X Template](./ads_x_template)** | Enterprise ads with strict timing and brand guidelines. | High (Template-driven) | Gemini, Imagen, Veo |
| **🚀 [Ads-X (Autonomous)](./ads_x)** | Quick ideation and full automation from a brief. | Low (Fully Autonomous) | Gemini, Imagen, Veo |
| **🧬 [Elements to Video](./elements_to_video)** | Maintaining character or product consistency across shots. | Medium | Gemini, Imagen, Veo |
| **🎨 [Creative Toolbox](./creative_toolbox)** | One-off asset generation and experimentation. | Manual/Chat | Gemini, Imagen, Veo |

For more details on each agent, click on their links above to visit their specific directories.

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

1. **Prerequisites**: Ensure you have configured your `.env.dev` or `.env.local` file with your Google Cloud credentials and project details.
2. **Launch Server**: From the monorepo root, execute the backend startup script:
   ```bash
   ./scripts/start-local-server.sh
   ```
3. **Explore APIs**: The API will spin up on `http://localhost:8000`. You can test endpoints interactively using the FastAPI Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs).

## ➕ Adding a New Agent

To add a new specialized agent to the ecosystem, follow these detailed steps:

1. **Create the Agent Directory**: 
   Create a new directory under `demos/backend/` (e.g., `demos/backend/my_new_agent`). We recommend following the pattern established by `ads_x_template`:
   ```text
   my_new_agent/
   ├── __init__.py
   ├── agent.py          # Main agent logic and orchestration
   ├── tools/             # Custom tools specific to this agent
   └── instructions/      # Prompts and instructions for the agent
   ```

2. **Implement Agent Logic**:
   - Leverage `mediagent_kit` services (via `ServiceFactory`) for tasks like media generation, asset management, and job orchestration.
   - Utilize the centralized model configuration by passing a `purpose` parameter to media generation methods to fetch the appropriate model from `mediagent_config.json`.

3. **Expose REST Endpoints**:
   - Define a FastAPI `APIRouter` in your agent directory to expose its capabilities (e.g., triggering a run).
   - Mount your router in `demos/backend/main.py`.

4. **Add Tests**:
   - Add corresponding unit and integration tests in a new directory under `tests/` (e.g., `tests/demos/my_new_agent/`).
