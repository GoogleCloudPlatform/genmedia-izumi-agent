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
import { vi } from 'vitest';
import GenerateConfigPanel from './GenerateConfigPanel';
import type {
  AssetImageGenerateConfig,
  AssetVideoGenerateConfig,
  AssetSpeechGenerateConfig,
  AssetMusicGenerateConfig,
  Asset,
} from '../../data/types/assets';

describe('GenerateConfigPanel', () => {
  const mockAsset: Asset = {
    id: 'test-asset-id',
    user_id: 'test-user-id',
    mime_type: 'image/png',
    file_name: 'test-image.png',
    current_version: 1,
  };

  const mockOnAssetClick = vi.fn();

  beforeEach(() => {
    mockOnAssetClick.mockClear();
  });

  it('renders image generation config correctly and handles click', () => {
    const config: AssetImageGenerateConfig = {
      model: 'test-image-model',
      prompt: 'test image prompt',
      reference_images: [mockAsset],
    };

    render(
      <GenerateConfigPanel config={config} onAssetClick={mockOnAssetClick} />,
    );

    expect(screen.getByText('test-image-model')).toBeInTheDocument();
    expect(screen.getByText('test image prompt')).toBeInTheDocument();
    expect(screen.getByText('Reference Images')).toBeInTheDocument();

    const assetName = screen.getByText('test-image.png');
    expect(assetName).toBeInTheDocument();

    // Simulate click on the asset preview
    fireEvent.click(assetName);
    expect(mockOnAssetClick).toHaveBeenCalledWith('test-asset-id');
  });

  it('renders video generation config correctly', () => {
    const config: AssetVideoGenerateConfig = {
      model: 'test-video-model',
      prompt: 'test video prompt',
      first_frame_asset: mockAsset,
      last_frame_asset: {
        ...mockAsset,
        id: 'test-asset-id-2',
        file_name: 'last-frame.png',
      },
    };

    render(
      <GenerateConfigPanel config={config} onAssetClick={mockOnAssetClick} />,
    );

    expect(screen.getByText('test-video-model')).toBeInTheDocument();
    expect(screen.getByText('test video prompt')).toBeInTheDocument();
    expect(screen.getByText('Key Frames')).toBeInTheDocument();
    expect(screen.getByText('test-image.png')).toBeInTheDocument();
    expect(screen.getByText('last-frame.png')).toBeInTheDocument();
    expect(screen.getByText('First Frame')).toBeInTheDocument();
    expect(screen.getByText('Last Frame')).toBeInTheDocument();
  });

  it('renders speech generation config correctly', () => {
    const config: AssetSpeechGenerateConfig = {
      model: 'test-speech-model',
      prompt: 'test speech prompt',
      voice: 'test-voice',
      spoken_text: 'test spoken text',
    };

    render(
      <GenerateConfigPanel config={config} onAssetClick={mockOnAssetClick} />,
    );

    expect(screen.getByText('test-speech-model')).toBeInTheDocument();
    expect(screen.getByText('test-voice')).toBeInTheDocument();
    expect(screen.getByText('test spoken text')).toBeInTheDocument();
    expect(screen.getByText('Spoken Text')).toBeInTheDocument();
  });

  it('renders music generation config correctly', () => {
    const config: AssetMusicGenerateConfig = {
      model: 'test-music-model',
      prompt: 'test music prompt',
    };

    render(
      <GenerateConfigPanel config={config} onAssetClick={mockOnAssetClick} />,
    );

    expect(screen.getByText('test-music-model')).toBeInTheDocument();
    expect(screen.getByText('test music prompt')).toBeInTheDocument();
  });
});
