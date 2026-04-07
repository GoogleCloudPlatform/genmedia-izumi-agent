import pytest
from unittest.mock import MagicMock, patch
import subprocess
import os

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.types import (
    VideoTimeline,
    VideoClip,
    AudioClip,
    Transition,
    TransitionType,
    Asset,
    Trim,
    AudioPlacement,
)


@pytest.fixture
def mock_asset_service():
    return MagicMock()


@pytest.fixture
def mock_config():
    config = MagicMock(spec=MediagentKitConfig)
    return config


def test_build_filter_complex_single_video(mock_asset_service, mock_config):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    timeline = VideoTimeline(
        title="Test Timeline",
        video_clips=[VideoClip(asset=MagicMock(spec=Asset))],
        transitions=[],
        audio_clips=[],
    )

    video_files = ["/path/to/video1.mp4"]
    video_durations = [10.0]
    video_metadata = [(10.0, 1280, 720, 24.0)]

    filter_complex, v_out, a_out = service._build_filter_complex(
        timeline, video_files, video_durations, 0, video_metadata
    )

    assert "[norm_v0]" in filter_complex
    assert "scale=w=1280:h=720" in filter_complex
    assert v_out == "[norm_v0]"
    assert a_out == ""


def test_build_filter_complex_multi_video_with_xfade(mock_asset_service, mock_config):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    timeline = VideoTimeline(
        title="Test Timeline",
        video_clips=[
            VideoClip(asset=MagicMock(spec=Asset)),
            VideoClip(asset=MagicMock(spec=Asset)),
        ],
        transitions=[Transition(type=TransitionType.FADE, duration_seconds=1.0)],
        audio_clips=[],
    )

    video_files = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
    video_durations = [10.0, 10.0]
    video_metadata = [(10.0, 1280, 720, 24.0), (10.0, 1280, 720, 24.0)]

    filter_complex, v_out, a_out = service._build_filter_complex(
        timeline, video_files, video_durations, 0, video_metadata
    )

    assert "xfade=transition=fade:duration=1.0:offset=9.0" in filter_complex
    assert v_out == "[v1]"


@patch("mediagent_kit.services.video_stitching_service.subprocess.run")
@patch("mediagent_kit.services.video_stitching_service.get_ffmpeg_exe")
def test_create_placeholder_clip(
    mock_get_ffmpeg, mock_subprocess_run, mock_asset_service, mock_config
):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService

    mock_get_ffmpeg.return_value = "ffmpeg"
    mock_subprocess_run.return_value = MagicMock(stdout=b"success", stderr=b"")

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    clip = VideoClip(placeholder="Test Placeholder", trim=Trim(duration_seconds=5))

    placeholder_path = service._create_placeholder_clip(
        clip, "/tmp", 0, mock_asset_service, 1280, 720
    )

    assert "placeholder_0.mp4" in placeholder_path
    mock_subprocess_run.assert_called_once()
    args = mock_subprocess_run.call_args[0][0]
    assert "color=c=black:s=1280x720:d=5" in args[4]  # lavfi input


