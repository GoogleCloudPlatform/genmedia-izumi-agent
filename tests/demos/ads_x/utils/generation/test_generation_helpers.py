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
    mock_mediagen.generate_music.return_value = mock_asset

    music_prompt = {"description": "Upbeat jazz"}
    result = await generate_background_music("user1", music_prompt)

    assert result == mock_asset
    assert music_prompt["asset_id"] == "music_123"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_background_music_does_not_pin_a_model(
    mock_get_asset_service,
    mock_get_media_gen_service,
):
    """The model pinned here overrode the configured one, so the music model
    could not be changed from config."""
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "music_123"
    mock_mediagen.generate_music.return_value = mock_asset

    await generate_background_music("user1", {"description": "Upbeat jazz"})

    assert "model" not in mock_mediagen.generate_music.call_args.kwargs


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_background_music_failure(
    mock_get_media_gen_service,
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen

    mock_mediagen.generate_music.side_effect = Exception("API Error")

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
    mock_asset.duration_seconds = 3.0
    mock_mediagen.generate_speech.return_value = mock_asset

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
    mock_asset_long.duration_seconds = 10.0

    mock_asset_short = MagicMock(spec=Asset)
    mock_asset_short.id = "voice_short"
    mock_asset_short.duration_seconds = 3.0

    # First call returns long asset, second returns short asset
    mock_mediagen.generate_speech.side_effect = [
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


def test_clamp_duration_keeps_what_omni_can_render():
    """Omni renders any whole second from 3 to 10, so nothing is rounded up."""
    assert clamp_duration(3, model="gemini-omni-flash-preview") == 3
    assert clamp_duration(5, model="gemini-omni-flash-preview") == 5
    assert clamp_duration(7, model="gemini-omni-flash-preview") == 7
    # Outside Omni's range it still has to be fitted.
    assert clamp_duration(2, model="gemini-omni-flash-preview") == 3
    assert clamp_duration(12, model="gemini-omni-flash-preview") == 10


def test_clamp_duration_is_unchanged_for_veo():
    assert clamp_duration(3, model="veo-3.1-generate-001") == 4
    assert clamp_duration(5, model="veo-3.1-generate-001") == 6
    assert clamp_duration(7, model="veo-3.1-generate-001") == 8


# ---------------------------------------------------------------------------
# Instrumental beds
#
# Lyria 3 renders vocals when a prompt invites them, and vocals compete with
# the voiceover they play beneath. Constraining the presets is insufficient:
# the storyboard agent copies the sonic landscape into the music brief and may
# rephrase it, so the constraint is applied where every prompt passes.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_music_is_asked_for_without_vocals(
    mock_get_asset_service, mock_get_media_gen_service
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "music_1"
    mock_mediagen.generate_music.return_value = mock_asset

    brief = {"description": "Nostalgic Folk: acoustic guitar, warm"}
    await generate_background_music("user1", brief)

    sent = mock_mediagen.generate_music.call_args.kwargs["prompt"]
    assert "no vocals" in sent
    assert "no singing" in sent
    # The stored brief is shown to the reviewer at the storyboard checkpoint
    # and is therefore left unchanged.
    assert brief["description"] == "Nostalgic Folk: acoustic guitar, warm"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_the_constraint_is_not_repeated_on_a_re_render(
    mock_get_asset_service, mock_get_media_gen_service
):
    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "music_1"
    mock_mediagen.generate_music.return_value = mock_asset

    from demos.backend.ads_x.utils.generation.generation_helpers import (
        _as_instrumental,
    )

    once = _as_instrumental("acoustic guitar")
    assert _as_instrumental(once) == once


def test_simplified_brief_keeps_the_style_and_drops_the_imagery():
    from demos.backend.ads_x.utils.generation.generation_helpers import (
        _simplified_music_brief,
    )

    simplified = _simplified_music_brief(
        "Industrial Minimalist: rhythmic metallic pings, deep sub-bass pulses, "
        "clean silence, transitioning into high-energy driving synth beats."
    )
    assert simplified.startswith("Industrial Minimalist instrumental background")
    assert "metallic pings" not in simplified
    assert "no vocals" in simplified

    # A connective introduces the imagery, so the phrase ends before it.
    assert _simplified_music_brief(
        "Aspirational athletic minimalist track featuring rhythmic breath-like swells"
    ).startswith("Aspirational athletic minimalist track instrumental")

    # Nothing usable left to try.
    assert _simplified_music_brief("") == ""
    assert _simplified_music_brief(",,,") == ""


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_a_refused_music_brief_is_retried_in_plainer_words(
    mock_get_asset_service, mock_get_media_gen_service
):
    """Lyria 3 refuses some elaborate briefs on policy grounds. The refusal is
    a property of the wording, so the retry has to reword rather than repeat."""
    from mediagent_kit.utils.retry import ContentBlockedError

    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "music_1"
    mock_mediagen.generate_music.side_effect = [
        ContentBlockedError("refused"),
        mock_asset,
    ]

    brief = {
        "description": (
            "Industrial Minimalist: rhythmic metallic pings, deep sub-bass "
            "pulses, transitioning into high-energy driving synth beats."
        )
    }
    result = await generate_background_music("user1", brief)

    assert result == mock_asset
    assert brief["asset_id"] == "music_1"
    assert mock_mediagen.generate_music.call_count == 2
    retried = mock_mediagen.generate_music.call_args_list[1].kwargs["prompt"]
    assert retried.startswith("Industrial Minimalist instrumental background")


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_a_brief_refused_twice_leaves_the_campaign_without_music(
    mock_get_asset_service, mock_get_media_gen_service
):
    from mediagent_kit.utils.retry import ContentBlockedError

    mock_mediagen = AsyncMock()
    mock_get_media_gen_service.return_value = mock_mediagen
    mock_mediagen.generate_music.side_effect = ContentBlockedError("refused")

    brief = {"description": "Industrial Minimalist: metallic pings"}
    result = await generate_background_music("user1", brief)

    assert result is None
    assert brief["asset_id"] is None
    assert mock_mediagen.generate_music.call_count == 2
