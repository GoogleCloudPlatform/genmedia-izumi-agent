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

"""Tests for Creative Studio service stubs and factory integration."""

import pytest

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import (
    CSAssetService,
    CSCanvasService,
    CSMediaGenerationService,
    CSStoryboardService,
    CSTimelineService,
    ServiceFactory,
)
from mediagent_kit.services.errors import UnsupportedFeatureError
from mediagent_kit.services.interfaces import (
    AssetServiceInterface,
    HtmlCanvasServiceInterface,
    MediaGenerationServiceInterface,
    StoryboardServiceInterface,
    VideoTimelineServiceInterface,
)
from mediagent_kit.utils.context import (
    get_request_context,
    reset_request_context,
    set_request_context,
)


def test_cs_services_instantiation():
    """Verify CS service stubs instantiate and satisfy interface typing."""
    asset_svc = CSAssetService(workspace_id="ws_123", user_auth_token="token_abc")
    canvas_svc = CSCanvasService(workspace_id="ws_123", user_auth_token="token_abc")
    timeline_svc = CSTimelineService(workspace_id="ws_123", user_auth_token="token_abc")
    storyboard_svc = CSStoryboardService(
        workspace_id="ws_123", user_auth_token="token_abc"
    )
    media_svc = CSMediaGenerationService(
        workspace_id="ws_123", user_auth_token="token_abc"
    )

    assert isinstance(asset_svc, AssetServiceInterface)
    assert isinstance(canvas_svc, HtmlCanvasServiceInterface)
    assert isinstance(timeline_svc, VideoTimelineServiceInterface)
    assert isinstance(storyboard_svc, StoryboardServiceInterface)
    assert isinstance(media_svc, MediaGenerationServiceInterface)


@pytest.mark.asyncio
async def test_cs_canvas_service_unsupported():
    """Verify CSCanvasService raises UnsupportedFeatureError on create_canvas."""
    canvas_svc = CSCanvasService(workspace_id="ws_123", user_auth_token="token_abc")
    with pytest.raises(UnsupportedFeatureError):
        await canvas_svc.create_canvas(
            workspace_id="ws_123", html_content="<div></div>"
        )


def test_request_context_propagation():
    """Verify set_request_context and get_request_context work as expected."""
    tok = set_request_context(user_auth_token="auth_xyz", workspace_id="ws_999")
    ctx = get_request_context()
    assert ctx is not None
    assert ctx["user_auth_token"] == "auth_xyz"
    assert ctx["workspace_id"] == "ws_999"
    reset_request_context(tok)
    assert get_request_context() is None


def test_service_factory_cs_mode():
    """Verify ServiceFactory vends CS service stubs when use_creative_studio is True."""
    config = MediagentKitConfig(use_creative_studio=True)
    factory = ServiceFactory(config=config)

    tok = set_request_context(user_auth_token="auth_456", workspace_id="ws_789")

    asset_svc = factory.get_asset_service()
    assert isinstance(asset_svc, CSAssetService)
    assert asset_svc._workspace_id == "ws_789"
    assert asset_svc._user_auth_token == "auth_456"

    canvas_svc = factory.get_canvas_service()
    assert isinstance(canvas_svc, CSCanvasService)

    media_svc = factory.get_media_generation_service()
    assert isinstance(media_svc, CSMediaGenerationService)

    timeline_svc = factory.get_timeline_service()
    assert isinstance(timeline_svc, CSTimelineService)

    storyboard_svc = factory.get_storyboard_service()
    assert isinstance(storyboard_svc, CSStoryboardService)

    reset_request_context(tok)


def test_service_factory_custom_token_key():
    """Verify ServiceFactory extracts token using cs_user_auth_token_key configuration."""
    config = MediagentKitConfig(
        use_creative_studio=True, cs_user_auth_token_key="custom_auth_key"
    )
    factory = ServiceFactory(config=config)

    # Context with non-default token key
    tok = set_request_context(user_auth_token=None, workspace_id="ws_custom")
    # Simulate custom token key in context
    ctx = get_request_context()
    ctx["custom_auth_key"] = "custom_secret_777"

    asset_svc = factory.get_asset_service()
    assert isinstance(asset_svc, CSAssetService)
    assert asset_svc._workspace_id == "ws_custom"
    assert asset_svc._user_auth_token == "custom_secret_777"

    reset_request_context(tok)


@pytest.mark.asyncio
async def test_cs_media_generation_service_music_aliasing():
    """Verify CSMediaGenerationService normalizes 'lyria' to 'lyria-002'."""
    from unittest.mock import AsyncMock, MagicMock, patch

    media_svc = CSMediaGenerationService(
        workspace_id="123", user_auth_token="token_abc"
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Mock POST /api/audios/generate
        resp_post = MagicMock()
        resp_post.status_code = 200
        resp_post.json.return_value = {"id": "audio_999"}
        mock_client.post.return_value = resp_post

        # Mock polling via _wait_for_media_completion
        media_svc._wait_for_media_completion = AsyncMock(
            return_value={
                "id": "audio_999",
                "status": "completed",
                "gcsUris": ["gs://bucket/audio.mp3"],
                "durationSeconds": 30.0,
            }
        )

        await media_svc.generate_music(
            workspace_id="123",
            prompt="upbeat beat",
            model="lyria",
            duration_seconds=30,
            file_name="test.mp3",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["model"] == "lyria-002"
