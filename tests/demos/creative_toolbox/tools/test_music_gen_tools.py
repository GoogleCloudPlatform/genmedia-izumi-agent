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

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


@pytest.mark.asyncio
@patch("creative_toolbox.tools.music_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_music_with_lyria_success(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    mock_service = AsyncMock()
    mock_get_media_gen_service.return_value = mock_service

    mock_asset = MagicMock()
    mock_asset.file_name = "test_music.wav"
    mock_service.generate_music_with_lyria.return_value = mock_asset

    from creative_toolbox.tools.music_gen_tools import generate_music_with_lyria

    result = await generate_music_with_lyria(
        mock_tool_context, prompt="upbeat jazz", file_name="jazz.wav", model="lyria-002"
    )

    assert "Music saved as asset with file name: test_music.wav" in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.music_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_music_with_lyria_unsupported_model_fallback(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    mock_service = AsyncMock()
    mock_get_media_gen_service.return_value = mock_service

    mock_asset = MagicMock()
    mock_asset.file_name = "fallback_music.wav"
    mock_service.generate_music_with_lyria.return_value = mock_asset

    from creative_toolbox.tools.music_gen_tools import generate_music_with_lyria

    result = await generate_music_with_lyria(
        mock_tool_context, prompt="rock", file_name="rock.wav", model="unsupported-model"
    )

    assert "Music saved as asset with file name: fallback_music.wav" in result
    assert "Warning: Unsupported model 'unsupported-model' was provided" in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.music_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_music_with_lyria_failure(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    mock_service = AsyncMock()
    mock_get_media_gen_service.return_value = mock_service
    mock_service.generate_music_with_lyria.side_effect = Exception("Generation failed")

    from creative_toolbox.tools.music_gen_tools import generate_music_with_lyria

    result = await generate_music_with_lyria(
        mock_tool_context, prompt="fail", file_name="fail.wav", model="lyria-002"
    )

    assert "Error generating music with Lyria: Generation failed" in result
