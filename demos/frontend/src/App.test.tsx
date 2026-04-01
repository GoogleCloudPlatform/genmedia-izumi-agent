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
import { act } from 'react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

vi.mock('./services/projectService.ts', async () => ({
  default: {
    getProjects: vi.fn().mockResolvedValue([]),
    getProjectById: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('./services/chatService.ts', async () => ({
  default: {
    getChatSessionMessages: vi.fn().mockResolvedValue([]),
    createSession: vi.fn().mockResolvedValue({
      id: 'new-session-id',
      title: 'New Chat',
      messages: [],
    }),
    sendMessage: vi.fn().mockResolvedValue({
      id: 'mock-message',
      sender: 'gemini',
      text: 'Mock response',
      timestamp: new Date().toISOString(),
    }),
  },
}));

vi.mock('./services/mediaService.ts', async () => ({
  default: {
    checkJobStatus: vi
      .fn()
      .mockResolvedValue({ activeJobs: [], completedJobs: [], failedJobs: [] }),
    getPendingJobs: vi.fn().mockReturnValue([]),
    generateMusic: vi.fn().mockResolvedValue({}),
    generateImageWithImagen: vi.fn().mockResolvedValue({}),
    generateImageWithGemini: vi.fn().mockResolvedValue({}),
    generateVideo: vi.fn().mockResolvedValue({}),
    generateSpeech: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('./services/userService.ts', async () => ({
  default: {
    getUser: vi.fn().mockResolvedValue({ id: 'test-user' }),
    findUserByEmail: vi.fn().mockResolvedValue({
      id: 'test-user',
      name: 'Test User',
      email: 'test@example.com',
    }),
  },
}));

vi.mock('./services/db.ts', () => ({
  init: vi.fn(),
}));

describe('App', () => {
  it('renders headline and navigates to projects', async () => {
    await act(async () => {
      render(<App />);
    });
    // Since "/" redirects to "/projects", we expect to see the projects page content.
    // However, ProjectsPage is not mocked in this test, but its children might be.
    // Actually, ProjectsPage renders TopAppBar which renders "Izumi Studio".
    const headline = screen.getByText(/Izumi Studio/i);
    expect(headline).toBeInTheDocument();
  });
});
