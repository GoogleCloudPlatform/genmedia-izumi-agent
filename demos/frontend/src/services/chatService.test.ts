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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import chatService, {
  collectReviewedGates,
  findPendingGate,
  rewriteLegacyReport,
} from './chatService';
import { api } from './api';
import type { ChatApiResponse, ChatMessage, PendingGate } from '../data/types';

vi.mock('./api', () => ({
  api: {
    getChatMessages: vi.fn(),
    createChatSession: vi.fn(),
    sendMessage: vi.fn(),
    sendFunctionResponse: vi.fn(),
    renameChatSession: vi.fn(),
    deleteChatSession: vi.fn(),
  },
}));

/** The call event a review checkpoint opens with. */
const gateCall = (id: string, name: string) =>
  ({
    author: 'ads_x',
    longRunningToolIds: [id],
    content: { parts: [{ functionCall: { id, name, args: {} } }] },
  }) as unknown as ChatApiResponse;

/** The "awaiting review" placeholder the checkpoint returns. */
const gateResponse = (id: string, name: string, stage: string) =>
  ({
    author: 'ads_x',
    content: {
      parts: [
        {
          functionResponse: {
            id,
            name,
            response: {
              status: 'succeeded',
              result: {
                status: 'awaiting_human_review',
                stage,
                message: `Review the ${stage}.`,
              },
            },
          },
        },
      ],
    },
  }) as unknown as ChatApiResponse;

/** The reviewer's verdict, which closes the checkpoint. */
const gateAnswer = (id: string, name: string) =>
  ({
    author: 'user',
    content: {
      parts: [
        {
          functionResponse: {
            id,
            name,
            response: { decision: 'accept', guidance: '' },
          },
        },
      ],
    },
  }) as unknown as ChatApiResponse;

