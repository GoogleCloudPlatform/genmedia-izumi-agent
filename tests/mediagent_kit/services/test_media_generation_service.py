import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_asset_service():
    service = (
        MagicMock()
    )  # AssetService is synchronous in its base definition, wait, let's check if it's AsyncAssetService or AssetService.
    # In media_generation_service.py it imports AssetService from mediagent_kit.services.asset_service.
    # Let's assume it's synchronous for now, or mock it as MagicMock.
    return service


@pytest.fixture
def mock_config():
    config = MagicMock(spec=MediagentKitConfig)
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    config.models = {
        "text": {"default": "gemini-2.5-flash"},
        "image_imagen": {"default": "imagen-4.0-generate-001"},
        "image_gemini": {"default": "gemini-3.1-flash-image"},
        "video": {"default": "veo-3.1-generate-001"},
        "music": {"default": "lyria-002"},
        "tts": {"default": "gemini-2.5-pro-tts"},
    }
    return config


def test_get_genai_client_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )
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

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

    result = service.generate_image_with_imagen(
        user_id="user_123",
        file_name="test.png",
        prompt="A beautiful sunset",
    )

    assert result == "saved_asset"
    mock_asset_service.save_asset.assert_called_once()


@patch(
    "mediagent_kit.services.media_generation_service.texttospeech.TextToSpeechClient"
)
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

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

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
            {
                "bytesBase64Encoded": base64.b64encode(b"fake_music_bytes").decode(
                    "utf-8"
                )
            }
        ]
    }
    mock_requests_post.return_value = mock_response

    # Mock convert_wav
    mock_convert_wav.return_value = b"fake_mp3_bytes"

    # Mock save_asset
    mock_asset_service.save_asset.return_value = "saved_music_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

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

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

    # Mock _get_asset via asset_service
    mock_asset = MagicMock()
    mock_version = MagicMock()
    mock_version.gcs_uri = "gs://test-bucket/test.png"
    mock_asset.current = mock_version
    mock_asset.mime_type = "image/png"
    mock_asset_service.get_asset_by_file_name.return_value = mock_asset

    # Mock _generate_gemini_text_content.
    # part.thought is explicitly False so this part is classified as a
    # response part, not a thought part (default include_thoughts=False
    # behavior). Without this, MagicMock's auto-attribute would make
    # part.thought truthy and the text would be routed to thoughts_text,
    # leaving generated_text empty and triggering "No text was generated".
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Generated text response"
    mock_part.thought = False
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = None  # No block
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

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)

    mock_response = MagicMock()
    mock_response.prompt_feedback.block_reason.name = "SAFETY"
    service._generate_gemini_text_content = MagicMock(return_value=mock_response)

    with pytest.raises(
        ValueError, match="Text generation failed. The prompt was blocked"
    ):
        service.generate_text_with_gemini(
            user_id="user_123",
            file_name="test.txt",
            prompt="Some prompt",
            reference_image_filenames=[],
        )


def test_generate_image_with_gemini_success(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

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

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

    mock_client = MagicMock()
    service._get_genai_client = MagicMock(return_value=mock_client)

    # Mock response
    mock_response = MagicMock()
    mock_response.prompt_feedback.block_reason.name = "SAFETY"
    service._generate_gemini_image_content = MagicMock(return_value=mock_response)

    # ContentBlockedError rather than a bare ValueError: the refusal depends on
    # the prompt, so a caller recovers by rewording rather than by repeating.
    from mediagent_kit.utils.retry import ContentBlockedError

    with pytest.raises(
        ContentBlockedError, match="Image generation failed. The prompt was blocked"
    ):
        service.generate_image_with_gemini(
            user_id="user_123",
            file_name="test.png",
            prompt="Some prompt",
            reference_image_filenames=[],
        )


def test_generate_text_with_gemini_with_purpose(mock_asset_service, mock_config):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_config.models = {
        "text": {"default": "gemini-2.5-flash", "repair": "gemini-2.5-pro"}
    }

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )

    # part.thought is explicitly False so this part is classified as a
    # response part, not a thought part. See the note in
    # test_generate_text_with_gemini_success for details.
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Generated text response"
    mock_part.thought = False
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = None

    mock_generate = MagicMock(return_value=mock_response)
    service._generate_gemini_text_content = mock_generate

    mock_asset_service.save_asset.return_value = "saved_text_asset"

    result = service.generate_text_with_gemini(
        user_id="user_123",
        file_name="test.txt",
        prompt="Describe this image",
        purpose="repair",
    )

    assert result == "saved_text_asset"
    args, kwargs = mock_generate.call_args
    assert kwargs["model"] == "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# Lyria 3
