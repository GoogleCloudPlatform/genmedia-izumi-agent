import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from google.cloud.firestore_v1 import Client
from mediagent_kit.services.job_service import JobService
from mediagent_kit.services.types.jobs import Job, JobStatus, JobType
from mediagent_kit.config import MediagentKitConfig


@pytest.fixture
def mock_db():
    return MagicMock(spec=Client)


@pytest.fixture
def mock_config():
    return MagicMock(spec=MediagentKitConfig)


@pytest.fixture
def service(mock_db, mock_config):
    with patch.object(JobService, "_get_collection") as mock_get_col:
        mock_col = MagicMock()
        mock_get_col.return_value = mock_col
        svc = JobService(mock_db, mock_config)
        svc.jobs_collection = mock_col
        return svc


def test_create_job(service):
    user_id = "user1"
    job_type = JobType.IMAGE_GENERATION
    job_input = {"prompt": "A cat"}

    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "new-job-id"
    service.jobs_collection.add.return_value = (None, mock_doc_ref)

    job = service.create_job(user_id, job_type, job_input)

    assert job.id == "new-job-id"
    assert job.user_id == user_id
    assert job.job_type == job_type
    assert job.status == JobStatus.PENDING
    assert job.job_input == job_input

    service.jobs_collection.add.assert_called_once()


def test_get_job_exists(service):
    job_id = "job1"

    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = True
    mock_doc_snapshot.id = job_id
    mock_doc_snapshot.to_dict.return_value = {
        "user_id": "user1",
        "job_type": JobType.IMAGE_GENERATION.value,
        "status": JobStatus.PENDING.value,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "job_input": {"prompt": "A cat"},
    }
    mock_doc_ref.get.return_value = mock_doc_snapshot
    service.jobs_collection.document.return_value = mock_doc_ref

    job = service.get_job(job_id)

    assert job is not None
    assert job.id == job_id
    assert job.user_id == "user1"


def test_get_job_not_found(service):
    job_id = "job1"

    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_doc_ref.get.return_value = mock_doc_snapshot
    service.jobs_collection.document.return_value = mock_doc_ref

    job = service.get_job(job_id)

    assert job is None


def test_get_jobs(service):
    user_id = "user1"

    mock_query = MagicMock()
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.id = "job1"
    mock_doc_snapshot.to_dict.return_value = {
        "user_id": user_id,
        "job_type": JobType.IMAGE_GENERATION.value,
        "status": JobStatus.PENDING.value,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    # Chained calls: where().order_by().limit().offset().stream()
    mock_where = MagicMock()
    mock_orderby = MagicMock()
    mock_limit = MagicMock()
    mock_offset = MagicMock()

    service.jobs_collection.where.return_value = mock_where
    mock_where.order_by.return_value = mock_orderby
    mock_orderby.limit.return_value = mock_limit
    mock_limit.offset.return_value = mock_offset
    mock_offset.stream.return_value = [mock_doc_snapshot]

    jobs = service.get_jobs(user_id)

    assert len(jobs) == 1
    assert jobs[0].id == "job1"


def test_update_job_status(service):
    job_id = "job1"
    status = JobStatus.RUNNING

    mock_doc_ref = MagicMock()
    service.jobs_collection.document.return_value = mock_doc_ref

    service.update_job_status(job_id, status)

    service.jobs_collection.document.assert_called_once_with(job_id)
    mock_doc_ref.update.assert_called_once()


def test_update_job_result(service):
    job_id = "job1"
    status = JobStatus.COMPLETED
    result_asset_id = "asset1"

    mock_doc_ref = MagicMock()
    service.jobs_collection.document.return_value = mock_doc_ref

    service.update_job_result(job_id, status, result_asset_id=result_asset_id)

    service.jobs_collection.document.assert_called_once_with(job_id)
    mock_doc_ref.update.assert_called_once()
