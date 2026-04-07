# Copyright 2025 Google LLC
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

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime

from mediagent_kit.api.media_generation import router, get_job_orchestrator_service
from mediagent_kit.services import JobOrchestratorService
from mediagent_kit.api.types import (
    Job,
    LyriaModel,
    ImagenModel,
    ImagenAspectRatio,
    GeminiImageModel,
    GeminiImageAspectRatio,
    SpeechModel,
    SpeechVoice,
    VeoModel,
    VeoAspectRatio,
    VeoDuration,
)
from mediagent_kit.services.types.jobs import JobType, JobStatus

app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_orchestrator():
    return MagicMock(spec=JobOrchestratorService)


@pytest.fixture
def client(mock_orchestrator):
    app.dependency_overrides[get_job_orchestrator_service] = lambda: mock_orchestrator
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_generate_music_success(client, mock_orchestrator):
    mock_job = Job(
        id="job_1",
        user_id="user_1",
        job_type=JobType.MUSIC_GENERATION,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_orchestrator.submit_music_generation_job.return_value = mock_job

    response = client.post(
        "/users/user_1/media:generate-music",
        json={
            "prompt": "smooth jazz",
            "file_name": "jazz.mp3",
            "model": LyriaModel.LYRIA_002.value,
        },
    )
    assert response.status_code == 202
    assert response.json()["id"] == "job_1"


def test_generate_image_with_imagen_success(client, mock_orchestrator):
    mock_job = Job(
        id="job_2",
        user_id="user_1",
        job_type=JobType.IMAGE_GENERATION,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_orchestrator.submit_image_generation_job.return_value = mock_job

    response = client.post(
        "/users/user_1/media:generate-image-with-imagen",
        json={
            "prompt": "a sunset",
            "aspect_ratio": ImagenAspectRatio.RATIO_16_9.value,
            "model": ImagenModel.IMAGEN_4_0_GENERATE_001.value,
            "file_name": "sunset.png",
        },
    )
    assert response.status_code == 202
    assert response.json()["id"] == "job_2"


def test_generate_image_with_gemini_success(client, mock_orchestrator):
    mock_job = Job(
        id="job_3",
        user_id="user_1",
        job_type=JobType.IMAGE_GENERATION,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_orchestrator.submit_gemini_image_generation_job.return_value = mock_job

    response = client.post(
        "/users/user_1/media:generate-image-with-gemini",
        json={
            "prompt": "a cat",
            "aspect_ratio": GeminiImageAspectRatio.RATIO_1_1.value,
            "file_name": "cat.png",
            "model": GeminiImageModel.GEMINI_2_5_FLASH_IMAGE.value,
        },
    )
    assert response.status_code == 202
    assert response.json()["id"] == "job_3"


def test_generate_video_success(client, mock_orchestrator):
    mock_job = Job(
        id="job_4",
        user_id="user_1",
        job_type=JobType.VIDEO_GENERATION,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_orchestrator.submit_video_generation_job.return_value = mock_job

    response = client.post(
        "/users/user_1/media:generate-video",
        json={
            "prompt": "a dog running",
            "file_name": "dog.mp4",
            "model": VeoModel.VEO_3_0_GENERATE_001.value,
            "aspect_ratio": VeoAspectRatio.RATIO_16_9.value,
            "duration_seconds": VeoDuration.SECONDS_4.value,
        },
    )
    assert response.status_code == 202
    assert response.json()["id"] == "job_4"


def test_generate_video_missing_first_frame(client, mock_orchestrator):
    response = client.post(
        "/users/user_1/media:generate-video",
        json={
            "prompt": "a dog running",
            "file_name": "dog.mp4",
            "model": VeoModel.VEO_3_0_GENERATE_001.value,
            "aspect_ratio": VeoAspectRatio.RATIO_16_9.value,
            "duration_seconds": VeoDuration.SECONDS_4.value,
            "last_frame_filename": "last.png",
        },
    )
    assert response.status_code == 400
    assert "A first frame is required" in response.json()["detail"]


def test_generate_speech_single_speaker_success(client, mock_orchestrator):
    mock_job = Job(
        id="job_5",
        user_id="user_1",
        job_type=JobType.SPEECH_SINGLE_SPEAKER_GENERATION,
        status=JobStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_orchestrator.submit_speech_single_speaker_generation_job.return_value = (
        mock_job
    )

    response = client.post(
        "/users/user_1/media:generate-speech-single-speaker",
        json={
            "prompt": "speak this",
            "text": "Hello world",
            "model": SpeechModel.GEMINI_2_5_FLASH_TTS.value,
            "voice_name": SpeechVoice.ACHERNAR.value,
            "file_name": "hello.mp3",
        },
    )
    assert response.status_code == 202
    assert response.json()["id"] == "job_5"
