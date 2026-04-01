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


# This script starts the local development server.
#
# There are three ways to handle the Firestore database:
#
# 1. Connect to Real DB (Default):
#    > ./scripts/start-local-server.sh
#    (Uses the project configured in your .env.local files)
#
# 2. Managed Emulator (Script starts and kills it for you):
#    > ./scripts/start-local-server.sh --with-db-emulator
#    (This will KILL any existing process on port 8083 to ensure a clean state)
#
# 3. Manual/External Emulator:
#    Start externally:
#    > gcloud emulators firestore start --host-port=localhost:8083
#    Export var:
#    > export FIRESTORE_EMULATOR_HOST=localhost:8083
#    Run script:
#    > ./scripts/start-local-server.sh
#
# To kill a stale emulator manually which is running on port 8083:
# > lsof -t -i:8083 | xargs kill -9
#
# To start the server with the dev environment config:
# APP_ENV=dev ./scripts/start-local-server.sh

# Fix for gRPC + subprocess forking issues on macOS/Linux
export GRPC_ENABLE_FORK_SUPPORT=0
export GRPC_POLL_STRATEGY=poll

if [ "$1" == "--with-db-emulator" ]; then
  FIRESTORE_PORT=8083
  # Use single quotes for the trap command to prevent immediate expansion
  # and ensure we check if PID exists before killing
  trap 'echo "Stopping Firestore emulator..."; if [ -n "$EMULATOR_PID" ]; then kill "$EMULATOR_PID"; fi' EXIT

  lsof -t -i:$FIRESTORE_PORT | xargs kill -9

  echo "Starting Firestore emulator in background..."
  rm -f firestore-emulator.log
  gcloud emulators firestore start --host-port=localhost:$FIRESTORE_PORT 2>&1 | tee firestore-emulator.log &
  EMULATOR_PID=$!

  echo "Waiting for emulator to be ready..."
  for i in {1..40}; do
      # Use single quotes for grep pattern to avoid shell escaping issues
      if grep -q '\[firestore\] Dev App Server is now running.' firestore-emulator.log; then
          echo "Firestore emulator is ready."
          break
      fi
      sleep 0.5
      if [ $i -eq 40 ]; then
          echo "Firestore emulator failed to start." >&2
          cat firestore-emulator.log
          exit 1
      fi
  done

  export FIRESTORE_EMULATOR_HOST=localhost:$FIRESTORE_PORT
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/app_$TIMESTAMP.log"

echo "Starting application... Logging to $LOG_FILE"
cd demos/backend
uv run uvicorn main:app --reload --use-colors --app-dir . --reload-dir . --reload-dir ../../mediagent_kit 2>&1 | tee "../../$LOG_FILE"