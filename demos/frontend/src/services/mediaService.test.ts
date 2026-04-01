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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import mediaService from './mediaService';
import { api } from './api';
import {
  Job,
  JobStatus,
  GenerateMusicRequest,
  GenerateImageWithImagenRequest,
  GenerateImageWithGeminiRequest,
  GenerateVideoRequest,
  GenerateSpeechSingleSpeakerRequest,
} from '../data/types';

vi.mock('./api', () => ({
  api: {
    getJob: vi.fn(),
    generateMusic: vi.fn(),
    generateImageWithImagen: vi.fn(),
    generateImageWithGemini: vi.fn(),
    generateVideo: vi.fn(),
    generateSpeech: vi.fn(),
  },
}));

describe('mediaService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mediaService['_clearPendingJobs']();
  });

  describe('checkJobStatus', () => {
    const userId = 'user-1';

    it('should poll jobs and categorize them correctly', async () => {
      const pendingJobs: Job[] = [
        { id: 'job-1', user_id: userId, status: JobStatus.PENDING },
        { id: 'job-2', user_id: userId, status: JobStatus.RUNNING },
        { id: 'job-3', user_id: userId, status: JobStatus.PENDING },
        { id: 'job-4', user_id: 'user-2', status: JobStatus.PENDING }, // Different user
      ];
      mediaService['_setPendingJobs'](pendingJobs);

      (api.getJob as vi.Mock)
        .mockResolvedValueOnce({ id: 'job-1', status: JobStatus.COMPLETED })
        .mockResolvedValueOnce({ id: 'job-2', status: JobStatus.RUNNING })
        .mockResolvedValueOnce({ id: 'job-3', status: JobStatus.FAILED });

      const result = await mediaService.checkJobStatus(userId);

      expect(api.getJob).toHaveBeenCalledTimes(3);
      expect(result.completedJobs).toHaveLength(1);
      expect(result.completedJobs[0].id).toBe('job-1');
      expect(result.activeJobs).toHaveLength(1);
      expect(result.activeJobs[0].id).toBe('job-2');
      expect(result.failedJobs).toHaveLength(1);
      expect(result.failedJobs[0].id).toBe('job-3');

      // Check remaining pending jobs
      const remaining = mediaService.getPendingJobs();
      expect(remaining).toHaveLength(2); // job-2 (active) and job-4 (other user)
      expect(remaining.map((j) => j.id)).toContain('job-2');
      expect(remaining.map((j) => j.id)).toContain('job-4');
    });

    it('should handle API errors gracefully', async () => {
      const pendingJobs: Job[] = [
        { id: 'job-err', user_id: userId, status: JobStatus.PENDING },
      ];
      mediaService['_setPendingJobs'](pendingJobs);

      (api.getJob as vi.Mock).mockRejectedValue(new Error('API Error'));

      const result = await mediaService.checkJobStatus(userId);

      expect(result.activeJobs).toHaveLength(1);
      expect(result.activeJobs[0].id).toBe('job-err');
      expect(mediaService.getPendingJobs()).toHaveLength(1);
    });

    it('should remove CANCELLED jobs from pending list', async () => {
      const pendingJobs: Job[] = [
        { id: 'job-cancelled', user_id: userId, status: JobStatus.PENDING },
      ];
      mediaService['_setPendingJobs'](pendingJobs);

      (api.getJob as vi.Mock).mockResolvedValue({
        id: 'job-cancelled',
        status: JobStatus.CANCELLED,
      });

      const result = await mediaService.checkJobStatus(userId);

      expect(result.failedJobs).toHaveLength(1); // Treat cancelled as failed/removed
      expect(result.failedJobs[0].id).toBe('job-cancelled');
      expect(mediaService.getPendingJobs()).toHaveLength(0);
    });

    it('should remove jobs that return 404 Not Found', async () => {
      const pendingJobs: Job[] = [
        { id: 'job-gone', user_id: userId, status: JobStatus.PENDING },
      ];
      mediaService['_setPendingJobs'](pendingJobs);

      const notFoundError = new Error('HTTP error! status: 404');
      (api.getJob as vi.Mock).mockRejectedValue(notFoundError);

      const result = await mediaService.checkJobStatus(userId);

      expect(result.failedJobs).toHaveLength(1);
      expect(result.failedJobs[0].id).toBe('job-gone');
      expect(mediaService.getPendingJobs()).toHaveLength(0);
    });
  });

  describe('generate functions', () => {
    const projectId = 'proj-g';

    it('generateMusic should call api and add to pending jobs', async () => {
      const request: GenerateMusicRequest = { prompt: 'test' };
      const job = { id: 'music-job', status: JobStatus.PENDING };
      (api.generateMusic as vi.Mock).mockResolvedValue(job);

      const result = await mediaService.generateMusic(projectId, request);

      expect(api.generateMusic).toHaveBeenCalledWith(projectId, request);
      expect(result).toEqual(job);
      expect(mediaService.getPendingJobs()).toContainEqual(job);
    });

    it('generateImageWithImagen should call api and add to pending jobs', async () => {
      const request: GenerateImageWithImagenRequest = { prompt: 'test' };
      const job = { id: 'imagen-job', status: JobStatus.PENDING };
      (api.generateImageWithImagen as vi.Mock).mockResolvedValue(job);

      const result = await mediaService.generateImageWithImagen(
        projectId,
        request,
      );

      expect(api.generateImageWithImagen).toHaveBeenCalledWith(
        projectId,
        request,
      );
      expect(result).toEqual(job);
      expect(mediaService.getPendingJobs()).toContainEqual(job);
    });

    it('generateImageWithGemini should call api and add to pending jobs', async () => {
      const request: GenerateImageWithGeminiRequest = { prompt: 'test' };
      const job = { id: 'gemini-job', status: JobStatus.PENDING };
      (api.generateImageWithGemini as vi.Mock).mockResolvedValue(job);

      const result = await mediaService.generateImageWithGemini(
        projectId,
        request,
      );

      expect(api.generateImageWithGemini).toHaveBeenCalledWith(
        projectId,
        request,
      );
      expect(result).toEqual(job);
      expect(mediaService.getPendingJobs()).toContainEqual(job);
    });

    it('generateVideo should call api and add to pending jobs', async () => {
      const request: GenerateVideoRequest = { prompt: 'test' };
      const job = { id: 'video-job', status: JobStatus.PENDING };
      (api.generateVideo as vi.Mock).mockResolvedValue(job);

      const result = await mediaService.generateVideo(projectId, request);

      expect(api.generateVideo).toHaveBeenCalledWith(projectId, request);
      expect(result).toEqual(job);
      expect(mediaService.getPendingJobs()).toContainEqual(job);
    });

    it('generateSpeech should call api and add to pending jobs', async () => {
      const request: GenerateSpeechSingleSpeakerRequest = { text: 'test' };
      const job = { id: 'speech-job', status: JobStatus.PENDING };
      (api.generateSpeech as vi.Mock).mockResolvedValue(job);

      const result = await mediaService.generateSpeech(projectId, request);

      expect(api.generateSpeech).toHaveBeenCalledWith(projectId, request);
      expect(result).toEqual(job);
      expect(mediaService.getPendingJobs()).toContainEqual(job);
    });
  });
});
