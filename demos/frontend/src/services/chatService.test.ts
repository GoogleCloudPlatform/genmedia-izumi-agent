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
import chatService from './chatService';
import { api } from './api';
import type { ChatMessage } from '../data/types';

vi.mock('./api', () => ({
  api: {
    getChatMessages: vi.fn(),
    createChatSession: vi.fn(),
    sendMessage: vi.fn(),
  },
}));

describe('chatService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Assuming chatService has a way to clear its cache for tests
    chatService['_clearCache']();
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
});
