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

/**
 * Chat Types
 */

export interface ChatMessage {
  id: string;
  sender: 'user' | 'gemini';
  text: string;
  timestamp: string; // ISO string
  canvasId?: string;
  assetId?: string;
  attachments?: {
    type: 'image' | 'file';
    url: string;
    name: string;
  }[];
}

export interface ChatSession {
  id: string;
  title: string; // e.g., "Chat about images"
  messages: ChatMessage[];
  lastUpdated: string; // ISO string
  appName?: string;
}

export interface APIChatSession {
  id: string;
  appName: string;
  lastUpdateTime?: number; // Unix timestamp
}

// --- API Response Types (Moved from src/services/api/chat-types.ts) ---

export interface FunctionCall {
  id: string;
  args: { [key: string]: unknown };
  name: string;
}

export interface FunctionResponse {
  id: string;
  name: string;
  response: {
    result: string; // This appears to be a JSON string
  };
}

export interface BackendEventPart {
  text?: string;
  inlineData?: {
    mimeType: string;
    data: string;
    displayName?: string;
  };
  functionCall?: FunctionCall;
  functionResponse?: FunctionResponse;
  thoughtSignature?: string; // Appears to be a base64 encoded string
}

export interface BackendEventContent {
  parts: BackendEventPart[];
  role: 'user' | 'model';
}

export interface UsageMetadata {
  candidatesTokenCount?: number;
  candidatesTokensDetails?: Array<{
    modality: string;
    tokenCount: number;
  }>;
  promptTokenCount?: number;
  promptTokensDetails?: Array<{
    modality: string;
    tokenCount: number;
  }>;
  thoughtsTokenCount?: number;
  totalTokenCount: number;
  trafficType: string;
}

export interface Actions {
  stateDelta: object;
  artifactDelta: object;
  requestedAuthConfigs: object;
}

export interface ChatApiResponse {
  content?: BackendEventContent;
  finishReason?: string;
  usageMetadata?: UsageMetadata;
  invocationId: string;
  author: string;
  actions: Actions;
  longRunningToolIds?: string[];
  id: string;
  timestamp: number;
  partial?: boolean;
}
