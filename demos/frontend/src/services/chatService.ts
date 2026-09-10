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

import type {
  ChatMessage,
  ChatSession,
  ChatApiResponse,
  FunctionResponse,
  GateDecision,
  GatePayload,
  PendingGate,
  ReviewedGate,
} from '../data/types';
import type { SSECallbacks } from './api/client';
import { api } from './api';
import projectService from './projectService';

const DEFAULT_APP_NAME = 'creative_toolbox';

// Cache to store chat messages by session ID to avoid reloading when switching views
const messageCache = new Map<string, ChatMessage[]>();

// The review checkpoint each session is currently blocked on, if any.
const gateCache = new Map<string, PendingGate | null>();

/** Long-running tools that suspend the run for a human verdict. */
const GATE_TOOL_PATTERN = /^await_.+_approval$/;

/** Reads a checkpoint's "awaiting review" payload, or null if this is not one. */
function gatePayloadOf(response: FunctionResponse): GatePayload | null {
  const result = response.response?.result;
  if (!result || typeof result !== 'object') {
    return null;
  }
  const payload = result as GatePayload;
  return payload.status === 'awaiting_human_review' && payload.stage
    ? payload
    : null;
}

/**
 * Finds the checkpoints that were answered earlier in a session.
 *
 * The plan behind a decision is only ever sent once, in the pending payload,
 * and the answer arrives later as a separate response quoting the same call
 * id. Pairing the two is the only way to show a reviewer what they approved
 * after the card has closed.
 *
 * Keyed by the index of the answering event, so each one lands in the
 * transcript where the decision was actually made.
 */
export function collectReviewedGates(
  events: readonly ChatApiResponse[],
): Map<number, ReviewedGate> {
  const gateCalls = new Map<string, string>(); // call id -> tool name
  const pendingPayloads = new Map<string, GatePayload>();
  const reviewed = new Map<number, ReviewedGate>();

  events.forEach((event, index) => {
    const longRunning = new Set(event.longRunningToolIds || []);

    for (const part of event.content?.parts || []) {
      const call = part.functionCall;
      if (
        call &&
        longRunning.has(call.id) &&
        GATE_TOOL_PATTERN.test(call.name)
      ) {
        gateCalls.set(call.id, call.name);
      }

      const response = part.functionResponse;
      const name = response && gateCalls.get(response.id);
      if (!response || !name) {
        continue;
      }

      const payload = gatePayloadOf(response);
      if (payload) {
        pendingPayloads.set(response.id, payload);
        continue;
      }

      // Anything else answers the call. Without the payload from the pending
      // response there is nothing worth showing, so skip it.
      const answered = pendingPayloads.get(response.id);
      if (!answered) {
        continue;
      }
      const verdict = (response.response || {}) as Record<string, unknown>;
      reviewed.set(index, {
        id: response.id,
        name,
        payload: answered,
        decision: verdict.decision as ReviewedGate['decision'],
        guidance:
          typeof verdict.guidance === 'string' ? verdict.guidance : undefined,
      });
      pendingPayloads.delete(response.id);
    }
  });

  return reviewed;
}

/**
 * Finds the review checkpoint a run is suspended on, if any.
 *
 * A checkpoint opens as a long-running function call and stays open until a
 * function response quotes its id. The pending payload is itself a function
 * response, so a checkpoint counts as answered only once a response arrives
 * that is not another "awaiting review" placeholder.
 */
export function findPendingGate(
  events: readonly ChatApiResponse[],
): PendingGate | null {
  const gateCalls = new Map<string, string>(); // call id -> tool name
  let pending: PendingGate | null = null;

  for (const event of events) {
    const longRunning = new Set(event.longRunningToolIds || []);

    for (const part of event.content?.parts || []) {
      const call = part.functionCall;
      if (
        call &&
        longRunning.has(call.id) &&
        GATE_TOOL_PATTERN.test(call.name)
      ) {
        gateCalls.set(call.id, call.name);
      }

      const response = part.functionResponse;
      const name = response && gateCalls.get(response.id);
      if (!response || !name) {
        continue;
      }

      const payload = gatePayloadOf(response);
      if (payload) {
        pending = { id: response.id, name, payload };
      } else if (pending?.id === response.id) {
        // Anything else answers the call, so the run is no longer suspended.
        pending = null;
      }
    }
  }

  return pending;
}

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

function updateCache(cacheKey: string, msg: ChatMessage) {
  const currentCache = messageCache.get(cacheKey) || [];
  const existingMsgIndex = currentCache.findIndex((m) => m.id === msg.id);
  if (existingMsgIndex !== -1) {
    currentCache[existingMsgIndex] = msg;
    messageCache.set(cacheKey, [...currentCache]);
  } else {
    messageCache.set(cacheKey, [...currentCache, msg]);
  }
}

