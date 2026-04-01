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

export interface AssetImageGenerateConfig {
  model: string;
  prompt: string;
  reference_images?: Asset[];
}

export interface AssetVideoGenerateConfig {
  model: string;
  prompt: string;
  first_frame_asset?: Asset | null;
  last_frame_asset?: Asset | null;
  duration_seconds?: number;
}

export interface AssetSpeechGenerateConfig {
  model: string;
  prompt: string;
  voice: string;
  spoken_text: string;
}

export interface AssetMusicGenerateConfig {
  model: string;
  prompt: string;
}

export type AssetGenerateConfig =
  | AssetImageGenerateConfig
  | AssetVideoGenerateConfig
  | AssetSpeechGenerateConfig
  | AssetMusicGenerateConfig;

export interface ProjectAsset {
  id: string;
  type: 'image' | 'video' | 'audio' | 'text' | 'binary';
  url: string;
  thumbnailUrl?: string;
  fileName?: string;
  createdAt?: string; // ISO string
  generateConfig?: AssetGenerateConfig | null;
  currentVersion: number;
  versions: AssetVersion[];
  duration?: number | null;
}

export interface AssetVersion {
  asset_id: string;
  version_number: number;
  gcs_uri: string;
  create_time: string; // ISO 8601 timestamp
  image_generate_config?: AssetImageGenerateConfig | null;
  music_generate_config?: AssetMusicGenerateConfig | null;
  video_generate_config?: AssetVideoGenerateConfig | null;
  speech_generate_config?: AssetSpeechGenerateConfig | null;
  text_generate_config?: unknown | null;
  duration_seconds?: number | null;
}

export interface Asset {
  id: string;
  user_id: string;
  mime_type: string;
  file_name: string;
  current_version: number;
  versions?: AssetVersion[];
}
