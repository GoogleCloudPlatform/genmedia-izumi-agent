<div align="center">
  <h1>GenMedia Izumi Agent Ecosystem ✨</h1>
  <p><strong>A Unified Monorepo for Building Generative AI Multimedia Agents</strong></p>
</div>

---

## 📖 Overview

This repository contains reference implementations of **GenMedia Agents** built using the `mediagent-kit` framework. It serves as a comprehensive, end-to-end full-stack workbench for building cinematic advertisements, storyline visualizers, and interactive creative sandboxes using Google GenAI / Vertex AI.

The repository provides a complete decoupled workspace:
*   **🔌 Headless Backend Agents** (`demos/backend`): Independent Python FastAPI processes powered by `mediagent-kit` handling reasoning, orchestrations, and `ffmpeg` heavy lifting.
*   **🎨 Frontend Studio UI** (`demos/frontend`): A modern, standalone React + Vite Single Page Application (SPA) providing visual campaign canvas.

---

## 🚀 Getting Started (Local Development)

The repository utilizes **Astra Space's `uv` toolchain** for blazing fast, deterministic python environments.

### 1. Prerequisite Checklist
- Node.js (Version 20+)
- Google Cloud CLI (`gcloud`)
- Astra Space `uv` (Fast python package resolver)
  - *Install via command*: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - *If it's not in your path*: Run `source $HOME/.local/bin/env` or use `$HOME/.local/bin/uv` (MacOS default).

### 2. Authenticate Google Cloud Services
Before spinning up the AI models, configure your local environment with ambient cloud application credentials:
```bash
gcloud auth login
gcloud auth application-default login
```

### 3. Sync Workspace Tree Dependencies
Navigate to the root workspace folder and sync the tree using `uv`. This creates a unified virtual environment holding both library and agent dependencies:
```bash
uv sync
```

### 4. Setup Environment Manifests
Run the declarative Python setup helper to provision standard `.env.local` bindings (written to `demos/backend/.env.local`) pointing to your sandbox GCS buckets and Vertex AI projects:
```bash
uv run scripts/setup_gcp_project.py --app_env local
```

### 5. Start Unified App Workspace
Run the native single-click launcher to boot BOTH the API server and the React UI simultaneously (port multiplexed). By default, it is recommended to run using the **local Firestore Emulator** mock to avoid real cloud database conflicts:
```bash
./scripts/start-all.sh --with-db-emulator
```

---

### 🌐 Alternative: Connecting to Live Google Cloud Firestore
If you prefer testing against your real live **Google Cloud Projects** (no local emulator), follow these steps to bypass 404 connection errors:

1.  **Create the Database** in your Google Cloud Console:
    *   Visit the [Firestore Console](https://console.cloud.google.com/firestore).
    *   Click **Create Database** and select **Native Mode**. Choose a region (e.g., `us-central1`).
2.  **Resolve Default vs Named database**:
    *   If you created the standard `(default)` database in Step 1, leave `FIRESTORE_DATABASE_ID=` blank in your `demos/backend/.env.local` file. The system will resolve it properly as long as it exists in GCP!
    *   If you created a named database (e.g., via Terraform run), enter that name inside `FIRESTORE_DATABASE_ID=my-database-name`.
3.  **Run without the emulator flag**:
    ```bash
    ./scripts/start-all.sh
    ```

---

## 🧪 Testing & Quality Standards

The repository enforces high quality standards through automated testing and pre-commit hooks.

### Running Tests

We utilize `pytest` for unit testing and coverage tracking. To run the full test suite with coverage reporting:

```bash
uv run pytest tests/demos/ --cov=demos/backend --cov-report=term-missing
```

The repository maintains an **80% coverage threshold** for core modules.

### Code Style & Pre-commit

We use `black` for formatting, `pylint` for linting, and automated license header checks. Pre-commit hooks are configured to run these checks before every commit.

To install pre-commit hooks:

```bash
uv run pre-commit install
```

To run checks manually:

```bash
uv run pre-commit run --all-files
```

---

## 🧩 Architectural Topography

| Folder | Description |
| :--- | :--- |
| `mediagent_kit/` | Foundational python library housing Firebase, GenAI connectors, and image manipulation utils. |
| `demos/backend/` | Suite of 4 standard orchestrator agents listening to REST events. |
| `demos/frontend/` | The isolated React SPA client UI. |
| `deployment/` | Multi-architecture Dockerfiles and Terraform IaC suites. |
| `scripts/` | Shell tools orchestration. |

### 🛠 Implemented Agents Suite (`demos/backend/`)
-   **`ads_x`**: Flagship cinematics generator orchestrating multimodals.
-   **`ads_x_template`**: Strict format campaign tracker.
-   **`creative_toolbox`**: Loose scratchpad workbench for free-form text-to-image/audio.
-   **`elements_to_video`**: Veo character consistency storyboarder.

---

## ☁️ Cloud Deployments

To deploy these headless agents up into serverless Google Cloud Run profiles under high compliance environments (IAP protection, Terraform auditing), refer to the [Deployment Guide](deployment/README.md).
