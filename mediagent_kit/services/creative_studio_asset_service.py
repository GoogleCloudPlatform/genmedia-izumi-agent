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

"""Custom Asset Service that integrates with the Creative Studio media backend."""

import datetime
import io
import json
import logging
import os
from typing import Any

import httpx
from firebase_admin import firestore
from google.cloud.storage.bucket import Bucket

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.utils.auth import get_google_id_token

logger = logging.getLogger(__name__)


class CreativeStudioAssetService(AssetService):
    """Asset service subclass for integration with a custom Creative Studio media backend."""

    def __init__(
        self,
        db: firestore.Client,
        gcs_bucket: Bucket | None,
        config: MediagentKitConfig,
        workspace_id: str | int | None = None,
        user_auth_token: str | None = None,
        transient_cache: dict[str, Any] | None = None,
    ):
        """Initializes the CreativeStudioAssetService.

        Args:
            db: The Firestore client.
            gcs_bucket: The GCS bucket (optional, Creative Studio handles storage).
            config: The service configuration.
            workspace_id: The workspace ID.
            user_auth_token: The user authentication token.
            transient_cache: Optional cache dictionary for transient assets.
        """
        super().__init__(db, gcs_bucket, config)
        self.__workspace_id = workspace_id
        self.__user_auth_token = user_auth_token
        self.__transient_cache = transient_cache

    @property
    def _workspace_id(self) -> Any:
        if self.__workspace_id is not None:
            return self.__workspace_id
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("workspace_id") if ctx else None

    @property
    def _user_auth_token(self) -> str | None:
        if self.__user_auth_token is not None:
            return self.__user_auth_token
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("user_auth_token") if ctx else None

    @property
    def _transient_cache(self) -> dict[str, Any]:
        if self.__transient_cache is not None:
            return self.__transient_cache
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("transient_cache") if (ctx and ctx.get("transient_cache") is not None) else {}

    def _get_headers(self, user_auth_token: str, url: str, content_type: str | None = "application/json") -> dict:
        headers = {
            "X-User-Authorization": f"Bearer {user_auth_token}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        id_token_str = get_google_id_token(url)
        if id_token_str:
            headers["Authorization"] = f"Bearer {id_token_str}"
        return headers

    def save_asset(
        self,
        user_id: str,
        file_name: str,
        blob: bytes,
        mime_type: str | None = None,
        text_generate_config: types.TextGenerateConfig | None = None,
        image_generate_config: types.ImageGenerateConfig | None = None,
        music_generate_config: types.MusicGenerateConfig | None = None,
        video_generate_config: types.VideoGenerateConfig | None = None,
        speech_generate_config: types.SpeechGenerateConfig | None = None,
        gcs_path_override: str | None = None,
    ) -> types.Asset:
        """Saves a user-provided asset by uploading it to Creative Studio backend if integrated, or locally."""

        if not self._workspace_id or not self._user_auth_token:
            raise ValueError(
                f"CreativeStudioAssetService.save_asset: workspace_id ({self._workspace_id}) "
                f"and user_auth_token must be provided at initialization for Creative Studio integration."
            )

        # Upload to Creative Studio source assets endpoint
        url = f"{self._config.creative_studio_backend_url}/api/source_assets/upload"
        headers = self._get_headers(self._user_auth_token, url, content_type=None)

        # Default asset type
        asset_type = "generic_image"
        if mime_type:
            if mime_type.startswith("video/"):
                asset_type = "generic_video"

        data = {
            "workspaceId": str(self._workspace_id),
            "scope": "private",
            "assetType": asset_type,
        }

        files = {
            "file": (file_name, io.BytesIO(blob), mime_type or "application/octet-stream")
        }

        logger.info(f"Uploading user asset '{file_name}' to Creative Studio backend at {url}...")
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=120.0
                )
                response.raise_for_status()
                latest_item = response.json()
                logger.info(f"Successfully uploaded asset to Creative Studio backend: {latest_item.get('id')}")

                created_at_str = latest_item.get("created_at") or latest_item.get("createdAt")
                created_at = datetime.datetime.now(datetime.UTC)
                if created_at_str:
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    try:
                        created_at = datetime.datetime.fromisoformat(created_at_str)
                    except ValueError:
                        pass

                gcs_uri = latest_item.get("gcs_uri") or latest_item.get("gcsUri") or ""

                asset = self.to_asset(
                    asset_id=str(latest_item["id"]),
                    workspace_id=str(self._workspace_id),
                    file_name=file_name,
                    gcs_uri=gcs_uri,
                    created_at=created_at,
                    mime_type=mime_type,
                    text_generate_config=text_generate_config,
                    image_generate_config=image_generate_config,
                    music_generate_config=music_generate_config,
                    video_generate_config=video_generate_config,
                    speech_generate_config=speech_generate_config,
                    item_type="source_asset",
                )

                # Cache the asset in the transient cache so it is immediately available
                if self._transient_cache is not None:
                    if hasattr(asset, "to_dict"):
                        self._transient_cache[asset.id] = asset.to_dict()
                    else:
                        self._transient_cache[asset.id] = asset

                return asset
        except Exception as e:
            logger.error(f"Failed to upload asset '{file_name}' to Creative Studio backend: {e}")
            raise RuntimeError(f"Failed to upload asset '{file_name}' to Creative Studio backend: {e}") from e

    def to_asset(
        self,
        asset_id: str,
        workspace_id: str,
        file_name: str,
        gcs_uri: str,
        created_at: datetime.datetime,
        mime_type: str | None = None,
        text_generate_config: types.TextGenerateConfig | None = None,
        image_generate_config: types.ImageGenerateConfig | None = None,
        music_generate_config: types.MusicGenerateConfig | None = None,
        video_generate_config: types.VideoGenerateConfig | None = None,
        speech_generate_config: types.SpeechGenerateConfig | None = None,
        item_type: str | None = None,
        duration_seconds: float | None = None,
    ) -> types.Asset:
        """
        """
        versions = [
            types.AssetVersion(
                asset_id=asset_id,
                version_number=1,
                gcs_uri=gcs_uri,
                create_time=created_at,
                duration_seconds=duration_seconds,
                text_generate_config=text_generate_config,
                image_generate_config=image_generate_config,
                music_generate_config=music_generate_config,
                video_generate_config=video_generate_config,
                speech_generate_config=speech_generate_config,
            )
        ]

        asset = types.CreativeStudioAsset(
            id=asset_id,
            user_id=workspace_id,
            mime_type=mime_type,
            file_name=file_name,
            current_version=1,
            versions=versions,
            workspace_id=workspace_id,
            item_type=item_type or "media_item",
        )
        return asset

    def save_asset_from_file(
        self,
        user_id: str,
        file_name: str,
        file_path: str,
        mime_type: str | None = None,
        text_generate_config: types.TextGenerateConfig | None = None,
        image_generate_config: types.ImageGenerateConfig | None = None,
        music_generate_config: types.MusicGenerateConfig | None = None,
        video_generate_config: types.VideoGenerateConfig | None = None,
        speech_generate_config: types.SpeechGenerateConfig | None = None,
        gcs_path_override: str | None = None,
    ) -> types.Asset:
        """Saves a user-provided asset from local file path by uploading it to Creative Studio backend or locally."""
        with open(file_path, "rb") as f:
            blob = f.read()
        return self.save_asset(
            user_id=user_id,
            file_name=file_name,
            blob=blob,
            mime_type=mime_type,
            text_generate_config=text_generate_config,
            image_generate_config=image_generate_config,
            music_generate_config=music_generate_config,
            video_generate_config=video_generate_config,
            speech_generate_config=speech_generate_config,
            gcs_path_override=gcs_path_override,
        )

    def get_asset_by_id(
        self, asset_id: str, fetch_references: bool = True
    ) -> types.Asset | None:
        """Fetches asset details from Creative Studio by asset identifier.

        Args:
            asset_id: Unique string identifier of the target asset. Must match expected alphanumeric/UUID structure.
            fetch_references: Recursively load parents or child references.

        Returns:
            The Asset instance if found, otherwise None.
        """
        # 1. Check transient cache
        if self._transient_cache and asset_id in self._transient_cache:
            cached = self._transient_cache[asset_id]
            if isinstance(cached, dict):
                return types.CreativeStudioAsset.from_dict(cached, self, fetch_references)
            return cached
        
        # 2. Fetch from Creative Studio remote backend
        if not self._user_auth_token:
            logger.warning("CreativeStudioAssetService.get_asset_by_id: user_auth_token is required. Returning None.")
            return None

        url = f"{self._config.creative_studio_backend_url}/api/gallery/item/{asset_id}"
        headers = self._get_headers(self._user_auth_token, url)

        logger.info(f"Fetching asset '{asset_id}' metadata from Creative Studio backend at {url}...")
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=30.0)
                if response.status_code == 404:
                    logger.info(f"Asset '{asset_id}' not found in Creative Studio backend.")
                    return None
                response.raise_for_status()
                data = response.json()

                metadata = data.get("metadata", {}) or {}
                file_name = metadata.get("fileName") or metadata.get("originalFilename") or f"asset_{asset_id}"
                mime_type = metadata.get("mimeType") or "application/octet-stream"

                gcs_uris = data.get("gcsUris", []) or []
                if not gcs_uris:
                    gcs_uri = data.get("gcsUri")
                    if gcs_uri:
                        gcs_uris = [gcs_uri]

                if not gcs_uris:
                    logger.warning(f"No GCS URIs found for asset {asset_id}")
                    return None

                gcs_uri = gcs_uris[0]
                
                created_at_str = data.get("createdAt")
                if created_at_str:
                    try:
                        created_at = datetime.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        created_at = datetime.datetime.now()
                else:
                    created_at = datetime.datetime.now()

                return self.to_asset(
                    asset_id=str(asset_id),
                    workspace_id=str(data.get("workspaceId", self._workspace_id)),
                    file_name=file_name,
                    gcs_uri=gcs_uri,
                    created_at=created_at,
                    mime_type=mime_type,
                    item_type=data.get("itemType"),
                )
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code} fetching asset '{asset_id}': {exc.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve asset '{asset_id}' from Creative Studio backend: {e}")
            raise RuntimeError(f"Failed to retrieve asset '{asset_id}' from Creative Studio backend: {e}") from e

    def get_asset_by_file_name(
        self, file_name: str
    ) -> types.CreativeStudioAsset | None:
        """Fetches asset details from Creative Studio using user scope and filename.

        Args:
            file_name: The target filename.

        Returns:
            The Asset instance if located, otherwise None.
        """
        if self._transient_cache:
            for asset in self._transient_cache.values():
                if isinstance(asset, dict):
                    if asset.get("file_name") == file_name:
                        logger.info(f"Found asset '{file_name}' in transient cache (dict form).")
                        return types.CreativeStudioAsset.from_dict(asset, self, fetch_references=False)
                else:
                    if asset.file_name == file_name:
                        logger.info(f"Found asset '{file_name}' in transient cache.")
                        return asset

        if not self._user_auth_token or not self._workspace_id:
            raise ValueError("user_auth_token and workspace_id required to fetch from Creative Studio gallery")

        user_auth_header = f"Bearer {self._user_auth_token}"
        
        # Block 1: Get assets
        # API Request variables
        url = f"{self._config.creative_studio_backend_url}/api/gallery/search"

        creative_studio_headers = self._get_headers(self._user_auth_token, url)
        creative_studio_gallery_search_dto = {
            "query": file_name,
            "workspaceId": self._workspace_id,
            "limit": 100,
            "offset": 0,
        }

        # API Request generation
        try:
            with httpx.Client() as client:
                response = client.post(
                    url, json=creative_studio_gallery_search_dto, headers=creative_studio_headers, timeout=60.0
                )

                response.raise_for_status()

                data = response.json()
                logger.info(f"[IMAGE_GEN] Backend response status {response.status_code}: {json.dumps(data)}")
                
                # Filter response only for files that have the exact same filename
                filtered_items = []
                for item in data.get("data", []):
                    metadata = item.get("metadata", {}) or {}
                    item_filename = metadata.get("fileName") or metadata.get("originalFilename")
                    if item_filename == file_name:
                        filtered_items.append(item)
                
                if not filtered_items:
                    logger.info(f"No asset found matching filename: {file_name}")
                    return None

                # Order by createdAt and return the latest one
                filtered_items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
                latest_item = filtered_items[0]

                # Map the response to the Asset type
                metadata = latest_item.get("metadata", {}) or {}
                
                # Extract mime type
                mime_type = metadata.get("mimeType")

                # Parse created_at
                created_at_str = latest_item.get("createdAt")
                created_at = datetime.datetime.now(datetime.UTC)
                if created_at_str:
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    try:
                        created_at = datetime.datetime.fromisoformat(created_at_str)
                    except ValueError:
                        pass

                # Duration seconds mapping
                duration_seconds = metadata.get("duration_seconds") or metadata.get("durationSeconds") or metadata.get("duration")
                if duration_seconds is not None:
                    try:
                        duration_seconds = float(duration_seconds)
                    except (ValueError, TypeError):
                        duration_seconds = None

                # Construct appropriate media generation config
                is_video = metadata.get("isVideo", False)
                is_audio = metadata.get("isAudio", False)
                
                text_config = None
                image_config = None
                music_config = None
                video_config = None
                speech_config = None

                if mime_type.startswith("image/"): # TODO: We may need reference images here as well
                    image_config = types.ImageGenerateConfig(
                        model=metadata.get("model"),
                        prompt=metadata.get("prompt") or metadata.get("originalPrompt"),
                        aspect_ratio=metadata.get("aspectRatio"),
                    )
                elif mime_type.startswith("video/") or is_video:
                    video_config = types.VideoGenerateConfig(
                        model=metadata.get("model"),
                        prompt=metadata.get("prompt") or metadata.get("originalPrompt"),
                        aspect_ratio=metadata.get("aspectRatio"),
                        duration_seconds=metadata.get("durationSeconds"),
                        resolution=metadata.get("resolution"),
                        generate_audio=metadata.get("isAudio") or metadata.get("generateAudio"),
                    )
                elif mime_type.startswith("audio/") or is_audio:
                    if metadata.get("voice") or metadata.get("spokenText"):
                        speech_config = types.SpeechGenerateConfig(
                            model=metadata.get("model"),
                            prompt=metadata.get("prompt") or metadata.get("originalPrompt"),
                            voice=metadata.get("voice"),
                            spoken_text=metadata.get("spokenText"),
                        )
                    else:
                        music_config = types.MusicGenerateConfig(
                            model=metadata.get("model"),
                            prompt=metadata.get("prompt") or metadata.get("originalPrompt"),
                            negative_prompt=metadata.get("negativePrompt"),
                        )
                # Map GCS URIs to asset versions
                gcs_uris = latest_item.get("gcsUris", [])
                gcs_uri = gcs_uris[0] if gcs_uris else ""

                versions = [
                    types.AssetVersion(
                        asset_id=str(latest_item["id"]),
                        version_number=1,
                        gcs_uri=gcs_uri,
                        create_time=created_at,
                        text_generate_config=text_config,
                        image_generate_config=image_config,
                        music_generate_config=music_config,
                        video_generate_config=video_config,
                        speech_generate_config=speech_config,
                        duration_seconds=duration_seconds,
                    )
                ]

                asset = types.CreativeStudioAsset(
                    id=str(latest_item["id"]),
                    user_id=str(latest_item.get("workspaceId", self._workspace_id)),
                    mime_type=mime_type,
                    file_name=file_name,
                    current_version=1,
                    versions=versions,
                    workspace_id=str(self._workspace_id),
                    item_type=latest_item.get("itemType"),
                )
                return asset

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            logger.error(f"Request error: {exc}")
        except Exception as exc:
            logger.error(f"Mapping or unexpected error in get_asset_by_file_name: {exc}")

        return None

    def _download_from_gcs(self, gcs_uri: str) -> bytes:
        """Downloads direct raw bytes from GCS storage."""
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        path = gcs_uri.removeprefix("gs://")
        bucket_name, blob_path = path.split("/", 1)

        if self._gcs_bucket and bucket_name == self._gcs_bucket.name:
            blob = self._gcs_bucket.blob(blob_path)
            return blob.download_as_bytes()

        from google.cloud import storage
        storage_client = storage.Client(project=self._config.google_cloud_project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        return blob.download_as_bytes()

    def get_asset_blob(
        self, asset_id: str, version: int | None = None
    ) -> types.AssetBlob:
        """Downloads/retrieves the raw media file binary stream from Creative Studio.

        Args:
            asset_id: The unique asset UUID.
            version: The desired file version increment.

        Returns:
            An AssetBlob payload wrap containing MIME, title, and raw bytes.
        """
        # 1. Check if it is a cached Creative Studio Asset first
        if self._transient_cache and asset_id in self._transient_cache:
            cached_asset = self._transient_cache[asset_id]
            if isinstance(cached_asset, dict):
                cached_asset = types.CreativeStudioAsset.from_dict(cached_asset, self, fetch_references=False)
            if hasattr(cached_asset, "_content") and isinstance(getattr(cached_asset, "_content", None), bytes):
                return types.AssetBlob(
                    content=cached_asset._content,
                    file_name=cached_asset.file_name,
                    mime_type=cached_asset.mime_type or "text/plain"
                )
            
            version_num = version if version is not None else cached_asset.current_version
            asset_version = next((v for v in cached_asset.versions if v.version_number == version_num), None)
            if asset_version and asset_version.gcs_uri:
                try:
                    content = self._download_from_gcs(asset_version.gcs_uri)
                    return types.AssetBlob(
                        content=content,
                        file_name=cached_asset.file_name,
                        mime_type=cached_asset.mime_type
                    )
                except Exception as gcs_err:
                    logger.error(f"Failed direct GCS download for GCS URI {asset_version.gcs_uri}: {gcs_err}")

        # 2. Call remote backend
        if not self._user_auth_token:
            raise ValueError(
                "CreativeStudioAssetService.get_asset_blob: user_auth_token is required "
                "to fetch asset metadata from the Creative Studio backend. None provided."
            )

        url = f"{self._config.creative_studio_backend_url}/api/gallery/item/{asset_id}"
        headers = self._get_headers(self._user_auth_token, url)

        logger.info(f"Fetching asset '{asset_id}' metadata from Creative Studio backend at {url}...")
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                # Extract details
                metadata = data.get("metadata", {}) or {}
                file_name = metadata.get("fileName") or metadata.get("originalFilename") or f"asset_{asset_id}"
                mime_type = metadata.get("mimeType") or "application/octet-stream"

                gcs_uris = data.get("gcsUris", []) or []
                if not gcs_uris:
                    # Let's check single gcs_uri key just in case
                    gcs_uri = data.get("gcsUri")
                    if gcs_uri:
                        gcs_uris = [gcs_uri]

                if not gcs_uris:
                    raise ValueError(f"No GCS URIs found for asset {asset_id}")

                # Choose the GCS URI
                gcs_uri = gcs_uris[0]

                logger.info(f"Downloading asset '{file_name}' from GCS path: {gcs_uri}...")
                content = self._download_from_gcs(gcs_uri)

                return types.AssetBlob(
                    content=content,
                    file_name=file_name,
                    mime_type=mime_type,
                )
        except Exception as e:
            logger.error(f"Failed to retrieve asset '{asset_id}' from Creative Studio backend: {e}")
            raise RuntimeError(f"Failed to retrieve asset '{asset_id}' from Creative Studio backend: {e}") from e

    def list_assets(self, user_id: str) -> list[types.Asset]:
        """Lists all files owned/managed by the specific user on Creative Studio.

        Args:
            user_id: Target caller identifier. Strict authentication limits search results to this owner.

        Returns:
            A list of Asset object representations.
        """
        logger.warning("CreativeStudioAssetService.list_assets is not implemented for Creative Studio. Returning an empty list.")
        return []

    def update_asset(self, asset_id: str, **kwargs: Any) -> types.Asset | None:
        """Updates asset attributes on Creative Studio.

        Args:
            asset_id: The target asset ID. Ownership validation must be executed.
            **kwargs: Dynamic payload tags (like updating description or tag classifications).

        Returns:
            The updated Asset instance, or None if modification failed.
        """
        raise NotImplementedError(
            "CreativeStudioAssetService.update_asset is not implemented yet. "
            "Please configure the integration endpoints with Creative Studio."
        )

    def delete_asset(self, asset_id: str) -> None:
        """Deletes the asset database record and raw storage files from Creative Studio.

        Args:
            asset_id: Target asset identification token. Ownership checks are strictly required.
        """
        raise NotImplementedError(
            "CreativeStudioAssetService.delete_asset is not implemented yet. "
            "Please configure the integration endpoints with Creative Studio."
        )