/**
 * Runs one turn against the agent and streams the reply into the cache.
 *
 * A turn that ends at a review checkpoint is reported through `onGate`. Only
 * checkpoints this turn opened are reported: closing one is the caller's job,
 * since the answer is what closes it.
 */
async function streamTurn(
  cacheKey: string,
  invoke: (callbacks: SSECallbacks<ChatApiResponse>) => unknown,
  onPartialUpdate?: (partialMessage: ChatMessage, isFinal: boolean) => void,
  onGate?: (gate: PendingGate) => void,
): Promise<ChatMessage> {
  const result = await new Promise<ChatMessage>((resolve, reject) => {
    const events: ChatApiResponse[] = [];
    let reportedGateId: string | null = null;
    let fullText = '';
    let responseId = `msg-${Date.now()}-response`;
    let messageCount = 0;

    invoke({
      onMessage: (messageData: ChatApiResponse) => {
        const contentParts = messageData.content?.parts || [];
        const hasText = contentParts.some((p) => p.text);

        events.push(messageData);
        const gate = findPendingGate(events);
        if (gate && gate.id !== reportedGateId) {
          reportedGateId = gate.id;
          gateCache.set(cacheKey, gate);
          onGate?.(gate);
        }

        if (!messageData.partial) {
          if (fullText) {
            updateCache(cacheKey, {
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

  updateCache(cacheKey, result);
  return result;
}

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

    // Checkpoints answered earlier, so the reviewer can look back at what
    // they approved rather than only at the verdict they gave.
    const reviewedGates = collectReviewedGates(response.events);

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
          reviewedGate: reviewedGates.get(index),
        };
      })
      .filter(
        (msg: ChatMessage) =>
          msg.text ||
          msg.reviewedGate ||
          (msg.attachments && msg.attachments.length > 0),
      );

    messageCache.set(cacheKey, messages);
    gateCache.set(cacheKey, findPendingGate(response.events));
    return messages;
  },

  /**
   * The review checkpoint this session is waiting on, as of the last load or
   * streamed turn. Call after getChatSessionMessages has resolved.
   */
  getPendingGate: (
    projectId: string,
    appName: string | undefined,
    chatSessionId: string,
  ): PendingGate | null => {
    const app = appName || DEFAULT_APP_NAME;
    return gateCache.get(`${projectId}:${app}:${chatSessionId}`) || null;
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
    onGate?: (gate: PendingGate) => void,
  ): Promise<ChatMessage> => {
    const app = appName || DEFAULT_APP_NAME;
    const cacheKey = `${projectId}:${app}:${chatSessionId}`;

    updateCache(cacheKey, userMessage);

    return streamTurn(
      cacheKey,
      (callbacks) =>
        api.sendMessage(
          projectId,
          app,
          chatSessionId,
          userMessage.text,
          files,
          callbacks,
        ),
      onPartialUpdate,
      onGate,
    );
  },

  /**
   * Answers an open review checkpoint, resuming the suspended run.
   *
   * The verdict travels as a function response quoting the call id, which is
   * the only thing that resumes the run — plain text does not, however clearly
   * it is worded.
   */
  respondToGate: async (
    projectId: string,
    appName: string | undefined,
    chatSessionId: string,
    gate: PendingGate,
    decision: GateDecision,
    guidance: string = '',
    onPartialUpdate?: (partialMessage: ChatMessage, isFinal: boolean) => void,
    onGate?: (gate: PendingGate) => void,
  ): Promise<ChatMessage> => {
    const app = appName || DEFAULT_APP_NAME;
    const cacheKey = `${projectId}:${app}:${chatSessionId}`;

    // The checkpoint is answered the moment the request goes out; anything the
    // resumed run opens afterwards is a new one.
    gateCache.set(cacheKey, null);

    // Leave the answered checkpoint in the transcript rather than a bare
    // verdict, so what was approved stays readable without a reload.
    const verdict: ChatMessage = {
      id: `msg-${Date.now()}-gate-${gate.id}`,
      sender: 'user',
      text: '',
      timestamp: new Date().toISOString(),
      reviewedGate: { ...gate, decision, guidance },
    };
    updateCache(cacheKey, verdict);
    onPartialUpdate?.(verdict, false);

    return streamTurn(
      cacheKey,
      (callbacks) =>
        api.sendFunctionResponse(
          projectId,
          app,
          chatSessionId,
          {
            id: gate.id,
            name: gate.name,
            response: { decision, guidance },
          },
          callbacks,
        ),
      onPartialUpdate,
      onGate,
    );
  },
};

export default chatService;

if (import.meta.env.MODE === 'test') {
  Object.assign(chatService, {
    _clearCache: () => {
      messageCache.clear();
      gateCache.clear();
    },
    _getCache: (key: string) => messageCache.get(key),
    _setCache: (key: string, messages: ChatMessage[]) => {
      messageCache.set(key, messages);
    },
  });
}
