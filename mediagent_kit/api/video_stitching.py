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

"""
API for video stitching.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

import mediagent_kit
from mediagent_kit.api.types import Job
from mediagent_kit.services import CanvasService, JobOrchestratorService
from mediagent_kit.utils.background_job_runner import FastAPIBackgroundJobRunner

router = APIRouter()


def get_canvas_service() -> CanvasService:
    return mediagent_kit.services.get_canvas_service()


def get_job_orchestrator_service(
    background_tasks: BackgroundTasks,
) -> JobOrchestratorService:
    return mediagent_kit.services._get_job_orchestrator_service(
        background_runner=FastAPIBackgroundJobRunner(background_tasks),
    )


@router.post(
    "/users/{user_id}/canvases/{canvas_id}:stitch",
    response_model=Job,
    status_code=202,
    tags=["Video Stitching"],
)
def stitch_video(
    user_id: str,
    canvas_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    orchestrator: Annotated[
        JobOrchestratorService, Depends(get_job_orchestrator_service)
    ],
) -> Job:
    """Stitches a video from a canvas."""
    canvas = canvas_service.get_canvas(canvas_id)
    if not canvas or not canvas.video_timeline:
        raise HTTPException(
            status_code=400, detail="Canvas does not have a video timeline."
        )

    job = orchestrator.submit_video_stitching_job(user_id=user_id, canvas_id=canvas_id)
    return job
