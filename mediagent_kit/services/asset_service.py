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

import datetime
import os
import uuid
from typing import Any

from firebase_admin import firestore
from google.cloud.storage.bucket import Bucket

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types
from mediagent_kit.services.base_service import BaseService


class AssetService(BaseService):
    """Service for managing assets in Firestore."""

    def __init__(
        self,
        db: firestore.Client,
        gcs_bucket: Bucket | None,
        config: MediagentKitConfig,
    ):
        """Initializes the AssetService.

        Args:
            db: The Firestore client.
            gcs_bucket: The GCS bucket to store assets in.
            config: The service configuration.
        """
        super().__init__(db)
        self._config = config
        self._assets_collection = self._get_collection("assets")
        self._gcs_bucket = gcs_bucket

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
        """Saves an asset. If an asset with the same user_id and file_name
        already exists, a new version is created. Otherwise, a new asset is created.

        Args:
            user_id: The ID of the user.
            file_name: The name of the asset file.
            blob: The content of the asset file as bytes.
            mime_type: The MIME type of the asset. Required for new assets.
            text_generate_config: The configuration for generating text.
            image_generate_config: The configuration for generating an image.
            music_generate_config: The configuration for generating music.
            video_generate_config: The configuration for generating a video.
            speech_generate_config: The configuration for generating speech.
            gcs_path_override: The GCS path to save the asset to.

        Returns:
            The saved asset.
        """
        return self._save_asset_impl(
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
        """Saves an asset from a local file path.

        Args:
            user_id: The ID of the user.
            file_name: The name of the asset file.
            file_path: The path to the local file.
            mime_type: The MIME type of the asset. Required for new assets.
            text_generate_config: The configuration for generating text.
            image_generate_config: The configuration for generating an image.
            music_generate_config: The configuration for generating music.
            video_generate_config: The configuration for generating a video.
            speech_generate_config: The configuration for generating speech.
            gcs_path_override: The GCS path to save the asset to.

        Returns:
            The saved asset.
        """
        return self._save_asset_impl(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
            text_generate_config=text_generate_config,
            image_generate_config=image_generate_config,
            music_generate_config=music_generate_config,
            video_generate_config=video_generate_config,
            speech_generate_config=speech_generate_config,
            gcs_path_override=gcs_path_override,
        )

    def _save_asset_impl(
        self,
        user_id: str,
        file_name: str,
        blob: bytes | None = None,
        file_path: str | None = None,
        mime_type: str | None = None,
        text_generate_config: types.TextGenerateConfig | None = None,
        image_generate_config: types.ImageGenerateConfig | None = None,
        music_generate_config: types.MusicGenerateConfig | None = None,
        video_generate_config: types.VideoGenerateConfig | None = None,
        speech_generate_config: types.SpeechGenerateConfig | None = None,
        gcs_path_override: str | None = None,
    ) -> types.Asset:
        """Internal implementation for saving an asset."""
        if not self._gcs_bucket:
            raise ValueError("GCS bucket not configured for AssetService.")

        if blob is None and file_path is None:
            raise ValueError("Either blob or file_path must be provided.")

        existing_asset = self.get_asset_by_file_name(user_id, file_name)

        if existing_asset:
            # Asset exists, create a new version
            if mime_type and mime_type != existing_asset.mime_type:
                raise ValueError("mime_type cannot be changed for an existing asset.")

            asset_ref = self._assets_collection.document(existing_asset.id)
            new_version_number = existing_asset.current_version + 1
            asset_mime_type = existing_asset.mime_type
            asset_id = existing_asset.id
        else:
            # New asset
            if not mime_type:
                raise ValueError("mime_type is required for new assets.")
            asset_id = str(uuid.uuid4())
            asset = types.Asset(
                id=asset_id,
                user_id=user_id,
                mime_type=mime_type,
                file_name=file_name,
                current_version=0,
                versions=[],
            )
            asset_ref = self._assets_collection.document(asset_id)
            asset_ref.set(asset.to_firestore())
            new_version_number = 1
            asset_mime_type = mime_type

        # Calculate duration if video or audio
        duration_seconds = None
        if asset_mime_type.startswith("video/") or asset_mime_type.startswith("audio/"):
            try:
                from mediagent_kit.utils import media_tools

                if blob is not None:
                    file_extension = f".{file_name.split('.')[-1]}"
                    metadata = media_tools.get_media_metadata_from_blob(
                        blob, file_extension
                    )
                else:
                    metadata = media_tools.get_media_metadata_from_file(file_path)
                duration_seconds = metadata.duration
            except Exception as e:
                print(
                    f"Warning: Failed to calculate duration for asset {file_name}: {e}"
                )

        if gcs_path_override:
            gcs_path = gcs_path_override
        elif os.environ.get("BATCH_JOB_MODE") == "True":
            gcs_root = os.environ.get("ASSET_GCS_ROOT", "batch_job")
            # For batch jobs, we flatten the structure and put assets in an 'assets/' subfolder
            gcs_path = f"{gcs_root}/{user_id}/assets/{file_name}"
        else:
            gcs_path = f"assets/{user_id}/{asset_id}/{new_version_number}/{file_name}"

        gcs_blob = self._gcs_bucket.blob(gcs_path)

        if blob is not None:
            gcs_blob.upload_from_string(blob, content_type=asset_mime_type)
        else:
            gcs_blob.upload_from_filename(file_path, content_type=asset_mime_type)

        gcs_uri = f"gs://{self._gcs_bucket.name}/{gcs_path}"

        new_version = types.AssetVersion(
            asset_id=asset_id,
            version_number=new_version_number,
            gcs_uri=gcs_uri,
            create_time=datetime.datetime.now(datetime.UTC),
            text_generate_config=text_generate_config,
            image_generate_config=image_generate_config,
            music_generate_config=music_generate_config,
            video_generate_config=video_generate_config,
            speech_generate_config=speech_generate_config,
            duration_seconds=duration_seconds,
        )

        update_data = {
            "versions": firestore.ArrayUnion([new_version.to_firestore()]),
            "current_version": new_version_number,
        }
        asset_ref.update(update_data)

        return self.get_asset_by_id(asset_id)

    def get_asset_by_id(
        self, asset_id: str, fetch_references: bool = True
    ) -> types.Asset | None:
        """Gets an asset from database by its ID.

        Args:
            asset_id: The ID of the asset to get.
            fetch_references: Whether to fetch referenced assets (e.g. parent images).
                Defaults to True. If False, referenced assets will be None.
                This is to prevent infinite recursion.

        Returns:
            The asset, or None if it does not exist.
        """
        asset_doc = self._assets_collection.document(asset_id).get()
        if asset_doc.exists:
            return types.Asset.from_firestore(
                asset_doc.to_dict(),
                asset_service=self,
                fetch_references=fetch_references,
            )
        return None

    def get_asset_by_file_name(
        self, user_id: str, file_name: str, version: int | None = None
    ) -> types.Asset | None:
        """Gets an asset from database by its user_id and file_name.

        Args:
            user_id: The ID of the user.
            file_name: The file name of the asset.
            version: If provided, the returned asset will only contain this version.
                If None, the asset will contain all versions.

        Returns:
            The asset, or None if it does not exist.
        """
        query = (
            self._assets_collection.where(
                filter=firestore.FieldFilter("user_id", "==", user_id)
            )
            .where(filter=firestore.FieldFilter("file_name", "==", file_name))
            .limit(1)
        )
        docs = list(query.stream())
        if not docs:
            return None

        asset = types.Asset.from_firestore(docs[0].to_dict(), asset_service=self)

        if version is not None:
            filtered_versions = [
                v for v in asset.versions if v.version_number == version
            ]
            if not filtered_versions:
                # If the specified version is not found, return None
                # as the asset does not have that version.
                return None
            asset.versions = filtered_versions

        return asset

    def get_asset_blob(
        self, asset_id: str, version: int | None = None
    ) -> types.AssetBlob:
        """Gets the blob of an asset version from GCS.

        Args:
            asset_id: The ID of the asset.
            version: The version number to get. If None, gets the latest version.

        Returns:
            An AssetBlob object containing the content, file name, and mime type.
        """
        if not self._gcs_bucket:
            raise ValueError("GCS bucket not configured for AssetService.")

        asset = self.get_asset_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found.")

        version_to_get = version if version is not None else asset.current_version

        if version_to_get == 0 or not asset.versions:
            raise ValueError(f"Asset {asset_id} has no versions.")

        asset_version = next(
            (v for v in asset.versions if v.version_number == version_to_get), None
        )

        if not asset_version:
            raise ValueError(
                f"Version {version_to_get} for asset {asset_id} not found."
            )

        gcs_uri = asset_version.gcs_uri
        # Assuming gcs_uri is in gs://<bucket>/<path> format
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

        uri_parts = gcs_uri[5:].split("/", 1)
        bucket_name = uri_parts[0]
        gcs_path = uri_parts[1]

        if bucket_name != self._gcs_bucket.name:
            raise ValueError(
                f"GCS URI {gcs_uri} does not belong to the configured bucket."
            )

        blob_to_download = self._gcs_bucket.blob(gcs_path)
        content = blob_to_download.download_as_bytes()

        return types.AssetBlob(
            content=content,
            file_name=asset.file_name,
            mime_type=asset.mime_type,
        )

    def list_assets(self, user_id: str) -> list[types.Asset]:
        """Lists all assets for a user.

        Args:
            user_id: The ID of the user to list assets for.

        Returns:
            A list of assets.
        """
        assets = []
        for doc in self._assets_collection.where(
            filter=firestore.FieldFilter("user_id", "==", user_id)
        ).stream():
            assets.append(types.Asset.from_firestore(doc.to_dict(), asset_service=self))
        return assets

    def update_asset(self, asset_id: str, **kwargs: Any) -> types.Asset | None:
        """Updates an asset in Firestore.

        Args:
            asset_id: The ID of the asset to update.
            **kwargs: The fields to update.

        Returns:
            The updated asset.
        """
        asset_ref = self._assets_collection.document(asset_id)
        asset_ref.update(kwargs)
        return self.get_asset_by_id(asset_id)

    def delete_asset(self, asset_id: str) -> None:
        """Deletes an asset from Firestore and all its versions from GCS.

        Args:
            asset_id: The ID of the asset to delete.
        """
        if not self._gcs_bucket:
            raise ValueError("GCS bucket not configured for AssetService.")

        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return

        # Delete all versions from GCS
        for version in asset.versions:
            gcs_uri = version.gcs_uri
            if gcs_uri and gcs_uri.startswith(f"gs://{self._gcs_bucket.name}/"):
                gcs_path = gcs_uri[len(f"gs://{self._gcs_bucket.name}/") :]
                blob = self._gcs_bucket.blob(gcs_path)
                blob.delete()

        # Delete the asset from Firestore
        self._assets_collection.document(asset_id).delete()
