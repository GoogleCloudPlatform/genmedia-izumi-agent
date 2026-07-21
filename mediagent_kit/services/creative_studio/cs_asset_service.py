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

"""Creative Studio implementation of AssetServiceInterface."""

import asyncio
import datetime
import io
import logging
from typing import Any, Optional, Union

import httpx
from google.cloud import storage

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.errors import (
    AuthenticationError,
    AuthorizationError,
    BackendError,
    NotFoundError,
    ValidationError,
)
from mediagent_kit.services.interfaces import AssetServiceInterface
from mediagent_kit.services.types.common import (
    AssetRef,
    AssetType,
    GeneratedAsset,
    GenerationMetadata,
    UploadedAsset,
)
from mediagent_kit.utils.auth import get_google_id_token
from mediagent_kit.utils.context import get_request_context

logger = logging.getLogger(__name__)


class CSAssetService(AssetServiceInterface):
    """Creative Studio implementation of AssetServiceInterface."""

    def __init__(
        self,
        workspace_id: str | None = None,
        user_auth_token: str | None = None,
        config: MediagentKitConfig | None = None,
    ):
        self._workspace_id = workspace_id
        self._user_auth_token = user_auth_token
        self._config = config or MediagentKitConfig()

    def _get_workspace_id(self, override: str | None = None) -> str:
        ctx = get_request_context() or {}
        ws_id = override or ctx.get("workspace_id") or self._workspace_id
        if not ws_id or not str(ws_id).isdigit():
            raise ValidationError(
                f"Invalid workspace_id: '{ws_id}'. Workspace ID must be a non-empty numeric string."
            )
        return str(ws_id)

    def _get_user_auth_token(self) -> str:
        ctx = get_request_context()
        if ctx:
            token_key = self._config.cs_user_auth_token_key or "user_auth_token"
            token = ctx.get(token_key) or ctx.get("user_auth_token")
            if token:
                return str(token)
        if self._user_auth_token:
            return self._user_auth_token
        raise ValueError("user_auth_token is required")

    def _get_headers(
        self,
        token: str,
        url: str,
        content_type: str | None = "application/json",
    ) -> dict[str, str]:
        headers = {
            "X-User-Authorization": f"Bearer {token}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        id_token_str = get_google_id_token(url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"
        return headers

    def _parse_asset_item(
        self, item: dict[str, Any], default_type: str = "uploaded"
    ) -> Union[UploadedAsset, GeneratedAsset]:
        item_id = str(item.get("id", ""))
        ws_id = str(item.get("workspaceId") or self._workspace_id or "")

        created_at_str = item.get("created_at") or item.get("createdAt")
        created_at = datetime.datetime.now(datetime.timezone.utc)
        if created_at_str:
            if created_at_str.endswith("Z"):
                created_at_str = created_at_str[:-1] + "+00:00"
            try:
                created_at = datetime.datetime.fromisoformat(created_at_str)
            except ValueError:
                pass

        gcs_uris = item.get("gcsUris", [])
        gcs_uri = (
            item.get("gcsUri")
            or item.get("gcs_uri")
            or (gcs_uris[0] if gcs_uris else "")
        )
        file_name = item.get("fileName") or item.get("file_name") or f"asset_{item_id}"
        mime_type = (
            item.get("mimeType") or item.get("mime_type") or "application/octet-stream"
        )
        item_type = item.get("itemType") or default_type

        if item_type in ["source_asset", "uploaded"]:
            return UploadedAsset(
                id=item_id,
                workspace_id=ws_id,
                user_id=str(item.get("userId") or item.get("user_id") or ""),
                file_name=file_name,
                gcs_uri=gcs_uri,
                mime_type=mime_type,
                created_at=created_at,
            )

        status = item.get("status", "completed")
        error_msg = item.get("errorMessage") if status == "failed" else None
        duration = item.get("durationSeconds") or item.get("duration_seconds")
        if duration is not None:
            duration = float(duration)

        metadata_obj = GenerationMetadata(
            source="creative_studio",
            model=item.get("generationModel") or item.get("model"),
            prompt=item.get("prompt") or item.get("originalPrompt"),
            raw=item,
        )

        return GeneratedAsset(
            id=item_id,
            workspace_id=ws_id,
            file_name=file_name,
            gcs_uri=gcs_uri,
            mime_type=mime_type,
            created_at=created_at,
            status=status,
            duration_seconds=duration,
            error_message=error_msg,
            generation_metadata=metadata_obj,
        )

    async def upload_asset(
        self,
        workspace_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str,
        scope: str = "private",
        idempotency_key: Optional[str] = None,
    ) -> UploadedAsset:
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/source_assets/upload"
        headers = self._get_headers(token, url, content_type=None)

        data = {
            "workspaceId": int(ws_id),
            "scope": scope,
        }
        files = {"file": (file_name, io.BytesIO(blob), mime_type)}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, data=data, files=files, headers=headers, timeout=60.0
            )
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized uploading source asset")
            if resp.status_code == 403:
                raise AuthorizationError("Forbidden uploading source asset")
            if resp.status_code == 422:
                raise ValidationError(
                    f"CS source asset upload validation error: {resp.text}"
                )
            resp.raise_for_status()

            item = resp.json()
            asset = self._parse_asset_item(item, default_type="source_asset")
            if isinstance(asset, UploadedAsset):
                return asset
            raise BackendError(
                f"Unexpected response type uploading asset: {type(asset)}"
            )

    async def get_asset(
        self, ref: AssetRef
    ) -> Optional[Union[UploadedAsset, GeneratedAsset]]:
        token = self._get_user_auth_token()
        backend_url = self._config.cs_backend_url or "http://backend:8080"

        if ref.asset_type == "uploaded":
            url = f"{backend_url}/api/source_assets/{int(ref.id)}"
            default_type = "source_asset"
        else:
            url = f"{backend_url}/api/gallery/item/{int(ref.id)}"
            default_type = "media_item"

        headers = self._get_headers(token, url)

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            if resp.status_code == 404:
                return None
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized fetching asset")
            if resp.status_code == 403:
                raise AuthorizationError("Forbidden fetching asset")
            resp.raise_for_status()

            item = resp.json()
            asset = self._parse_asset_item(item, default_type=default_type)

            if (
                isinstance(asset, GeneratedAsset)
                and not asset.duration_seconds
                and asset.status == "completed"
                and asset.gcs_uri
                and (
                    asset.mime_type.startswith("audio/")
                    or asset.mime_type.startswith("video/")
                )
            ):
                try:
                    import asyncio
                    import mimetypes
                    from mediagent_kit.utils.media_tools import (
                        get_media_metadata_from_blob,
                    )

                    blob = await asyncio.to_thread(
                        self._download_from_gcs, asset.gcs_uri
                    )
                    ext = mimetypes.guess_extension(asset.mime_type) or ".bin"
                    meta = await asyncio.to_thread(
                        get_media_metadata_from_blob, blob, ext
                    )
                    if meta and meta.duration:
                        asset.duration_seconds = meta.duration
                except Exception as e:
                    logger.warning(
                        f"Failed to probe duration for asset {asset.id}: {e}"
                    )

            return asset

    async def search_assets(
        self,
        workspace_id: str,
        query: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Union[UploadedAsset, GeneratedAsset]]:
        ws_id = self._get_workspace_id(workspace_id)
        token = self._get_user_auth_token()

        backend_url = self._config.cs_backend_url or "http://backend:8080"
        url = f"{backend_url}/api/gallery/search"
        headers = self._get_headers(token, url)

        payload: dict[str, Any] = {
            "workspaceId": int(ws_id),
            "query": query,
            "limit": limit,
            "offset": offset,
        }

        item_type = None
        if asset_type == "uploaded":
            item_type = "source_asset"
        elif asset_type == "generated":
            item_type = "media_item"

        if item_type:
            payload["itemType"] = item_type

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            if resp.status_code == 401:
                raise AuthenticationError("Unauthorized searching assets")
            if resp.status_code == 403:
                raise AuthorizationError("Forbidden searching assets")
            resp.raise_for_status()

            items = resp.json()
            if isinstance(items, dict) and "items" in items:
                items = items["items"]
            if not isinstance(items, list):
                items = []

            results = []
            for item in items:
                results.append(
                    self._parse_asset_item(
                        item, default_type=item_type or "source_asset"
                    )
                )
            return results

    def _download_from_gcs(self, gcs_uri: str) -> bytes:
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        path = gcs_uri.removeprefix("gs://")
        bucket_name, blob_path = path.split("/", 1)

        storage_client = storage.Client(project=self._config.google_cloud_project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        return blob.download_as_bytes()

    async def download_asset_bytes(self, ref: AssetRef) -> bytes:
        asset = await self.get_asset(ref)
        if not asset:
            raise NotFoundError(f"Asset not found for download: {ref}")
        gcs_uri = getattr(asset, "gcs_uri", None)
        if not gcs_uri:
            raise ValidationError(f"Asset {ref} missing gcs_uri for download")
        return await asyncio.to_thread(self._download_from_gcs, gcs_uri)

    async def delete_asset(self, ref: AssetRef) -> None:
        token = self._get_user_auth_token()
        backend_url = self._config.cs_backend_url or "http://backend:8080"

        if ref.asset_type == "uploaded":
            url = f"{backend_url}/api/source_assets/{int(ref.id)}"
            headers = self._get_headers(token, url, content_type=None)
            async with httpx.AsyncClient() as client:
                resp = await client.delete(url, headers=headers, timeout=30.0)
                if resp.status_code == 404:
                    raise NotFoundError(f"Source asset {ref.id} not found")
                if resp.status_code == 401:
                    raise AuthenticationError("Unauthorized deleting source asset")
                if resp.status_code == 403:
                    raise AuthorizationError("Forbidden deleting source asset")
                resp.raise_for_status()
        else:
            url = f"{backend_url}/api/gallery/bulk-delete"
            headers = self._get_headers(token, url, content_type="application/json")
            payload = {"item_ids": [int(ref.id)]}
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, json=payload, headers=headers, timeout=30.0
                )
                if resp.status_code == 404:
                    raise NotFoundError(f"Generated asset {ref.id} not found")
                if resp.status_code == 401:
                    raise AuthenticationError("Unauthorized deleting generated asset")
                if resp.status_code == 403:
                    raise AuthorizationError("Forbidden deleting generated asset")
                resp.raise_for_status()
