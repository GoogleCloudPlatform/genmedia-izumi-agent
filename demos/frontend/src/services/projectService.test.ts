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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import projectService from './projectService';
import { dbService } from './db';
import { api } from './api';
import type { Project } from '../data/types';
import { API_BASE_URL } from './api/client';

vi.mock('./db', () => ({
  dbService: {
    init: vi.fn().mockResolvedValue(undefined),
    getAll: vi.fn(),
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
  },
}));

vi.mock('./api', () => ({
  api: {
    createProject: vi.fn(),
    getAssets: vi.fn(),
    createAsset: vi.fn(), // Add this mock
    getCanvases: vi.fn(),
    getCanvas: vi.fn(),
    getChatSessions: vi.fn(),
    getAllChatSessions: vi.fn(),
    listApps: vi.fn(),
  },
}));

describe('projectService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset cache before each test
    projectService['_resetCache']();
  });

  describe('uploadAsset', () => {
    it('should upload a file and return a correctly mapped ProjectAsset', async () => {
      const projectId = 'proj-123';
      const file = new File([''], 'test-image.png', { type: 'image/png' });
      const rawAssetFromApi = {
        id: 'asset-456',
        file_name: 'test-image.png',
        mime_type: 'image/png',
        current_version: 1,
        versions: [
          {
            version_number: 1,
            create_time: '2025-11-21T10:00:00Z',
          },
        ],
      };

      (api.createAsset as vi.Mock).mockResolvedValue(rawAssetFromApi);

      const result = await projectService.uploadAsset(projectId, file);

      expect(api.createAsset).toHaveBeenCalledWith(projectId, file);
      expect(result).toEqual({
        id: 'asset-456',
        fileName: 'test-image.png',
        type: 'image',
        url: `${API_BASE_URL}/users/${projectId}/assets/asset-456/view?version=1`,
        thumbnailUrl: undefined,
        createdAt: '2025-11-21T10:00:00Z',
        currentVersion: 1,
        versions: rawAssetFromApi.versions,
      });
    });

    it('should invalidate the assets cache after upload', async () => {
      const projectId = 'proj-123';
      const file = new File([''], 'test.txt', { type: 'text/plain' });

      // 1. Prime the cache with some stale data
      const staleAssets = [{ id: 'stale-asset' }];
      projectService['_setCacheEntry'](projectId, {
        info: null,
        assets: staleAssets,
        canvases: null,
        chatSessions: null,
        availableApps: null,
        lastUpdated: Date.now(),
      });

      // 2. Mock the API call
      (api.createAsset as vi.Mock).mockResolvedValue({
        id: 'new-asset',
        file_name: 'test.txt',
        mime_type: 'text/plain',
      });

      // 3. Perform the upload
      await projectService.uploadAsset(projectId, file);

      // 4. Mock the subsequent getAssets call to see if it fetches fresh data
      const freshAssetsFromApi = [
        {
          id: 'fresh-asset',
          file_name: 'fresh.png',
          mime_type: 'image/png',
          versions: [{ version_number: 1, create_time: '2023-01-01' }],
          current_version: 1,
        },
      ];
      (api.getAssets as vi.Mock).mockResolvedValue(freshAssetsFromApi);

      // 5. Call getAssets and check that it returns the fresh data, not the stale cached one
      const result = await projectService.getAssets(projectId, false); // forceRefresh = false

      expect(api.getAssets).toHaveBeenCalled(); // It should have been called because cache was invalidated
      expect(result[0].id).toBe('fresh-asset');
    });
  });

  describe('getProjects', () => {
    it('should fetch projects and sort them by lastAccessedAt', async () => {
      const projects: Project[] = [
        {
          id: '1',
          name: 'Project 1',
          lastAccessedAt: '2023-01-01T00:00:00Z',
        } as Project,
        {
          id: '2',
          name: 'Project 2',
          lastAccessedAt: '2023-01-03T00:00:00Z',
        } as Project,
        {
          id: '3',
          name: 'Project 3',
          lastAccessedAt: '2023-01-02T00:00:00Z',
        } as Project,
      ];
      (dbService.getAll as vi.Mock).mockResolvedValue(projects);

      const result = await projectService.getProjects();

      expect(dbService.init).toHaveBeenCalled();
      expect(dbService.getAll).toHaveBeenCalled();
      expect(result.map((p) => p.id)).toEqual(['2', '3', '1']);
    });

    it('should filter for active projects by default', async () => {
      const projects: Project[] = [
        { id: '1', name: 'Active Project', isArchived: false } as Project,
        { id: '2', name: 'Archived Project', isArchived: true } as Project,
      ];
      (dbService.getAll as vi.Mock).mockResolvedValue(projects);

      const result = await projectService.getProjects();

      expect(result.length).toBe(1);
      expect(result[0].id).toBe('1');
    });

    it('should filter for archived projects when specified', async () => {
      const projects: Project[] = [
        { id: '1', name: 'Active Project', isArchived: false } as Project,
        { id: '2', name: 'Archived Project', isArchived: true } as Project,
      ];
      (dbService.getAll as vi.Mock).mockResolvedValue(projects);

      const result = await projectService.getProjects('archived');

      expect(result.length).toBe(1);
      expect(result[0].id).toBe('2');
    });

    it('should return all projects when specified', async () => {
      const projects: Project[] = [
        { id: '1', name: 'Active Project', isArchived: false } as Project,
        { id: '2', name: 'Archived Project', isArchived: true } as Project,
      ];
      (dbService.getAll as vi.Mock).mockResolvedValue(projects);

      const result = await projectService.getProjects('all');

      expect(result.length).toBe(2);
    });
  });

  describe('createProject', () => {
    it('should call api.createProject with the correct name', async () => {
      const projectName = 'New Awesome Project';
      const newProject = { id: 'new-proj', name: projectName } as Project;
      (api.createProject as vi.Mock).mockResolvedValue(newProject);

      const result = await projectService.createProject(projectName);

      expect(api.createProject).toHaveBeenCalledWith(projectName);
      expect(result).toEqual(newProject);
    });
  });

  describe('getProjectById', () => {
    beforeEach(() => {
      // Reset cache before each test
      projectService['_resetCache']();
    });

    it('should fetch all project data in parallel and return a composite object', async () => {
      const projectId = 'proj-1';
      const projectInfo = { id: projectId, name: 'Test Project' } as Project;
      const assets = [
        {
          id: 'asset-1',
          fileName: 'a.png',
          versions: [
            { version_number: 1, create_time: '2023-01-01T00:00:00Z' },
          ],
          current_version: 1,
          mime_type: 'image/png',
        },
      ];
      const canvases = [{ id: 'canvas-1', name: 'My Canvas' }];
      const sessions = [
        {
          id: 'session-1',
          appName: 'app1',
          lastUpdateTime: 1672531200,
        },
      ];

      (dbService.get as vi.Mock).mockResolvedValue(projectInfo);
      (api.getAssets as vi.Mock).mockResolvedValue(assets);
      (api.getCanvases as vi.Mock).mockResolvedValue(canvases);
      (api.getAllChatSessions as vi.Mock).mockResolvedValue(sessions);

      const result = await projectService.getProjectById(projectId, true);

      expect(dbService.get).toHaveBeenCalledWith(projectId);
      expect(api.getAssets).toHaveBeenCalledWith(projectId);
      expect(api.getCanvases).toHaveBeenCalledWith(projectId);
      expect(api.getAllChatSessions).toHaveBeenCalledWith(projectId);

      expect(result.id).toBe(projectId);
      expect(result.assets).toBeDefined();
      expect(result.canvases).toBeDefined();
      expect(result.chatSessions).toBeDefined();
      expect(result.chatSessions[0].appName).toBe('app1');
      expect(result.chatSessions[0].title).toBe('session-1');
    });

    it('should use cached data if forceRefresh is false', async () => {
      const projectId = 'proj-cached';
      const cachedEntry = {
        info: { id: projectId, name: 'Cached Project' } as Project,
        assets: [{ id: 'asset-c', fileName: 'c.png' }],
        canvases: [{ id: 'canvas-c', name: 'Cached Canvas' }],
        chatSessions: [{ id: 'session-c', title: 'Cached Chat' }],
        lastUpdated: Date.now(),
      };

      // Prime the cache
      projectService['_setCacheEntry'](projectId, cachedEntry);

      // Mock dbService.get for the updateLastAccessed call
      (dbService.get as vi.Mock).mockResolvedValue(cachedEntry.info);

      const result = await projectService.getProjectById(projectId, false);

      // Verify no new API calls were made for fetching data
      expect(api.getAssets).not.toHaveBeenCalled();
      expect(api.getCanvases).not.toHaveBeenCalled();
      expect(api.getAllChatSessions).not.toHaveBeenCalled();

      // dbService.get is called by updateLastAccessed
      expect(dbService.get).toHaveBeenCalledWith(projectId);

      expect(result.id).toBe(projectId);
      expect(result.name).toBe('Cached Project');
    });

    it('should re-fetch data if forceRefresh is true', async () => {
      const projectId = 'proj-refresh';
      const cachedEntry = {
        info: { id: projectId, name: 'Old Project' } as Project,
        assets: [],
        canvases: [],
        chatSessions: [],
        lastUpdated: Date.now() - 10000,
      };

      // Prime the cache
      projectService['_setCacheEntry'](projectId, cachedEntry);

      // Mock new data
      const newInfo = { id: projectId, name: 'Refreshed Project' } as Project;
      (dbService.get as vi.Mock).mockResolvedValue(newInfo);
      (api.getAssets as vi.Mock).mockResolvedValue([]);
      (api.getCanvases as vi.Mock).mockResolvedValue([]);
      (api.getAllChatSessions as vi.Mock).mockResolvedValue([]);

      const result = await projectService.getProjectById(projectId, true);

      expect(dbService.get).toHaveBeenCalledWith(projectId);
      expect(api.getAssets).toHaveBeenCalledWith(projectId);
      expect(api.getCanvases).toHaveBeenCalledWith(projectId);
      expect(result.name).toBe('Refreshed Project');
    });
  });

  describe('getCanvas', () => {
    const projectId = 'project-123';
    const canvasId = 'canvas-456';
    const mockApi = api as unknown as { getCanvas: ReturnType<typeof vi.fn> };

    it('should correctly map a video_timeline canvas with explicit type', async () => {
      const mockApiResponse = {
        id: canvasId,
        title: 'My Video Project',
        user_id: projectId,
        canvas_type: 'video_timeline',
        create_time: '2023-10-27T10:00:00Z',
        video_timeline: {
          title: 'My Video Project',
          video_clips: [],
          audio_clips: [],
          transitions: [],
          transition_in: null,
          transition_out: null,
        },
      };

      mockApi.getCanvas.mockResolvedValue(mockApiResponse);

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toEqual({
        id: canvasId,
        name: 'My Video Project',
        type: 'video_timeline',
        url: undefined,
        videoTimeline: mockApiResponse.video_timeline,
        createdAt: '2023-10-27T10:00:00Z',
      });
    });

    it('should infer video_timeline type if canvas_type is missing but video_timeline data exists', async () => {
      const mockApiResponse = {
        id: canvasId,
        title: 'Inferred Video Project',
        user_id: projectId,
        // canvas_type is MISSING
        create_time: '2023-10-27T11:00:00Z',
        video_timeline: {
          title: 'Inferred Video Project',
          video_clips: [],
          audio_clips: [],
          transitions: [],
          transition_in: null,
          transition_out: null,
        },
      };

      mockApi.getCanvas.mockResolvedValue(mockApiResponse);

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toEqual({
        id: canvasId,
        name: 'Inferred Video Project',
        type: 'video_timeline', // Should be inferred
        url: undefined,
        videoTimeline: mockApiResponse.video_timeline,
        createdAt: '2023-10-27T11:00:00Z',
      });
    });

    it('should infer html type and construct URL if canvas_type and video_timeline are missing', async () => {
      const mockApiResponse = {
        id: canvasId,
        title: 'Inferred HTML Canvas',
        user_id: projectId,
        // canvas_type is MISSING
        // video_timeline is MISSING
        create_time: '2023-10-27T12:00:00Z',
      };

      mockApi.getCanvas.mockResolvedValue(mockApiResponse);

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toEqual({
        id: canvasId,
        name: 'Inferred HTML Canvas',
        type: 'html', // Should be inferred as default
        url: `${API_BASE_URL}/users/${projectId}/canvases/${canvasId}/view`,
        videoTimeline: undefined,
        createdAt: '2023-10-27T12:00:00Z',
      });
    });

    it('should handle explicit html type correctly', async () => {
      const mockApiResponse = {
        id: canvasId,
        title: 'Explicit HTML Canvas',
        user_id: projectId,
        canvas_type: 'html',
        create_time: '2023-10-27T13:00:00Z',
      };

      mockApi.getCanvas.mockResolvedValue(mockApiResponse);

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toEqual({
        id: canvasId,
        name: 'Explicit HTML Canvas',
        type: 'html',
        url: `${API_BASE_URL}/users/${projectId}/canvases/${canvasId}/view`,
        videoTimeline: undefined,
        createdAt: '2023-10-27T13:00:00Z',
      });
    });

    it('should return null if api returns null', async () => {
      mockApi.getCanvas.mockResolvedValue(null);

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toBeNull();
    });

    it('should return null and log error if api throws', async () => {
      const consoleSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      mockApi.getCanvas.mockRejectedValue(new Error('API Error'));

      const result = await projectService.getCanvas(projectId, canvasId);

      expect(result).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});
