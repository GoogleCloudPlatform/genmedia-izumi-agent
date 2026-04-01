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
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AssetModal from './AssetModal';
import projectService from '../../services/projectService';

// Mock projectService
vi.mock('../../services/projectService', () => ({
  default: {
    getAssetTextContent: vi.fn(),
  },
}));

describe('AssetModal', () => {
  const mockOnClose = vi.fn();
  const mockOnNavigate = vi.fn();
  const mockOnAssetClick = vi.fn();

  const mockAssets = [
    {
      id: '1',
      type: 'image' as const,
      url: 'http://example.com/assets/1/view?version=1',
      fileName: 'image.png',
      currentVersion: 1,
      versions: [
        {
          asset_id: '1',
          version_number: 1,
          gcs_uri: 'gs://test/1.png',
          create_time: '2023-01-01',
          image_generate_config: { model: 'imagen-1', prompt: 'v1 prompt' },
        },
        {
          asset_id: '1',
          version_number: 2,
          gcs_uri: 'gs://test/1_v2.png',
          create_time: '2023-01-02',
          image_generate_config: { model: 'imagen-2', prompt: 'v2 prompt' },
        },
      ],
    },
    {
      id: '2',
      type: 'text' as const,
      url: 'http://example.com/assets/2/view?version=1',
      fileName: 'text.txt',
      currentVersion: 1,
      versions: [],
    },
    {
      id: '3',
      type: 'video' as const,
      url: 'http://example.com/assets/3/view?version=1',
      fileName: 'video.mp4',
      currentVersion: 1,
      versions: [],
    },
  ];

  // New mock asset with multiple versions for specific testing
  const assetWithMultipleVersions = {
    id: '4',
    type: 'image' as const,
    url: 'http://example.com/multi_image.png?version=3',
    fileName: 'multi_image.png',
    currentVersion: 3,
    versions: [
      {
        asset_id: '4',
        version_number: 1,
        gcs_uri: 'gs://test/multi_image_v1.png',
        create_time: '2023-01-01',
        image_generate_config: { model: 'imagen-multi-1', prompt: 'multi v1' },
      },
      {
        asset_id: '4',
        version_number: 2,
        gcs_uri: 'gs://test/multi_image_v2.png',
        create_time: '2023-01-02',
        image_generate_config: { model: 'imagen-multi-2', prompt: 'multi v2' },
      },
      {
        asset_id: '4',
        version_number: 3,
        gcs_uri: 'gs://test/multi_image_v3.png',
        create_time: '2023-01-03',
        image_generate_config: { model: 'imagen-multi-3', prompt: 'multi v3' },
      },
    ],
  };

  const allMockAssets = [...mockAssets, assetWithMultipleVersions];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when open is false', () => {
    render(
      <AssetModal
        open={false}
        onClose={mockOnClose}
        asset={mockAssets[0]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    expect(screen.queryByText('image.png')).not.toBeInTheDocument();
  });

  it('should render image asset correctly', () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[0]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    expect(screen.getByText('image.png')).toBeInTheDocument();
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
    const img = screen.getByAltText('asset');
    expect(img).toHaveAttribute(
      'src',
      'http://example.com/assets/1/view?version=1',
    );
  });

  it('should fetch and render text content for text assets', async () => {
    const mockTextContent = 'This is some text content';
    (projectService.getAssetTextContent as vi.Mock).mockResolvedValue(
      mockTextContent,
    );

    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[1]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // Should show loading initially? Or waits?
    // The component sets loadingText state.
    // We wait for the text to appear.
    await waitFor(() => {
      expect(projectService.getAssetTextContent).toHaveBeenCalledWith(
        'http://example.com/assets/2/view?version=1',
      );
      expect(screen.getByText(mockTextContent)).toBeInTheDocument();
    });
  });

  it('should render video asset correctly', () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[2]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // HTMLMediaElement is hard to fully test in jsdom, but we can check the tag presence
    // querySelector logic might be needed as there is no standard role for video without controls/aria
    // The component uses <video controls ... />
    // We can try looking for the source or the container.
    // Or check by display name
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
  });

  it('should handle navigation clicks', async () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[0]} // First asset
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // First asset: Prev disabled, Next enabled
    const nextButtons = screen
      .getAllByRole('button')
      .filter((b) => b.querySelector('svg[data-testid="ArrowForwardIosIcon"]'));

    // Note: Material UI IconButton might render multiple times due to responsiveness or structure?
    // In the component:
    // Prev Button has ArrowBackIosNewIcon
    // Next Button has ArrowForwardIosIcon

    // Let's try firing clicks if enabled
    // The component disables the button.

    // We can use userEvent to click "next"
    // We need to identify it.
    // Using the svg icon inside button is a common strategy if no aria-label is unique.
    // The component code doesn't have aria-labels on these nav buttons explicitly shown in snippet,
    // actually wait, the snippet shows:
    /*
    <IconButton onClick={() => onNavigate('prev')} disabled={!hasPrev} ...>
       <ArrowBackIosNewIcon fontSize="large" />
    </IconButton>
    */

    // We can grab by the Icon existence.
    const nextBtn = nextButtons[0]; // Assuming only one visible or all do same
    expect(nextBtn).not.toBeDisabled();

    await userEvent.click(nextBtn);
    expect(mockOnNavigate).toHaveBeenCalledWith('next');
  });

  it('should handle keyboard navigation', async () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[1]} // Middle asset
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(mockOnNavigate).toHaveBeenCalledWith('next');

    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(mockOnNavigate).toHaveBeenCalledWith('prev');
  });

  it('should close when close button is clicked', async () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={allMockAssets[0]}
        allAssets={allMockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // The close button usually is top right with CloseIcon
    const closeButtons = screen
      .getAllByRole('button')
      .filter((b) => b.querySelector('svg[data-testid="CloseIcon"]'));
    await userEvent.click(closeButtons[0]);
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should allow switching between versions and update content/config', async () => {
    const asset = assetWithMultipleVersions;
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={asset}
        allAssets={allMockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // Initial render: should show current version (v3) content and config
    const img = screen.getByAltText('asset');
    expect(img).toHaveAttribute(
      'src',
      'http://example.com/multi_image.png?version=3',
    );
    expect(screen.getByText('imagen-multi-3')).toBeInTheDocument();
    expect(screen.getByText('multi v3')).toBeInTheDocument();

    // Open the version select dropdown
    const select = screen.getByLabelText('Version');
    await userEvent.click(select);

    // Select version 1
    await userEvent.click(screen.getByText('Version 1'));

    // Content should update to version 1
    await waitFor(() => {
      expect(img).toHaveAttribute(
        'src',
        'http://example.com/multi_image.png?version=1',
      );
      expect(screen.getByText('imagen-multi-1')).toBeInTheDocument();
      expect(screen.getByText('multi v1')).toBeInTheDocument();
    });
  });

  it('should not show loading spinner if image is cached (complete=true)', async () => {
    // Mock HTMLImageElement.complete to return true
    const originalCompleteDescriptor = Object.getOwnPropertyDescriptor(
      HTMLImageElement.prototype,
      'complete',
    );

    Object.defineProperty(HTMLImageElement.prototype, 'complete', {
      get: () => true,
      configurable: true,
    });

    // Verify mock
    const testImg = document.createElement('img');
    if (!testImg.complete) {
      throw new Error('Mock for HTMLImageElement.complete failed');
    }

    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[0]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    // Spinner is CircularProgress. We can look for it by role 'progressbar' usually,
    // or just check if it exists.
    // Since complete is true, the effect should set isMediaLoading(false) immediately (or not set true).
    // Actually, my code sets true in effect IF not complete.
    // Wait, my code:
    /*
      if (asset.type === 'image' && element instanceof HTMLImageElement && element.complete) {
        setIsMediaLoading(false);
        return;
      }
      setIsMediaLoading(true);
    */
    // So if complete is true, it sets false (which is default anyway, but ensures reset).
    // So spinner should NOT be present.
    await waitFor(() => {
      const spinner = screen.queryByRole('progressbar');
      expect(spinner).not.toBeInTheDocument();
    });

    // Restore
    if (originalCompleteDescriptor) {
      Object.defineProperty(
        HTMLImageElement.prototype,
        'complete',
        originalCompleteDescriptor,
      );
    }
  });

  it('should render download button with correct URL', () => {
    render(
      <AssetModal
        open={true}
        onClose={mockOnClose}
        asset={mockAssets[0]}
        allAssets={mockAssets}
        onNavigate={mockOnNavigate}
        onAssetClick={mockOnAssetClick}
      />,
    );

    const downloadBtn = screen.getByTitle('Download Asset');
    expect(downloadBtn).toBeInTheDocument();
    expect(downloadBtn).toHaveAttribute(
      'href',
      'http://example.com/assets/1/download?version=1',
    );
  });
});
