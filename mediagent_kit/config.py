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
import json
import os


@dataclasses.dataclass
class MediagentKitConfig:
    """Configuration for MediagentKit services."""

    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    model_target_location: str | None = None
    asset_service_gcs_bucket: str | None = None
    firestore_database_id: str | None = None
    use_creative_studio: bool = False
    cs_backend_url: str | None = None
    cs_frontend_url: str | None = None
    cs_user_auth_token_key: str = "user_auth_token"
    models: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self):

        # Hardcoded defaults as fallback
        self.models = {
            "text": {
                "default": "gemini-3.5-flash",
                "repair": "gemini-3.5-flash",
                "enrichment": "gemini-3.5-flash",
            },
            "image_imagen": {"default": "imagen-4.0-generate-001"},
            "image_gemini": {"default": "gemini-3.1-flash-image"},
            "video": {"default": "veo-3.1-generate-001"},
            "music": {"default": "lyria-002"},
            "tts": {"default": "gemini-2.5-pro-tts"},
        }

        # Resolve mediagent_config.json regardless of the process working
        # directory. The backend server runs from demos/backend, but the file
        # lives at the repo root; a bare relative path silently missed it and
        # fell back to the hardcoded defaults above. Search order:
        #   1. MEDIAGENT_CONFIG_PATH env override (explicit),
        #   2. the current working directory (back-compat),
        #   3. the repo root (the parent of this package directory).
        _package_dir = os.path.dirname(os.path.abspath(__file__))
        _repo_root = os.path.dirname(_package_dir)
        _candidate_paths = [
            os.environ.get("MEDIAGENT_CONFIG_PATH"),
            "mediagent_config.json",
            os.path.join(_repo_root, "mediagent_config.json"),
        ]
        config_path = next(
            (p for p in _candidate_paths if p and os.path.exists(p)), None
        )
        if config_path:
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    file_models = data.get("models", {})
                    # Merge file models into defaults
                    for key, value in file_models.items():
                        if isinstance(value, dict) and key in self.models:
                            self.models[key].update(value)
                        else:
                            self.models[key] = value
                print(f"[MediagentKitConfig] Loaded models from {config_path}")
            except Exception as e:
                print(f"[MediagentKitConfig] Error loading {config_path}: {e}")
