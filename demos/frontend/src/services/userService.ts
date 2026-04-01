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

import type { User } from '../data/types';

// Mock user data since backend doesn't support user management yet
const mockUser: User = {
  id: 1,
  name: 'Demo User',
  email: 'demo@example.com',
};

const userService = {
  findUserByEmail: async (email: string): Promise<User> => {
    // Simulate API call
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ ...mockUser, email });
      }, 300);
    });
  },
};

export default userService;
