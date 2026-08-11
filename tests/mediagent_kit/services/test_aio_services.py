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

"""Tests for AsyncMediaGenerationService delegation logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mediagent_kit.services.aio.async_services import AsyncMediaGenerationService
from mediagent_kit.services.creative_studio.cs_media_generation_service import (
    CSMediaGenerationService,
)


@pytest.mark.asyncio
async def test_async_media_gen_service_cs_delegation():
    """Verify AsyncMediaGenerationService directly awaits CSMediaGenerationService methods."""
    cs_svc = MagicMock(spec=CSMediaGenerationService)
    cs_svc.generate_text = AsyncMock(return_value="rewritten prompt text")
    cs_svc.generate_image = AsyncMock(return_value="mock_generated_image_asset")
    cs_svc.generate_video = AsyncMock(return_value="mock_generated_video_asset")
    cs_svc.generate_speech = AsyncMock(return_value="mock_generated_speech_asset")
    cs_svc.generate_music = AsyncMock(return_value="mock_generated_music_asset")

    async_svc = AsyncMediaGenerationService(sync_service=cs_svc)

    text_res = await async_svc.generate_text(workspace_id="ws_1", prompt="test prompt")
    assert text_res == "rewritten prompt text"
    cs_svc.generate_text.assert_awaited_once_with(
        workspace_id="ws_1", prompt="test prompt"
    )

    img_res = await async_svc.generate_image(
        workspace_id="ws_1",
        prompt="test image",
        generation_model="imagen-4.0-generate-001",
        aspect_ratio="16:9",
        resolution="1K",
        file_name="img.png",
    )
    assert img_res == "mock_generated_image_asset"
    cs_svc.generate_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_media_gen_service_native_delegation():
    """The native (legacy) media service is adapted via
    IzumiMediaGenerationService: unified generate_text maps workspace_id->
    user_id, resolves the legacy generator, and returns the text inline
    (read back from the persisted asset) rather than forwarding unified
    kwargs straight to the legacy method."""
    from types import SimpleNamespace

    sync_svc = MagicMock()
    sync_svc.generate_text_with_gemini.return_value = SimpleNamespace(id="t1")
    sync_svc._asset_service.get_asset_blob.return_value = SimpleNamespace(
        content=b"sync_legacy_text"
    )

    async_svc = AsyncMediaGenerationService(sync_service=sync_svc)

    res = await async_svc.generate_text(workspace_id="ws_1", prompt="test sync")
    assert res == "sync_legacy_text"
    _, kwargs = sync_svc.generate_text_with_gemini.call_args
    assert kwargs["user_id"] == "ws_1"
    assert kwargs["prompt"] == "test sync"
    assert kwargs["reference_image_filenames"] == []
