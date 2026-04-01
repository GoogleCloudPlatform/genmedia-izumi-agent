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

import type {
  GenerateImageWithGeminiRequest,
  GenerateImageWithImagenRequest,
  GenerateMusicRequest,
  GenerateSpeechSingleSpeakerRequest,
  GenerateVideoRequest,
} from './media';

export const JobType = {
  MEDIA_GENERATION_IMAGE: 'media_generation_image',
  MEDIA_GENERATION_VIDEO: 'media_generation_video',
  MEDIA_GENERATION_MUSIC: 'media_generation_music',
  VIDEO_STITCHING: 'video_stitching',
} as const;
export type JobType = (typeof JobType)[keyof typeof JobType];

export const JobStatus = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  CANCELLED: 'CANCELLED',
} as const;
export type JobStatus = (typeof JobStatus)[keyof typeof JobStatus];

export interface Job {
  id: string;
  user_id: string;
  job_type: JobType;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  job_input?:
    | GenerateMusicRequest
    | GenerateImageWithImagenRequest
    | GenerateImageWithGeminiRequest
    | GenerateSpeechSingleSpeakerRequest
    | GenerateVideoRequest;
  result_asset_id?: string | null;
  error_message?: string | null;
}
