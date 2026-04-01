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

import dataclasses


@dataclasses.dataclass
class MediagentKitConfig:
    """Configuration for MediagentKit services."""

    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    asset_service_gcs_bucket: str | None = None
    firestore_database_id: str | None = None