describe('chatService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Assuming chatService has a way to clear its cache for tests
    chatService['_clearCache']();
  });

  describe('reports written by earlier builds', () => {
    const chat =
      'project/project_1792673070181/chat/46412a59-dd72-4340-baec-8a8161cafe25';
    const legacy = [
      '🎬 **Production Complete!** Cinematic magic assembled, rendered, and stitched.',
      '',
      '🚀 Deliverables Ready! Access your results in the Creative Studio:',
      '',
      `* [View Video in Creative Studio](http://localhost:5173/studio/#/${chat}?contentTab=canvas&canvasId=c1)`,
      `* [View Storyboard and timeline in Creative Studio](http://localhost:5173/studio/#/${chat}?contentTab=canvas&canvasId=c2)`,
    ].join('\n');

    const links = (text: string) => text.match(/\]\(/g)?.length ?? 0;

    it('link to the timeline and to the campaign summary canvas', () => {
      const text = rewriteLegacyReport(legacy, 'summary-1');

      expect(text).not.toContain('Creative Studio');
      expect(text).not.toContain('localhost');
      expect(text).toContain('🚀 Deliverables Ready!\n');
      expect(links(text)).toBe(2);
      expect(text).toContain(
        `* [View Video Timeline in Izumi Studio](#/${chat}?contentTab=canvas&canvasId=c1)\n` +
          `* [View Campaign Summary in Izumi Studio](#/${chat}?contentTab=canvas&canvasId=summary-1)`,
      );
    });

    it('give one link to the timeline when no summary is recorded', () => {
      const text = rewriteLegacyReport(legacy);

      expect(links(text)).toBe(1);
      expect(text).toContain(
        `[View Video Timeline in Izumi Studio](#/${chat}?contentTab=canvas&canvasId=c1)`,
      );
      expect(text).not.toContain('Creative Studio');
    });

    it('leaves other text and links alone', () => {
      const text =
        'Open the [timeline](https://cs.example.com/workbench?timelineId=1) ' +
        'in Creative Studio.';

      expect(rewriteLegacyReport(text)).toBe(text);
    });

    it('are rewritten in the agent messages of a loaded chat only', async () => {
      (api.getChatMessages as vi.Mock).mockResolvedValue({
        state: { summary_canvas_id: 'summary-1' },
        events: [
          {
            author: 'user',
            content: { parts: [{ text: 'View Video in Creative Studio' }] },
          },
          { author: 'videos_agent', content: { parts: [{ text: legacy }] } },
        ],
      });

      const [user, report] = await chatService.getChatSessionMessages(
        'proj-1',
        'ads_x',
        's-legacy',
        true,
      );

      expect(user.text).toBe('View Video in Creative Studio');
      expect(report.text).not.toContain('Creative Studio');
      expect(report.text).toContain('canvasId=summary-1');
    });
  });

  describe('renaming and deleting sessions', () => {
    it('returns the title as the server stored it', async () => {
      (api.renameChatSession as vi.Mock).mockResolvedValue({
        id: 's-1',
        title: 'Dior launch',
      });

      const title = await chatService.renameSession(
        'proj-1',
        'ads_x',
        's-1',
        '  Dior   launch ',
      );

      expect(api.renameChatSession).toHaveBeenCalledWith(
        'proj-1',
        'ads_x',
        's-1',
        '  Dior   launch ',
      );
      expect(title).toBe('Dior launch');
    });

    it('drops the cached messages of a deleted session', async () => {
      (api.getChatMessages as vi.Mock).mockResolvedValue({ events: [] });
      (api.deleteChatSession as vi.Mock).mockResolvedValue(null);
      await chatService.getChatSessionMessages('proj-1', 'ads_x', 's-del');

      await chatService.deleteSession('proj-1', 'ads_x', 's-del');
      await chatService.getChatSessionMessages('proj-1', 'ads_x', 's-del');

      expect(api.deleteChatSession).toHaveBeenCalledWith(
        'proj-1',
        'ads_x',
        's-del',
      );
      expect(api.getChatMessages).toHaveBeenCalledTimes(2);
    });
  });

  describe('getChatSessionMessages', () => {
    const projectId = 'proj-1';
    const appName = 'test-app';
    const chatSessionId = 'session-1';

    it('should fetch messages from the API if cache is empty', async () => {
      const apiResponse = {
        events: [{ author: 'gemini', content: { parts: [{ text: 'Hello' }] } }],
      };
      (api.getChatMessages as vi.Mock).mockResolvedValue(apiResponse);

      const messages = await chatService.getChatSessionMessages(
        projectId,
        appName,
        chatSessionId,
        true,
      );

      expect(api.getChatMessages).toHaveBeenCalledWith(
        projectId,
        appName,
        chatSessionId,
      );
      expect(messages).toHaveLength(1);
      expect(messages[0].text).toBe('Hello');
    });

    it('should return cached messages if forceRefresh is false', async () => {
      const projectId = 'proj-cached';
      const appName = 'cached-app';
      const chatSessionId = 'cached-session';
      const cacheKey = `${projectId}:${appName}:${chatSessionId}`;
      const cachedMessages: ChatMessage[] = [
        { id: '1', sender: 'user', text: 'Cached message', timestamp: '' },
      ];

      // Prime the cache
      chatService['_setCache'](cacheKey, cachedMessages);

      const messages = await chatService.getChatSessionMessages(
        projectId,
        appName,
        chatSessionId,
        false,
      );

      expect(api.getChatMessages).not.toHaveBeenCalled();
      expect(messages).toEqual(cachedMessages);
    });

    it('should fetch messages from the API if forceRefresh is true', async () => {
      const projectId = 'proj-refresh';
      const appName = 'refresh-app';
      const chatSessionId = 'refresh-session';
      const cacheKey = `${projectId}:${appName}:${chatSessionId}`;
      const cachedMessages: ChatMessage[] = [
        { id: '1', sender: 'user', text: 'Old message', timestamp: '' },
      ];
      const apiResponse = {
        events: [
          { author: 'gemini', content: { parts: [{ text: 'New message' }] } },
        ],
      };

      // Prime the cache
      chatService['_setCache'](cacheKey, cachedMessages);
      (api.getChatMessages as vi.Mock).mockResolvedValue(apiResponse);

      const messages = await chatService.getChatSessionMessages(
        projectId,
        appName,
        chatSessionId,
        true,
      );

      expect(api.getChatMessages).toHaveBeenCalledWith(
        projectId,
        appName,
        chatSessionId,
      );
      expect(messages[0].text).toBe('New message');
    });
  });

  describe('sendMessage', () => {
    const projectId = 'proj-1';
    const appName = 'test-app';
    const chatSessionId = 'session-1';
    const userMessage: ChatMessage = {
      id: 'user-msg',
      sender: 'user',
      text: 'Hello Gemini',
      timestamp: '',
    };

    it('should accumulate partial messages and call onPartialUpdate', async () => {
      const onPartialUpdate = vi.fn();

      (api.sendMessage as vi.Mock).mockImplementation(
        (_p, _a, _cs, _ut, _f, callbacks) => {
          callbacks.onMessage({
            partial: true,
            content: { parts: [{ text: 'Hello ' }] },
          });
          callbacks.onMessage({
            partial: true,
            content: { parts: [{ text: 'World' }] },
          });
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.sendMessage(
        projectId,
        appName,
        chatSessionId,
        userMessage,
        [],
        onPartialUpdate,
      );

      expect(onPartialUpdate).toHaveBeenCalledTimes(2);
      expect(onPartialUpdate).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ text: 'Hello ' }),
        false,
      );
      expect(onPartialUpdate).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ text: 'Hello World' }),
        false,
      );
    });

    it('should handle non-partial messages and call onPartialUpdate with isFinal:true', async () => {
      const onPartialUpdate = vi.fn();

      (api.sendMessage as vi.Mock).mockImplementation(
        (_p, _a, _cs, _ut, _f, callbacks) => {
          callbacks.onMessage({
            partial: false,
            content: { parts: [{ text: 'Tool output' }] },
          });
          callbacks.onMessage({
            partial: true,
            content: { parts: [{ text: 'Final answer' }] },
          });
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.sendMessage(
        projectId,
        appName,
        chatSessionId,
        userMessage,
        [],
        onPartialUpdate,
      );

      expect(onPartialUpdate).toHaveBeenCalledTimes(2);
      expect(onPartialUpdate).toHaveBeenNthCalledWith(
        1,
        expect.any(Object),
        true,
      );
      expect(onPartialUpdate).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ text: 'Final answer' }),
        false,
      );
    });

    it('should update message cache with user and agent messages', async () => {
      const cacheKey = `${projectId}:${appName}:${chatSessionId}`;
      (api.sendMessage as vi.Mock).mockImplementation(
        (_p, _a, _cs, _ut, _f, callbacks) => {
          callbacks.onMessage({
            partial: true,
            content: { parts: [{ text: 'Agent response' }] },
          });
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.sendMessage(
        projectId,
        appName,
        chatSessionId,
        userMessage,
      );

      const cachedMessages = chatService['_getCache'](cacheKey);
      expect(cachedMessages).toHaveLength(2);
      expect(cachedMessages[0].text).toBe('Hello Gemini');
      expect(cachedMessages[1].text).toBe('Agent response');
    });
  });

  describe('findPendingGate', () => {
    it('returns nothing when no checkpoint was opened', () => {
      expect(
        findPendingGate([
          { content: { parts: [{ text: 'Hi' }] } } as ChatApiResponse,
        ]),
      ).toBeNull();
    });

    it('finds the checkpoint a run is suspended on', () => {
      const gate = findPendingGate([
        gateCall('call-1', 'await_strategy_approval'),
        gateResponse('call-1', 'await_strategy_approval', 'strategy'),
      ]);

      expect(gate).toEqual({
        id: 'call-1',
        name: 'await_strategy_approval',
        payload: {
          status: 'awaiting_human_review',
          stage: 'strategy',
          message: 'Review the strategy.',
        },
      });
    });

    it('ignores a long-running call that is not a checkpoint', () => {
      expect(
        findPendingGate([
          gateCall('call-1', 'generate_all_media'),
          gateResponse('call-1', 'generate_all_media', 'strategy'),
        ]),
      ).toBeNull();
    });

    it('ignores a checkpoint call that is not long-running', () => {
      const call = gateCall('call-1', 'await_strategy_approval');
      expect(
        findPendingGate([
          { ...call, longRunningToolIds: [] },
          gateResponse('call-1', 'await_strategy_approval', 'strategy'),
        ]),
      ).toBeNull();
    });

    it('treats a checkpoint as closed once it has been answered', () => {
      expect(
        findPendingGate([
          gateCall('call-1', 'await_strategy_approval'),
          gateResponse('call-1', 'await_strategy_approval', 'strategy'),
          gateAnswer('call-1', 'await_strategy_approval'),
        ]),
      ).toBeNull();
    });

    it('returns the later checkpoint when an earlier one was answered', () => {
      const gate = findPendingGate([
        gateCall('call-1', 'await_strategy_approval'),
        gateResponse('call-1', 'await_strategy_approval', 'strategy'),
        gateAnswer('call-1', 'await_strategy_approval'),
        gateCall('call-2', 'await_storyboard_approval'),
        gateResponse('call-2', 'await_storyboard_approval', 'storyboard'),
      ]);

      expect(gate?.id).toBe('call-2');
      expect(gate?.payload.stage).toBe('storyboard');
    });
  });

  describe('review checkpoints', () => {
    const projectId = 'proj-gate';
    const appName = 'ads_x';
    const chatSessionId = 'session-gate';
    const gate: PendingGate = {
      id: 'call-1',
      name: 'await_storyboard_approval',
      payload: { status: 'awaiting_human_review', stage: 'storyboard' },
    };

    it('exposes the checkpoint found while loading history', async () => {
      (api.getChatMessages as vi.Mock).mockResolvedValue({
        events: [
          gateCall('call-1', 'await_storyboard_approval'),
          gateResponse('call-1', 'await_storyboard_approval', 'storyboard'),
        ],
      });

      await chatService.getChatSessionMessages(
        projectId,
        appName,
        chatSessionId,
        true,
      );

      expect(
        chatService.getPendingGate(projectId, appName, chatSessionId)?.id,
      ).toBe('call-1');
    });

    it('reports a checkpoint opened mid-stream', async () => {
      const onGate = vi.fn();
      (api.sendMessage as vi.Mock).mockImplementation(
        (_p, _a, _cs, _ut, _f, callbacks) => {
          callbacks.onMessage(gateCall('call-9', 'await_final_cut_approval'));
          callbacks.onMessage(
            gateResponse('call-9', 'await_final_cut_approval', 'final_cut'),
          );
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.sendMessage(
        projectId,
        appName,
        chatSessionId,
        { id: 'u1', sender: 'user', text: 'go', timestamp: '' },
        [],
        undefined,
        onGate,
      );

      expect(onGate).toHaveBeenCalledTimes(1);
      expect(onGate.mock.calls[0][0].id).toBe('call-9');
    });

    it('answers a checkpoint with a function response, not text', async () => {
      (api.sendFunctionResponse as vi.Mock).mockImplementation(
        (_p, _a, _cs, _fr, callbacks) => {
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.respondToGate(
        projectId,
        appName,
        chatSessionId,
        gate,
        'modify',
        'Shorten scene_2.',
      );

      expect(api.sendMessage).not.toHaveBeenCalled();
      expect(api.sendFunctionResponse).toHaveBeenCalledWith(
        projectId,
        appName,
        chatSessionId,
        {
          id: 'call-1',
          name: 'await_storyboard_approval',
          response: { decision: 'modify', guidance: 'Shorten scene_2.' },
        },
        expect.any(Object),
      );
    });

    it('clears the cached checkpoint once it has been answered', async () => {
      (api.getChatMessages as vi.Mock).mockResolvedValue({
        events: [
          gateCall('call-1', 'await_storyboard_approval'),
          gateResponse('call-1', 'await_storyboard_approval', 'storyboard'),
        ],
      });
      (api.sendFunctionResponse as vi.Mock).mockImplementation(
        (_p, _a, _cs, _fr, callbacks) => {
          callbacks.onClose();
          return Promise.resolve();
        },
      );

      await chatService.getChatSessionMessages(
        projectId,
        appName,
        chatSessionId,
        true,
      );
      await chatService.respondToGate(
        projectId,
        appName,
        chatSessionId,
        gate,
        'accept',
      );

      expect(
        chatService.getPendingGate(projectId, appName, chatSessionId),
      ).toBeNull();
    });
  });

  describe('collectReviewedGates', () => {
    it('pairs an answered checkpoint with the plan it approved', () => {
      const reviewed = collectReviewedGates([
        gateCall('call-1', 'await_strategy_approval'),
        gateResponse('call-1', 'await_strategy_approval', 'strategy'),
        gateAnswer('call-1', 'await_strategy_approval'),
      ]);

      // Keyed by the answering event, so it lands where the call was made.
      const entry = reviewed.get(2);
      expect(entry?.decision).toBe('accept');
      expect(entry?.payload.stage).toBe('strategy');
      expect(entry?.payload.message).toBe('Review the strategy.');
    });

    it('ignores a checkpoint that is still open', () => {
      const reviewed = collectReviewedGates([
        gateCall('call-1', 'await_strategy_approval'),
        gateResponse('call-1', 'await_strategy_approval', 'strategy'),
      ]);

      expect(reviewed.size).toBe(0);
    });

    it('keeps every checkpoint of a run, not just the last', () => {
      const reviewed = collectReviewedGates([
        gateCall('call-1', 'await_strategy_approval'),
        gateResponse('call-1', 'await_strategy_approval', 'strategy'),
        gateAnswer('call-1', 'await_strategy_approval'),
        gateCall('call-2', 'await_storyboard_approval'),
        gateResponse('call-2', 'await_storyboard_approval', 'storyboard'),
        gateAnswer('call-2', 'await_storyboard_approval'),
      ]);

      expect([...reviewed.values()].map((g) => g.payload.stage)).toEqual([
        'strategy',
        'storyboard',
      ]);
    });

    it('surfaces past reviews when the session is reloaded', async () => {
      (api.getChatMessages as vi.Mock).mockResolvedValue({
        events: [
          gateCall('call-1', 'await_strategy_approval'),
          gateResponse('call-1', 'await_strategy_approval', 'strategy'),
          gateAnswer('call-1', 'await_strategy_approval'),
        ],
      });

      const messages = await chatService.getChatSessionMessages(
        'proj-r',
        'ads_x',
        'session-r',
        true,
      );

      const withGate = messages.filter((m) => m.reviewedGate);
      expect(withGate).toHaveLength(1);
      expect(withGate[0].reviewedGate?.payload.stage).toBe('strategy');
    });
  });
});
