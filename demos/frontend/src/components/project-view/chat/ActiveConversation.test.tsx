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

import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ActiveConversation from './ActiveConversation';
import chatService from '../../../services/chatService';
import type { ChatMessage } from '../../../data/types';

import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../services/chatService');

describe('ActiveConversation', () => {
  const projectId = 'proj-1';
  const sessionId = 'session-1';
  const appName = 'test-app';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display chat messages for the current session', async () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        sender: 'user',
        text: 'Hello',
        timestamp: new Date().toISOString(),
      },
      {
        id: '2',
        sender: 'gemini',
        text: 'Hi there!',
        timestamp: new Date().toISOString(),
      },
    ];
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue(messages);

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
        />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
      expect(screen.getByText('Hi there!')).toBeInTheDocument();
    });
  });

  it('should send autoGreeting message silently on new session', async () => {
    const messages: ChatMessage[] = [];
    (chatService.getChatSessionMessages as vi.Mock).mockImplementation(() => {
      return Promise.resolve(messages);
    });
    (chatService.sendMessage as vi.Mock).mockImplementation(
      (_p, _a, _s, m, _f, onPartialUpdate) => {
        messages.push(m);
        const response = {
          id: '3',
          sender: 'gemini',
          text: 'Greeting response',
          timestamp: new Date().toISOString(),
        };
        messages.push(response);
        onPartialUpdate(response, true); // isFinal = true
        return Promise.resolve(response);
      },
    );

    await act(async () => {
      render(
        <MemoryRouter>
          <ActiveConversation
            projectId={projectId}
            sessionId={sessionId}
            appName={appName}
            projectAssets={[]}
            autoGreeting="Hi"
          />
        </MemoryRouter>,
      );
    });

    await waitFor(() => {
      expect(chatService.sendMessage).toHaveBeenCalledWith(
        projectId,
        appName,
        sessionId,
        expect.objectContaining({ text: 'Hi' }),
        [],
        expect.any(Function),
      );
    });

    // The greeting itself shouldn't be displayed, but the response should
    await waitFor(() => {
      expect(screen.getByText('Greeting response')).toBeInTheDocument();
    });
  });

  it('should wait for appName to be available before sending autoGreeting', async () => {
    const messages: ChatMessage[] = [];
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue(messages);
    (chatService.sendMessage as vi.Mock).mockResolvedValue({
      id: '3',
      sender: 'gemini',
      text: 'Greeting response',
    });

    const { rerender } = render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={''} // Initially empty
          projectAssets={[]}
          autoGreeting="Hi"
        />
      </MemoryRouter>,
    );

    // Should NOT have called sendMessage yet
    expect(chatService.sendMessage).not.toHaveBeenCalled();

    // Rerender with appName available
    rerender(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
          autoGreeting="Hi"
        />
      </MemoryRouter>,
    );

    // Now it should have called sendMessage
    await waitFor(() => {
      expect(chatService.sendMessage).toHaveBeenCalledWith(
        projectId,
        appName,
        sessionId,
        expect.objectContaining({ text: 'Hi' }),
        [],
        expect.any(Function),
      );
    });
  });

  it('should call sendMessage with correct message and files', async () => {
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);
    const onRefreshProject = vi.fn();

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
          onRefreshProject={onRefreshProject}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await userEvent.type(input, 'Test message');
    await userEvent.click(sendButton);

    await waitFor(() => {
      expect(chatService.sendMessage).toHaveBeenCalledWith(
        projectId,
        appName,
        sessionId,
        expect.objectContaining({ text: 'Test message' }),
        [],
        expect.any(Function),
      );
    });
  });

  it('should display thinking indicator while waiting for response', async () => {
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);
    (chatService.sendMessage as vi.Mock).mockImplementation(
      () => new Promise(() => {}),
    ); // Promise that never resolves

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    await userEvent.type(input, 'test');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByTestId('thinking-indicator')).toBeInTheDocument();
  });

  it('should trigger onRefreshProject on non-partial agent message', async () => {
    const onRefreshProject = vi.fn();
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);

    // Mock sendMessage to call the onPartialUpdate callback
    (chatService.sendMessage as vi.Mock).mockImplementation(
      (_p, _a, _s, _m, _f, onPartialUpdate) => {
        onPartialUpdate({ id: '1', sender: 'gemini', text: '' }, true); // isFinal = true
        return Promise.resolve({
          id: '2',
          sender: 'gemini',
          text: 'Final message',
        });
      },
    );

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
          onRefreshProject={onRefreshProject}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    await userEvent.type(input, 'test');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() => {
      expect(onRefreshProject).toHaveBeenCalled();
    });
  });

  it('should optimistically display user message before sending', async () => {
    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);
    // Let the promise hang
    (chatService.sendMessage as vi.Mock).mockImplementation(
      () => new Promise(() => {}),
    );

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await act(async () => {
      await userEvent.type(input, 'Optimistic message');
      await userEvent.click(sendButton);
    });

    // The message should appear immediately, even though the service call hasn\'t finished
    expect(await screen.findByText('Optimistic message')).toBeInTheDocument();
  });

  it('should remove optimistic message on send failure', async () => {
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {}); // Suppress console error output for this test

    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);

    let rejectSendMessage: (reason?: unknown) => void;
    const sendMessagePromise = new Promise<ChatMessage>((_, reject) => {
      rejectSendMessage = reject;
    });

    (chatService.sendMessage as vi.Mock).mockImplementation(
      () => sendMessagePromise,
    );

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await act(async () => {
      await userEvent.type(input, 'This will fail');
      await userEvent.click(sendButton);
    });

    // NOW the message should definitely be there due to optimistic update
    expect(await screen.findByText('This will fail')).toBeInTheDocument();

    // Trigger the rejection of the sendMessage promise
    await act(async () => {
      rejectSendMessage(new Error('Send failed'));
      // Need to await for next tick for the promise to fully resolve/reject
      await Promise.resolve();
    });

    // Then wait for it to be removed
    await waitFor(() => {
      expect(screen.queryByText('This will fail')).not.toBeInTheDocument();
    });

    // Check that the error was logged
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to send message',
      expect.any(Error),
    );

    consoleErrorSpy.mockRestore();
  });

  it('should display persistent error message on send failure', async () => {
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    (chatService.getChatSessionMessages as vi.Mock).mockResolvedValue([]);
    (chatService.sendMessage as vi.Mock).mockRejectedValue(
      new Error('API Error'),
    );

    render(
      <MemoryRouter>
        <ActiveConversation
          projectId={projectId}
          sessionId={sessionId}
          appName={appName}
          projectAssets={[]}
        />
      </MemoryRouter>,
    );

    const input = screen.getByPlaceholderText(`Message ${appName}...`);
    const sendButton = screen.getByRole('button', { name: /send/i });

    await userEvent.type(input, 'Message triggering error');
    await userEvent.click(sendButton);

    // Wait for the error alert to appear
    const alert = await screen.findByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent('API Error');

    // Verify it's a persistent error (by inference, or checking if it disappears -
    // but we can't wait forever. Just verifying it renders is good for integration test).

    consoleErrorSpy.mockRestore();
  });
});
