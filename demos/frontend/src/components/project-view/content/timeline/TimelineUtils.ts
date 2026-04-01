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
  Asset,
  ProjectAsset,
  AssetVersion,
  AssetGenerateConfig,
} from '../../../../data/types/assets';
import type { AudioClip, VideoClip } from '../../../../data/types/canvas';
import { API_BASE_URL } from '../../../../services/api/client';

export const RULER_HEIGHT = 15;
export const TRACK_HEIGHT = 80; // For video tracks
export const AUDIO_TRACK_HEIGHT = 60; // For audio tracks
export const PIXELS_PER_SECOND = 60; // Increased resolution for finer control

// Helper to format seconds as MM:SS
export const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

export const getClipDuration = (clip: VideoClip | AudioClip): number => {
  // 1. Use explicit trim duration if available
  if (clip.trim && typeof clip.trim.duration_seconds === 'number') {
    return clip.trim.duration_seconds;
  }

  // 2. Try to get duration from AssetVersion (API source of truth)
  if (clip.asset) {
    const currentVersion =
      clip.asset.versions?.find(
        (v) => v.version_number === clip.asset!.current_version,
      ) || clip.asset.versions?.[0];

    if (
      currentVersion?.duration_seconds !== undefined &&
      currentVersion?.duration_seconds !== null
    ) {
      return Number(currentVersion.duration_seconds);
    }

    if (currentVersion?.video_generate_config?.duration_seconds) {
      return Number(currentVersion.video_generate_config.duration_seconds);
    }
  }

  // 3. Fallback
  return 5;
};

// Helper to convert Asset to ProjectAsset for rendering in previews
export const mapAssetToProjectAsset = (asset: Asset): ProjectAsset => {
  const currentVersion =
    asset.versions?.find(
      (v: AssetVersion) => v.version_number === asset.current_version,
    ) || asset.versions?.[0];

  const generateConfig = currentVersion
    ? currentVersion.image_generate_config ||
      currentVersion.music_generate_config ||
      currentVersion.video_generate_config ||
      currentVersion.speech_generate_config ||
      currentVersion.text_generate_config
    : null;

  return {
    id: asset.id,
    type: asset.mime_type.startsWith('video')
      ? 'video'
      : asset.mime_type.startsWith('audio')
        ? 'audio'
        : asset.mime_type.startsWith('image')
          ? 'image'
          : asset.mime_type.startsWith('text')
            ? 'text'
            : 'binary',
    url: `${API_BASE_URL}/users/${asset.user_id}/assets/${asset.id}/view?version=${asset.current_version}`,
    fileName: asset.file_name,
    generateConfig: generateConfig as AssetGenerateConfig | null,
    currentVersion: asset.current_version,
    versions: asset.versions || [],
  };
};

// Helper to organize audio clips into non-overlapping tracks
// Returns an array of arrays, where each inner array is a track containing clips and their start times
export const organizeAudioTracks = (
  clips: AudioClip[],
  videoClipStartTimes: number[],
): { clip: AudioClip; startTime: number }[][] => {
  const tracks: { clip: AudioClip; startTime: number }[][] = [];

  // Calculate absolute start and end times for all clips first
  const positionedClips = clips
    .map((clip) => {
      const videoStartIndex = clip.start_at.video_clip_index;
      const videoStartTime = videoClipStartTimes[videoStartIndex] ?? 0;
      const startTime = videoStartTime + clip.start_at.offset_seconds;
      const endTime = startTime + getClipDuration(clip);
      return { clip, startTime, endTime };
    })
    .sort((a, b) => a.startTime - b.startTime); // Sort by start time

  // Place clips into tracks
  positionedClips.forEach((item) => {
    let placed = false;

    // Try to fit in existing tracks
    for (const track of tracks) {
      const lastClipInTrack = track[track.length - 1];
      // Check if this clip starts after the last one ends (with a tiny buffer)
      if (
        item.startTime >=
        getClipDuration(lastClipInTrack.clip) + lastClipInTrack.startTime
      ) {
        track.push(item);
        placed = true;
        break;
      }
    }

    // If it doesn't fit in any existing track, create a new one
    if (!placed) {
      tracks.push([item]);
    }
  });

  return tracks;
};
