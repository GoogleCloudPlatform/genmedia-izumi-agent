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

export const assetsApi = {
  async getAssets(projectId: string) {
    console.log(`[API] Fetching assets for project (user_id) ${projectId}`);
    return request(`/users/${projectId}/assets`);
  },

  async createAsset(projectId: string, file: File) {
    console.log(`[API] Uploading asset for project ${projectId}: ${file.name}`);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_name', file.name);
    formData.append('mime_type', file.type);

    return request(`/users/${projectId}/assets`, {
      method: 'POST',
      body: formData,
    });
  },
};
