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

import type { ChatMessage, ChatSession, ChatApiResponse } from '../data/types';
import { api } from './api';
import projectService from './projectService';

const DEFAULT_APP_NAME = 'creative_toolbox';

// Cache to store chat messages by session ID to avoid reloading when switching views
const messageCache = new Map<string, ChatMessage[]>();

/**
 * Converts a URL-safe Base64 string to a standard Base64 string.
 * The backend may return Base64 encoded images with URL-safe characters ('-' instead of '+' and '_' instead of '/').
 * Browsers require standard Base64 characters for `data:image/...;base64,` URIs.
 * @param str The URL-safe Base64 string.
 * @returns The standard Base64 string.
 */
const fixBase64 = (str: string) => {
  return str.replace(/-/g, '+').replace(/_/g, '/');
};

const chatService = {
  getChatSessionMessages: async (
    projectId: string,
    appName: string | undefined,
    chatSessionId: string,
    forceRefresh: boolean = false,
  ): Promise<ChatMessage[]> => {
    const app = appName || DEFAULT_APP_NAME;
    const cacheKey = `${projectId}:${app}:${chatSessionId}`;

    if (!forceRefresh && messageCache.has(cacheKey)) {
      return messageCache.get(cacheKey)!;
    }

    const response = await api.getChatMessages(projectId, app, chatSessionId);

    // Map ChatApiResponse back to ChatMessage.
    const messages = response.events
      .map((event: ChatApiResponse, index: number) => {
        let text = '';
        const attachments: NonNullable<ChatMessage['attachments']> = [];

        if (event.content?.parts) {
          for (const part of event.content.parts) {
            if (part.text) {
              // Try to parse the text as JSON to see if it contains inlineData
              try {
                const parsedText = JSON.parse(part.text);
                if (parsedText.inlineData) {
                  const mimeType = parsedText.inlineData.mimeType;
                  const type = mimeType.startsWith('image/') ? 'image' : 'file';
                  attachments.push({
                    type,
                    url: `data:${mimeType};base64,${fixBase64(parsedText.inlineData.data)}`,
                    name:
                      parsedText.inlineData.displayName ||
                      (type === 'image' ? 'Image' : 'File'),
                  });
                  continue;
                }
              } catch {
                // Ignore
              }
              text += part.text;
            }
            if (part.inlineData) {
              const mimeType = part.inlineData.mimeType;
              const type = mimeType.startsWith('image/') ? 'image' : 'file';
              attachments.push({
                type,
                url: `data:${mimeType};base64,${fixBase64(part.inlineData.data)}`,
                name:
                  part.inlineData.displayName ||
                  (type === 'image' ? 'Image' : 'File'),
              });
            }
          }
        }

        return {
          id: `msg-${index}`,
          sender: event.author === 'user' ? 'user' : 'gemini',
          text: text,
          timestamp: new Date().toISOString(),
          attachments: attachments.length > 0 ? attachments : undefined,
        };
      })
      .filter(
        (msg: ChatMessage) =>
          msg.text || (msg.attachments && msg.attachments.length > 0),
      );

    messageCache.set(cacheKey, messages);
    return messages;
  },

  createSession: async (
    projectId: string,
    appName?: string,
  ): Promise<ChatSession> => {
    const app = appName || DEFAULT_APP_NAME;
    const backendSession = await api.createChatSession(projectId, app);

    projectService.invalidateChatSessionsCache(projectId);

    const cacheKey = `${projectId}:${app}:${backendSession.id}`;
    messageCache.set(cacheKey, []);

    return {
      id: backendSession.id,
      title: backendSession.name,
      messages: [],
      lastUpdated: new Date().toISOString(),
      appName: app,
    };
  },

  sendMessage: async (
    projectId: string,
    appName: string | undefined,
    chatSessionId: string,
    userMessage: ChatMessage,
    files: File[] = [],
    onPartialUpdate?: (partialMessage: ChatMessage, isFinal: boolean) => void,
  ): Promise<ChatMessage> => {
    const app = appName || DEFAULT_APP_NAME;
    const cacheKey = `${projectId}:${app}:${chatSessionId}`;

    const updateCache = (msg: ChatMessage) => {
      const currentCache = messageCache.get(cacheKey) || [];
      const existingMsgIndex = currentCache.findIndex((m) => m.id === msg.id);
      if (existingMsgIndex !== -1) {
        currentCache[existingMsgIndex] = msg;
        messageCache.set(cacheKey, [...currentCache]);
      } else {
        messageCache.set(cacheKey, [...currentCache, msg]);
      }
    };

    updateCache(userMessage);

    const result = await new Promise<ChatMessage>((resolve, reject) => {
      let fullText = '';
      let responseId = `msg-${Date.now()}-response`;
      let messageCount = 0;

      api.sendMessage(projectId, app, chatSessionId, userMessage.text, files, {
        onMessage: (messageData: ChatApiResponse) => {
          const contentParts = messageData.content?.parts || [];
          const hasText = contentParts.some((p) => p.text);

          if (!messageData.partial) {
            if (fullText) {
              updateCache({
                id: responseId,
                sender: 'gemini',
                text: fullText,
                timestamp: new Date().toISOString(),
              });
            }
            fullText = '';
            messageCount++;
            responseId = `msg-${Date.now()}-response-${messageCount}`;

            if (onPartialUpdate) {
              onPartialUpdate(
                {
                  id: responseId,
                  sender: 'gemini',
                  text: '',
                  timestamp: new Date().toISOString(),
                },
                true,
              );
            }
          } else if (hasText) {
            const partialText = contentParts
              .filter((p) => p.text)
              .map((p) => p.text)
              .join('');

            if (partialText) {
              fullText += partialText;
              if (onPartialUpdate) {
                onPartialUpdate(
                  {
                    id: responseId,
                    sender: 'gemini',
                    text: fullText,
                    timestamp: new Date().toISOString(),
                  },
                  false,
                );
              }
            }
          }
        },
        onClose: () => {
          resolve({
            id: responseId,
            sender: 'gemini',
            text: fullText,
            timestamp: new Date().toISOString(),
          });
        },
        onError: (err: unknown) => {
          reject(err);
        },
      });
    });

    updateCache(result);

    return result;
  },
};

export default chatService;

if (import.meta.env.MODE === 'test') {
  Object.assign(chatService, {
    _clearCache: () => messageCache.clear(),
    _getCache: (key: string) => messageCache.get(key),
    _setCache: (key: string, messages: ChatMessage[]) => {
      messageCache.set(key, messages);
    },
  });
}
