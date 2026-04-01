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

# Service account for Cloud Run (runtime)
resource "google_service_account" "cloud_run_sa" {
  account_id   = "genmedia-run-${var.app_env}"
  display_name = "GenMedia Agent Cloud Run Service Account (${var.app_env})"
  project      = var.google_cloud_project
}

# Grant the required permissions to the Cloud Run service account
resource "google_project_iam_member" "cloud_run_sa_roles" {
  for_each = toset([
    "roles/datastore.user",          # Access Firestore
    "roles/storage.objectAdmin",     # Access GCS buckets
    "roles/aiplatform.user",         # Access Vertex AI for generation
    "roles/logging.logWriter",       # Write logs during runtime
  ])

  project = var.google_cloud_project
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Service account for Cloud Build (buildtime)
resource "google_service_account" "cloud_build_sa" {
  account_id   = "genmedia-build-sa-${var.app_env}"
  display_name = "GenMedia Agent Cloud Build Service Account (${var.app_env})"
  project      = var.google_cloud_project
}

# Grant the required permissions to the Cloud Build service account
resource "google_project_iam_member" "cloud_build_sa_roles" {
  for_each = toset([
    "roles/run.admin",               # Deploy and manage Cloud Run services
    "roles/artifactregistry.writer", # Push images to Artifact Registry
    "roles/logging.logWriter",       # Write logs during build
    "roles/iam.serviceAccountUser",  # Allow Cloud Build to act as the Cloud Run SA
    "roles/storage.objectViewer",    # Read source from GCS
    "roles/storage.objectCreator",   # Write logs to GCS
  ])

  project = var.google_cloud_project
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}