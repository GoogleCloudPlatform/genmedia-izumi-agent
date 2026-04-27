import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
    return context


@pytest.fixture
def mock_mediagen_service():
    service = MagicMock()
    service.generate_text_with_gemini = AsyncMock()
    return service


@pytest.fixture
def mock_asset_service():
    service = MagicMock()
    service.get_asset_blob = AsyncMock()
    return service


def test_finalize_and_persist_storyboard_valid(mock_tool_context):
    from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
        finalize_and_persist_storyboard,
    )

    valid_storyboard = {
        "campaign_title": "Test Campaign",
        "scenes": [
            {
                "topic": "Intro",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F1"},
                "video_prompt": {"description": "V1", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Hello",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "Body 1",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F2"},
                "video_prompt": {"description": "V2", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "World",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "Body 2",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F3"},
                "video_prompt": {"description": "V3", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Foo",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "CTA",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F4"},
                "video_prompt": {"description": "V4", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Bar",
                    "gender": "female",
                    "description": "Happy",
                },
            },
        ],
    }
    raw_output = json.dumps(valid_storyboard)

    import asyncio

    result = asyncio.run(finalize_and_persist_storyboard(mock_tool_context, raw_output))

    assert result["status"] == "succeeded"
    assert "Validated & Synchronized" in result["result"]
    assert "storyboard" in mock_tool_context.state


def test_finalize_and_persist_storyboard_repair(
    mock_tool_context, mock_mediagen_service, mock_asset_service
):
    from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
        finalize_and_persist_storyboard,
    )

    truncated_json = '{"campaign_title": "Test Campaign", "scenes": ['  # Invalid JSON

    valid_storyboard = {
        "campaign_title": "Test Campaign",
        "scenes": [
            {
                "topic": "Intro",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F1"},
                "video_prompt": {"description": "V1", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Hello",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "Body 1",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F2"},
                "video_prompt": {"description": "V2", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "World",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "Body 2",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F3"},
                "video_prompt": {"description": "V3", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Foo",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "CTA",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F4"},
                "video_prompt": {"description": "V4", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Bar",
                    "gender": "female",
                    "description": "Happy",
                },
            },
        ],
    }

    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_mediagen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):

            mock_repair_result = MagicMock()
            mock_repair_result.id = "repair_id"
            mock_mediagen_service.generate_text_with_gemini.return_value = (
                mock_repair_result
            )

            mock_blob = MagicMock()
            mock_blob.content = json.dumps(valid_storyboard).encode()
            mock_asset_service.get_asset_blob.return_value = mock_blob

            import asyncio

            result = asyncio.run(
                finalize_and_persist_storyboard(mock_tool_context, truncated_json)
            )

            assert result["status"] == "succeeded"
            mock_mediagen_service.generate_text_with_gemini.assert_called_once()


def test_finalize_and_persist_storyboard_validation_failure(mock_tool_context):
    from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
        finalize_and_persist_storyboard,
    )

    # Missing required scenes
    invalid_storyboard = {"campaign_title": "Test Campaign", "scenes": []}
    raw_output = json.dumps(invalid_storyboard)

    import asyncio

    result = asyncio.run(finalize_and_persist_storyboard(mock_tool_context, raw_output))

    assert result["status"] == "failed"
    assert "validation failed" in result["error_message"]
