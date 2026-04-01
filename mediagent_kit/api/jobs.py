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
API for managing long-running jobs.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

import mediagent_kit
from mediagent_kit.api.types import Job
from mediagent_kit.services import JobService
from mediagent_kit.services.types.jobs import JobStatus

router = APIRouter()


def get_job_service() -> JobService:
    return mediagent_kit.services.get_job_service()


@router.get("/users/{user_id}/jobs/{job_id}", response_model=Job, tags=["Jobs"])
def get_job(
    user_id: str,
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> Job:
    """Gets a job by its ID."""
    job = job_service.get_job(job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/users/{user_id}/jobs", response_model=list[Job], tags=["Jobs"])
def get_jobs(
    user_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    status: JobStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Job]:
    """Gets all jobs for a user."""
    return job_service.get_jobs(user_id, status, limit, offset)
