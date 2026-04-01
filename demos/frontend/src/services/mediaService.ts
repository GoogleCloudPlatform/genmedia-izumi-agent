/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { api } from './api';
import {
  type GenerateMusicRequest,
  type GenerateImageWithImagenRequest,
  type GenerateImageWithGeminiRequest,
  type GenerateVideoRequest,
  type GenerateSpeechSingleSpeakerRequest,
  type Job,
  JobStatus,
} from '../data/types';

// In-memory store for pending jobs
let pendingJobs: Job[] = [];

const mediaService = {
  getPendingJobs: (): Job[] => {
    return [...pendingJobs];
  },

  // Polls all pending jobs and updates their status.
  // Returns lists of jobs that are still active, completed, or failed in this poll cycle.
  checkJobStatus: async (
    userId: string,
  ): Promise<{
    activeJobs: Job[];
    completedJobs: Job[];
    failedJobs: Job[];
  }> => {
    const activeJobs: Job[] = [];
    const completedJobs: Job[] = [];
    const failedJobs: Job[] = [];
    const remainingPendingJobs: Job[] = [];

    for (const job of pendingJobs) {
      try {
        // Only poll jobs for the current user/project context
        if (job.user_id !== userId) {
          remainingPendingJobs.push(job);
          continue;
        }

        const updatedJob = await api.getJob(userId, job.id);

        if (updatedJob.status === JobStatus.COMPLETED) {
          completedJobs.push(updatedJob);
        } else if (
          updatedJob.status === JobStatus.FAILED ||
          updatedJob.status === JobStatus.CANCELLED
        ) {
          failedJobs.push(updatedJob);
        } else {
          activeJobs.push(updatedJob);
          remainingPendingJobs.push(updatedJob);
        }
      } catch (error: unknown) {
        console.error(`Failed to check status for job ${job.id}`, error);

        // Check if error is a 404 Not Found (Job gone)
        // The client throws "HTTP error! status: 404"
        if (error instanceof Error && error.message.includes('status: 404')) {
          // Treat as failed/removed
          const failedJob = { ...job, status: JobStatus.FAILED }; // Or CANCELLED
          failedJobs.push(failedJob);
        } else {
          // Keep it in pending if check fails to retry later (e.g. network error, 500)
          activeJobs.push(job);
          remainingPendingJobs.push(job);
        }
      }
    }

    pendingJobs = remainingPendingJobs;

    return { activeJobs, completedJobs, failedJobs };
  },

  generateMusic: async (
    projectId: string,
    request: GenerateMusicRequest,
  ): Promise<Job> => {
    const job = await api.generateMusic(projectId, request);
    pendingJobs.push(job);
    return job;
  },

  generateImageWithImagen: async (
    projectId: string,
    request: GenerateImageWithImagenRequest,
  ): Promise<Job> => {
    const job = await api.generateImageWithImagen(projectId, request);
    pendingJobs.push(job);
    return job;
  },

  generateImageWithGemini: async (
    projectId: string,
    request: GenerateImageWithGeminiRequest,
  ): Promise<Job> => {
    const job = await api.generateImageWithGemini(projectId, request);
    pendingJobs.push(job);
    return job;
  },

  generateVideo: async (
    projectId: string,
    request: GenerateVideoRequest,
  ): Promise<Job> => {
    const job = await api.generateVideo(projectId, request);
    pendingJobs.push(job);
    return job;
  },

  generateSpeech: async (
    projectId: string,
    request: GenerateSpeechSingleSpeakerRequest,
  ): Promise<Job> => {
    const job = await api.generateSpeech(projectId, request);
    pendingJobs.push(job);
    return job;
  },
};

export default mediaService;

if (import.meta.env.MODE === 'test') {
  Object.assign(mediaService, {
    _clearPendingJobs: () => (pendingJobs = []),
    _setPendingJobs: (jobs: Job[]) => (pendingJobs = jobs),
  });
}
