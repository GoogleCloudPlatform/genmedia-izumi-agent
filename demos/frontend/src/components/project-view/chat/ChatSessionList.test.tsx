/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import ChatSessionList from './ChatSessionList';
import type { ChatSession } from '../../../data/types';

const session: ChatSession = {
  id: 'c985c541-b406-46a1-88dc-070ce7828207',
  title: 'Untitled chat',
  messages: [],
  lastUpdated: '2026-10-21T20:20:00Z',
  appName: 'ads_x',
};

const renderList = (
  overrides: Partial<Parameters<typeof ChatSessionList>[0]> = {},
) => {
  const props = {
    sessions: [session],
    onSelectSession: vi.fn(),
    onNewChat: vi.fn(),
    isSelectingAgent: false,
    availableApps: [],
    onAgentSelect: vi.fn(),
    onCancelSelection: vi.fn(),
    onRenameSession: vi.fn().mockResolvedValue(undefined),
    onDeleteSession: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
  render(<ChatSessionList {...props} />);
  return props;
};

const openMenu = async (user: ReturnType<typeof userEvent.setup>) =>
  user.click(screen.getByRole('button', { name: /chat options for/i }));

describe('ChatSessionList', () => {
  it('describes when to use each agent', () => {
    renderList({
      isSelectingAgent: true,
      availableApps: ['ads_x', 'unlisted_agent'],
    });

    expect(screen.getByText(/want a finished video ad/i)).toBeInTheDocument();
    expect(screen.getByText('unlisted_agent')).toBeInTheDocument();
  });

  it('lists a chat by its title, not its id', () => {
    renderList({ sessions: [{ ...session, title: 'Dior launch' }] });

    expect(screen.getByText('Dior launch')).toBeInTheDocument();
    expect(screen.queryByText(session.id)).not.toBeInTheDocument();
  });

  it('renames a chat from its menu', async () => {
    const user = userEvent.setup();
    const props = renderList();

    await openMenu(user);
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }));
    const field = screen.getByRole('textbox', { name: 'Chat name' });
    await user.clear(field);
    await user.type(field, 'Dior launch{Enter}');

    expect(props.onRenameSession).toHaveBeenCalledWith(session, 'Dior launch');
  });

  it('abandons a rename on Escape', async () => {
    const user = userEvent.setup();
    const props = renderList();

    await openMenu(user);
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }));
    await user.type(
      screen.getByRole('textbox', { name: 'Chat name' }),
      ' draft{Escape}',
    );

    expect(props.onRenameSession).not.toHaveBeenCalled();
    expect(screen.getByText('Untitled chat')).toBeInTheDocument();
  });

  it('deletes a chat only once the deletion is confirmed', async () => {
    const user = userEvent.setup();
    const props = renderList();

    await openMenu(user);
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }));
    expect(props.onDeleteSession).not.toHaveBeenCalled();

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText(/assets it generated stay/i)).toBeVisible();
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(props.onDeleteSession).toHaveBeenCalledWith(session);
  });

  it('says so when a rename fails', async () => {
    const user = userEvent.setup();
    renderList({
      onRenameSession: vi.fn().mockRejectedValue(new Error('500')),
    });

    await openMenu(user);
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }));
    await user.type(
      screen.getByRole('textbox', { name: 'Chat name' }),
      ' 2{Enter}',
    );

    expect(
      await screen.findByText("Couldn't rename the chat. Please try again."),
    ).toBeInTheDocument();
  });
});
