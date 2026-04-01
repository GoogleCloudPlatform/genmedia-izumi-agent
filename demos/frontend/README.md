<div align="center">
  <h1>Izumi Studio ✨</h1>
  <p><strong>The React Frontend for the GenMedia Agent Ecosystem</strong></p>
</div>

---

## 📖 Overview

This directory contains the decoupled React Single Page Application (SPA) for **Izumi Studio**. It provides the graphical user interface for interacting with the backend AI agents, managing active storyboards, and visualizing generated media workflows in real-time.

It is designed to be served independently in development and communicates directly with the Python FastAPI backend via REST.

## 🚀 Quick Start (Development)

The Izumi Studio frontend utilizes **Vite** for blazing fast HMR (Hot Module Replacement) and optimized bundling.

### 1. Prerequisites
- Node.js (version 20+ recommended)
- npm

### 2. Install Dependencies
Switch into the `demos/frontend` directory and install the required modules:
```bash
npm install
```

### 3. Server Configuration
The frontend needs to know where the FastAPI backend is located. Update the `.env` file in this directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```


### 5. Building for Production
To compile the React application into optimized static assets for production hosting (e.g., Firebase Hosting, Cloud Run):
```bash
npm run build
```
The production assets will be generated in the `dist/` directory.

## 🧩 Code Structure

The codebase follows a strict feature-based React taxonomy:

- **`src/pages/`**: Top-level route components mapped to specific dashboard views (`ProjectsPage`, `CanvasPage`).
- **`src/components/`**: Modular UI components.
  - **`project-view/`**: The core workspace housing the interactive Timeline, Asset Galleries, and Chat orchestrator.
  - **`shared/`**: Reusable generic blocks (Modals, Uploaders, AppBars).
- **`src/services/`**: The data layer handling all state and fetching.
  - **`api/`**: The raw fetch wrappers querying the `VITE_API_BASE_URL` targets.
  - **`*Service.ts`**: Higher-level caching and state transformation classes (e.g. `mediaService`).
- **`src/data/types/`**: TypeScript interfaces strongly typing the API contracts.

## 📡 API Contract (`/specs`)

To ensure seamless integration between this React app and the Python Agent backend, the communication schema is heavily standardized. A comprehensive breakdown of these API endpoints, request schemas, and expected asset payloads can be found in the `specs/` folder of this directory.

## 🛠️ Tech Stack
-   **Framework**: [React](https://react.dev/) + [Vite](https://vitejs.dev/)
-   **Language**: [TypeScript](https://www.typescriptlang.org/)
-   **UI Library**: [Material UI (MUI)](https://mui.com/)
-   **Test Suite**: [Vitest](https://vitest.dev/)