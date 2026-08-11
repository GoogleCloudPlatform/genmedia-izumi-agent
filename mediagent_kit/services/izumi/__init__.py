# Copyright 2026 Google LLC
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

"""Native (Izumi) implementations of the unified service interfaces.

These adapt the legacy synchronous services (``MediaGenerationService``,
``AssetService``, ...) to the unified async interfaces in
``mediagent_kit.services.interfaces``, so the open-source non-Creative-Studio
path works through the same interface the agents now call. Creative Studio's
equivalents live in ``mediagent_kit.services.creative_studio``.
"""

from mediagent_kit.services.izumi.asset_service import IzumiAssetService
from mediagent_kit.services.izumi.media_generation_service import (
    IzumiMediaGenerationService,
)

__all__ = [
    "IzumiAssetService",
    "IzumiMediaGenerationService",
]
