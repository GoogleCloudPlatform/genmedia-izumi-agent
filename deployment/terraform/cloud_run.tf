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

locals {
  cloud_run_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_cloud_run_v2_service" "default" {
  provider    = google-beta
  name        = var.cloud_run_service_name
  location    = var.google_cloud_location
  ingress     = "INGRESS_TRAFFIC_ALL"
  launch_stage = "BETA"
  iap_enabled = true
  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run_sa.email
    scaling {
      min_instance_count = 1
      max_instance_count = 100
    }
    containers {
      image = local.cloud_run_image
      resources {
        limits = {
          cpu    = "1000m"
          memory = "4Gi"
        }
        cpu_idle = false
      }
    }
  }

  # The initial Cloud Run service will be initialize with the `hello` image.
  # Then subsequent Cloud Build will replace it with the GenMedia Agent image.
  # Therefore, we need to tell Terraform to ignore subsequent changes of the Cloud Run image.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  depends_on = [google_project_service.apis]
}
