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
  /** A checkpoint answered earlier in this session, kept for reference. */
  reviewedGate?: ReviewedGate;
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
    // Tools return {status, result}; `result` is a string for most tools and a
    // structured object for the review checkpoints.
    status?: string;
    result?: unknown;
    [key: string]: unknown;
  };
}

// --- Human review checkpoints ---
// The ads_x pipeline suspends at three checkpoints, each a long-running tool
// named await_<stage>_approval. The run resumes only when the client answers
// that call with a matching functionResponse carrying the reviewer's verdict.

export type GateDecision = 'accept' | 'modify' | 'regenerate';

export type GateStage = 'strategy' | 'storyboard' | 'frames' | 'final_cut';

/** A scene or rendered clip as the checkpoint payload describes it. */
export interface GateScene {
  scene_id?: string;
  topic?: string;
  action?: string;
  art_direction?: string;
  /** What the first frame shows, before anything moves. */
  opening_frame?: string;
  /** Camera, lens, lighting and mood, as the scene will be filmed. */
  shot?: Record<string, string>;
  voiceover?: string;
  duration_seconds?: number;
  rendered?: boolean;
  asset_id?: string;
  /** Where the rendered image lives, at the frame checkpoint. */
  asset_ref?: { id?: string; asset_type?: string; workspace_id?: string };
}

/** The payload a checkpoint returns while it waits for a verdict. */
export interface GatePayload {
  status: string;
  stage: GateStage;
  /** Always present, unlike the model's lead-in. Render this. */
  message?: string;
  // Strategy checkpoint.
  campaign?: {
    name?: string;
    audience?: string;
    duration?: string;
    orientation?: string;
    theme?: string;
    tone?: string;
    key_message?: string;
    vertical?: string;
  };
  look?: { name?: string; aesthetic?: string };
  /** Campaign-wide art direction every scene inherits. */
  direction?: Record<string, string>;
  features_a_person?: boolean;
  creator_description?: string | null;
  uploaded_assets?: string[];
  // Storyboard checkpoint.
  campaign_title?: string;
  music?: string;
  scenes?: GateScene[];
  // Final cut checkpoint.
  final_video?: { asset_id?: string; asset_ref?: string };
  clips?: GateScene[];
  // Frame checkpoint: the rendered opening frames, before any video.
  frames?: GateScene[];
}

/**
 * A checkpoint that has already been answered.
 *
 * Kept so the reviewer can look back at what they approved. The payload is
 * only ever sent once, in the event stream, so without this the plan behind a
 * decision is gone the moment the card closes.
 */
export interface ReviewedGate {
  id: string;
  name: string;
  payload: GatePayload;
  decision?: GateDecision;
  guidance?: string;
}

/** A checkpoint that is waiting on this client for an answer. */
export interface PendingGate {
  /** The function call id the answer must quote to resume the run. */
  id: string;
  /** The tool that suspended, e.g. "await_storyboard_approval". */
  name: string;
  payload: GatePayload;
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