@patch("mediagent_kit.services.video_stitching_service.get_media_metadata_from_file")
@patch("mediagent_kit.services.video_stitching_service.subprocess.run")
@patch("mediagent_kit.services.video_stitching_service.get_ffmpeg_exe")
def test_stitch_video_success(
    mock_get_ffmpeg,
    mock_subprocess_run,
    mock_get_metadata,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService
    from mediagent_kit.utils.media_tools import MediaMetadata

    mock_get_ffmpeg.return_value = "ffmpeg"
    mock_subprocess_run.return_value = MagicMock(stdout=b"success", stderr=b"")

    # Mock metadata
    mock_metadata = MagicMock(spec=MediaMetadata)
    mock_metadata.duration = 10.0
    mock_metadata.width = 1280
    mock_metadata.height = 720
    mock_metadata.fps = 24.0
    mock_get_metadata.return_value = mock_metadata

    # Mock AssetService
    mock_asset_service.get_asset_file_path.return_value = "/path/to/asset.mp4"
    mock_blob = MagicMock()
    mock_blob.content = b"fake bytes"
    mock_asset_service.get_asset_blob.return_value = mock_blob
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset_out"
    mock_asset_service.save_asset_from_file.return_value = mock_asset

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    mock_source_asset = MagicMock(spec=Asset)
    mock_source_asset.id = "source_asset_1"
    mock_source_asset.file_name = "input.mp4"
    mock_source_asset.mime_type = "video/mp4"
    timeline = VideoTimeline(
        title="My Awesome Video",
        video_clips=[VideoClip(asset=mock_source_asset)],
        transitions=[],
        audio_clips=[],
    )

    result = service.stitch_video(
        user_id="user_123", timeline=timeline, output_filename="result.mp4"
    )

    assert result == mock_asset
    mock_asset_service.save_asset_from_file.assert_called_once()
    mock_subprocess_run.assert_called()


@patch("mediagent_kit.services.video_stitching_service.get_media_metadata_from_file")
@patch("mediagent_kit.services.video_stitching_service.subprocess.run")
@patch("mediagent_kit.services.video_stitching_service.get_ffmpeg_exe")
def test_stitch_video_with_image_clip(
    mock_get_ffmpeg,
    mock_subprocess_run,
    mock_get_metadata,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService
    from mediagent_kit.utils.media_tools import MediaMetadata

    mock_get_ffmpeg.return_value = "ffmpeg"
    mock_subprocess_run.return_value = MagicMock(stdout=b"success", stderr=b"")

    mock_metadata = MagicMock(spec=MediaMetadata)
    mock_metadata.duration = 0.0
    mock_metadata.width = 1200
    mock_metadata.height = 800
    mock_metadata.fps = 24.0
    mock_get_metadata.return_value = mock_metadata

    mock_asset_service.get_asset_file_path.return_value = "/path/to/image.jpg"
    mock_blob = MagicMock()
    mock_blob.content = b"fake image bytes"
    mock_asset_service.get_asset_blob.return_value = mock_blob
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset_out"
    mock_asset_service.save_asset_from_file.return_value = mock_asset

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    mock_source_asset = MagicMock(spec=Asset)
    mock_source_asset.id = "source_asset_image"
    mock_source_asset.file_name = "input.jpg"
    mock_source_asset.mime_type = "image/jpeg"
    timeline = VideoTimeline(
        title="Image Video",
        video_clips=[VideoClip(asset=mock_source_asset, trim=Trim(duration_seconds=5))],
        transitions=[],
        audio_clips=[],
    )

    result = service.stitch_video(
        user_id="user_123", timeline=timeline, output_filename="result.mp4"
    )

    assert result == mock_asset
    mock_asset_service.save_asset_from_file.assert_called_once()
    mock_subprocess_run.assert_called()


@patch("mediagent_kit.services.video_stitching_service.get_media_metadata_from_file")
@patch("mediagent_kit.services.video_stitching_service.subprocess.run")
@patch("mediagent_kit.services.video_stitching_service.get_ffmpeg_exe")
def test_stitch_video_with_placeholder_clip(
    mock_get_ffmpeg,
    mock_subprocess_run,
    mock_get_metadata,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService

    mock_get_ffmpeg.return_value = "ffmpeg"
    mock_subprocess_run.return_value = MagicMock(stdout=b"success", stderr=b"")

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset_out"
    mock_asset_service.save_asset_from_file.return_value = mock_asset

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    timeline = VideoTimeline(
        title="Placeholder Video",
        video_clips=[
            VideoClip(
                asset=None, placeholder="Loading...", trim=Trim(duration_seconds=5)
            )
        ],
        transitions=[],
        audio_clips=[],
    )

    result = service.stitch_video(
        user_id="user_123", timeline=timeline, output_filename="result.mp4"
    )

    assert result == mock_asset
    mock_asset_service.save_asset_from_file.assert_called_once()
    mock_subprocess_run.assert_called()


@patch("mediagent_kit.services.video_stitching_service.get_media_metadata_from_file")
@patch("mediagent_kit.services.video_stitching_service.subprocess.run")
@patch("mediagent_kit.services.video_stitching_service.get_ffmpeg_exe")
def test_stitch_video_with_audio_clip(
    mock_get_ffmpeg,
    mock_subprocess_run,
    mock_get_metadata,
    mock_asset_service,
    mock_config,
):
    from mediagent_kit.services.video_stitching_service import VideoStitchingService
    from mediagent_kit.utils.media_tools import MediaMetadata

    mock_get_ffmpeg.return_value = "ffmpeg"
    mock_subprocess_run.return_value = MagicMock(stdout=b"success", stderr=b"")

    mock_metadata = MagicMock(spec=MediaMetadata)
    mock_metadata.duration = 10.0
    mock_metadata.width = 1280
    mock_metadata.height = 720
    mock_metadata.fps = 24.0
    mock_get_metadata.return_value = mock_metadata

    mock_asset_service.get_asset_file_path.return_value = "/path/to/asset.mp4"
    mock_blob = MagicMock()
    mock_blob.content = b"fake bytes"
    mock_asset_service.get_asset_blob.return_value = mock_blob
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset_out"
    mock_asset_service.save_asset_from_file.return_value = mock_asset

    service = VideoStitchingService(
        asset_service=mock_asset_service, config=mock_config
    )

    mock_source_asset = MagicMock(spec=Asset)
    mock_source_asset.id = "source_asset_1"
    mock_source_asset.file_name = "input.mp4"
    mock_source_asset.mime_type = "video/mp4"

    mock_audio_asset = MagicMock(spec=Asset)
    mock_audio_asset.id = "audio_asset_1"
    mock_audio_asset.file_name = "background.mp3"
    mock_audio_asset.mime_type = "audio/mp3"

    timeline = VideoTimeline(
        title="Audio Video",
        video_clips=[VideoClip(asset=mock_source_asset)],
        transitions=[],
        audio_clips=[
            AudioClip(
                asset=mock_audio_asset,
                start_at=AudioPlacement(video_clip_index=0, offset_seconds=0),
            )
        ],
    )

    result = service.stitch_video(
        user_id="user_123", timeline=timeline, output_filename="result.mp4"
    )

    assert result == mock_asset
    mock_asset_service.save_asset_from_file.assert_called_once()
    mock_subprocess_run.assert_called()
