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

import { renderHook } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import * as router from 'react-router-dom';
import { useRouteParams } from './useRouteParams';

// Mock react-router-dom hooks
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useParams: vi.fn(),
    useLocation: vi.fn(),
    matchPath: vi.fn(),
  };
});

describe('useRouteParams', () => {
  const mockUseParams = vi.mocked(router.useParams);
  const mockUseLocation = vi.mocked(router.useLocation);
  const mockMatchPath = vi.mocked(router.matchPath);

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mocks
    mockUseLocation.mockReturnValue({
      pathname: '/project/proj-abc/chat/session-123',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
  });

  it('should return params directly from useParams if available', () => {
    mockUseParams.mockReturnValue({
      projectId: 'proj-1',
      chatSessionId: 'sess-1',
    });
    // Even if useParams has everything, matchPath might still be called in a robust hook implementation
    mockMatchPath.mockReturnValue({
      params: {
        projectId: 'proj-match-fallback',
        chatSessionId: 'sess-match-fallback',
      },
      pathname: '/project/proj-abc/chat/session-123',
      pattern: {
        path: '/project/:projectId/chat/:chatSessionId',
        exact: false,
        caseSensitive: false,
      },
    });

    const { result } = renderHook(() =>
      useRouteParams('/project/:projectId/chat/:chatSessionId'),
    );

    expect(result.current).toEqual({
      projectId: 'proj-1',
      chatSessionId: 'sess-1',
    });
    expect(mockUseParams).toHaveBeenCalledTimes(1);
    expect(mockMatchPath).toHaveBeenCalledTimes(1); // Expect it to be called
  });

  it('should use matchPath as a fallback if useParams returns undefined for a specific param', () => {
    // Simulate useParams not catching child params in a wildcard setup
    mockUseParams.mockReturnValue({ projectId: 'proj-abc' });
    mockUseLocation.mockReturnValue({
      pathname: '/project/proj-abc/chat/session-123',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
    mockMatchPath.mockReturnValue({
      params: { projectId: 'proj-abc', chatSessionId: 'session-123' },
      pathname: '/project/proj-abc/chat/session-123',
      pattern: {
        path: '/project/:projectId/chat/:chatSessionId',
        exact: false,
        caseSensitive: false,
      },
    });

    const { result } = renderHook(() =>
      useRouteParams('/project/:projectId/chat/:chatSessionId'),
    );

    expect(result.current).toEqual({
      projectId: 'proj-abc',
      chatSessionId: 'session-123',
    });
    expect(mockUseParams).toHaveBeenCalledTimes(1);
    expect(mockMatchPath).toHaveBeenCalledTimes(1);
    expect(mockMatchPath).toHaveBeenCalledWith(
      '/project/:projectId/chat/:chatSessionId',
      '/project/proj-abc/chat/session-123',
    );
  });

  it('should correctly extract params for a generate modality wildcard route', () => {
    mockUseParams.mockReturnValue({ projectId: 'proj-gen' });
    mockUseLocation.mockReturnValue({
      pathname: '/project/proj-gen/generate/image',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
    mockMatchPath.mockReturnValue({
      params: { projectId: 'proj-gen', modality: 'image' },
      pathname: '/project/proj-gen/generate/image',
      pattern: {
        path: '/project/:projectId/generate/:modality',
        exact: false,
        caseSensitive: false,
      },
    });

    const { result } = renderHook(() =>
      useRouteParams<{ projectId?: string; modality?: string }>(
        '/project/:projectId/generate/:modality',
      ),
    );

    expect(result.current).toEqual({
      projectId: 'proj-gen',
      modality: 'image',
    });
  });

  it('should return empty object if no params are found and no match', () => {
    mockUseParams.mockReturnValue({});
    mockUseLocation.mockReturnValue({
      pathname: '/some/other/path',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
    mockMatchPath.mockReturnValue(null);

    const { result } = renderHook(() =>
      useRouteParams('/project/:projectId/chat/:chatSessionId'),
    );

    expect(result.current).toEqual({});
  });

  it('should prefer useParams value over matchPath fallback if both exist', () => {
    mockUseParams.mockReturnValue({
      projectId: 'proj-param',
      chatSessionId: 'sess-param',
    });
    mockMatchPath.mockReturnValue({
      params: { projectId: 'proj-match', chatSessionId: 'sess-match' }, // Different values
      pathname: '/project/proj-param/chat/sess-param',
      pattern: {
        path: '/project/:projectId/chat/:chatSessionId',
        exact: false,
        caseSensitive: false,
      },
    });

    const { result } = renderHook(() =>
      useRouteParams('/project/:projectId/chat/:chatSessionId'),
    );

    expect(result.current).toEqual({
      projectId: 'proj-param',
      chatSessionId: 'sess-param',
    });
    expect(mockUseParams).toHaveBeenCalledTimes(1);
    expect(mockMatchPath).toHaveBeenCalledTimes(1);
  });

  it('should handle partial matchPath params correctly', () => {
    mockUseParams.mockReturnValue({});
    mockUseLocation.mockReturnValue({
      pathname: '/project/proj-partial/details',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
    mockMatchPath.mockReturnValue({
      params: { projectId: 'proj-partial' }, // Only projectId is matched
      pathname: '/project/proj-partial/details',
      pattern: {
        path: '/project/:projectId/details',
        exact: false,
        caseSensitive: false,
      },
    });

    const { result } = renderHook(() =>
      useRouteParams<{ projectId?: string; otherId?: string }>(
        '/project/:projectId/details',
      ),
    );

    expect(result.current).toEqual({ projectId: 'proj-partial' });
  });
});
