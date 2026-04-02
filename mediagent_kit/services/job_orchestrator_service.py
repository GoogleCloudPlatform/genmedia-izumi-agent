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

from typing import Any

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services.canvas_service import CanvasService
from mediagent_kit.services.job_service import JobService
from mediagent_kit.services.media_generation_service import MediaGenerationService
from mediagent_kit.services.types.jobs import Job, JobStatus, JobType
from mediagent_kit.services.video_stitching_service import VideoStitchingService
from mediagent_kit.utils.background_job_runner import AbstractBackgroundJobRunner


class JobOrchestratorService:
    """
    Service for orchestrating long-running jobs.
    """

    def __init__(
        self,
        background_job_runner: AbstractBackgroundJobRunner,
        job_service: JobService,
        canvas_service: CanvasService,
        media_generation_service: MediaGenerationService,
        video_stitching_service: VideoStitchingService,
        config: MediagentKitConfig,
    ):
        self._background_job_runner = background_job_runner
        self._job_service = job_service
        self._canvas_service = canvas_service
        self._media_generation_service = media_generation_service
        self._video_stitching_service = video_stitching_service
        self._config = config

    def submit_music_generation_job(self, user_id: str, **kwargs: Any) -> Job:
        """
        Submits a music generation job.

        Args:
            user_id: The ID of the user.
            **kwargs: The arguments for the music generation job.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.MUSIC_GENERATION,
            job_input=kwargs,
        )
        self._background_job_runner.schedule_job_execution(
            self._run_music_generation_job, job_id=job.id, user_id=user_id, **kwargs
        )
        return job

    def submit_image_generation_job(self, user_id: str, **kwargs: Any) -> Job:
        """
        Submits an image generation job.

        Args:
            user_id: The ID of the user.
            **kwargs: The arguments for the image generation job.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.IMAGE_GENERATION,
            job_input=kwargs,
        )
        self._background_job_runner.schedule_job_execution(
            self._run_image_generation_job, job_id=job.id, user_id=user_id, **kwargs
        )
        return job

    def submit_gemini_image_generation_job(self, user_id: str, **kwargs: Any) -> Job:
        """
        Submits a Gemini image generation job.

        Args:
            user_id: The ID of the user.
            **kwargs: The arguments for the image generation job.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.IMAGE_GENERATION,
            job_input=kwargs,
        )
        self._background_job_runner.schedule_job_execution(
            self._run_gemini_image_generation_job,
            job_id=job.id,
            user_id=user_id,
            **kwargs,
        )
        return job

    def submit_video_generation_job(self, user_id: str, **kwargs: Any) -> Job:
        """
        Submits a video generation job.

        Args:
            user_id: The ID of the user.
            **kwargs: The arguments for the video generation job.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.VIDEO_GENERATION,
            job_input=kwargs,
        )
        self._background_job_runner.schedule_job_execution(
            self._run_video_generation_job, job_id=job.id, user_id=user_id, **kwargs
        )
        return job

    def submit_speech_single_speaker_generation_job(
        self, user_id: str, **kwargs: Any
    ) -> Job:
        """
        Submits a single speaker speech generation job.

        Args:
            user_id: The ID of the user.
            **kwargs: The arguments for the speech generation job.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.SPEECH_SINGLE_SPEAKER_GENERATION,
            job_input=kwargs,
        )
        self._background_job_runner.schedule_job_execution(
            self._run_speech_single_speaker_generation_job,
            job_id=job.id,
            user_id=user_id,
            **kwargs,
        )
        return job

    def submit_video_stitching_job(self, user_id: str, canvas_id: str) -> Job:
        """
        Submits a video stitching job.

        Args:
            user_id: The ID of the user.
            canvas_id: The ID of the canvas to stitch.

        Returns:
            The created job.
        """
        job = self._job_service.create_job(
            user_id=user_id,
            job_type=JobType.VIDEO_STITCHING,
            job_input={"canvas_id": canvas_id},
        )
        self._background_job_runner.schedule_job_execution(
            self._run_video_stitching_job,
            job_id=job.id,
            user_id=user_id,
            canvas_id=canvas_id,
        )
        return job

    def _run_music_generation_job(
        self, job_id: str, user_id: str, **kwargs: Any
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            asset = self._media_generation_service.generate_music_with_lyria(
                user_id=user_id, **kwargs
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

    def _run_image_generation_job(
        self, job_id: str, user_id: str, **kwargs: Any
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            asset = self._media_generation_service.generate_image_with_imagen(
                user_id=user_id, **kwargs
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

    def _run_gemini_image_generation_job(
        self, job_id: str, user_id: str, **kwargs: Any
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            asset = self._media_generation_service.generate_image_with_gemini(
                user_id=user_id, **kwargs
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

    def _run_speech_single_speaker_generation_job(
        self, job_id: str, user_id: str, **kwargs: Any
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            asset = self._media_generation_service.generate_speech_single_speaker(
                user_id=user_id, **kwargs
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

    def _run_video_generation_job(
        self, job_id: str, user_id: str, **kwargs: Any
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            asset = self._media_generation_service.generate_video_with_veo(
                user_id=user_id, **kwargs
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )

    def _run_video_stitching_job(
        self, job_id: str, user_id: str, canvas_id: str
    ) -> None:
        self._job_service.update_job_status(job_id, JobStatus.RUNNING)
        try:
            canvas = self._canvas_service.get_canvas(canvas_id)
            if not canvas:
                raise ValueError(f"Canvas {canvas_id} not found")
            if not canvas.video_timeline:
                raise ValueError(f"Canvas {canvas_id} has no video timeline")

            output_filename = f"{canvas.title or 'stitched_video'}.mp4"
            asset = self._video_stitching_service.stitch_video(
                user_id=user_id,
                timeline=canvas.video_timeline,
                output_filename=output_filename,
            )
            self._job_service.update_job_result(
                job_id, JobStatus.COMPLETED, result_asset_id=asset.id
            )
        except Exception as e:
            self._job_service.update_job_result(
                job_id, JobStatus.FAILED, error_message=str(e)
            )
