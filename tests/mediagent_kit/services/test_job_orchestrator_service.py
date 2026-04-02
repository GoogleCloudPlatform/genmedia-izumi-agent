import pytest
from unittest.mock import MagicMock, patch
from mediagent_kit.services.job_orchestrator_service import JobOrchestratorService
from mediagent_kit.services.types.jobs import Job, JobStatus, JobType
from mediagent_kit.services.types import Asset
from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_background_job_runner():
    return MagicMock()


@pytest.fixture
def mock_job_service():
    return MagicMock()


@pytest.fixture
def mock_media_generation_service():
    return MagicMock()


@pytest.fixture
def mock_video_stitching_service():
    return MagicMock()


@pytest.fixture
def mock_canvas_service():
    return MagicMock()


@pytest.fixture
def mock_config():
    return MagicMock(spec=MediagentKitConfig)


@pytest.fixture
def service(
    mock_background_job_runner,
    mock_job_service,
    mock_canvas_service,
    mock_media_generation_service,
    mock_video_stitching_service,
    mock_config,
):
    return JobOrchestratorService(
        mock_background_job_runner,
        mock_job_service,
        mock_canvas_service,
        mock_media_generation_service,
        mock_video_stitching_service,
        mock_config,
    )


def test_submit_music_generation_job(
    service, mock_job_service, mock_background_job_runner
):
    user_id = "user1"
    kwargs = {"prompt": "Upbeat happy music"}

    mock_job = MagicMock(spec=Job)
    mock_job.id = "job1"
    mock_job_service.create_job.return_value = mock_job

    job = service.submit_music_generation_job(user_id, **kwargs)

    assert job == mock_job
    mock_job_service.create_job.assert_called_once_with(
        user_id=user_id,
        job_type=JobType.MUSIC_GENERATION,
        job_input=kwargs,
    )
    mock_background_job_runner.schedule_job_execution.assert_called_once()


def test_run_music_generation_job_success(
    service, mock_job_service, mock_media_generation_service
):
    job_id = "job1"
    user_id = "user1"
    kwargs = {"prompt": "Upbeat happy music"}

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset1"
    mock_media_generation_service.generate_music_with_lyria.return_value = mock_asset

    service._run_music_generation_job(job_id, user_id, **kwargs)

    mock_job_service.update_job_status.assert_called_once_with(
        job_id, JobStatus.RUNNING
    )
    mock_media_generation_service.generate_music_with_lyria.assert_called_once_with(
        user_id=user_id, **kwargs
    )
    mock_job_service.update_job_result.assert_called_once_with(
        job_id, JobStatus.COMPLETED, result_asset_id="asset1"
    )


def test_run_music_generation_job_failure(
    service, mock_job_service, mock_media_generation_service
):
    job_id = "job1"
    user_id = "user1"
    kwargs = {"prompt": "Upbeat happy music"}

    mock_media_generation_service.generate_music_with_lyria.side_effect = Exception(
        "Generation failed"
    )

    service._run_music_generation_job(job_id, user_id, **kwargs)

    mock_job_service.update_job_status.assert_called_once_with(
        job_id, JobStatus.RUNNING
    )
    mock_job_service.update_job_result.assert_called_once_with(
        job_id, JobStatus.FAILED, error_message="Generation failed"
    )


def test_submit_image_generation_job(
    service, mock_job_service, mock_background_job_runner
):
    user_id = "user1"
    kwargs = {"prompt": "A sunset"}

    mock_job = MagicMock(spec=Job)
    mock_job.id = "job2"
    mock_job_service.create_job.return_value = mock_job

    job = service.submit_image_generation_job(user_id, **kwargs)

    assert job == mock_job
    mock_job_service.create_job.assert_called_once_with(
        user_id=user_id,
        job_type=JobType.IMAGE_GENERATION,
        job_input=kwargs,
    )
    mock_background_job_runner.schedule_job_execution.assert_called_once()


def test_run_image_generation_job_success(
    service, mock_job_service, mock_media_generation_service
):
    job_id = "job2"
    user_id = "user1"
    kwargs = {"prompt": "A sunset"}

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset2"
    mock_media_generation_service.generate_image_with_imagen.return_value = mock_asset

    service._run_image_generation_job(job_id, user_id, **kwargs)

    mock_job_service.update_job_status.assert_called_once_with(
        job_id, JobStatus.RUNNING
    )
    mock_media_generation_service.generate_image_with_imagen.assert_called_once_with(
        user_id=user_id, **kwargs
    )
    mock_job_service.update_job_result.assert_called_once_with(
        job_id, JobStatus.COMPLETED, result_asset_id="asset2"
    )


def test_submit_video_stitching_job(
    service, mock_job_service, mock_background_job_runner
):
    user_id = "user1"
    canvas_id = "canvas1"

    mock_job = MagicMock(spec=Job)
    mock_job.id = "job3"
    mock_job_service.create_job.return_value = mock_job

    job = service.submit_video_stitching_job(user_id, canvas_id)

    assert job == mock_job
    mock_job_service.create_job.assert_called_once_with(
        user_id=user_id,
        job_type=JobType.VIDEO_STITCHING,
        job_input={"canvas_id": canvas_id},
    )
    mock_background_job_runner.schedule_job_execution.assert_called_once()


def test_run_video_stitching_job_success(
    service, mock_job_service, mock_canvas_service, mock_video_stitching_service
):
    job_id = "job3"
    user_id = "user1"
    canvas_id = "canvas1"

    mock_canvas = MagicMock()
    mock_canvas.title = "Test Canvas"
    mock_timeline = MagicMock()
    mock_canvas.video_timeline = mock_timeline
    mock_canvas_service.get_canvas.return_value = mock_canvas

    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = "asset3"
    mock_video_stitching_service.stitch_video.return_value = mock_asset

    service._run_video_stitching_job(job_id, user_id, canvas_id)

    mock_job_service.update_job_status.assert_called_once_with(
        job_id, JobStatus.RUNNING
    )
    mock_canvas_service.get_canvas.assert_called_once_with(canvas_id)
    mock_video_stitching_service.stitch_video.assert_called_once_with(
        user_id=user_id, timeline=mock_timeline, output_filename="Test Canvas.mp4"
    )
    mock_job_service.update_job_result.assert_called_once_with(
        job_id, JobStatus.COMPLETED, result_asset_id="asset3"
    )
