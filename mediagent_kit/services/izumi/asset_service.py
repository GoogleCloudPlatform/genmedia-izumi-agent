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

"""Native (Izumi) implementation of AssetServiceInterface.

Adapts the legacy, synchronous ``AssetService`` (keyed by
``(user_id, file_name)``, returning ``Asset``) to the unified async
interface (keyed by ``AssetRef``, returning ``UploadedAsset`` /
``GeneratedAsset``).

Native Izumi is single-tenant, so the unified ``workspace_id`` maps onto the
legacy ``user_id``.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Union

from mediagent_kit.services.errors import NotFoundError
from mediagent_kit.services.interfaces import AssetServiceInterface
from mediagent_kit.services.types.common import (
    AssetRef,
    AssetType,
    GeneratedAsset,
    GenerationMetadata,
    UploadedAsset,
)

logger = logging.getLogger(__name__)


class IzumiAssetService(AssetServiceInterface):
    """Adapts the legacy ``AssetService`` to the unified interface."""

    def __init__(self, sync_asset_service: Any):
        self._assets = sync_asset_service

    # ------------------------------------------------------------------ #
    # Mapping helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _current_fields(asset: Any) -> tuple[str, datetime, Optional[float]]:
        current = getattr(asset, "current", None)
        gcs_uri = getattr(current, "gcs_uri", "") if current else ""
        created_at = getattr(current, "create_time", None) if current else None
        duration = getattr(current, "duration_seconds", None) if current else None
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        return gcs_uri, created_at, duration

    def _to_generated_asset(self, asset: Any, workspace_id: str) -> GeneratedAsset:
        gcs_uri, created_at, duration = self._current_fields(asset)
        return GeneratedAsset(
            id=str(asset.id),
            workspace_id=workspace_id,
            file_name=asset.file_name,
            gcs_uri=gcs_uri,
            mime_type=getattr(asset, "mime_type", None) or "application/octet-stream",
            created_at=created_at,
            status="completed",
            duration_seconds=float(duration) if duration is not None else None,
            generation_metadata=GenerationMetadata(source="izumi"),
        )

    def _to_uploaded_asset(self, asset: Any, workspace_id: str) -> UploadedAsset:
        gcs_uri, created_at, _ = self._current_fields(asset)
        return UploadedAsset(
            id=str(asset.id),
            workspace_id=workspace_id,
            user_id=getattr(asset, "user_id", workspace_id),
            scope="private",
            file_name=asset.file_name,
            gcs_uri=gcs_uri,
            mime_type=getattr(asset, "mime_type", None) or "application/octet-stream",
            created_at=created_at,
        )

    def _map_asset(
        self, asset: Any, workspace_id: str, asset_type: Optional[AssetType]
    ) -> Union[UploadedAsset, GeneratedAsset]:
        """Maps a legacy Asset to the unified type indicated by asset_type.

        Defaults to ``GeneratedAsset`` when the type is unknown, because the
        richer shape (status/duration) is what ads_x reads on generated
        media; an uploaded asset simply won't populate those.
        """
        if asset_type == "uploaded":
            return self._to_uploaded_asset(asset, workspace_id)
        return self._to_generated_asset(asset, workspace_id)

    # ------------------------------------------------------------------ #
    # Interface methods
    # ------------------------------------------------------------------ #

    async def upload_asset(
        self,
        workspace_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str,
        scope: str = "private",
        idempotency_key: Optional[str] = None,
    ) -> UploadedAsset:
        asset = await asyncio.to_thread(
            self._assets.save_asset,
            user_id=workspace_id,
            file_name=file_name,
            blob=blob,
            mime_type=mime_type,
        )
        return self._to_uploaded_asset(asset, workspace_id)

    async def get_asset(
        self, ref: AssetRef
    ) -> Optional[Union[UploadedAsset, GeneratedAsset]]:
        asset = await asyncio.to_thread(self._assets.get_asset_by_id, ref.id)
        if asset is None:
            return None
        return self._map_asset(asset, ref.workspace_id, ref.asset_type)

    async def search_assets(
        self,
        workspace_id: str,
        query: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Union[UploadedAsset, GeneratedAsset]]:
        assets = await asyncio.to_thread(self._assets.list_assets, workspace_id)
        if query:
            q = query.lower()
            assets = [a for a in assets if q in (a.file_name or "").lower()]
        window = assets[offset : offset + limit]
        return [self._map_asset(a, workspace_id, asset_type) for a in window]

    async def download_asset_bytes(self, ref: AssetRef) -> bytes:
        blob = await asyncio.to_thread(self._assets.get_asset_blob, ref.id)
        if blob is None or blob.content is None:
            raise NotFoundError(f"No blob content for asset id={ref.id}")
        return blob.content

    async def delete_asset(self, ref: AssetRef) -> None:
        await asyncio.to_thread(self._assets.delete_asset, ref.id)
