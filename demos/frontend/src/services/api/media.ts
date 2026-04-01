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

import { request } from './client';
import type {
  GenerateMusicRequest,
  GenerateImageWithImagenRequest,
  GenerateImageWithGeminiRequest,
  GenerateVideoRequest,
  GenerateSpeechSingleSpeakerRequest,
  Job,
} from '../../data/types';

export const mediaApi = {
  async generateMusic(
    userId: string,
    requestBody: GenerateMusicRequest,
  ): Promise<Job> {
    console.log(`[API] Generating music for user ${userId}`);
    return request(`/users/${userId}/media:generate-music`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async generateImageWithImagen(
    userId: string,
    requestBody: GenerateImageWithImagenRequest,
  ): Promise<Job> {
    console.log(`[API] Generating image with Imagen for user ${userId}`);
    return request(`/users/${userId}/media:generate-image-with-imagen`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async generateImageWithGemini(
    userId: string,
    requestBody: GenerateImageWithGeminiRequest,
  ): Promise<Job> {
    console.log(`[API] Generating image with Gemini for user ${userId}`);
    return request(`/users/${userId}/media:generate-image-with-gemini`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async generateVideo(
    userId: string,
    requestBody: GenerateVideoRequest,
  ): Promise<Job> {
    console.log(`[API] Generating video for user ${userId}`);
    return request(`/users/${userId}/media:generate-video`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async generateSpeech(
    userId: string,
    requestBody: GenerateSpeechSingleSpeakerRequest,
  ): Promise<Job> {
    console.log(`[API] Generating speech for user ${userId}`);
    return request(`/users/${userId}/media:generate-speech-single-speaker`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async getJob(userId: string, jobId: string): Promise<Job> {
    return request(`/users/${userId}/jobs/${jobId}`, {
      method: 'GET',
    });
  },
};
