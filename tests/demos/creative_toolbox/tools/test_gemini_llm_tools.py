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

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from google.adk.tools import ToolContext


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


@pytest.mark.asyncio
@patch("creative_toolbox.tools.gemini_llm_tools.genai.Client")
@patch("creative_toolbox.tools.gemini_llm_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_creative_writer_with_gemini_success(
    mock_get_asset_service,
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    # Mock GenAI Client
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    # Mock async generate_content
    mock_response = MagicMock()
    mock_response.text = "Generated creative text"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    from creative_toolbox.tools.gemini_llm_tools import creative_writer_with_gemini

    result_str = await creative_writer_with_gemini(
        mock_tool_context, request="Write a story about a cat", reference_files=""
    )
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert result["writer_result"] == "Generated creative text"


@pytest.mark.asyncio
@patch("creative_toolbox.tools.gemini_llm_tools.genai.Client")
@patch("creative_toolbox.tools.gemini_llm_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_creative_writer_with_gemini_with_references(
    mock_get_asset_service,
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    # Mock Asset Service
    mock_assets = AsyncMock()
    mock_get_asset_service.return_value = mock_assets

    mock_asset = MagicMock()
    mock_asset.id = "asset_1"
    mock_assets.get_asset_by_file_name.return_value = mock_asset

    mock_blob = MagicMock()
    mock_blob.content = b"fake image content"
    mock_blob.mime_type = "image/png"
    mock_assets.get_asset_blob.return_value = mock_blob

    # Mock GenAI Client
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Generated text from image"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    from creative_toolbox.tools.gemini_llm_tools import creative_writer_with_gemini

    result_str = await creative_writer_with_gemini(
        mock_tool_context, request="Describe this image", reference_files="img1.png"
    )
    result = json.loads(result_str)

    assert result["status"] == "success"
    assert result["writer_result"] == "Generated text from image"


@pytest.mark.asyncio
@patch("creative_toolbox.tools.gemini_llm_tools.genai.Client")
@patch("creative_toolbox.tools.gemini_llm_tools.get_user_id_from_context")
async def test_creative_writer_with_gemini_failure(
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    # Mock GenAI Client to raise exception
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("API Error")
    )

    from creative_toolbox.tools.gemini_llm_tools import creative_writer_with_gemini

    result_str = await creative_writer_with_gemini(
        mock_tool_context, request="Failing request", reference_files=""
    )
    result = json.loads(result_str)

    assert result["status"] == "failure"
    assert "API Error" in result["error_message"]


@pytest.mark.asyncio
@patch("creative_toolbox.tools.gemini_llm_tools.genai.Client")
@patch("creative_toolbox.tools.gemini_llm_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_creative_writer_with_gemini_asset_not_found(
    mock_get_asset_service,
    mock_get_user_id,
    mock_genai_client_class,
    mock_tool_context,
):
    mock_get_user_id.return_value = "user_123"

    # Mock Asset Service to return None
    mock_assets = AsyncMock()
    mock_get_asset_service.return_value = mock_assets
    mock_assets.get_asset_by_file_name.return_value = None

    from creative_toolbox.tools.gemini_llm_tools import creative_writer_with_gemini

    result_str = await creative_writer_with_gemini(
        mock_tool_context, request="Describe this image", reference_files="missing.png"
    )
    result = json.loads(result_str)

    assert result["status"] == "failure"
    assert "Could not find reference file asset" in result["error_message"]


@pytest.mark.asyncio
@patch("creative_toolbox.tools.gemini_llm_tools.config.settings")
async def test_creative_writer_with_gemini_missing_env_vars(
    mock_settings,
    mock_tool_context,
):
    # Mock settings to be empty or missing
    mock_settings.GOOGLE_CLOUD_PROJECT = None
    mock_settings.GOOGLE_CLOUD_LOCATION = None

    from creative_toolbox.tools.gemini_llm_tools import creative_writer_with_gemini

    with pytest.raises(ValueError) as exc_info:
        await creative_writer_with_gemini(
            mock_tool_context, request="Write a story", reference_files=""
        )
    assert "Missing required environment variables" in str(exc_info.value)