#
# Lyria 3 is a different API to Lyria 2, not a new model id on the same one:
# the interactions resource rather than :predict, audio among `outputs` rather
# than `predictions`, and MP3 rather than WAV.
# ---------------------------------------------------------------------------


@pytest.fixture
def lyria3_config(mock_config):
    mock_config.models = dict(
        mock_config.models, music={"default": "lyria-3-clip-preview"}
    )
    return mock_config


def _lyria3_response(status="completed"):
    import base64

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "status": status,
        "outputs": [
            {"type": "text", "text": "some generated lyrics"},
            {
                "type": "audio",
                "mime_type": "audio/mpeg",
                "data": base64.b64encode(b"fake_mp3_bytes").decode("utf-8"),
            },
        ],
    }
    return response


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
@patch("mediagent_kit.services.media_generation_service.convert_wav_blob_to_mp3_blob")
def test_generate_music_with_lyria3_uses_interactions_endpoint(
    mock_convert_wav,
    mock_auth_default,
    mock_requests_post,
    mock_asset_service,
    lyria3_config,
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _lyria3_response()
    mock_asset_service.save_asset.return_value = "saved_music_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=lyria3_config
    )
    result = service.generate_music_with_lyria(
        user_id="user_123", file_name="test.mp3", prompt="Warm cinematic strings"
    )

    assert result == "saved_music_asset"

    url = mock_requests_post.call_args.args[0]
    assert url == (
        "https://aiplatform.googleapis.com/v1beta1/projects/test-project"
        "/locations/global/interactions"
    )
    # Global endpoint, so no regional host prefix.
    assert "us-central1-aiplatform" not in url

    body = mock_requests_post.call_args.kwargs["json"]
    assert body == {
        "model": "lyria-3-clip-preview",
        "input": [{"type": "text", "text": "Warm cinematic strings"}],
    }


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
@patch("mediagent_kit.services.media_generation_service.convert_wav_blob_to_mp3_blob")
def test_lyria3_output_is_not_run_through_the_wav_converter(
    mock_convert_wav,
    mock_auth_default,
    mock_requests_post,
    mock_asset_service,
    lyria3_config,
):
    """Lyria 3 already returns MP3; converting it as WAV would corrupt it."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _lyria3_response()
    mock_asset_service.save_asset.return_value = "saved_music_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=lyria3_config
    )
    service.generate_music_with_lyria(
        user_id="user_123", file_name="test.mp3", prompt="Warm cinematic strings"
    )

    mock_convert_wav.assert_not_called()
    saved = mock_asset_service.save_asset.call_args.kwargs
    assert saved["blob"] == b"fake_mp3_bytes"
    assert saved["mime_type"] == "audio/mpeg"


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
@patch("mediagent_kit.services.media_generation_service.convert_wav_blob_to_mp3_blob")
def test_lyria3_drops_a_negative_prompt_it_cannot_send(
    mock_convert_wav,
    mock_auth_default,
    mock_requests_post,
    mock_asset_service,
    lyria3_config,
):
    """Lyria 3 has no negative_prompt, and folding it into the prompt would
    ask for the very thing it excludes."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _lyria3_response()
    mock_asset_service.save_asset.return_value = "saved_music_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=lyria3_config
    )
    service.generate_music_with_lyria(
        user_id="user_123",
        file_name="test.mp3",
        prompt="Warm cinematic strings",
        negative_prompt="drums",
    )

    body = mock_requests_post.call_args.kwargs["json"]
    assert "negative_prompt" not in body
    assert "drums" not in body["input"][0]["text"]


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
def test_lyria3_reports_an_unfinished_interaction_as_such(
    mock_auth_default,
    mock_requests_post,
    mock_asset_service,
    lyria3_config,
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    response = _lyria3_response(status="running")
    response.json.return_value["outputs"] = []
    mock_requests_post.return_value = response

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=lyria3_config
    )

    with pytest.raises(Exception, match="not 'completed'"):
        service._call_lyria3_api(model="lyria-3-clip-preview", prompt="strings")


