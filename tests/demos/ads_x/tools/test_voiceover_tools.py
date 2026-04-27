import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture
def mock_mediagen_service():
    service = MagicMock()
    service.generate_text_with_gemini = AsyncMock()
    service.generate_speech_single_speaker = AsyncMock()
    return service


@pytest.fixture
def mock_asset_service():
    service = MagicMock()
    service.get_asset_blob = AsyncMock()
    service.get_asset = AsyncMock()
    return service


def test_rewrite_group_script_success(mock_mediagen_service, mock_asset_service):
    from demos.backend.ads_x.tools.generation.voiceover_tools import (
        rewrite_group_script,
    )
    from demos.backend.ads_x.utils.storyboard.storyboard_model import (
        VoiceoverGroup,
    )

    group = VoiceoverGroup(
        group_id="test_group",
        scene_indices=[0, 1],
        original_scripts=["Hello", "World"],
        total_duration=6.0,
        narrative_block="BODY",
    )

    mock_response_asset = MagicMock()
    mock_response_asset.id = "response_asset_id"
    mock_mediagen_service.generate_text_with_gemini.return_value = mock_response_asset

    mock_blob = MagicMock()
    mock_blob.content = b"Rewritten script text."
    mock_asset_service.get_asset_blob.return_value = mock_blob

    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_mediagen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):

            import asyncio

            result = asyncio.run(rewrite_group_script("user_123", group))

            assert result == "Rewritten script text."
            mock_mediagen_service.generate_text_with_gemini.assert_called_once()
            mock_asset_service.get_asset_blob.assert_called_once_with(
                "response_asset_id"
            )


def test_generate_group_voiceover_success(mock_mediagen_service, mock_asset_service):
    from demos.backend.ads_x.tools.generation.voiceover_tools import (
        generate_group_voiceover,
    )
    from demos.backend.ads_x.utils.storyboard.storyboard_model import (
        VoiceoverGroup,
    )

    group = VoiceoverGroup(
        group_id="test_group",
        scene_indices=[0, 1],
        original_scripts=["Hello", "World"],
        total_duration=6.0,
        narrative_block="BODY",
    )

    # Mock rewrite_group_script to return a string
    with patch(
        "demos.backend.ads_x.tools.generation.voiceover_tools.rewrite_group_script",
        new_callable=AsyncMock,
    ) as mock_rewrite:
        mock_rewrite.return_value = "Rewritten script"

        mock_voiceover_asset = MagicMock()
        mock_voiceover_asset.id = "voiceover_asset_id"
        mock_version = MagicMock()
        mock_version.duration_seconds = 5.0
        mock_voiceover_asset.versions = [mock_version]
        mock_mediagen_service.generate_speech_single_speaker.return_value = (
            mock_voiceover_asset
        )

        with patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_mediagen_service,
        ):

            import asyncio

            result = asyncio.run(generate_group_voiceover("user_123", group))

            assert result == mock_voiceover_asset
            assert group.audio_asset_id == "voiceover_asset_id"
            assert group.rewritten_script == "Rewritten script"
