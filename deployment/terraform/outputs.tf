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

output "CLOUD_RUN_SERVICE_URL" {
  description = "The URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.default.uri
}

output "ASSET_SERVICE_GCS_BUCKET" {
  description = "The name of the GCS bucket for the asset service."
  value       = data.google_storage_bucket.asset_service_gcs_bucket.name
}

output "ARTIFACT_SERVICE_GCS_BUCKET" {
  description = "The name of the GCS bucket for the artifact service."
  value       = data.google_storage_bucket.artifact_service_gcs_bucket.name
}

output "CLOUD_RUN_SERVICE_ACCOUNT_EMAIL" {
  description = "The email of the dedicated service account for Cloud Run."
  value       = google_service_account.cloud_run_sa.email
}

output "CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL" {
  description = "The email of the dedicated service account for Cloud Build."
  value       = google_service_account.cloud_build_sa.email
}