@patch(
    "mediagent_kit.services.media_generation_service.texttospeech.TextToSpeechClient"
)
def test_speech_names_a_quota_project(
    mock_tts_client_class, mock_asset_service, mock_config
):
    """Cloud TTS 403s on user credentials that carry no quota project, which
    reads as though the API were disabled."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.audio_content = b"fake_audio"
    mock_client.synthesize_speech.return_value = mock_response
    mock_tts_client_class.return_value = mock_client
    mock_asset_service.save_asset.return_value = "saved_speech_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )
    service.generate_speech_single_speaker(
        user_id="user_123", file_name="vo.mp3", text="Hello", voice_name="Achernar"
    )

    assert mock_tts_client_class.call_args.kwargs["client_options"] == {
        "quota_project_id": "test-project"
    }


# ---------------------------------------------------------------------------
# Gemini Omni Flash video
#
# Omni speaks the interactions API, renders any duration from 3 to 10 seconds,
# and scores every clip whether asked to or not. Veo does none of those things,
# so the two share an entry point and nothing else.
# ---------------------------------------------------------------------------


@pytest.fixture
def omni_config(mock_config):
    mock_config.models = dict(
        mock_config.models, video={"default": "gemini-omni-flash-preview"}
    )
    return mock_config


def _omni_response(status="completed"):
    import base64

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "status": status,
        "steps": [
            {"type": "thought", "summary": [{"type": "text", "text": "thinking"}]},
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "video",
                        "mime_type": "video/mp4",
                        "data": base64.b64encode(b"fake_mp4_with_audio").decode(
                            "utf-8"
                        ),
                    }
                ],
            },
        ],
    }
    return response


@patch("mediagent_kit.services.media_generation_service.strip_audio_from_video_blob")
@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
def test_omni_video_uses_the_interactions_endpoint(
    mock_auth_default, mock_requests_post, mock_strip, mock_asset_service, omni_config
):
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _omni_response()
    mock_strip.return_value = b"silent_mp4"
    mock_asset_service.save_asset.return_value = "saved_video_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=omni_config
    )
    result = service.generate_video_with_veo(
        user_id="user_1", file_name="scene.mp4", prompt="A bottle on a counter"
    )

    assert result == "saved_video_asset"
    url = mock_requests_post.call_args.args[0]
    assert url == (
        "https://aiplatform.googleapis.com/v1beta1/projects/test-project"
        "/locations/global/interactions"
    )
    body = mock_requests_post.call_args.kwargs["json"]
    assert body["model"] == "gemini-omni-flash-preview"
    assert body["generation_config"]["video_config"]["task"] == "text_to_video"


@patch("mediagent_kit.services.media_generation_service.strip_audio_from_video_blob")
@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
def test_omni_renders_the_duration_asked_for(
    mock_auth_default, mock_requests_post, mock_strip, mock_asset_service, omni_config
):
    """Veo would round 3s up to 4s and trim the tail; Omni just renders 3s."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _omni_response()
    mock_strip.return_value = b"silent_mp4"
    mock_asset_service.save_asset.return_value = "saved_video_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=omni_config
    )
    service.generate_video_with_veo(
        user_id="user_1",
        file_name="scene.mp4",
        prompt="A bottle",
        duration_seconds=3,
    )

    body = mock_requests_post.call_args.kwargs["json"]
    assert body["response_format"][0]["duration"] == "3s"


@patch("mediagent_kit.services.media_generation_service.strip_audio_from_video_blob")
@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
def test_omni_audio_is_stripped_because_it_cannot_be_declined(
    mock_auth_default, mock_requests_post, mock_strip, mock_asset_service, omni_config
):
    """Omni has no parameter to suppress audio, and the pipeline lays its own
    voiceover and music over the finished cut."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")
    mock_requests_post.return_value = _omni_response()
    mock_strip.return_value = b"silent_mp4"
    mock_asset_service.save_asset.return_value = "saved_video_asset"

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=omni_config
    )
    service.generate_video_with_veo(
        user_id="user_1", file_name="scene.mp4", prompt="A bottle"
    )

    mock_strip.assert_called_once_with(b"fake_mp4_with_audio", "mp4")
    assert mock_asset_service.save_asset.call_args.kwargs["blob"] == b"silent_mp4"


@patch("mediagent_kit.services.media_generation_service.requests.post")
@patch("mediagent_kit.services.media_generation_service.google.auth.default")
def test_veo_never_touches_the_interactions_endpoint(
    mock_auth_default, mock_requests_post, mock_asset_service, mock_config
):
    """The Veo path must be exactly what it was."""
    from mediagent_kit.services.media_generation_service import MediaGenerationService

    mock_config.models = dict(
        mock_config.models, video={"default": "veo-3.1-generate-001"}
    )
    mock_creds = MagicMock()
    mock_creds.token = "fake_token"
    mock_auth_default.return_value = (mock_creds, "test-project")

    service = MediaGenerationService(
        asset_service=mock_asset_service, config=mock_config
    )
    with patch.object(service, "_get_genai_client", side_effect=RuntimeError("veo")):
        with pytest.raises(RuntimeError, match="veo"):
            service.generate_video_with_veo(
                user_id="user_1", file_name="scene.mp4", prompt="A bottle"
            )

    # It went down the Veo path (the genai client), not the REST interactions one.
    mock_requests_post.assert_not_called()
