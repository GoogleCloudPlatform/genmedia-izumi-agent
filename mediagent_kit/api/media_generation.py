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

from enum import Enum
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

import mediagent_kit
from mediagent_kit.api.types import (
    GenerateImageWithGeminiRequest,
    GenerateImageWithImagenRequest,
    GenerateMusicRequest,
    GenerateSpeechSingleSpeakerRequest,
    GenerateVideoRequest,
    Job,
)
from mediagent_kit.services import JobOrchestratorService
from mediagent_kit.utils.background_job_runner import FastAPIBackgroundJobRunner

router = APIRouter()


def get_job_orchestrator_service(
    background_tasks: BackgroundTasks,
) -> JobOrchestratorService:
    return mediagent_kit.services._get_job_orchestrator_service(
        background_runner=FastAPIBackgroundJobRunner(background_tasks),
    )


def _extract_job_input(request: BaseModel) -> dict:
    """Extracts job input from request, converting Enums to their values."""
    job_input = request.model_dump()
    for key, value in request:
        if isinstance(value, Enum):
            job_input[key] = value.value
    return job_input


# --- API Endpoints ---


@router.post(
    "/users/{user_id}/media:generate-music",
    response_model=Job,
    status_code=202,
    tags=["Media Generation"],
)
def generate_music(
    user_id: str,
    request: GenerateMusicRequest,
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Generates music using Lyria."""
    job_input = _extract_job_input(request)
    job = orchestrator.submit_music_generation_job(user_id=user_id, **job_input)
    return job


@router.post(
    "/users/{user_id}/media:generate-image-with-imagen",
    response_model=Job,
    status_code=202,
    tags=["Media Generation"],
)
def generate_image_with_imagen(
    user_id: str,
    request: GenerateImageWithImagenRequest,
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Generates an image using Imagen."""
    job_input = _extract_job_input(request)
    job = orchestrator.submit_image_generation_job(user_id=user_id, **job_input)
    return job


@router.post(
    "/users/{user_id}/media:generate-image-with-gemini",
    response_model=Job,
    status_code=202,
    tags=["Media Generation"],
)
def generate_image_with_gemini(
    user_id: str,
    request: GenerateImageWithGeminiRequest,
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Generates an image using Gemini."""
    job_input = _extract_job_input(request)
    job = orchestrator.submit_gemini_image_generation_job(user_id=user_id, **job_input)
    return job


@router.post(
    "/users/{user_id}/media:generate-video",
    response_model=Job,
    status_code=202,
    tags=["Media Generation"],
)
def generate_video(
    user_id: str,
    request: GenerateVideoRequest,
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Generates a video using Veo."""
    if request.last_frame_filename and not request.first_frame_filename:
        raise HTTPException(
            status_code=400,
            detail="A first frame is required when providing a last frame for interpolation.",
        )
    job_input = _extract_job_input(request)
    job = orchestrator.submit_video_generation_job(user_id=user_id, **job_input)
    return job


@router.post(
    "/users/{user_id}/media:generate-speech-single-speaker",
    response_model=Job,
    status_code=202,
    tags=["Media Generation"],
)
def generate_speech_single_speaker(
    user_id: str,
    request: GenerateSpeechSingleSpeakerRequest,
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Generates speech from text with a single speaker."""
    job_input = _extract_job_input(request)
    job = orchestrator.submit_speech_single_speaker_generation_job(
        user_id=user_id, **job_input
    )
    return job
