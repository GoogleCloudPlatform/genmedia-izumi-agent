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

import { describe, it, expect } from 'vitest';
import { formatTime, organizeAudioTracks } from './TimelineUtils';
import type { AudioClip } from '../../../../data/types/canvas';
import type { Asset } from '../../../../data/types/assets';

describe('TimelineUtils', () => {
  describe('formatTime', () => {
    it('formats seconds to MM:SS', () => {
      expect(formatTime(0)).toBe('00:00');
      expect(formatTime(5)).toBe('00:05');
      expect(formatTime(65)).toBe('01:05');
      expect(formatTime(600)).toBe('10:00');
    });
  });

  describe('organizeAudioTracks', () => {
    it('places non-overlapping clips in the same track', () => {
      const clips: AudioClip[] = [
        {
          start_at: { video_clip_index: 0, offset_seconds: 0 },
          trim: { offset_seconds: 0, duration_seconds: 5 },
          asset: { id: '1', mime_type: 'audio/mp3' } as unknown as Asset,
        } as AudioClip,
        {
          start_at: { video_clip_index: 0, offset_seconds: 6 },
          trim: { offset_seconds: 0, duration_seconds: 5 },
          asset: { id: '2', mime_type: 'audio/mp3' } as unknown as Asset,
        } as AudioClip,
      ];
      // Assume video starts at 0
      const videoStartTimes = [0];

      const tracks = organizeAudioTracks(clips, videoStartTimes);
      expect(tracks.length).toBe(1);
      expect(tracks[0].length).toBe(2);
    });

    it('creates new tracks for overlapping clips', () => {
      const clips: AudioClip[] = [
        {
          start_at: { video_clip_index: 0, offset_seconds: 0 },
          trim: { offset_seconds: 0, duration_seconds: 10 },
          asset: { id: '1', mime_type: 'audio/mp3' } as unknown as Asset,
        } as AudioClip,
        {
          start_at: { video_clip_index: 0, offset_seconds: 5 }, // Overlaps the first one
          trim: { offset_seconds: 0, duration_seconds: 5 },
          asset: { id: '2', mime_type: 'audio/mp3' } as unknown as Asset,
        } as AudioClip,
      ];
      const videoStartTimes = [0];

      const tracks = organizeAudioTracks(clips, videoStartTimes);
      expect(tracks.length).toBe(2);
      expect(tracks[0].length).toBe(1);
      expect(tracks[1].length).toBe(1);
    });
  });
});
