import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from google.adk.tools import ToolContext

@pytest.fixture
def mock_tool_context():
    return MagicMock(spec=ToolContext)


@pytest.fixture
def mock_media_generation_service():
    return AsyncMock()


@pytest.mark.asyncio
@patch("creative_toolbox.tools.image_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_image_with_imagen_success(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "test_image.png"
    mock_media_generation_service.generate_image_with_imagen.return_value = mock_asset

    from creative_toolbox.tools.image_gen_tools import generate_image_with_imagen

    result = await generate_image_with_imagen(
        mock_tool_context,
        prompt="A beautiful sunset",
        aspect_ratio="16:9",
        model="imagen-4.0-generate-001",
        file_name="test_image.png",
    )

    assert "Image saved as asset with file name: test_image.png" in result
    mock_media_generation_service.generate_image_with_imagen.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        aspect_ratio="16:9",
        model="imagen-4.0-generate-001",
        file_name="test_image.png",
    )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.image_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_image_with_imagen_fallback(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "test_image.png"
    mock_media_generation_service.generate_image_with_imagen.return_value = mock_asset

    from creative_toolbox.tools.image_gen_tools import generate_image_with_imagen

    result = await generate_image_with_imagen(
        mock_tool_context,
        prompt="A beautiful sunset",
        aspect_ratio="invalid_ratio",
        model="invalid_model",
        file_name="test_image.png",
    )

    assert "Image saved as asset with file name: test_image.png" in result
    assert "Warning: Unsupported model 'invalid_model' was provided. Fell back to default model 'imagen-4.0-generate-001'." in result
    assert "Unsupported aspect ratio 'invalid_ratio' was provided. Fell back to default aspect ratio '1:1'." in result
    
    # Verify it was called with fallbacks
    mock_media_generation_service.generate_image_with_imagen.assert_called_once_with(
        user_id="user_123",
        prompt="A beautiful sunset",
        aspect_ratio="1:1",
        model="imagen-4.0-generate-001",
        file_name="test_image.png",
    )


@pytest.mark.asyncio
@patch("creative_toolbox.tools.image_gen_tools.get_user_id_from_context")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_generate_image_with_gemini_success(
    mock_get_media_gen_service,
    mock_get_user_id,
    mock_tool_context,
    mock_media_generation_service,
):
    mock_get_user_id.return_value = "user_123"
    mock_get_media_gen_service.return_value = mock_media_generation_service

    mock_asset = MagicMock()
    mock_asset.file_name = "test_gemini.png"
    mock_media_generation_service.generate_image_with_gemini.return_value = mock_asset

    from creative_toolbox.tools.image_gen_tools import generate_image_with_gemini

    result = await generate_image_with_gemini(
        mock_tool_context,
        prompt="A futuristic city",
        aspect_ratio="16:9",
        file_name="test_gemini.png",
        reference_image_1_filename="ref1.png",
    )

    assert "Image saved as asset with file name: test_gemini.png" in result
    mock_media_generation_service.generate_image_with_gemini.assert_called_once_with(
        user_id="user_123",
        prompt="A futuristic city",
        aspect_ratio="16:9",
        file_name="test_gemini.png",
        reference_image_filenames=["ref1.png", "", "", ""],
    )
