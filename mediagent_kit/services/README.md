<div align="center">
  <h1>Mediagent Kit Services ⚙️</h1>
  <p><strong>Cloud Abstractions & Asynchronous Orchestration</strong></p>
</div>

---

## 📖 Overview

The `mediagent_kit/services` directory is the heavy-lifting engine of the backend orchestration framework. It provides the isolated controller classes that connect our conceptual agent frameworks (`creative_toolbox`, `ads_x_template`) to the persistent Google Cloud Platform infrastructure.

Using the Factory Design Pattern (`service_factory.py`), backend tasks request instances of these services to execute long-running asynchronous ML jobs, construct FFmpeg assembly pipelines natively without locking the API threads, and manage Firestore data blobs securely.

## 🗂️ Core Service Abstractions

### 1. The Cloud Data Layer
- **`asset_service.py`**: A unified wrapper around Google Cloud Storage. Agents call this to transparently bounce local files (like generated images or stitched audio) up to GCS, returning a localized `Asset` definition.
- **`canvas_service.py`**: The interface binding the active `Session` state directly back to a Firestore document, allowing live tracking for the frontend React user.

### 2. The Job Orchestrators
Because generating videos across Vertex AI APIs can take minutes, everything must be asynchronous to prevent HTTP connection timeouts. 
- **`job_service.py`**: Handles tracking `JobStatus` state (e.g. `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`) in Firestore so clients can poll.
- **`job_orchestrator_service.py`**: Encapsulates the multi-step execution loop for generation tools.

### 3. The Media Generators
- **`media_generation_service.py`**: The raw translation layer piping prompts to native Google AI models. It natively implements abstractions like **Imagen** (for Text-to-Image / Image-Editing), **Veo** (for Text/Image-to-Video), and Google Cloud Text-to-Speech (for natural voiceovers).
- **`video_stitching_service.py`**: An advanced Python controller bridging the `AssetService` blobs into native local `tempfile` buffers, dynamically generating complex `filter_complex` graphs, and executing optimized `ffmpeg` subprocesses to concatenate multi-clip campaigns with fading audio chains into single unified MP4s. 

> [!IMPORTANT]
> **Developer Note on Security:**
> All services that write back to local disk (like `video_stitching_service.py` buffering ffmpeg imports) MUST sanitize input data pulled from the database via `os.path.basename()` to protect against path traversal (LFI) server-side exploits.
