import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from demos.backend.ads_x_template.utils.common.enrichment_utils import enrich_prompt_with_llm, shorten_script

@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_enrich_prompt_with_llm_success(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_asset_service = AsyncMock()
    mock_get_asset_service.return_value = mock_asset_service

    # Mock generate_text_with_gemini
    mock_asset = MagicMock()
    mock_asset.id = "asset_123"
    mock_mediagen.generate_text_with_gemini.return_value = mock_asset

    # Mock get_asset_blob
    mock_blob = MagicMock()
    mock_blob.content = b"Enriched prompt text"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    prompt_data = {
        "cinematography": {
            "camera_description": "Close up",
            "lens_specification": "50mm",
            "lighting_description": "Daylight",
            "velocity_hint": "Slow",
            "mood": ["Dramatic"]
        },
        "audio": {
            "dialogue_hint": "Hello"
        },
        "on_screen_text_hint": "Buy now"
    }

    enriched_text, asset_id = await enrich_prompt_with_llm(
        user_id="user1",
        description="A dog running",
        prompt_data=prompt_data,
        scene_index=0,
        prompt_type="video",
        context="Some context",
        is_ugc=True
    )

    assert enriched_text == "Enriched prompt text"
    assert asset_id == "asset_123"
    mock_mediagen.generate_text_with_gemini.assert_called_once()


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_enrich_prompt_with_llm_failure_fallback(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    # Simulate failure
    mock_mediagen.generate_text_with_gemini.side_effect = Exception("API Error")

    prompt_data = {
        "cinematography": {"camera_description": "Pan"},
        "audio": {},
    }

    enriched_text, asset_id = await enrich_prompt_with_llm(
        user_id="user1",
        description="A dog running",
        prompt_data=prompt_data,
        scene_index=0,
        prompt_type="image",
        context="Some context",
        is_ugc=False
    )

    # Fallback should be used
    assert asset_id is None
    assert "Camera: Pan" in enriched_text
    assert "Action: A dog running" in enriched_text


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_shorten_script_success(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_asset_service = AsyncMock()
    mock_get_asset_service.return_value = mock_asset_service

    mock_asset = MagicMock()
    mock_asset.id = "asset_short"
    mock_mediagen.generate_text_with_gemini.return_value = mock_asset

    mock_blob = MagicMock()
    mock_blob.content = b"Shortened text"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    result = await shorten_script("Long text", 10.0, "user1")

    assert result == "Shortened text"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_shorten_script_failure_fallback(
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_mediagen.generate_text_with_gemini.side_effect = Exception("API Error")

    result = await shorten_script("Long text", 10.0, "user1")

    assert result == "Long text"
