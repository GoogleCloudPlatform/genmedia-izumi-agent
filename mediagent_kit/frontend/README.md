<div align="center">
  <h1>Mediagent Kit Static UI 🔧</h1>
  <p><strong>Lightweight Base Diagnostics</strong></p>
</div>

---

## 📖 Overview

The `mediagent_kit/frontend` directory contains the ultra-lightweight, zero-dependency static HTML/JS files that allow foundational debugging of the Agent Engine REST routes without needing to spin up the monolithic React application.

**⚠️ Do not confuse this directory with the production `demos/frontend` React codebase!**

This folder houses simple HTML skeletons that interact directly with the `mediagent_kit/api` controllers using vanilla `fetch()` scripts, designed exclusively for isolated orchestration testing.

## 🗂️ Core Components

### `spa_static_files.py`
This Python script provides the `mount_static_ui(app)` FastAPI helper function. When injected into a centralized API loader (like `main.py`), it automatically mounts the `/public` directory to the root domain.

### `/public/debug-ui`
A barebones browser interface containing:
- **`debug.html`**: A skeletal inspector that allows a developer to manually paste JSON payloads against the Vertex AI endpoints to verify generation jobs are queueing and tracking properly inside Firestore.
- **`app.js`**: Vanilla javascript fetch wrappers abstracting away boilerplate CORS and network handling when calling the `mediagent_kit/api` bindings.

## 🚀 Purpose

When building new features for an autonomous agent, developers often don't want to boot the entire Vite React framework or deal with state management complexity just to see if a prompt generated an MP4 correctly.

By hitting `localhost:8000/debug-ui/debug.html` directly, you can bypass the front-end lifecycle and stress-test the back-end orchestration layer in complete isolation.
