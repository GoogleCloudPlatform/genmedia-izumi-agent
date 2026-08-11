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

"""Unit tests for CSStoryboardService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.creative_studio.cs_storyboard_service import (
    CSStoryboardService,
)


@pytest.fixture
def cs_config():
    return MediagentKitConfig(
        cs_backend_url="http://backend:8080",
        google_cloud_project="test-project",
    )


@pytest.fixture
def cs_storyboard_service(cs_config):
    return CSStoryboardService(
        workspace_id="123",
        user_auth_token="user_token_abc",
        config=cs_config,
    )


@pytest.mark.asyncio
async def test_save_storyboard_create_and_update(cs_storyboard_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # 1. Mock POST /api/storyboards/ creation response
        resp_post = MagicMock()
        resp_post.status_code = 200
        resp_post.is_error = False
        resp_post.json.return_value = {
            "id": 501,
            "workspaceId": 123,
            "templateName": "Social Native",
        }
        mock_client.post.return_value = resp_post

        # 2. Mock PUT /api/storyboards/501 update response
        resp_put = MagicMock()
        resp_put.status_code = 200
        resp_put.is_error = False
        resp_put.json.return_value = {
            "id": 501,
            "workspaceId": 123,
            "templateName": "Social Native",
            "scenes": [],
        }
        mock_client.put.return_value = resp_put

        storyboard_dict = {
            "template_name": "Social Native",
            "campaign_title": "Summer Campaign",
            "scenes": [
                {
                    "topic": "Scene 1",
                    "video_prompt": {
                        "description": "Zoom in",
                        "asset_ref": {
                            "id": "302",
                            "asset_type": "generated",
                            "workspace_id": "123",
                        },
                    },
                    "first_frame_prompt": {
                        "description": "Start logo",
                        "asset_ref": {
                            "id": "101",
                            "asset_type": "uploaded",
                            "workspace_id": "123",
                        },
                    },
                }
            ],
        }

        saved = await cs_storyboard_service.save_storyboard(storyboard_dict)

        assert isinstance(saved, dict)
        assert saved["storyboard_id"] == "501"
        mock_client.post.assert_called_once()
        mock_client.put.assert_called_once()

        # Verify normalized fields sent in PUT body
        put_kwargs = mock_client.put.call_args.kwargs
        sent_payload = put_kwargs["json"]["storyboard"]
        scene_sent = sent_payload["scenes"][0]

        # Generated video asset -> HAS media_item_id, NO asset_id/source_asset_id
        assert scene_sent["video_prompt"]["media_item_id"] == 302
        assert "asset_id" not in scene_sent["video_prompt"]
        assert "source_asset_id" not in scene_sent["video_prompt"]

        # Uploaded first_frame asset -> HAS source_asset_id, NO media_item_id
        assert scene_sent["first_frame_prompt"]["source_asset_id"] == 101
        assert "media_item_id" not in scene_sent["first_frame_prompt"]


@pytest.mark.asyncio
async def test_get_storyboard_hydration(cs_storyboard_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock GET response with both generated (media_item_id) and uploaded (source_asset_id) assets
        resp_get = MagicMock()
        resp_get.status_code = 200
        resp_get.is_error = False
        resp_get.json.return_value = {
            "id": 501,
            "workspace_id": 123,
            "template_name": "Social Native",
            "scenes": [
                {
                    "id": 1,
                    "topic": "Intro",
                    "duration_seconds": 5.0,
                    "first_frame_description": "Logo frame",
                    "first_frame_source_asset_id": 101,
                    "video_description": "Cinematic shot",
                    "video_media_item_id": 302,
                    "voiceover_text": "Welcome to our product",
                    "voiceover_media_item_id": 401,
                    "transition_type": "fade",
                    "transition_duration": 0.5,
                    "audio_ambient_description": "Rain sounds",
                    "audio_sfx_description": "Whoosh",
                }
            ],
        }
        mock_client.get.return_value = resp_get

        sb = await cs_storyboard_service.get_storyboard("501")
        assert sb is not None
        assert sb["storyboard_id"] == "501"

        hydrated_scene = sb["scenes"][0]
        # First frame is uploaded source_asset_id -> HAS asset_id & asset_ref(uploaded), NO media_item_id
        assert hydrated_scene["first_frame_prompt"]["asset_id"] == "101"
        assert hydrated_scene["first_frame_prompt"]["source_asset_id"] == "101"
        assert "media_item_id" not in hydrated_scene["first_frame_prompt"]
        assert hydrated_scene["first_frame_prompt"]["asset_ref"] == {
            "id": "101",
            "asset_type": "uploaded",
            "workspace_id": "123",
        }

        # Video is generated media_item_id -> HAS media_item_id & asset_ref(generated), NO asset_id/source_asset_id
        assert hydrated_scene["video_prompt"]["media_item_id"] == "302"
        assert "asset_id" not in hydrated_scene["video_prompt"]
        assert "source_asset_id" not in hydrated_scene["video_prompt"]
        assert hydrated_scene["video_prompt"]["asset_ref"] == {
            "id": "302",
            "asset_type": "generated",
            "workspace_id": "123",
        }

        # Voiceover is generated media_item_id
        assert hydrated_scene["voiceover_prompt"]["media_item_id"] == "401"
        assert hydrated_scene["voiceover_prompt"]["asset_ref"] == {
            "id": "401",
            "asset_type": "generated",
            "workspace_id": "123",
        }


@pytest.mark.asyncio
async def test_list_and_delete_storyboard(cs_storyboard_service):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        resp_list = MagicMock()
        resp_list.status_code = 200
        resp_list.is_error = False
        resp_list.json.return_value = [{"id": 501, "templateName": "Social Native"}]
        mock_client.get.return_value = resp_list

        items = await cs_storyboard_service.list_storyboards(workspace_id="123")
        assert len(items) == 1

        resp_del = MagicMock()
        resp_del.status_code = 200
        resp_del.is_error = False
        mock_client.delete.return_value = resp_del

        await cs_storyboard_service.delete_storyboard("501")
        mock_client.delete.assert_called_once()
