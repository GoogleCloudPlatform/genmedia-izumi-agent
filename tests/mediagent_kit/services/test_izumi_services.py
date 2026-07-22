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

"""Tests for the native (Izumi) service adapters.

These verify the adapter contract between the unified async interface and the
legacy synchronous services:
  * unified ``workspace_id`` maps onto the legacy ``user_id``;
  * ``AssetRef`` inputs resolve to the legacy filename kwargs the generators
    expect (``reference_image_filenames`` / ``first_frame_filename``);
  * legacy ``Asset`` objects convert to terminal ``GeneratedAsset`` /
    ``UploadedAsset`` values;
  * ``generate_text`` returns the text inline as a ``str`` (not an asset).

They mock the legacy services entirely, so no network / Firestore / GCS is
touched.
"""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mediagent_kit.services.aio.async_services import AsyncCanvasService
from mediagent_kit.services.errors import NotFoundError
from mediagent_kit.services.izumi.asset_service import IzumiAssetService
from mediagent_kit.services.izumi.media_generation_service import (
    IzumiMediaGenerationService,
)
from mediagent_kit.services.types.common import (
    AssetRef,
    GeneratedAsset,
    UploadedAsset,
)

_CREATED = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def _legacy_asset(
    *,
    asset_id="a1",
    file_name="file.png",
    mime_type="image/png",
    gcs_uri="gs://bucket/file.png",
    duration=None,
    user_id="ws1",
):
    """Builds a stand-in for a legacy ``Asset`` with a ``current`` version."""
    current = SimpleNamespace(
        gcs_uri=gcs_uri,
        create_time=_CREATED,
        duration_seconds=duration,
    )
    return SimpleNamespace(
        id=asset_id,
        file_name=file_name,
        mime_type=mime_type,
        user_id=user_id,
        current=current,
    )


# --------------------------------------------------------------------------- #
# IzumiMediaGenerationService
# --------------------------------------------------------------------------- #


@pytest.fixture
def media_mocks():
    media = MagicMock(name="legacy_media_service")
    assets = MagicMock(name="legacy_asset_service")
    service = IzumiMediaGenerationService(media, assets)
    return service, media, assets


@pytest.mark.asyncio
async def test_generate_text_returns_str(media_mocks):
    service, media, assets = media_mocks
    media.generate_text_with_gemini.return_value = _legacy_asset(asset_id="t1")
    assets.get_asset_blob.return_value = SimpleNamespace(content=b"hello world")

    result = await service.generate_text(workspace_id="ws1", prompt="say hi")

    assert isinstance(result, str)
    assert result == "hello world"
    # workspace_id -> user_id; no reference assets -> empty filename list.
    _, kwargs = media.generate_text_with_gemini.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["prompt"] == "say hi"
    assert kwargs["reference_image_filenames"] == []


@pytest.mark.asyncio
async def test_generate_text_resolves_reference_assets(media_mocks):
    service, media, assets = media_mocks
    assets.get_asset_by_id.return_value = _legacy_asset(file_name="ref.png")
    media.generate_text_with_gemini.return_value = _legacy_asset()
    assets.get_asset_blob.return_value = SimpleNamespace(content=b"ok")

    await service.generate_text(
        workspace_id="ws1",
        prompt="describe",
        reference_assets=[AssetRef(id="9", workspace_id="ws1", asset_type="uploaded")],
    )

    _, kwargs = media.generate_text_with_gemini.call_args
    assert kwargs["reference_image_filenames"] == ["ref.png"]


@pytest.mark.asyncio
async def test_generate_text_empty_blob_returns_empty_string(media_mocks):
    service, media, assets = media_mocks
    media.generate_text_with_gemini.return_value = _legacy_asset()
    assets.get_asset_blob.return_value = None

    result = await service.generate_text(workspace_id="ws1", prompt="x")
    assert result == ""


@pytest.mark.asyncio
async def test_generate_image_maps_args_and_converts(media_mocks):
    service, media, assets = media_mocks
    media.generate_image_with_gemini.return_value = _legacy_asset(
        asset_id="img1", file_name="car.png", mime_type="image/png"
    )

    asset = await service.generate_image(
        workspace_id="ws1",
        prompt="a red car",
        generation_model="gemini-image-x",
        aspect_ratio="16:9",
        resolution="1K",
        file_name="car.png",
    )

    assert isinstance(asset, GeneratedAsset)
    assert asset.id == "img1"
    assert asset.workspace_id == "ws1"
    assert asset.status == "completed"
    assert asset.gcs_uri == "gs://bucket/file.png"
    assert asset.generation_metadata.source == "izumi"
    assert asset.generation_metadata.model == "gemini-image-x"

    _, kwargs = media.generate_image_with_gemini.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["file_name"] == "car.png"
    assert kwargs["aspect_ratio"] == "16:9"
    assert kwargs["model"] == "gemini-image-x"
    assert kwargs["reference_image_filenames"] == []


