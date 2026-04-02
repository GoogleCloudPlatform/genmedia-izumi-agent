import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from google.adk.tools import ToolContext

@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    return context


@pytest.fixture
def mock_media_generation_service():
    return AsyncMock()


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_success(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    # Mock media generation service response
    mock_asset = MagicMock()
    mock_asset.file_name = "generated_video.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = mock_asset

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    result = await generate_video_with_veo(
        mock_tool_context,
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )

    assert "Video saved as asset with file name: generated_video.mp4" in result
    mock_media_generation_service.generate_video_with_veo.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        model="veo-3.1-generate-001",
        first_frame_filename="",
        last_frame_filename="",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_unsupported_model_fallback(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "fallback_video.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = mock_asset

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    result = await generate_video_with_veo(
        mock_tool_context,
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        model="unsupported-model",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )

    assert "Video saved as asset with file name: fallback_video.mp4" in result
    assert "Unsupported model 'unsupported-model'. Fell back to default model 'veo-3.1-generate-001'." in result
    mock_media_generation_service.generate_video_with_veo.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        model="veo-3.1-generate-001", # Fallback!
        first_frame_filename="",
        last_frame_filename="",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_missing_first_frame_for_last_frame(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    with pytest.raises(ValueError, match="A first frame.*is required"):
        await generate_video_with_veo(
            mock_tool_context,
            prompt="A beautiful sunset",
            file_name="sunset.mp4",
            aspect_ratio="16:9",
            duration_seconds=5,
            resolution="720p",
            generate_audio=True,
            last_frame_filename="last.png", # Provided last frame but no first frame!
        )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_service_failure(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    # Mock service to raise ValueError
    mock_media_generation_service.generate_video_with_veo.side_effect = ValueError("Service failure")

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    result = await generate_video_with_veo(
        mock_tool_context,
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )

    assert "Error generating video with Veo: Service failure" in result


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_unsupported_resolution_and_aspect_ratio_fallback(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "fallback_params.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = mock_asset

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    result = await generate_video_with_veo(
        mock_tool_context,
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        aspect_ratio="unsupported-aspect",
        duration_seconds=5,
        resolution="unsupported-res",
        generate_audio=True,
    )

    assert "Video saved as asset with file name: fallback_params.mp4" in result
    assert "Unsupported resolution 'unsupported-res'. Fell back to default resolution '720p'." in result
    assert "Unsupported aspect ratio 'unsupported-aspect'. Fell back to default aspect ratio '16:9'." in result
    
    mock_media_generation_service.generate_video_with_veo.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        model="veo-3.1-generate-001",
        first_frame_filename="",
        last_frame_filename="",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.video_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_video_with_veo_none_params(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "none_params.mp4"
    mock_media_generation_service.generate_video_with_veo.return_value = mock_asset

    from creative_toolbox.tools.video_gen_tools import generate_video_with_veo

    result = await generate_video_with_veo(
        mock_tool_context,
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        first_frame_filename=None,
        last_frame_filename=None,
        generate_audio=None,
    )

    assert "Video saved as asset with file name: none_params.mp4" in result
    
    mock_media_generation_service.generate_video_with_veo.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        file_name="sunset.mp4",
        model="veo-3.1-generate-001",
        first_frame_filename="",
        last_frame_filename="",
        aspect_ratio="16:9",
        duration_seconds=5,
        resolution="720p",
        generate_audio=True,
    )
