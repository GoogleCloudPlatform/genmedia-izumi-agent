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

import type { ProjectAsset } from './assets';
import type { Canvas } from './canvas';
import type { ChatSession } from './chat';
import type { ProjectUser } from './user';

export interface Project {
  id: string;
  name: string;
  sharedWith: readonly ProjectUser[];
  assets: readonly ProjectAsset[];
  chatSessions?: readonly ChatSession[]; // Add optional chatSessions
  canvases?: readonly Canvas[];
  isArchived?: boolean;
  lastAccessedAt?: string; // ISO string
}
