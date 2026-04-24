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

"""Unit tests for common utilities."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from ads_codirector.utils import common_utils
from google.adk.models.llm_request import LlmRequest
from google.genai import types


@pytest.mark.asyncio
async def test_json_repair():
    """Verify that malformed JSON can be repaired via Gemini mock."""
    malformed = '{"key": "value", "missing_brace": '
    fixed = {"key": "value", "missing_brace": "fixed"}
    mock_mediagen = MagicMock()
    mock_mediagen.generate_text_with_gemini = AsyncMock(
        return_value=MagicMock(id="rep_id")
    )
    mock_asset = MagicMock()
    mock_asset.get_asset_blob = AsyncMock(
        return_value=MagicMock(content=b'{"key": "value", "missing_brace": "fixed"}')
    )
    with (
        patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_mediagen,
        ),
        patch("mediagent_kit.services.aio.get_asset_service", return_value=mock_asset),
    ):
        result = await common_utils.repair_json_with_gemini("user_id", malformed)
        assert result == fixed


def test_describe_pydantic_model():
    """Verify that pydantic model descriptions are generated correctly."""
    from ads_codirector.utils.parameters_model import Parameters

    desc = common_utils.describe_pydantic_model(Parameters)
    assert "brand" in desc
    assert "product" in desc
    assert "target_duration" in desc


@pytest.mark.asyncio
async def test_store_user_input_callback():
    """Verify that user input is correctly stored in session state."""
    ctx = MagicMock()
    ctx.state = {}
    request = LlmRequest(
        contents=[
            types.Content(role="user", parts=[types.Part(text="Hello World")]),
            types.Content(
                role="user", parts=[types.Part(text="For context: ignore me")]
            ),
        ]
    )
    await common_utils.store_user_input_model_callback(ctx, request)
    assert ctx.state[common_utils.USER_INPUT_KEY] == "Hello World"
    assert common_utils.STORYBOARD_KEY in ctx.state


@pytest.mark.asyncio
async def test_prompt_logging_callback():
    """Verify that the prompt logging callback correctly extracts text and system instruction."""
    ctx = MagicMock()
    ctx.agent_name = "test_agent"
    # Case 1: String system instruction
    request = LlmRequest(
        config=types.GenerateContentConfig(system_instruction="System Rules"),
        contents=[
            types.Content(role="user", parts=[types.Part(text="Prompt Part 1")]),
            types.Content(role="model", parts=[types.Part(text="Assistant context")]),
        ],
    )
    with patch("ads_codirector.utils.common_utils.logger") as mock_logger:
        await common_utils.prompt_logging_callback(ctx, request)
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        assert "test_agent" in log_msg
        assert "[SYSTEM INSTRUCTION]\nSystem Rules" in log_msg
        assert "Prompt Part 1" in log_msg
        assert "Assistant context" in log_msg
        assert "[USER]" in log_msg
        assert "[MODEL]" in log_msg

    # Case 2: Content object system instruction
    request_content = LlmRequest(
        config=types.GenerateContentConfig(
            system_instruction=types.Content(parts=[types.Part(text="Complex Rules")])
        ),
        contents=[
            types.Content(role="user", parts=[types.Part(text="Prompt Part 2")]),
        ],
    )
    with patch("ads_codirector.utils.common_utils.logger") as mock_logger:
        await common_utils.prompt_logging_callback(ctx, request_content)
        log_msg = mock_logger.info.call_args[0][0]
        assert "[SYSTEM INSTRUCTION]\nComplex Rules" in log_msg
        assert "Prompt Part 2" in log_msg
