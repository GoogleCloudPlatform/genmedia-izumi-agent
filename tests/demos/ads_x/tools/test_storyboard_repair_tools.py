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

            mock_mediagen_service.generate_text = AsyncMock(
                return_value=json.dumps(valid_storyboard)
            )

            import asyncio

            result = asyncio.run(
                finalize_and_persist_storyboard(mock_tool_context, truncated_json)
            )

            assert result["status"] == "succeeded"
            mock_mediagen_service.generate_text.assert_called_once()


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


def test_finalize_and_persist_storyboard_injects_session_id(mock_tool_context):
    from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
        finalize_and_persist_storyboard,
    )
    from demos.backend.ads_x.utils.common import common_utils

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
                    "text": "Welcome",
                    "gender": "female",
                    "description": "Happy",
                },
            },
            {
                "topic": "Outro",
                "duration_seconds": 3.0,
                "first_frame_prompt": {"description": "F4"},
                "video_prompt": {"description": "V4", "duration_seconds": 3.0},
                "voiceover_prompt": {
                    "text": "Bye",
                    "gender": "female",
                    "description": "Happy",
                },
            },
        ],
    }

    mock_tool_context.state["workspace_id"] = "123"
    mock_tool_context._invocation_context.session.id = "session_test_999"

    import asyncio

    result = asyncio.run(
        finalize_and_persist_storyboard(mock_tool_context, json.dumps(valid_storyboard))
    )

    assert result["status"] == "succeeded"
    assert common_utils.STORYBOARD_KEY in mock_tool_context.state
    sb_dump = mock_tool_context.state[common_utils.STORYBOARD_KEY]
    assert sb_dump["session_id"] == "session_test_999"
    assert sb_dump["workspace_id"] == "123"


def test_finalize_and_persist_storyboard_drops_llm_id(mock_tool_context):
    from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
        finalize_and_persist_storyboard,
    )
    from demos.backend.ads_x.utils.common import common_utils

    storyboard_with_hallucinated_ids = {
        "storyboard_id": "sb_mountain_car_adventure",
        "id": "100",
        "current_storyboard_id": "100",
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

    import asyncio

    result = asyncio.run(
        finalize_and_persist_storyboard(
            mock_tool_context, json.dumps(storyboard_with_hallucinated_ids)
        )
    )

    assert result["status"] == "succeeded"
    sb_dump = mock_tool_context.state[common_utils.STORYBOARD_KEY]
    assert sb_dump.get("storyboard_id") is None
    assert "id" not in sb_dump or sb_dump.get("id") is None
    assert (
        "current_storyboard_id" not in sb_dump
        or sb_dump.get("current_storyboard_id") is None
    )
