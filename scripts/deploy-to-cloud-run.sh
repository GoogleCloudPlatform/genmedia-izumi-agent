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


set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error when substituting.
set -o pipefail # Return the exit status of the last command in the pipe that failed.

# --- Script Functions ---

# Function to print usage information
usage() {
  echo "Usage: $0 --app_env <ENVIRONMENT>"
  echo "  --app_env: The application environment (e.g., dev, staging, prod)."
  echo "             This will be used to find the corresponding .env.{app_env} file."
  exit 1
}

# Function to run a command and log it
run_command() {
  echo "▶️ Running: $*"
  "$@"
}

# --- Main Script ---

# 1. Parse Command-Line Arguments
APP_ENV=""

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --app_env) APP_ENV="$2"; shift ;;
    *) echo "Unknown parameter passed: $1"; usage ;;
  esac
  shift
done

# 2. Validate Arguments
if [ -z "$APP_ENV" ]; then
  echo "❌ Missing required --app_env argument."
  usage
fi

# 3. Load Environment Variables from .env file
ENV_FILE="demos/backend/.env.${APP_ENV}"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: ${ENV_FILE}"
    echo "Please run the setup script first to generate it."
    echo " > python scripts/setup_gcp_project.py --app_env ${APP_ENV}"
    exit 1
fi

# Export the variables to be available for the script
set -a
source "$ENV_FILE"
set +a

# 4. Validate required variables are set
: ${GOOGLE_CLOUD_PROJECT?"GOOGLE_CLOUD_PROJECT not set in $ENV_FILE"}
: ${GOOGLE_CLOUD_LOCATION?"GOOGLE_CLOUD_LOCATION not set in $ENV_FILE"}
: ${CLOUD_RUN_SERVICE_NAME?"CLOUD_RUN_SERVICE_NAME not set in $ENV_FILE"}
: ${CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL?"CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL not set in $ENV_FILE"}

# 5. Submit the build to Google Cloud Build
echo "--- Submitting build to Google Cloud Build for environment: ${APP_ENV} ---"

CLOUD_BUILD_SA_RESOURCE_NAME="projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/${CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL}"
echo "Using Cloud Build service account: ${CLOUD_BUILD_SA_RESOURCE_NAME}"

SUBSTITUTIONS="_APP_ENV=${APP_ENV},_PROJECT_ID=${GOOGLE_CLOUD_PROJECT},_LOCATION=us-central1,_SERVICE_NAME=${CLOUD_RUN_SERVICE_NAME},_CLOUD_BUILD_SA_RESOURCE_NAME=${CLOUD_BUILD_SA_RESOURCE_NAME}"

run_command gcloud builds submit --project="${GOOGLE_CLOUD_PROJECT}" --config deployment/cloudbuild.yaml --substitutions="${SUBSTITUTIONS}" "."

echo "✅ Build submitted successfully. Check the Google Cloud Console for progress."

echo "--- Fetching Cloud Run service URL ---"
echo "▶️ Running: gcloud run services describe ${CLOUD_RUN_SERVICE_NAME} --project=${GOOGLE_CLOUD_PROJECT} --region=us-central1 --format='value(status.url)'"
SERVICE_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE_NAME}" \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --region="us-central1" \
  --format="value(status.url)")

echo "✅ Cloud Run service deployed at: ${SERVICE_URL}"
