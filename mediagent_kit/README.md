<div align="center">
  <h1>Mediagent Kit 🧰</h1>
  <p><strong>The Asynchronous Backbone of the GenMedia Agent Ecosystem</strong></p>
</div>

---

## 📖 Overview

The `mediagent_kit` is the core Python Software Development Kit (SDK) that powers the entire GenMedia Izumi architecture. While the orchestrator pipelines (like `ads_x` and `creative_toolbox`) define *what* video an agent should make, the `mediagent_kit` defines exactly *how* to safely and asynchronously communicate with Google Cloud infrastructure to execute it.

By completely decoupling this layer from the specific front-end or back-end implementations, the `mediagent_kit` empowers developers to instantiate secure Vertex AI generation wrappers, ffmpeg handlers, and database listeners natively in their own applications.

## 🧱 Submodule Architecture

This kit guarantees strict separation of concerns across its directories:

- **[`/api`](api/README.md)**: The FastAPI REST controllers. Exposes endpoints for React frontends to manage active `Session` state, fetch Cloud Storage `Assets`, and manually trigger isolated `media_generation` jobs.
- **[`/services`](services/README.md)**: The multi-threaded Controller layer. Contains heavy-lifting Python classes wrapping native GCP calls (like `FirestoreSessionService` and `AssetService`) alongside the `video_stitching_service.py` that dynamically spawns ffmpeg pipelines over downloaded blobs.
- **[`/frontend`](frontend/README.md)**: A lightweight suite of native static vanilla JavaScript debugging HTML pages natively loadable by the `mediagent_kit` server to trace API states without booting up a heavy React workspace.
- **`/utils`**: Base-level execution abstractions. Contains optimized polling wrappers (`retry.py`) and background worker threads (`background_job_runner.py`) which prevent the FastAPI deployment from timing out during multi-minute video rendering events on Vertex AI.

## 🚀 Engine Boot sequence

Because this SDK is completely detached from the `demos/` workflows, booting the native server hooks is a simple process:

```python
from fastapi import FastAPI
from mediagent_kit.server import mount_to_fastapi_app
from mediagent_kit.config import MediagentKitConfig

# 1. Provide routing configs (bucket bindings, GCP project ID)
config = MediagentKitConfig(...) 

# 2. Instantiate your host app
app = FastAPI()

# 3. Mount the Mediagent SDK (Services + REST bindings) directly onto the app
mount_to_fastapi_app(app, config)
```
