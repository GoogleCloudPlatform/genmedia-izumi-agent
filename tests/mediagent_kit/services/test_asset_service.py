import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from firebase_admin import firestore
from google.cloud.storage.bucket import Bucket
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.types import Asset, AssetVersion, AssetBlob
from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_db():
    return MagicMock(spec=firestore.Client)


@pytest.fixture
def mock_bucket():
    return MagicMock(spec=Bucket)


@pytest.fixture
def mock_config():
    config = MagicMock(spec=MediagentKitConfig)
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    return config


@pytest.fixture
def service(mock_db, mock_bucket, mock_config):
    with patch.object(AssetService, "_get_collection") as mock_get_col:
        mock_col = MagicMock()
        mock_get_col.return_value = mock_col
        svc = AssetService(mock_db, mock_bucket, mock_config)
        svc._assets_collection = mock_col
        return svc


def test_save_asset_new(service, mock_bucket):
    user_id = "user1"
    file_name = "test.png"
    blob = b"fake image data"
    mime_type = "image/png"

    # Mock get_asset_by_file_name to return None (new asset)
    with patch.object(service, "get_asset_by_file_name", return_value=None):
        mock_doc_ref = MagicMock()
        service._assets_collection.document.return_value = mock_doc_ref

        # Mock get_asset_by_id to return the created asset (called at the end of save_asset)
        created_asset = Asset(
            id="new-uuid",
            user_id=user_id,
            mime_type=mime_type,
            file_name=file_name,
            current_version=1,
            versions=[
                AssetVersion(
                    asset_id="new-uuid",
                    version_number=1,
                    gcs_uri="gs://bucket/path",
                    create_time=datetime.now(UTC),
                )
            ],
        )
        with patch.object(service, "get_asset_by_id", return_value=created_asset):

            mock_gcs_blob = MagicMock()
            mock_bucket.blob.return_value = mock_gcs_blob
            mock_bucket.name = "test-bucket"

            asset = service.save_asset(user_id, file_name, blob, mime_type=mime_type)

            assert asset is not None
            assert asset.id == "new-uuid"
            mock_bucket.blob.assert_called_once()
            mock_gcs_blob.upload_from_string.assert_called_once_with(
                blob, content_type=mime_type
            )
            service._assets_collection.document.assert_called_once()  # For the set call


def test_get_asset_by_id_exists(service):
    asset_id = "asset1"

    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = True
    mock_doc_snapshot.to_dict.return_value = {
        "id": asset_id,
        "user_id": "user1",
        "mime_type": "image/png",
        "file_name": "test.png",
        "current_version": 1,
        "versions": [],
    }
    mock_doc_ref.get.return_value = mock_doc_snapshot
    service._assets_collection.document.return_value = mock_doc_ref

    # We might need to mock Asset.from_firestore if it fails on empty versions, but let's assume it works or we use real from_firestore
    asset = service.get_asset_by_id(asset_id)

    assert asset is not None
    assert asset.id == asset_id


def test_get_asset_by_file_name_exists(service):
    user_id = "user1"
    file_name = "test.png"

    mock_query_first = MagicMock()
    mock_query_second = MagicMock()
    mock_query_limit = MagicMock()
    mock_doc_snapshot = MagicMock()

    mock_doc_snapshot.to_dict.return_value = {
        "id": "asset1",
        "user_id": user_id,
        "mime_type": "image/png",
        "file_name": file_name,
        "current_version": 1,
        "versions": [],
    }

    service._assets_collection.where.return_value = mock_query_first
    mock_query_first.where.return_value = mock_query_second
    mock_query_second.limit.return_value = mock_query_limit
    mock_query_limit.stream.return_value = [mock_doc_snapshot]

    asset = service.get_asset_by_file_name(user_id, file_name)

    assert asset is not None
    assert asset.file_name == file_name


def test_get_asset_blob(service, mock_bucket):
    asset_id = "asset1"

    mock_asset = Asset(
        id=asset_id,
        user_id="user1",
        mime_type="image/png",
        file_name="test.png",
        current_version=1,
        versions=[
            AssetVersion(
                asset_id=asset_id,
                version_number=1,
                gcs_uri="gs://test-bucket/path",
                create_time=datetime.now(UTC),
            )
        ],
    )

    with patch.object(service, "get_asset_by_id", return_value=mock_asset):
        mock_gcs_blob = MagicMock()
        mock_gcs_blob.download_as_bytes.return_value = b"fake blob content"
        mock_bucket.blob.return_value = mock_gcs_blob
        mock_bucket.name = "test-bucket"

        blob = service.get_asset_blob(asset_id)

        assert blob.content == b"fake blob content"
        assert blob.file_name == "test.png"
        assert blob.mime_type == "image/png"


def test_delete_asset(service, mock_bucket):
    asset_id = "asset1"

    mock_asset = Asset(
        id=asset_id,
        user_id="user1",
        mime_type="image/png",
        file_name="test.png",
        current_version=1,
        versions=[
            AssetVersion(
                asset_id=asset_id,
                version_number=1,
                gcs_uri="gs://test-bucket/path",
                create_time=datetime.now(UTC),
            )
        ],
    )

    with patch.object(service, "get_asset_by_id", return_value=mock_asset):
        mock_doc_ref = MagicMock()
        service._assets_collection.document.return_value = mock_doc_ref

        mock_gcs_blob = MagicMock()
        mock_bucket.blob.return_value = mock_gcs_blob
        mock_bucket.name = "test-bucket"

        service.delete_asset(asset_id)

        mock_gcs_blob.delete.assert_called_once()
        mock_doc_ref.delete.assert_called_once()
