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

"""Creative Studio implementation of HtmlCanvasServiceInterface."""

import logging
from typing import Optional

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.errors import UnsupportedFeatureError
from mediagent_kit.services.interfaces import HtmlCanvasServiceInterface
from mediagent_kit.services.types.common import AssetRef, ScopedHtmlCanvas

logger = logging.getLogger(__name__)


class CSCanvasService(HtmlCanvasServiceInterface):
    """Creative Studio implementation of HtmlCanvasServiceInterface (Unsupported feature)."""

    def __init__(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
        config: MediagentKitConfig | None = None,
    ):
        self._workspace_id = workspace_id
        self._user_auth_token = user_auth_token
        self._config = config

    async def create_canvas(
        self,
        workspace_id: str,
        html_content: str,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        asset_references: Optional[list[AssetRef]] = None,
    ) -> ScopedHtmlCanvas:
        logger.error("HTML Canvas is not supported in Creative Studio")
        raise UnsupportedFeatureError("HTML Canvas is not supported by Creative Studio")

    async def get_canvas(self, canvas_id: str) -> Optional[ScopedHtmlCanvas]:
        raise UnsupportedFeatureError("HTML Canvas is not supported by Creative Studio")

    async def update_canvas(
        self,
        canvas_id: str,
        canvas_data: ScopedHtmlCanvas,
    ) -> None:
        raise UnsupportedFeatureError("HTML Canvas is not supported by Creative Studio")

    async def delete_canvas(self, canvas_id: str) -> None:
        raise UnsupportedFeatureError("HTML Canvas is not supported by Creative Studio")
