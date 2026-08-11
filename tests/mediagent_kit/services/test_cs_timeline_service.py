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

"""Unit tests for CSTimelineService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.errors import BackendError
from mediagent_kit.services.creative_studio.cs_timeline_service import CSTimelineService
from mediagent_kit.services.types.common import (
    AssetRef,
    GeneratedAsset,
    ScopedVideoTimeline,
    TimelineVideoClip,
)


@pytest.fixture
def cs_config():
    return MediagentKitConfig(
        cs_backend_url="http://backend:8080",
        google_cloud_project="test-project",
    )


@pytest.fixture
def cs_timeline_service(cs_config):
    return CSTimelineService(
        workspace_id="123",
        user_auth_token="user_token_abc",
        config=cs_config,
    )


@pytest.mark.asyncio
async def test_create_and_get_timeline(cs_timeline_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock POST /api/workbench/timelines creation response
        resp_post = MagicMock()
        resp_post.status_code = 201
        resp_post.is_error = False
        resp_post.json.return_value = {
            "id": 88,
            "workspace_id": 123,
            "title": "Summer Campaign Video",
            "video_clips": [
                {
                    "asset_ref": {"id": 302, "type": "media_item"},
                    "volume": 1.0,
                    "speed": 1.0,
                }
            ],
            "audio_clips": [],
            "transitions": [],
        }
        mock_client.post.return_value = resp_post

        tl = await cs_timeline_service.create_timeline(
            workspace_id="123", title="Summer Campaign Video"
        )

        assert isinstance(tl, ScopedVideoTimeline)
        assert tl.timeline_id == "88"
        assert tl.title == "Summer Campaign Video"
        assert len(tl.video_clips) == 1
        assert tl.video_clips[0].asset_ref.id == "302"
        assert tl.video_clips[0].asset_ref.asset_type == "generated"

        # Mock GET /api/workbench/timelines/88
        resp_get = MagicMock()
        resp_get.status_code = 200
        resp_get.is_error = False
        resp_get.json.return_value = resp_post.json.return_value
        mock_client.get.return_value = resp_get

        fetched = await cs_timeline_service.get_timeline("88")
        assert fetched is not None
        assert fetched.timeline_id == "88"


@pytest.mark.asyncio
async def test_update_and_delete_timeline(cs_timeline_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        resp_put = MagicMock()
        resp_put.status_code = 200
        resp_put.is_error = False
        mock_client.put.return_value = resp_put

        tl = ScopedVideoTimeline(
            timeline_id="88",
            workspace_id="123",
            title="Updated Title",
            video_clips=[
                TimelineVideoClip(
                    asset_ref=AssetRef(
                        id="101", asset_type="uploaded", workspace_id="123"
                    )
                )
            ],
        )

        await cs_timeline_service.update_timeline("88", tl)
        mock_client.put.assert_called_once()

        resp_del = MagicMock()
        resp_del.status_code = 204
        resp_del.is_error = False
        mock_client.delete.return_value = resp_del

        await cs_timeline_service.delete_timeline("88")
        mock_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_stitch_timeline(cs_timeline_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock render response from backend
        resp_render = MagicMock()
        resp_render.status_code = 200
        resp_render.is_error = False
        resp_render.json.return_value = {
            "asset_id": 999,
            "gcs_uri": "gs://bucket/render_999.mp4",
            "timeline_id": 88,
            "message": "Timeline rendered successfully",
        }
        mock_client.post.return_value = resp_render

        resp_poll = MagicMock()
        resp_poll.status_code = 200
        resp_poll.is_error = False
        resp_poll.json.return_value = {
            "id": 999,
            "status": "completed",
            "gcsUris": ["gs://bucket/render_999.mp4"],
        }
        mock_client.get.return_value = resp_poll

        with patch(
            "mediagent_kit.services.creative_studio.cs_asset_service.CSAssetService.get_asset",
            new_callable=AsyncMock,
        ) as mock_get_asset:
            mock_get_asset.return_value = None

            stitched = await cs_timeline_service.stitch_timeline(
                "88", "final_output.mp4"
            )

            assert isinstance(stitched, GeneratedAsset)
            assert stitched.id == "999"
            assert stitched.gcs_uri == "gs://bucket/render_999.mp4"
            assert stitched.status == "completed"


@pytest.mark.asyncio
async def test_stitch_timeline_failed_status(cs_timeline_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock render response from backend
        resp_render = MagicMock()
        resp_render.status_code = 200
        resp_render.is_error = False
        resp_render.json.return_value = {
            "asset_id": 999,
            "timeline_id": 88,
        }
        mock_client.post.return_value = resp_render

        # Mock poll response with failed status
        resp_poll = MagicMock()
        resp_poll.status_code = 200
        resp_poll.is_error = False
        resp_poll.json.return_value = {
            "id": 999,
            "status": "failed",
            "errorMessage": "Render failed due to asset error",
        }
        mock_client.get.return_value = resp_poll

        with patch(
            "mediagent_kit.services.creative_studio.cs_asset_service.CSAssetService.get_asset",
            new_callable=AsyncMock,
        ) as mock_get_asset:
            mock_get_asset.return_value = None

            stitched = await cs_timeline_service.stitch_timeline(
                "88", "final_output.mp4"
            )

            assert isinstance(stitched, GeneratedAsset)
            assert stitched.id == "999"
            assert stitched.status == "failed"
            assert stitched.error_message == "Render failed due to asset error"


@pytest.mark.asyncio
async def test_stitch_timeline_timeout(cs_timeline_service):
    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch(
            "mediagent_kit.services.creative_studio.cs_timeline_service.time.time"
        ) as mock_time,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock render response from backend
        resp_render = MagicMock()
        resp_render.status_code = 200
        resp_render.is_error = False
        resp_render.json.return_value = {
            "asset_id": 999,
            "timeline_id": 88,
        }
        mock_client.post.return_value = resp_render

        # Mock polling loop returning "pending"
        resp_poll = MagicMock()
        resp_poll.status_code = 200
        resp_poll.is_error = False
        resp_poll.json.return_value = {
            "id": 999,
            "status": "pending",
        }
        mock_client.get.return_value = resp_poll

        # Mock time progression to trigger timeout
        current_time = [100.0]

        def increment_time():
            val = current_time[0]
            current_time[0] += 301.0
            return val

        mock_time.side_effect = increment_time

        stitched = await cs_timeline_service.stitch_timeline("88", "final_output.mp4")

        assert isinstance(stitched, GeneratedAsset)
        assert stitched.id == "999"
        assert stitched.status == "failed"
        assert "timed out" in stitched.error_message


@pytest.mark.asyncio
async def test_stitch_timeline_missing_item_id(cs_timeline_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock render response missing item ID
        resp_render = MagicMock()
        resp_render.status_code = 200
        resp_render.is_error = False
        resp_render.json.return_value = {}
        mock_client.post.return_value = resp_render

        with pytest.raises(BackendError) as exc_info:
            await cs_timeline_service.stitch_timeline("88", "final_output.mp4")
        assert "No item ID returned" in str(exc_info.value)


def test_from_cs_response_int_ids(cs_timeline_service):
    """Verify _from_cs_response converts integer storyboard_id and session_id to strings."""
    data = {
        "id": 88,
        "workspace_id": 123,
        "storyboard_id": 140,
        "session_id": 55,
        "user_id": 77,
        "title": "Test Int IDs",
        "video_clips": [],
    }
    tl = cs_timeline_service._from_cs_response(data)
    assert tl.timeline_id == "88"
    assert tl.workspace_id == "123"
    assert tl.storyboard_id == "140"
    assert tl.session_id == "55"
    assert tl.user_id == "77"
