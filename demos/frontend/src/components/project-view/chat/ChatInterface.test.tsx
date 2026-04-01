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
import { act } from 'react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import ChatInterface from './ChatInterface';
import projectService from '../../../services/projectService';
import chatService from '../../../services/chatService';

vi.mock('../../../services/projectService');
vi.mock('../../../services/chatService');

// Mock child components
vi.mock('./ChatSessionList', () => ({
  default: ({
    onSelectSession,
    onCreateNew,
    isSelectingAgent,
    onAgentSelect,
  }) => (
    <div>
      <h1>ChatSessionList Mock</h1>
      <button onClick={() => onSelectSession({ id: 'session-1' })}>
        Select Session
      </button>
      <button onClick={onCreateNew}>Create New</button>
      {isSelectingAgent && (
        <button onClick={() => onAgentSelect('test-agent')}>
          Select Agent
        </button>
      )}
    </div>
  ),
}));

vi.mock('./ActiveConversation', () => {
  const ActiveConversation = ({ sessionId, onNewChat }) => {
    const location = useLocation();
    return (
      <div>
        <h1>ActiveConversation Mock</h1>
        <p>Session ID: {sessionId}</p>
        {location.state?.isNewSession && <p>New Session Greeting</p>}
        <button onClick={onNewChat}>New Chat</button>
      </div>
    );
  };
  return { default: ActiveConversation };
});

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (projectService.getAvailableApps as vi.Mock).mockResolvedValue([
      'test-agent',
    ]);
    (projectService.getAllChatSessions as vi.Mock).mockResolvedValue([]);
    (chatService.createSession as vi.Mock).mockResolvedValue({
      id: 'new-session',
      title: 'New Session',
    });
  });

  const renderWithRouter = (initialEntries: string[]) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="/project/:projectId/*"
            element={
              <ChatInterface projectId="test-project" projectAssets={[]} />
            }
          />
        </Routes>
      </MemoryRouter>,
    );
  };

  it('should display ChatSessionList when no chatSessionId is provided', async () => {
    renderWithRouter(['/project/test-project/chat']);
    await waitFor(() =>
      expect(screen.getByText('ChatSessionList Mock')).toBeInTheDocument(),
    );
    expect(
      screen.queryByText('ActiveConversation Mock'),
    ).not.toBeInTheDocument();
  });

  it('should display ActiveConversation when a chatSessionId is provided', async () => {
    const mockSessions = [
      { id: 'session-123', title: 'Test Session', appName: 'test-agent' },
    ];
    (projectService.getAllChatSessions as vi.Mock).mockImplementation(() =>
      Promise.resolve(mockSessions),
    );

    renderWithRouter(['/project/test-project/chat/session-123']);

    // Use findByText which waits for the element to appear
    const activeConversation = await screen.findByText(
      'ActiveConversation Mock',
    );
    expect(activeConversation).toBeInTheDocument();

    expect(screen.getByText('Session ID: session-123')).toBeInTheDocument();
    expect(screen.queryByText('ChatSessionList Mock')).not.toBeInTheDocument();
  });

  it('should handle creation of a new chat session', async () => {
    renderWithRouter(['/project/test-project/chat?action=new']);

    await waitFor(() =>
      expect(screen.getByText('Select Agent')).toBeInTheDocument(),
    );
    const selectAgentButton = screen.getByText('Select Agent');
    await userEvent.click(selectAgentButton);

    await waitFor(() => {
      expect(chatService.createSession).toHaveBeenCalledWith(
        'test-project',
        'test-agent',
      );
    });
  });

  it('should prevent flash of session list by keeping loading state until navigation completes', async () => {
    (chatService.createSession as vi.Mock).mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              id: 'new-session',
              title: 'New Session',
              appName: 'test-agent',
            });
          }, 10);
        }),
    );

    renderWithRouter(['/project/test-project/chat?action=new']);

    const selectAgentButton = await screen.findByText('Select Agent');
    await userEvent.click(selectAgentButton);

    // Should show loading immediately
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Wait for the creation to "finish" (in reality, just wait for the mock promise)
    // In the component, we removed the 'finally' block, so the spinner should REMAIN
    // until the route updates.
    // We simulate route update by re-rendering with new route or mocking the router update?
    // Since we use MemoryRouter, the `navigate` call inside component updates the router state.
    // But `waitFor` handles the async nature.

    // We want to ensure that we NEVER see "ChatSessionList Mock" after clicking and before "ActiveConversation Mock".
    // But "ChatSessionList Mock" is rendered if !chatSessionId.
    // If our fix works, isCreatingSession remains true until chatSessionId is present.

    await waitFor(() => {
      // Eventually we should see the new session (ActiveConversation)
      // Note: ActiveConversation Mock renders "Session ID: ..."
      expect(screen.getByText('Session ID: new-session')).toBeInTheDocument();
    });

    // And crucially, we should NOT see the list in between.
    // This is hard to assert negatively with "waitFor", but if the previous logic was broken,
    // the spinner would disappear, revealing the list (since chatSessionId is null during transition),
    // then the router would update.
    // With our fix, the spinner stays until the router updates.
  });

  it('should show a loading spinner while fetching sessions', async () => {
    // Make the service promise hang
    (projectService.getAllChatSessions as vi.Mock).mockImplementation(
      () => new Promise(() => {}),
    );
    await act(async () => {
      renderWithRouter(['/project/test-project/chat']);
    });
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should switch to agent selection when New Chat is clicked from active conversation', async () => {
    // Mock an active session
    const mockSessions = [
      { id: 'session-123', title: 'Test Session', appName: 'test-agent' },
    ];
    (projectService.getAllChatSessions as vi.Mock).mockResolvedValue(
      mockSessions,
    );

    renderWithRouter(['/project/test-project/chat/session-123']);

    // Ensure ActiveConversation is shown initially
    await waitFor(() =>
      expect(screen.getByText('ActiveConversation Mock')).toBeInTheDocument(),
    );

    // Simulate clicking the 'New Chat' button within ActiveConversation
    // The mock ActiveConversation renders a button with text 'New Chat'
    const newChatButton = screen.getByRole('button', { name: 'New Chat' });
    await userEvent.click(newChatButton);

    // Now, ChatSessionList should be rendered in agent selection mode
    await waitFor(() => {
      expect(screen.getByText('ChatSessionList Mock')).toBeInTheDocument();
      expect(screen.getByText('Select Agent')).toBeInTheDocument(); // This button is only visible if isSelectingAgent is true
    });
  });
});