@pytest.mark.asyncio
async def test_generate_video_maps_start_and_end_image(media_mocks):
    service, media, assets = media_mocks
    assets.get_asset_by_id.side_effect = [
        _legacy_asset(file_name="first.png"),
        _legacy_asset(file_name="last.png"),
    ]
    media.generate_video_with_veo.return_value = _legacy_asset(
        asset_id="v1", file_name="clip.mp4", mime_type="video/mp4", duration=6.0
    )

    asset = await service.generate_video(
        workspace_id="ws1",
        prompt="pan across city",
        generation_model="veo-x",
        aspect_ratio="16:9",
        duration_seconds=6,
        file_name="clip.mp4",
        start_image=AssetRef(id="1", workspace_id="ws1", asset_type="generated"),
        end_image=AssetRef(id="2", workspace_id="ws1", asset_type="generated"),
    )

    assert isinstance(asset, GeneratedAsset)
    assert asset.id == "v1"
    assert asset.mime_type == "video/mp4"
    assert asset.duration_seconds == 6.0

    _, kwargs = media.generate_video_with_veo.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["first_frame_filename"] == "first.png"
    assert kwargs["last_frame_filename"] == "last.png"
    assert kwargs["method"] == "image_to_video"
    assert kwargs["model"] == "veo-x"


@pytest.mark.asyncio
async def test_generate_speech_maps_args(media_mocks):
    service, media, assets = media_mocks
    media.generate_speech_single_speaker.return_value = _legacy_asset(
        asset_id="s1", file_name="vo.wav", mime_type="audio/wav", duration=3.5
    )

    asset = await service.generate_speech(
        workspace_id="ws1",
        text="welcome",
        voice_name="Puck",
        language_code="en-US",
        file_name="vo.wav",
    )

    assert isinstance(asset, GeneratedAsset)
    assert asset.duration_seconds == 3.5
    _, kwargs = media.generate_speech_single_speaker.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["text"] == "welcome"
    assert kwargs["voice_name"] == "Puck"
    assert kwargs["language_code"] == "en-US"


@pytest.mark.asyncio
async def test_generate_music_maps_args(media_mocks):
    service, media, assets = media_mocks
    media.generate_music_with_lyria.return_value = _legacy_asset(
        asset_id="m1", file_name="bg.mp3", mime_type="audio/mpeg"
    )

    asset = await service.generate_music(
        workspace_id="ws1",
        prompt="upbeat",
        model="lyria-x",
        duration_seconds=30,
        file_name="bg.mp3",
    )

    assert isinstance(asset, GeneratedAsset)
    assert asset.id == "m1"
    _, kwargs = media.generate_music_with_lyria.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["prompt"] == "upbeat"
    assert kwargs["model"] == "lyria-x"


# --------------------------------------------------------------------------- #
# IzumiAssetService
# --------------------------------------------------------------------------- #


@pytest.fixture
def asset_mocks():
    legacy = MagicMock(name="legacy_asset_service")
    service = IzumiAssetService(legacy)
    return service, legacy


@pytest.mark.asyncio
async def test_get_asset_generated(asset_mocks):
    service, legacy = asset_mocks
    legacy.get_asset_by_id.return_value = _legacy_asset(asset_id="g1")

    ref = AssetRef(id="g1", workspace_id="ws1", asset_type="generated")
    asset = await service.get_asset(ref)

    assert isinstance(asset, GeneratedAsset)
    assert asset.id == "g1"
    assert asset.workspace_id == "ws1"
    legacy.get_asset_by_id.assert_called_once_with("g1")


@pytest.mark.asyncio
async def test_get_asset_uploaded(asset_mocks):
    service, legacy = asset_mocks
    legacy.get_asset_by_id.return_value = _legacy_asset(asset_id="u1")

    ref = AssetRef(id="u1", workspace_id="ws1", asset_type="uploaded")
    asset = await service.get_asset(ref)

    assert isinstance(asset, UploadedAsset)
    assert asset.id == "u1"
    assert asset.workspace_id == "ws1"


