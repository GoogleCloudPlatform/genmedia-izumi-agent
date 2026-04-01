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

import {
  useLocation,
  useParams,
  matchPath,
  type PathMatch,
} from 'react-router-dom';

/**
 * A custom hook to extract route parameters, supporting wildcard routes.
 * It first tries to get the parameter from `useParams`. If not found,
 * it attempts to match the current pathname against the provided `pathPattern`.
 *
 * @param pathPattern The route pattern to match against (e.g., '/project/:projectId/chat/:chatSessionId')
 * @returns An object containing the extracted parameters.
 */
export function useRouteParams<T extends Record<string, string | undefined>>(
  pathPattern: string,
): T {
  const params = useParams<T>();
  const location = useLocation();

  const match = matchPath(pathPattern, location.pathname) as PathMatch<
    keyof T & string
  > | null;
  const fallbackParams: Partial<T> = (match?.params || {}) as Partial<T>;

  // Combine params and fallbackParams, preferring params
  const result = { ...fallbackParams, ...params };

  return result as T;
}
