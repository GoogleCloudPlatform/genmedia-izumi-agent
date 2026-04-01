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

import type { User } from './types';

export const currentUser: User = {
  id: 1, // Keeping number for now to avoid breaking User type compatibility if not all updated
  name: 'Demo User',
  email: 'demo@example.com',
  profilePhotoUrl: null, // Use null to indicate no custom photo, allowing a placeholder to be rendered
};
