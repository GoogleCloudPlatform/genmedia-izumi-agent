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
import CanvasView from './CanvasView';
import type { Canvas } from '../../../data/types';

// Mock VideoTimelineView to isolate testing of CanvasView logic
vi.mock('./VideoTimelineView', () => ({
  default: ({ onBack, canvas }: { onBack: () => void; canvas: Canvas }) => (
    <div data-testid="video-timeline-view">
      Video Timeline: {canvas.name}
      <button onClick={onBack}>Back</button>
    </div>
  ),
}));

describe('CanvasView', () => {
  const mockCanvases: Canvas[] = [
    {
      id: '1',
      name: 'Project Alpha',
      type: 'video_timeline',
      createdAt: '2023-01-01',
    },
    {
      id: '2',
      name: 'Design Beta',
      type: 'html',
      url: 'http://example.com/beta',
      createdAt: '2023-01-02',
    },
  ];

  const defaultProps = {
    canvases: mockCanvases,
    selectedCanvas: null,
    onCanvasClick: vi.fn(),
    onBackToCanvasList: vi.fn(),
  };

  it('renders empty state when there are no canvases', () => {
    render(<CanvasView {...defaultProps} canvases={[]} />);
    expect(screen.getByText(/No canvases yet/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Your created canvases will appear here/i),
    ).toBeInTheDocument();
  });

  it('renders a list of canvases when selectedCanvas is null', () => {
    render(<CanvasView {...defaultProps} />);

    expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    expect(screen.getByText('Video Project')).toBeInTheDocument();

    expect(screen.getByText('Design Beta')).toBeInTheDocument();
    expect(screen.getByText('HTML Canvas')).toBeInTheDocument();
  });

  it('calls onCanvasClick when a canvas card is clicked', () => {
    render(<CanvasView {...defaultProps} />);

    fireEvent.click(screen.getByText('Project Alpha'));
    expect(defaultProps.onCanvasClick).toHaveBeenCalledWith(mockCanvases[0]);

    fireEvent.click(screen.getByText('Design Beta'));
    expect(defaultProps.onCanvasClick).toHaveBeenCalledWith(mockCanvases[1]);
  });

  it('renders VideoTimelineView when a video_timeline canvas is selected', () => {
    render(<CanvasView {...defaultProps} selectedCanvas={mockCanvases[0]} />);

    expect(screen.getByTestId('video-timeline-view')).toBeInTheDocument();
    expect(
      screen.getByText('Video Timeline: Project Alpha'),
    ).toBeInTheDocument();
  });

  it('renders HtmlCanvasDetailView when an html canvas is selected', () => {
    render(<CanvasView {...defaultProps} selectedCanvas={mockCanvases[1]} />);

    expect(screen.getByText('Back')).toBeInTheDocument();
    // Iframe might take time to load or behave differently in test env,
    // but we can check if the container renders.
    // Since we can't easily access iframe content, we check for the back button
    // which is part of the HtmlCanvasDetailView.
  });

  it('calls onBackToCanvasList when back button is clicked in VideoTimelineView', () => {
    render(<CanvasView {...defaultProps} selectedCanvas={mockCanvases[0]} />);

    fireEvent.click(screen.getByText('Back'));
    expect(defaultProps.onBackToCanvasList).toHaveBeenCalled();
  });

  it('calls onBackToCanvasList when back button is clicked in HtmlCanvasDetailView', () => {
    render(<CanvasView {...defaultProps} selectedCanvas={mockCanvases[1]} />);

    fireEvent.click(screen.getByText('Back'));
    expect(defaultProps.onBackToCanvasList).toHaveBeenCalled();
  });
});
