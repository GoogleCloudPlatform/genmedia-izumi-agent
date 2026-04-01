<div align="center">
  <h1>Mediagent Kit API 📡</h1>
  <p><strong>The Decoupled Routing Layer for Izumi Studio</strong></p>
</div>

---

## 📖 Overview

The `mediagent_kit/api` directory defines the primary REST controller space for the GenMedia Izumi Agent ecosystem. These `APIRouter` submodules act as the protective bridge between the visual React frontend (`demos/frontend`) and the deep, asynchronous Firestore database services. 

They do not contain overarching agent orchestration logic natively; instead, they serve as the HTTP interface that routes incoming JSON payloads to the correct background task runner.

## 🗂️ Core Controller Endpoints

- **`canvases.py`**: Manages the ephemeral session state of the editor. This endpoint persists UI updates recursively so designers can drop off and resume their orchestrator sequences later.
- **`assets.py`**: A secure proxy for uploading and retrieving cloud storage blobs. The frontend uses these routes to hydrate images, upload new source reference variables (`image_file_name`), and pull down final synthesized MP4 streams.
- **`jobs.py`**: Exposes `/status` trackers to visually manage long-running asynchronous worker threads polling Vertex AI models in the background.
- **`media_generation.py`**: Native REST triggers explicitly used by the frontend to fire isolated, one-off generation requests (i.e. clicking "Generate Voiceover") bypassing the unified autonomous orchestrators.

## 🏗️ Architecture Role

By localizing all `fastapi` structural responses, schema translations (casting enums to strings), and Exception handling inside this `/api` module, the core `/services` and `/utils` layers underneath remain purely functionally agnostic.

To mount these endpoints in a consumer script (like what happens in `demos/backend/main.py`), you simply invoke the top-level factory method `mount_to_fastapi_app(app)`.
