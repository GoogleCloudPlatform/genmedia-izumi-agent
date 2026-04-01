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

import datetime

from google.cloud.firestore_v1 import Client, FieldFilter

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.base_service import BaseService
from mediagent_kit.services.types.jobs import Job, JobStatus


class JobService(BaseService):
    """
    Service for managing long-running jobs.
    """

    def __init__(self, db: Client, config: MediagentKitConfig):
        super().__init__(db)
        self._config = config
        self.jobs_collection = self._get_collection("jobs")

    def create_job(
        self, user_id: str, job_type: str, job_input: dict | None = None
    ) -> Job:
        """
        Creates a new job.

        Args:
            user_id: The ID of the user.
            job_type: The type of the job.
            job_input: The input for the job.

        Returns:
            The created job.
        """
        now = datetime.datetime.now(datetime.UTC)
        job = Job(
            id=None,  # Firestore will generate an ID
            user_id=user_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            job_input=job_input,
            created_at=now,
            updated_at=now,
        )
        _, doc_ref = self.jobs_collection.add(job.to_dict())
        job.id = doc_ref.id
        return job

    def get_job(self, job_id: str) -> Job | None:
        """
        Gets a job by its ID.

        Args:
            job_id: The ID of the job to get.

        Returns:
            The job, or None if it does not exist.
        """
        doc = self.jobs_collection.document(job_id).get()
        if not doc.exists:
            return None
        return Job.from_document(doc)

    def get_jobs(
        self,
        user_id: str,
        status: JobStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Job]:
        """
        Gets all jobs for a user.

        Args:
            user_id: The ID of the user to get jobs for.
            status: The status of the jobs to get.
            limit: The maximum number of jobs to return.
            offset: The offset to start from.

        Returns:
            A list of jobs.
        """
        query = self.jobs_collection.where(filter=FieldFilter("user_id", "==", user_id))
        if status:
            query = query.where(filter=FieldFilter("status", "==", status.value))
        query = query.order_by("created_at", direction="DESCENDING")
        query = query.limit(limit).offset(offset)
        docs = query.stream()
        return [Job.from_document(doc) for doc in docs]

    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """
        Updates the status of a job.

        Args:
            job_id: The ID of the job to update.
            status: The new status of the job.
        """
        now = datetime.datetime.now(datetime.UTC)
        self.jobs_collection.document(job_id).update(
            {"status": status.value, "updated_at": now}
        )

    def update_job_result(
        self,
        job_id: str,
        status: JobStatus,
        result_asset_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Updates the result of a job.

        Args:
            job_id: The ID of the job to update.
            status: The new status of the job.
            result_asset_id: The ID of the result asset.
            error_message: An error message if the job failed.
        """
        now = datetime.datetime.now(datetime.UTC)
        update_data = {"status": status.value, "updated_at": now}
        if result_asset_id:
            update_data["result_asset_id"] = result_asset_id
        if error_message:
            update_data["error_message"] = error_message
        self.jobs_collection.document(job_id).update(update_data)
