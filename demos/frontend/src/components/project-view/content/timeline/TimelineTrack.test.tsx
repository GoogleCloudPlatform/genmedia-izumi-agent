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

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TimelineTrack from './TimelineTrack';

describe('TimelineTrack', () => {
  it('renders the track name', () => {
    render(
      <TimelineTrack name="Video Track" height={100}>
        <div />
      </TimelineTrack>,
    );
    expect(screen.getByText('Video Track')).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <TimelineTrack name="Track" height={100}>
        <div data-testid="track-content">Content</div>
      </TimelineTrack>,
    );
    expect(screen.getByTestId('track-content')).toBeInTheDocument();
  });

  it('applies the correct height', () => {
    const height = 150;
    const { container } = render(
      <TimelineTrack name="Track" height={height}>
        <div />
      </TimelineTrack>,
    );
    const trackContainer = container.firstChild as HTMLElement;
    expect(trackContainer).toHaveStyle(`height: ${height}px`);
  });
});
