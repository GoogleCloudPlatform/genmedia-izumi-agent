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

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import VideoTimelineView from './VideoTimelineView';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock dependencies
vi.mock('../../../services/projectService', () => ({
  default: {
    getCanvas: vi.fn(),
  },
}));

// Mock sub-components to avoid complex rendering logic in unit test
vi.mock('./timeline/VideoClipItem', () => ({
  default: ({
    clip,
    onClick,
  }: {
    clip: unknown;
    onClick: (clip: unknown) => void;
  }) => (
    <div data-testid="video-clip" onClick={() => onClick(clip)}>
      Video Clip
    </div>
  ),
}));

vi.mock('./timeline/AudioClipItem', () => ({
  default: ({
    clip,
    onClick,
  }: {
    clip: unknown;
    onClick: (clip: unknown) => void;
  }) => (
    <div data-testid="audio-clip" onClick={() => onClick(clip)}>
      Audio Clip
    </div>
  ),
}));

describe('VideoTimelineView', () => {
  const mockCanvas = {
    id: 'canvas-1',
    name: 'Test Canvas',
    type: 'video_timeline' as const,
    videoTimeline: {
      title: 'Test Timeline',
      video_clips: [
        {
          asset: { id: 'v1', mime_type: 'video/mp4' },
          trim: { offset_seconds: 0, duration_seconds: 5 },
        },
      ],
      audio_clips: [
        {
          start_at: { video_clip_index: 0, offset_seconds: 0 },
          trim: { offset_seconds: 0, duration_seconds: 5 },
          asset: { id: 'a1', mime_type: 'audio/mp3' },
        },
      ],
      transitions: [],
      transition_in: null,
      transition_out: null,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock HTMLMediaElement methods which are not implemented in JSDOM
    window.HTMLMediaElement.prototype.load = vi.fn();
    window.HTMLMediaElement.prototype.play = vi
      .fn()
      .mockResolvedValue(undefined);
    window.HTMLMediaElement.prototype.pause = vi.fn();
  });

  it('renders without crashing and displays title', async () => {
    render(
      <MemoryRouter initialEntries={['/project/1']}>
        <Routes>
          <Route
            path="/project/:id"
            element={<VideoTimelineView canvas={mockCanvas} onBack={vi.fn()} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('Test Timeline')).toBeInTheDocument();
    expect(screen.getByText(/Total Duration:/)).toBeInTheDocument();
  });

  it('displays preview placeholder initially', () => {
    render(
      <MemoryRouter initialEntries={['/project/1']}>
        <Routes>
          <Route
            path="/project/:id"
            element={<VideoTimelineView canvas={mockCanvas} onBack={vi.fn()} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(
      screen.getByText('Click on a video or audio clip to preview it'),
    ).toBeInTheDocument();
  });

  it('updates preview when a clip is clicked', async () => {
    render(
      <MemoryRouter initialEntries={['/project/1']}>
        <Routes>
          <Route
            path="/project/:id"
            element={<VideoTimelineView canvas={mockCanvas} onBack={vi.fn()} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    const videoClip = screen.getByTestId('video-clip');
    fireEvent.click(videoClip);

    // Check if preview area updated (looking for trim info or similar)
    // Since we mocked VideoClipItem, the clip data passed to onClick comes from the mockCanvas prop
    // The real VideoTimelineView uses the 'content' state.
    // Our mock VideoClipItem onClick calls the prop passed to it.

    // Wait for the "Clip Details" text which appears in the side panel when a clip is selected
    await waitFor(() => {
      expect(screen.getByText('Clip Details')).toBeInTheDocument();
    });
  });

  it('renders version dropdown for multi-version assets', async () => {
    const multiVersionCanvas = {
      ...mockCanvas,
      videoTimeline: {
        ...mockCanvas.videoTimeline,
        video_clips: [
          {
            asset: {
              id: 'v1',
              mime_type: 'video/mp4',
              current_version: 2,
              versions: [
                { version_number: 1, create_time: '2023-01-01' },
                { version_number: 2, create_time: '2023-01-02' },
              ],
            },
            trim: { offset_seconds: 0, duration_seconds: 5 },
          },
        ],
      },
    };

    render(
      <MemoryRouter initialEntries={['/project/1']}>
        <Routes>
          <Route
            path="/project/:id"
            element={
              <VideoTimelineView canvas={multiVersionCanvas} onBack={vi.fn()} />
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    const videoClip = screen.getByTestId('video-clip');
    fireEvent.click(videoClip);

    await waitFor(() => {
      expect(screen.getByLabelText('Version')).toBeInTheDocument();
    });
  });
});
