import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from demos.backend.ads_x.utils.generation.generation_helpers import (
    generate_background_music,
    generate_scene_voiceover,
    build_global_context_string,
    clamp_duration,
)
from mediagent_kit.services.types import Asset


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_background_music_success(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "music_123"
    mock_mediagen.generate_music_with_lyria.return_value = mock_asset

    music_prompt = {"description": "Upbeat jazz"}
    result = await generate_background_music("user1", music_prompt)

    assert result == mock_asset
    assert music_prompt["asset_id"] == "music_123"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_background_music_failure(
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_mediagen.generate_music_with_lyria.side_effect = Exception("API Error")

    music_prompt = {"description": "Upbeat jazz"}
    result = await generate_background_music("user1", music_prompt)

    assert result is None
    assert music_prompt["asset_id"] is None


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_generate_scene_voiceover_success(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "voice_123"
    # Mock duration
    mock_version = MagicMock()
    mock_version.duration_seconds = 3.0
    mock_asset.versions = [mock_version]
    mock_mediagen.generate_speech_single_speaker.return_value = mock_asset

    voice_prompt = {"text": "Hello world", "gender": "male"}
    result = await generate_scene_voiceover("user1", voice_prompt, index=0)

    assert result == mock_asset
    assert voice_prompt["asset_id"] == "voice_123"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch(
    "demos.backend.ads_x.utils.common.enrichment_utils.shorten_script",
    new_callable=AsyncMock,
)
async def test_generate_scene_voiceover_too_long_shorten(
    mock_shorten_script,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_asset_long = MagicMock(spec=Asset)
    mock_asset_long.id = "voice_long"
    mock_version_long = MagicMock()
    mock_version_long.duration_seconds = 10.0
    mock_asset_long.versions = [mock_version_long]

    mock_asset_short = MagicMock(spec=Asset)
    mock_asset_short.id = "voice_short"
    mock_version_short = MagicMock()
    mock_version_short.duration_seconds = 3.0
    mock_asset_short.versions = [mock_version_short]

    # First call returns long asset, second returns short asset
    mock_mediagen.generate_speech_single_speaker.side_effect = [
        mock_asset_long,
        mock_asset_short,
    ]
    mock_shorten_script.return_value = "Short text"

    voice_prompt = {"text": "Very long text", "gender": "female"}
    result = await generate_scene_voiceover(
        "user1", voice_prompt, index=0, target_duration=4.0
    )

    assert result == mock_asset_short
    assert voice_prompt["asset_id"] == "voice_short"
    assert voice_prompt["text"] == "Short text"
    mock_shorten_script.assert_called_once()


def test_build_global_context_string():
    storyboard = {
        "campaign_theme": "Summer Sale",
        "campaign_tone": "Exciting",
        "concept_description": "Concept",
        "key_message": "Key",
        "global_visual_style": "Bright",
        "global_setting": "Beach",
        "target_audience_profile": "All",
        "brand_voice_keywords": ["Fast", "Fun"],
    }
    scene = {"establishment_shot": "Wide beach", "narrative_action": "People running"}

    result = build_global_context_string(storyboard, scene)

    assert "Summer Sale" in result
    assert "Wide beach" in result
    assert "People running" in result


def test_clamp_duration():
    assert clamp_duration(3) == 4
    assert clamp_duration(5) == 6
    assert clamp_duration(7) == 8
    assert clamp_duration(10) == 8
