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

variable "google_cloud_project" {
  type        = string
  description = "Your GCP Project ID."
}

variable "google_cloud_location" {
  type        = string
  description = "The region for deployment (e.g., `us-central1`)"
  default     = "us-central1"
}

variable "cloud_run_service_name" {
  type        = string
  description = "The name for the Cloud Run service (e.g., `izumi-demos`)"
  default     = "izumi-demos"
}

variable "artifact_service_gcs_bucket" {
  type        = string
  description = "Bucket name for Google ADK artifacts."
}

variable "asset_service_gcs_bucket" {
  type        = string
  description = "Bucket name for assets."
}

variable "firestore_database_id" {
  type        = string
  description = "The ID of the Firestore database."
  default = "(default)"
}

variable "app_env" {
  type        = string
  description = "The application environment (e.g., dev, staging, prod)."
}

variable "cloud_run_image" {
  type        = string
  description = "The Docker image for the Cloud Run service."
  default     = ""
}

variable "artifact_registry_repository_name" {
  type        = string
  description = "The name of the Artifact Registry repository."
  default     = "genmedia-images"
}

variable "iap_allowed_user_email" {
  type        = string
  description = "The user to grant IAP access, in the format user:email@example.com."
}


