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

import { request, requestSSE, type SSECallbacks } from './client';
import type { ChatApiResponse } from '../../data/types';

interface ChatPartText {
  text: string;
}

interface ChatPartInlineData {
  inlineData: {
    mimeType: string;
    data: string;
    displayName: string;
  };
}

interface ChatPartFunctionResponse {
  functionResponse: {
    id: string;
    name: string;
    response: Record<string, unknown>;
  };
}

type ChatPart = ChatPartText | ChatPartInlineData | ChatPartFunctionResponse;

/** Posts one turn to the agent and streams the events back. */
function runSse(
  projectId: string,
  appName: string,
  sessionId: string,
  parts: ChatPart[],
  callbacks: SSECallbacks<ChatApiResponse>,
) {
  const requestBody = {
    appName: appName,
    userId: projectId,
    sessionId: sessionId,
    newMessage: {
      role: 'user',
      parts: parts,
    },
    streaming: true,
    stateDelta: null,
  };
  return requestSSE<ChatApiResponse>(
    `/run_sse`,
    {
      method: 'POST',
      body: JSON.stringify(requestBody),
    },
    callbacks,
  );
}

export const chatApi = {
  async getAllChatSessions(projectId: string) {
    console.log(`[API] Fetching all chat sessions for project ${projectId}`);
    return request(`/workspaces/${projectId}/sessions`);
  },

  async getChatSessions(projectId: string, appName: string) {
    console.log(
      `[API] Fetching chat sessions for project ${projectId} and app ${appName}`,
    );
    return request(`/apps/${appName}/users/${projectId}/sessions`);
  },

  async createChatSession(projectId: string, appName: string) {
    console.log(
      `[API] Creating chat session for project ${projectId} and app ${appName}`,
    );
    return request(`/apps/${appName}/users/${projectId}/sessions`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  async getChatMessages(projectId: string, appName: string, sessionId: string) {
    console.log(`[API] Fetching messages for session ${sessionId}`);
    return request(`/apps/${appName}/users/${projectId}/sessions/${sessionId}`);
  },

  async sendMessage(
    projectId: string,
    appName: string,
    sessionId: string,
    message: string,
    files: File[],
    callbacks: SSECallbacks<ChatApiResponse>,
  ) {
    console.log(
      `[API] Sending message in session ${sessionId}: ${message} with ${files.length} files`,
    );

    const parts: ChatPart[] = [];

    // Add text message part if present
    if (message) {
      parts.push({ text: message });
    }

    // Process files and add as inlineData parts
    for (const file of files) {
      const base64Data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Remove data URL prefix (e.g., "data:image/png;base64,")
          const base64 = result.split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      parts.push({
        inlineData: {
          mimeType: file.type,
          data: base64Data,
          displayName: file.name,
        },
      });
    }

    return runSse(projectId, appName, sessionId, parts, callbacks);
  },

  /**
   * Answers a suspended long-running tool call, resuming the run.
   *
   * The id must be the one carried by the originating function call, and no
   * invocation id is sent: ADK matches the response to the call by id, and an
   * invocation id is not part of the request schema.
   */
  async sendFunctionResponse(
    projectId: string,
    appName: string,
    sessionId: string,
    functionResponse: { id: string; name: string; response: object },
    callbacks: SSECallbacks<ChatApiResponse>,
  ) {
    console.log(
      `[API] Answering ${functionResponse.name} (${functionResponse.id}) in session ${sessionId}`,
    );
    return runSse(
      projectId,
      appName,
      sessionId,
      [
        {
          functionResponse: {
            id: functionResponse.id,
            name: functionResponse.name,
            response: functionResponse.response as Record<string, unknown>,
          },
        },
      ],
      callbacks,
    );
  },

  async listApps() {
    console.log(`[API] Listing available apps`);
    return request('/list-apps');
  },
};
