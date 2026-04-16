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

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import GenerateInterface from './GenerateInterface';
import mediaService from '../../../services/mediaService';
import projectService from '../../../services/projectService';

// Mock services
vi.mock('../../../services/mediaService');
vi.mock('../../../services/projectService');

// Mock child components
vi.mock('../../shared/ImageUpload', () => ({
  default: ({ onUpload }) => (
    <div data-testid="mock-image-upload">
      <button onClick={() => onUpload(new File([''], 'test.png'))}>
        Upload
      </button>
    </div>
  ),
}));

describe('GenerateInterface', () => {
  const projectId = 'test-project';
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock successful generation calls
    (mediaService.generateImageWithImagen as vi.Mock).mockResolvedValue({
      jobId: 'imagen-job',
    });
    (mediaService.generateImageWithGemini as vi.Mock).mockResolvedValue({
      jobId: 'gemini-job',
    });
    (mediaService.generateVideo as vi.Mock).mockResolvedValue({
      jobId: 'video-job',
    });
    (mediaService.generateMusic as vi.Mock).mockResolvedValue({
      jobId: 'music-job',
    });
    (mediaService.generateSpeech as vi.Mock).mockResolvedValue({
      jobId: 'speech-job',
    });
    (projectService.uploadAsset as vi.Mock).mockResolvedValue({
      fileName: 'uploaded.png',
    });
  });
  const renderComponent = (initialModality = 'image') => {
    return render(
      <MemoryRouter>
        <GenerateInterface
          projectId={projectId}
          initialModality={initialModality}
        />
      </MemoryRouter>,
    );
  };

  it('should preserve form state when switching between modalities', async () => {
    renderComponent();

    // Interact with Image form
    const imagePrompt = screen.getByLabelText('Prompt');
    await userEvent.type(imagePrompt, 'An astronaut riding a horse');
    expect(imagePrompt).toHaveValue('An astronaut riding a horse');

    // Switch to Video
    const videoTab = screen.getByRole('button', { name: /video/i });
    await userEvent.click(videoTab);

    // Interact with Video form
    const videoPrompt = screen.getByLabelText('Prompt'); // This will be a new prompt field
    await userEvent.type(videoPrompt, 'A dog skateboarding');
    expect(videoPrompt).toHaveValue('A dog skateboarding');

    // Switch back to Image
    const imageTab = screen.getByRole('button', { name: /image/i });
    await userEvent.click(imageTab);

    // Verify Image prompt is preserved
    const preservedImagePrompt = screen.getByLabelText('Prompt');
    expect(preservedImagePrompt).toHaveValue('An astronaut riding a horse');
  }, 10000);

  it('should disable Generate button if prompt is empty', async () => {
    renderComponent();
    const generateButton = screen.getByRole('button', { name: /generate/i });
    expect(generateButton).toBeDisabled();

    const imagePrompt = screen.getByLabelText('Prompt');
    await userEvent.type(imagePrompt, '   '); // Whitespace
    expect(generateButton).toBeDisabled();

    await userEvent.type(imagePrompt, 'Not empty');
    expect(generateButton).not.toBeDisabled();
  });

  it('should call correct mediaService function for each modality', async () => {
    renderComponent();

    // Image (Gemini is default)
    let promptInput = screen.getByLabelText('Prompt');

    await userEvent.type(promptInput, 'A cat');
    let generateButton = screen.getByRole('button', { name: /generate/i });
    await userEvent.click(generateButton);
    await waitFor(() =>
      expect(mediaService.generateImageWithGemini).toHaveBeenCalledWith(
        projectId,
        expect.objectContaining({
          prompt: 'A cat',
          model: 'gemini-2.5-flash-image',
        }),
      ),
    );
    await waitFor(() => expect(generateButton).not.toBeDisabled());

    // Video
    await userEvent.click(screen.getByRole('button', { name: /video/i }));
    promptInput = screen.getByLabelText('Prompt'); // Get fresh prompt input
    await userEvent.type(promptInput, 'A dog');
    generateButton = screen.getByRole('button', { name: /generate/i }); // Get fresh generate button
    await waitFor(() => expect(generateButton).not.toBeDisabled());
    await userEvent.click(generateButton);
    await waitFor(() => expect(mediaService.generateVideo).toHaveBeenCalled());
    await waitFor(() => expect(generateButton).not.toBeDisabled());

    // Music
    await userEvent.click(screen.getByRole('button', { name: /music/i }));
    promptInput = screen.getByLabelText('Prompt'); // Get fresh prompt input
    await userEvent.type(promptInput, 'A song');
    generateButton = screen.getByRole('button', { name: /generate/i }); // Get fresh generate button
    await waitFor(() => expect(generateButton).not.toBeDisabled());
    await userEvent.click(generateButton);
    await waitFor(() => expect(mediaService.generateMusic).toHaveBeenCalled());
    await waitFor(() => expect(generateButton).not.toBeDisabled());

    // Speech
    await userEvent.click(screen.getByRole('button', { name: /speech/i }));
    // For speech, the main input is "Text to Speak"
    const speechText = screen.getByLabelText('Text to Speak'); // Get fresh speech text input
    await userEvent.type(speechText, 'Some speech');
    generateButton = screen.getByRole('button', { name: /generate/i }); // Get fresh generate button
    await waitFor(() => expect(generateButton).not.toBeDisabled());
    await userEvent.click(generateButton);
    await waitFor(() => expect(mediaService.generateSpeech).toHaveBeenCalled());
  }, 20000);

  it('should display an error message if generation fails', async () => {
    const error = new Error('Generation failed horribly');
    (mediaService.generateImageWithGemini as vi.Mock).mockRejectedValue(error);
    renderComponent();

    const promptInput = screen.getByLabelText('Prompt');
    await userEvent.type(promptInput, 'This will fail');
    await userEvent.click(screen.getByRole('button', { name: /generate/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Generation failed horribly');
  });

  it('should display a success message on successful job initiation', async () => {
    renderComponent();

    const promptInput = screen.getByLabelText('Prompt');
    await userEvent.type(promptInput, 'A successful prompt');
    await userEvent.click(screen.getByRole('button', { name: /generate/i }));

    const successMessage = await screen.findByText(
      /Successfully started generation/,
    );
    expect(successMessage).toBeInTheDocument();
  });

  it('should allow removing a reference image', async () => {
    renderComponent();

    // 1. Upload an image using the mock
    const uploadButton = screen.getByRole('button', { name: /upload/i });
    await userEvent.click(uploadButton);

    // 2. Verify image is displayed (by alt text)
    // The mock upload uses 'test.png' as the filename
    const image = await screen.findByAltText('test.png');
    expect(image).toBeInTheDocument();

    // 3. Find and click the remove button
    const removeButton = screen.getByRole('button', { name: /remove image/i });
    await userEvent.click(removeButton);

    // 4. Verify image is gone
    expect(screen.queryByAltText('test.png')).not.toBeInTheDocument();
  });
});
