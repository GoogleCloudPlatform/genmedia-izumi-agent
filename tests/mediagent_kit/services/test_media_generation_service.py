import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from mediagent_kit.config import MediagentKitConfig

@pytest.fixture
def mock_asset_service():
    service = MagicMock() # AssetService is synchronous in its base definition, wait, let's check if it's AsyncAssetService or AssetService.
    # In media_generation_service.py it imports AssetService from mediagent_kit.services.asset_service.
    # Let's assume it's synchronous for now, or mock it as MagicMock.
    return service

@pytest.fixture
def mock_config():
    config = MagicMock(spec=MediagentKitConfig)
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    return config


def test_get_genai_client_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    client = service._get_genai_client()
    
    assert client is not None


def test_get_genai_client_missing_config(mock_asset_service):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    config = MagicMock(spec=MediagentKitConfig)
    config.google_cloud_project = None
    config.google_cloud_location = None
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=config)
    
    with pytest.raises(ValueError, match="Missing required environment variables"):
        service._get_genai_client()


@patch("mediagent_kit.services.media_generation_service.genai.Client")
def test_generate_image_with_imagen_success(
    mock_genai_client_class,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    # Mock GenAI Client
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # Mock response
    mock_response = MagicMock()
    mock_image = MagicMock()
    mock_image.image_bytes = b"fake_image_bytes"
    mock_image.mime_type = "image/png"
    mock_generated_image = MagicMock()
    mock_generated_image.image = mock_image
    mock_response.generated_images = [mock_generated_image]
    mock_client.models.generate_images.return_value = mock_response

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_asset"

    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    result = service.generate_image_with_imagen(
        user_id="user_123",
        file_name="test.png",
        prompt="A beautiful sunset",
    )

    assert result == "saved_asset"
    mock_asset_service.save_asset.assert_called_once()


@patch("mediagent_kit.services.media_generation_service.texttospeech.TextToSpeechClient")
def test_generate_speech_single_speaker_success(
    mock_tts_client_class,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    mock_client = MagicMock()
    mock_tts_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.audio_content = b"fake_audio_bytes"
    mock_client.synthesize_speech.return_value = mock_response

    mock_asset_service.save_asset.return_value = "saved_audio_asset"

    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    result = service.generate_speech_single_speaker(
        user_id="user_123",
        file_name="test.mp3",
        text="Hello world",
        voice_name="Achernar",
    )

    assert result == "saved_audio_asset"
    mock_asset_service.save_asset.assert_called_once()


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
@patch("mediagent_kit.services.media_generation_service.convert_wav_blob_to_mp3_blob")
def test_generate_music_with_lyria_success(
    mock_convert_wav,
    mock_auth_default,
    mock_requests_post,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    import base64

    # Mock auth
    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")

    # Mock requests.post response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "predictions": [
            {"bytesBase64Encoded": base64.b64encode(b"fake_music_bytes").decode("utf-8")}
        ]
    }
    mock_requests_post.return_value = mock_response

    # Mock convert_wav
    mock_convert_wav.return_value = b"fake_mp3_bytes"

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_music_asset"

    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)

    result = service.generate_music_with_lyria(
        user_id="user_123",
        file_name="test.mp3",
        prompt="Upbeat electronic music",
    )

    assert result == "saved_music_asset"
    mock_asset_service.save_asset.assert_called_once()
    mock_convert_wav.assert_called_once_with(b"fake_music_bytes")


def test_generate_text_with_gemini_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    # Mock _get_asset via asset_service
    mock_asset = MagicMock()
    mock_version = MagicMock()
    mock_version.gcs_uri = "gs://test-bucket/test.png"
    mock_asset.current = mock_version
    mock_asset.mime_type = "image/png"
    mock_asset_service.get_asset_by_file_name.return_value = mock_asset

    # Mock _generate_gemini_text_content
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Generated text response"
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = None # No block
    service._generate_gemini_text_content = MagicMock(return_value=mock_response)

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_text_asset"

    result = service.generate_text_with_gemini(
        user_id="user_123",
        file_name="test.txt",
        prompt="Describe this image",
        reference_image_filenames=["ref.png"],
    )

    assert result == "saved_text_asset"
    mock_asset_service.save_asset.assert_called_once()
    mock_asset_service.get_asset_by_file_name.assert_called_once_with(
        user_id="user_123", file_name="ref.png"
    )


def test_generate_text_with_gemini_blocked(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)
    
    mock_response = MagicMock()
    mock_response.prompt_feedback.block_reason.name = "SAFETY"
    service._generate_gemini_text_content = MagicMock(return_value=mock_response)

    with pytest.raises(ValueError, match="Text generation failed. The prompt was blocked"):
        service.generate_text_with_gemini(
            user_id="user_123",
            file_name="test.txt",
            prompt="Some prompt",
            reference_image_filenames=[],
        )


def test_generate_image_with_gemini_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    # Mock _get_asset via asset_service
    mock_asset = MagicMock()
    mock_version = MagicMock()
    mock_version.gcs_uri = "gs://test-bucket/test.png"
    mock_asset.current = mock_version
    mock_asset.mime_type = "image/png"
    mock_asset_service.get_asset_by_file_name.return_value = mock_asset

    # Mock _generate_gemini_image_content
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"fake_image_bytes"
    mock_part.inline_data.mime_type = "image/png"
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = None
    service._generate_gemini_image_content = MagicMock(return_value=mock_response)

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_image_asset"

    result = service.generate_image_with_gemini(
        user_id="user_123",
        file_name="test.png",
        prompt="A beautiful sunset",
        reference_image_filenames=["ref.png"],
    )

    assert result == "saved_image_asset"
    mock_asset_service.save_asset.assert_called_once()


def test_generate_image_with_gemini_blocked(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)
    
    # Mock response
    mock_response = MagicMock()
    mock_response.prompt_feedback.block_reason.name = "SAFETY"
    service._generate_gemini_image_content = MagicMock(return_value=mock_response)

    with pytest.raises(ValueError, match="Image generation failed. The prompt was blocked"):
        service.generate_image_with_gemini(
            user_id="user_123",
            file_name="test.png",
            prompt="Some prompt",
            reference_image_filenames=[],
        )
