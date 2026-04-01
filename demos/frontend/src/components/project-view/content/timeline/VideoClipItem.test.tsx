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

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import VideoClipItem from './VideoClipItem';
import type { VideoClip } from '../../../../data/types/canvas';
import type { Asset } from '../../../../data/types/assets';

// Mock TimelineUtils
vi.mock('./TimelineUtils', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./TimelineUtils')>();
  return {
    ...actual,
    mapAssetToProjectAsset: vi.fn().mockReturnValue({
      url: 'http://test.url/video.mp4',
      fileName: 'video.mp4',
    }),
  };
});

describe('VideoClipItem', () => {
  const mockClip: VideoClip = {
    asset: {
      id: 'v1',
      mime_type: 'video/mp4',
      file_name: 'test.mp4',
    } as unknown as Asset,
    trim: { offset_seconds: 0, duration_seconds: 5 },
    first_frame_asset: null,
    last_frame_asset: null,
    volume: 1,
    placeholder: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with fallback title if no frames or static preview image', () => {
    // In this test setup, staticPreviewAsset will be null, so it should fall back to Typography
    render(<VideoClipItem clip={mockClip} startTime={0} />);

    expect(screen.getByText('Video')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument(); // Ensure no img tag
  });

  it('calls onClick handler', () => {
    const handleClick = vi.fn();
    render(
      <VideoClipItem clip={mockClip} startTime={0} onClick={handleClick} />,
    );

    // The title will now fall back to 'Video Clip' as staticPreviewAsset is null
    const container = screen.getByTitle('Video Clip');
    fireEvent.click(container);
    expect(handleClick).toHaveBeenCalledWith(mockClip);
  });
});
