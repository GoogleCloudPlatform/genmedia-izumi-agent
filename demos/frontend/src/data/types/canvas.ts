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

import type { Asset } from './assets';

export interface Trim {
  offset_seconds: number;
  duration_seconds: number;
}

export interface VideoClip {
  asset: Asset | null;
  trim: Trim | null;
  volume: number;
  first_frame_asset: Asset | null;
  last_frame_asset: Asset | null;
  placeholder: string | null;
}

export interface AudioClip {
  start_at: { video_clip_index: number; offset_seconds: number };
  asset: Asset;
  trim: Trim | null;
  volume: number;
  fade_in_duration_seconds: number;
  fade_out_duration_seconds: number;
  placeholder: string | null;
}

export interface Transition {
  type: 'none' | 'fade';
  duration_seconds: number;
}

export interface VideoTimelineContent {
  title: string;
  video_clips: VideoClip[];
  audio_clips: AudioClip[];
  transitions: Transition[];
  transition_in: { type: 'none' | 'fade'; duration_seconds: number } | null;
  transition_out: { type: 'none' | 'fade'; duration_seconds: number } | null;
}

export interface Canvas {
  id: string;
  name: string;
  type: 'html' | 'video_timeline';
  url?: string; // for html type
  videoTimeline?: VideoTimelineContent; // for video_timeline type (raw content)
  createdAt?: string; // ISO string
}

export interface CanvasInfo {
  id: string;
  title: string;
  user_id: string;
  canvas_type: 'video_timeline' | 'html';
  create_time?: string;
  video_timeline?: VideoTimelineContent;
}
