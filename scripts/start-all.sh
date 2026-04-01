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

# 1. Start backend process in background.
# Pass along any arguments (like --with-db-emulator)
echo "▶️ Starting Backend..."
./scripts/start-local-server.sh "$@" &
BACKEND_PID=$!

# 2. Start frontend process in background
echo "▶️ Starting Frontend..."
cd demos/frontend
if [ ! -d "node_modules" ]; then
  echo "Node modules not found. Running npm install..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!

# Wait for both background processes (keeps scroll active for logs)
wait
