import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from demos.backend.ads_x.utils.common.enrichment_utils import (
    enrich_prompt_with_llm,
    shorten_script,
)


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

    # Mock generate_text
    mock_mediagen.generate_text.return_value = "Enriched prompt text"

    prompt_data = {
        "cinematography": {
            "camera_description": "Close up",
            "lens_specification": "50mm",
            "lighting_description": "Daylight",
            "velocity_hint": "Slow",
            "mood": ["Dramatic"],
        },
        "audio": {"dialogue_hint": "Hello"},
        "on_screen_text_hint": "Buy now",
    }

    enriched_text, asset_id = await enrich_prompt_with_llm(
        workspace_id="workspace_1",
        description="A dog running",
        prompt_data=prompt_data,
        scene_index=0,
        prompt_type="video",
        context="Some context",
        is_ugc=True,
    )

    assert enriched_text == "Enriched prompt text"
    assert asset_id is None
    mock_mediagen.generate_text.assert_called_once()


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
    mock_mediagen.generate_text.side_effect = Exception("API Error")

    prompt_data = {
        "cinematography": {"camera_description": "Pan"},
        "audio": {},
    }

    enriched_text, asset_id = await enrich_prompt_with_llm(
        workspace_id="workspace_1",
        description="A dog running",
        prompt_data=prompt_data,
        scene_index=0,
        prompt_type="image",
        context="Some context",
        is_ugc=False,
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

    mock_mediagen.generate_text.return_value = "Shortened text"

    mock_blob = MagicMock()
    mock_blob.content = b"Shortened text"
    mock_asset_service.get_asset_blob.return_value = mock_blob

    result = await shorten_script("Long text", 10.0, workspace_id="workspace_1")

    assert result == "Shortened text"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_shorten_script_failure_fallback(
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_mediagen.generate_text.side_effect = Exception("API Error")

    result = await shorten_script("Long text", 10.0, workspace_id="workspace_1")

    assert result == "Long text"


# ---------------------------------------------------------------------------
# Brand mark fidelity
#
# The enrichment prompt requires every art-direction anchor to be woven into
# the description, including "Aesthetic". Applied without qualification, that
# directs the renderer to restyle a supplied brand mark in the Look's palette.
# The palette applies to the scene around the mark, not to the mark itself.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_the_logo_is_exempt_from_the_palette(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_get_asset_service.return_value = AsyncMock()
    mock_mediagen.generate_text.return_value = "Enriched prompt text"

    await enrich_prompt_with_llm(
        "workspace-1",
        "The brand logo on a clean surface. [ART DIRECTION (NON-NEGOTIABLE) -> "
        "Aesthetic: Deep mahogany, brushed gold, velvet textures]",
        {},
        scene_index=0,
        prompt_type="image",
    )

    sent = mock_mediagen.generate_text.call_args.kwargs["prompt"]
    assert "BRAND MARK FIDELITY" in sent
    # The rule must place the mark out of scope for the palette, not merely
    # sit alongside the instruction that applies it.
    assert "never the mark" in sent
    assert "recolour" in sent


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_the_product_surface_is_out_of_scope_for_enrichment(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    """The reference image is the authority on how the product looks.

    Enrichment adds cinematic language, and applied to a product's own surface
    that language invents detail the reference does not show: a plain brushed
    tin acquires filigree once the prompt calls it 'finely detailed'.
    """
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_get_asset_service.return_value = AsyncMock()
    mock_mediagen.generate_text.return_value = "Enriched prompt text"

    await enrich_prompt_with_llm(
        "workspace-1",
        "The product on a clean surface. [ART DIRECTION (NON-NEGOTIABLE) -> "
        "Aesthetic: Deep mahogany, brushed gold, velvet textures]",
        {},
        scene_index=0,
        prompt_type="image",
    )

    sent = mock_mediagen.generate_text.call_args.kwargs["prompt"]
    assert "PRODUCT FIDELITY" in sent
    # The scene may be embellished; the product's own surface may not.
    assert "never the product itself" in sent
    for banned in ("engraving", "embossing", "ornate", "finely detailed"):
        assert banned in sent, f"{banned} is not named as out of bounds"
