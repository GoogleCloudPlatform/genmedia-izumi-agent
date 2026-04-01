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

data "google_project" "project" {}

# Grant the IAP service account permission to invoke the Cloud Run service.
resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  provider = google
  project  = google_cloud_run_v2_service.default.project
  location = google_cloud_run_v2_service.default.location
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# Grant a specific user or group access to the IAP-secured Cloud Run service
resource "google_iap_web_cloud_run_service_iam_member" "member" {
  provider               = google-beta
  project                = google_cloud_run_v2_service.default.project
  location               = google_cloud_run_v2_service.default.location
  cloud_run_service_name = google_cloud_run_v2_service.default.name
  role                   = "roles/iap.httpsResourceAccessor"
  member = "${var.iap_allowed_user_email}"
}