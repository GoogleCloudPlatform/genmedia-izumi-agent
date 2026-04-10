#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script boots both the FastAPI backend server and the Vite React frontend
# simultaneously. It allows you to test the full application with a single command.

# Function to kill child processes on termination
cleanup() {
  echo -e "\n🛑 Stopping servers..."
  if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
  exit 0
}

# Trap Ctrl+C (SIGINT) and exit (SIGTERM)
trap cleanup SIGINT SIGTERM EXIT

echo "--- 🚀 Launching Full Stack (Izumi Studio) ---"

# Pre-flight check: Ensure uv is available
if ! command -v uv &> /dev/null; then
  echo -e "\n❌ CRITICAL: 'uv' command not found!"
  echo "The backend requires 'uv' to run."
  echo "If you installed it to ~/.local/bin, run this command first:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  exit 1
fi

# 1. Start backend process in background.
echo "▶️ Starting Backend [IN PROGRESS]..."
./scripts/start-local-server.sh "$@" &
BACKEND_PID=$!

# Wait for Backend port 8000 to open
echo -n "⏳ Waiting for Backend API (port 8000) to respond..."
for i in {1..30}; do
  if nc -z localhost 8000 2>/dev/null; then
    echo -e "\n✅ [DONE] Backend API is fully online!"
    break
  fi
  echo -n "."
  sleep 1
done

# 2. Start frontend process in background
echo -e "\n▶️ Starting Frontend [IN PROGRESS]..."
cd demos/frontend
if [ ! -d "node_modules" ]; then
  echo "Node modules not found. Running npm install..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!

# Wait for Frontend port 5173 to open
echo -n "⏳ Waiting for Frontend UI (port 5173) to respond..."
for i in {1..30}; do
  if nc -z localhost 5173 2>/dev/null; then
    echo -e "\n✅ [DONE] Frontend UI is fully online!"
    break
  fi
  echo -n "."
  sleep 1
done

echo -e "\n=================================================="
echo -e "🚀 Izumi Studio is ready for use!"
echo -e "🖥️  Open in browser: http://localhost:5173"
echo -e "=================================================="

# Wait for both background processes (keeps scroll active for logs)
wait

