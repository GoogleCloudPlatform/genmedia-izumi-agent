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
import { describe, it, expect, vi } from 'vitest';
import AudioClipItem from './AudioClipItem';
import type { AudioClip } from '../../../../data/types/canvas';
import type { Asset } from '../../../../data/types/assets';

describe('AudioClipItem', () => {
  const mockClip: AudioClip = {
    asset: {
      id: 'a1',
      mime_type: 'audio/mp3',
      file_name: 'audio.mp3',
    } as unknown as Asset,
    trim: { offset_seconds: 0, duration_seconds: 5 },
    start_at: { video_clip_index: 0, offset_seconds: 0 },
    volume: 1,
    fade_in_duration_seconds: 1,
    fade_out_duration_seconds: 1,
    placeholder: null,
  };

  it('renders the audio clip with filename', () => {
    render(<AudioClipItem clip={mockClip} startTime={0} />);
    expect(screen.getByText('audio.mp3')).toBeInTheDocument();
  });

  it('calls onClick handler', () => {
    const handleClick = vi.fn();
    render(
      <AudioClipItem clip={mockClip} startTime={0} onClick={handleClick} />,
    );

    const container = screen.getByTitle('audio.mp3');
    fireEvent.click(container);
    expect(handleClick).toHaveBeenCalledWith(mockClip);
  });
});
