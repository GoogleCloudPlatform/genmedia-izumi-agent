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
Data models for long-running jobs.
"""

import datetime
import enum
from typing import Any

from google.cloud.firestore_v1.base_document import DocumentSnapshot

from mediagent_kit.services.types.assets import Asset


@enum.unique
class JobStatus(enum.StrEnum):
    """
    Enum for the status of a job.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@enum.unique
class JobType(enum.StrEnum):
    """
    Enum for the type of a job.
    """

    IMAGE_GENERATION = "IMAGE_GENERATION"
    VIDEO_GENERATION = "VIDEO_GENERATION"
    MUSIC_GENERATION = "MUSIC_GENERATION"
    SPEECH_SINGLE_SPEAKER_GENERATION = "SPEECH_SINGLE_SPEAKER_GENERATION"
    VIDEO_STITCHING = "VIDEO_STITCHING"


class Job:
    """
    Represents a long-running job.
    """

    def __init__(
        self,
        id: str,
        user_id: str,
        job_type: JobType,
        status: JobStatus,
        created_at: datetime.datetime,
        updated_at: datetime.datetime,
        job_input: dict | None = None,
        result_asset_id: str | None = None,
        result_asset: Asset | None = None,
        error_message: str | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.job_type = job_type
        self.status = status
        self.job_input = job_input
        self.result_asset_id = result_asset_id
        self.result_asset = result_asset
        self.error_message = error_message
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the job.
        """
        data: dict[str, Any] = {
            "user_id": self.user_id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.job_input:
            data["job_input"] = self.job_input
        if self.result_asset_id:
            data["result_asset_id"] = self.result_asset_id
        if self.error_message:
            data["error_message"] = self.error_message
        return data

    @staticmethod
    def from_document(doc: DocumentSnapshot) -> "Job":
        """
        Creates a Job instance from a Firestore document.
        """
        data = doc.to_dict()
        if data is None:
            raise ValueError("Document data is None")
        user_id = data.get("user_id")
        if not isinstance(user_id, str):
            raise ValueError("Job document missing valid user_id")
        job_type = data.get("job_type")
        if not isinstance(job_type, str):
            raise ValueError("Job document missing valid job_type")
        status = data.get("status")
        if not isinstance(status, str):
            raise ValueError("Job document missing valid status")
        created_at = data.get("created_at")
        if not isinstance(created_at, datetime.datetime):
            raise ValueError("Job document missing valid created_at")
        updated_at = data.get("updated_at")
        if not isinstance(updated_at, datetime.datetime):
            raise ValueError("Job document missing valid updated_at")

        return Job(
            id=doc.id,
            user_id=user_id,
            job_type=JobType(job_type),
            status=JobStatus(status),
            job_input=data.get("job_input"),
            result_asset_id=data.get("result_asset_id"),
            error_message=data.get("error_message"),
            created_at=created_at,
            updated_at=updated_at,
        )
