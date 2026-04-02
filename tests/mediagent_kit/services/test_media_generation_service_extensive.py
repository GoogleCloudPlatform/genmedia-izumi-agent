# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import pytest
from unittest.mock import MagicMock, patch
from mediagent_kit.config import MediagentKitConfig

@pytest.fixture
def mock_asset_service():
    return MagicMock()

@pytest.fixture
def mock_config():
    config = MagicMock(spec=MediagentKitConfig)
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    return config


def test_generate_speech_multiple_speaker_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    # Mock texttospeech_v1beta1
    with patch("mediagent_kit.services.media_generation_service.texttospeech_v1beta1.TextToSpeechClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.audio_content = b"fake_audio_bytes"
        mock_client.synthesize_speech.return_value = mock_response

        # Mock save_asset
        mock_asset_service.save_asset.return_value = "saved_audio_asset"

        markup = '[{"text": "Hello", "speaker": "Achernar"}]'
        result = service.generate_speech_multiple_speaker(
            user_id="user_123",
            file_name="test.mp3",
            multi_speaker_markup=markup,
        )

        assert result == "saved_audio_asset"
        mock_asset_service.save_asset.assert_called_once()


def test_generate_speech_multiple_speaker_invalid_json(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    with pytest.raises(ValueError, match="Invalid multi_speaker_markup format"):
        service.generate_speech_multiple_speaker(
            user_id="user_123",
            file_name="test.mp3",
            multi_speaker_markup="invalid json",
        )


@patch("mediagent_kit.services.media_generation_service.time.sleep") # Prevent sleeping in tests
def test_generate_video_with_veo_success(mock_sleep, mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    # Mock GenAI Client
    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)
    
    # Mock operation
    mock_operation = MagicMock()
    mock_operation.done = False
    
    # We need to simulate polling. First call done=False, second call done=True.
    # operation = client.operations.get(operation)
    # So we need to mock client.operations.get to return a NEW operation or the same one with done=True.
    
    mock_operation_done = MagicMock()
    mock_operation_done.done = True
    mock_operation_done.error = None
    
    mock_response = MagicMock()
    mock_video = MagicMock()
    mock_video.video_bytes = b"fake_video_bytes"
    mock_generated_video = MagicMock()
    mock_generated_video.video = mock_video
    mock_operation_done.result.generated_videos = [mock_generated_video]
    mock_operation_done.response = True # Just to pass the if check
    
    # client.models.generate_videos returns operation
    mock_client.models.generate_videos.return_value = mock_operation
    # client.operations.get returns mock_operation_done
    mock_client.operations.get.return_value = mock_operation_done

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_video_asset"

    result = service.generate_video_with_veo(
        user_id="user_123",
        file_name="test.mp4",
        prompt="A dog running",
    )

    assert result == "saved_video_asset"
    mock_asset_service.save_asset.assert_called_once()
    mock_sleep.assert_called_once_with(15) # Verified it polled once


@patch("mediagent_kit.services.media_generation_service.time.sleep")
def test_generate_video_with_veo_error(mock_sleep, mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService
    
    service = MediaGenerationService(asset_service=mock_asset_service, config=mock_config)
    
    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)
    
    mock_operation = MagicMock()
    mock_operation.done = True
    mock_operation.error = "Some severe error"
    
    mock_client.models.generate_videos.return_value = mock_operation

    with pytest.raises(ValueError, match="Video generation failed with error"):
        service.generate_video_with_veo(
            user_id="user_123",
            file_name="test.mp4",
            prompt="A dog running",
        )
