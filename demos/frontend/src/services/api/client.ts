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

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function request(url: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export interface SSECallbacks<T> {
  onClose?: () => void;
  onMessage?: (data: T) => void;
  onError?: (error: unknown) => void;
}

export async function requestSSE<T>(
  url: string,
  options: RequestInit = {},
  callbacks: SSECallbacks<T>,
) {
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.body) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      if (callbacks.onClose) callbacks.onClose();
      break;
    }

    const chunk = decoder.decode(value, { stream: true });
    buffer += chunk;

    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep the last incomplete line in the buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.substring(6);
        if (data.trim() === '[DONE]') {
          if (callbacks.onClose) callbacks.onClose();
          return;
        }
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) {
            if (callbacks.onError) callbacks.onError(new Error(parsed.error));
            return; // Stop processing if it's an error? Or just notify? Usually error ends stream.
          }
          if (callbacks.onMessage) callbacks.onMessage(parsed);
        } catch (e) {
          console.error('Error parsing SSE data:', e);
          if (callbacks.onError) callbacks.onError(e);
        }
      }
    }
  }
}