@pytest.mark.asyncio
async def test_get_asset_not_found_returns_none(asset_mocks):
    service, legacy = asset_mocks
    legacy.get_asset_by_id.return_value = None

    ref = AssetRef(id="missing", workspace_id="ws1", asset_type="generated")
    assert await service.get_asset(ref) is None


@pytest.mark.asyncio
async def test_download_asset_bytes(asset_mocks):
    service, legacy = asset_mocks
    legacy.get_asset_blob.return_value = SimpleNamespace(content=b"raw-bytes")

    ref = AssetRef(id="a1", workspace_id="ws1", asset_type="generated")
    data = await service.download_asset_bytes(ref)

    assert data == b"raw-bytes"
    legacy.get_asset_blob.assert_called_once_with("a1")


@pytest.mark.asyncio
async def test_download_asset_bytes_missing_raises(asset_mocks):
    service, legacy = asset_mocks
    legacy.get_asset_blob.return_value = SimpleNamespace(content=None)

    ref = AssetRef(id="a1", workspace_id="ws1", asset_type="generated")
    with pytest.raises(NotFoundError):
        await service.download_asset_bytes(ref)


@pytest.mark.asyncio
async def test_upload_asset_maps_workspace_to_user_id(asset_mocks):
    service, legacy = asset_mocks
    legacy.save_asset.return_value = _legacy_asset(
        asset_id="up1", file_name="photo.jpg", mime_type="image/jpeg"
    )

    asset = await service.upload_asset(
        workspace_id="ws1",
        file_name="photo.jpg",
        blob=b"bytes",
        mime_type="image/jpeg",
    )

    assert isinstance(asset, UploadedAsset)
    assert asset.id == "up1"
    _, kwargs = legacy.save_asset.call_args
    assert kwargs["user_id"] == "ws1"
    assert kwargs["file_name"] == "photo.jpg"
    assert kwargs["blob"] == b"bytes"
    assert kwargs["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_search_assets_filters_by_query(asset_mocks):
    service, legacy = asset_mocks
    legacy.list_assets.return_value = [
        _legacy_asset(asset_id="1", file_name="cat.png"),
        _legacy_asset(asset_id="2", file_name="dog.png"),
        _legacy_asset(asset_id="3", file_name="catnip.png"),
    ]

    results = await service.search_assets(workspace_id="ws1", query="cat")

    assert [a.id for a in results] == ["1", "3"]
    legacy.list_assets.assert_called_once_with("ws1")


@pytest.mark.asyncio
async def test_search_assets_pagination(asset_mocks):
    service, legacy = asset_mocks
    legacy.list_assets.return_value = [
        _legacy_asset(asset_id=str(i), file_name=f"f{i}.png") for i in range(5)
    ]

    results = await service.search_assets(workspace_id="ws1", limit=2, offset=1)
    assert [a.id for a in results] == ["1", "2"]


@pytest.mark.asyncio
async def test_delete_asset(asset_mocks):
    service, legacy = asset_mocks
    ref = AssetRef(id="del1", workspace_id="ws1", asset_type="generated")

    await service.delete_asset(ref)
    legacy.delete_asset.assert_called_once_with("del1")


# --------------------------------------------------------------------------- #
# AsyncCanvasService native (legacy) kwarg mapping
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_async_canvas_native_maps_workspace_to_user_id():
    """The stitching caller passes workspace_id + video_timeline; the legacy
    CanvasService only accepts user_id/title/video_timeline/html."""
    legacy = MagicMock(name="legacy_canvas_service")
    legacy.create_canvas.return_value = SimpleNamespace(id="c1")
    service = AsyncCanvasService(legacy)
    timeline = object()

    await service.create_canvas(
        workspace_id="ws1", title="My Canvas", video_timeline=timeline
    )

    legacy.create_canvas.assert_called_once_with(
        user_id="ws1", title="My Canvas", video_timeline=timeline
    )


@pytest.mark.asyncio
async def test_async_canvas_native_drops_workspace_and_session_id():
    """The summary caller passes workspace_id + user_id + session_id + html;
    legacy rejects workspace_id/session_id, so they must be dropped."""
    legacy = MagicMock(name="legacy_canvas_service")
    legacy.create_canvas.return_value = SimpleNamespace(id="c2")
    service = AsyncCanvasService(legacy)
    html = object()

    await service.create_canvas(
        workspace_id="ws1",
        user_id="ws1",
        session_id="s1",
        title="Summary",
        html=html,
    )

    legacy.create_canvas.assert_called_once_with(
        user_id="ws1", title="Summary", html=html
    )
