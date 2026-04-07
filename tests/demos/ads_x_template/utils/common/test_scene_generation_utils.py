import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ads_x_template.utils.common.scene_generation_utils import (
    generate_scene_first_frame,
    generate_scene_video,
)


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch(
    "ads_x_template.utils.common.enrichment_utils.enrich_prompt_with_llm",
    new_callable=AsyncMock,
)
async def test_generate_scene_first_frame_success(
    mock_enrich_prompt, mock_get_media_gen_service
):
    mock_media_gen_service = MagicMock()
    mock_get_media_gen_service.return_value = mock_media_gen_service

    mock_asset = MagicMock()
    mock_asset.id = "asset_id_123"

    mock_media_gen_service.generate_image_with_gemini = AsyncMock(
        return_value=mock_asset
    )
    mock_enrich_prompt.return_value = ("Enriched prompt", "enrich_id_456")

    first_frame_prompt = {"description": "Original prompt"}

    result_asset, result_prompt = await generate_scene_first_frame(
        user_id="user_123",
        first_frame_prompt=first_frame_prompt,
        index=1,
        aspect_ratio="16:9",
        on_screen_text_hint="Text hint",
    )

    assert result_asset == mock_asset
    assert result_prompt == "Enriched prompt"
    assert first_frame_prompt["asset_id"] == "asset_id_123"
    assert first_frame_prompt["enrichment_asset_id"] == "enrich_id_456"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_scene_video_success(mock_get_media_gen_service):
    mock_media_gen_service = MagicMock()
    mock_get_media_gen_service.return_value = mock_media_gen_service

    mock_asset = MagicMock()
    mock_asset.file_name = "scene_1_video.mp4"

    mock_media_gen_service.generate_video_with_veo = AsyncMock(return_value=mock_asset)

    scene = {"first_frame_prompt": {"assets": []}}
    first_frame_asset = MagicMock()
    first_frame_asset.file_name = "scene_1_first_frame.png"

    result = await generate_scene_video(
        user_id="user_123",
        scene=scene,
        index=1,
        valid_duration=5.0,
        aspect_ratio="16:9",
        allow_veo_audio=True,
        veo_method="rectified_flow",
        first_frame_asset=first_frame_asset,
        final_video_prompt="Final prompt",
    )

    assert result == mock_asset


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
@patch(
    "ads_x_template.utils.common.enrichment_utils.enrich_prompt_with_llm",
    new_callable=AsyncMock,
)
async def test_generate_scene_first_frame_failure(
    mock_enrich_prompt, mock_get_media_gen_service
):
    mock_media_gen_service = MagicMock()
    mock_get_media_gen_service.return_value = mock_media_gen_service

    # Force failure
    mock_media_gen_service.generate_image_with_gemini = AsyncMock(
        side_effect=Exception("Gen failure")
    )
    mock_enrich_prompt.return_value = ("Enriched prompt", None)

    with pytest.raises(Exception) as exc_info:
        await generate_scene_first_frame(
            user_id="user_123",
            first_frame_prompt={"description": "Original"},
            index=1,
            aspect_ratio="16:9",
        )
    assert "Failed to generate valid first frame" in str(exc_info.value)


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_scene_video_failure(mock_get_media_gen_service):
    mock_media_gen_service = MagicMock()
    mock_get_media_gen_service.return_value = mock_media_gen_service

    mock_media_gen_service.generate_video_with_veo = AsyncMock(
        side_effect=Exception("Veo failure")
    )

    scene = {"first_frame_prompt": {"assets": []}}
    first_frame_asset = MagicMock()
    first_frame_asset.file_name = "scene_1_first_frame.png"

    with pytest.raises(Exception) as exc_info:
        await generate_scene_video(
            user_id="user_123",
            scene=scene,
            index=1,
            valid_duration=5.0,
            aspect_ratio="16:9",
            allow_veo_audio=True,
            veo_method="rectified_flow",
            first_frame_asset=first_frame_asset,
            final_video_prompt="Final prompt",
        )
    assert "Failed to generate valid video clip" in str(exc_info.value)


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_scene_video_reference_to_video(mock_get_media_gen_service):
    mock_media_gen_service = MagicMock()
    mock_get_media_gen_service.return_value = mock_media_gen_service

    mock_asset = MagicMock()
    mock_media_gen_service.generate_video_with_veo = AsyncMock(return_value=mock_asset)

    scene = {"first_frame_prompt": {"assets": ["other.png"]}}
    first_frame_asset = MagicMock()
    first_frame_asset.file_name = "scene_1_first_frame.png"

    await generate_scene_video(
        user_id="user_123",
        scene=scene,
        index=1,
        valid_duration=5.0,
        aspect_ratio="16:9",
        allow_veo_audio=True,
        veo_method="reference_to_video",
        first_frame_asset=first_frame_asset,
        final_video_prompt="Final prompt",
    )

    # Verify first_frame_asset.file_name was prepended
    call_args = mock_media_gen_service.generate_video_with_veo.call_args[1]
    assert call_args["reference_image_filenames"][0] == "scene_1_first_frame.png"
