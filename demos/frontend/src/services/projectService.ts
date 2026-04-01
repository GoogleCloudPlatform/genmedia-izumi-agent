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

import type {
  Project,
  ProjectUser,
  ProjectAsset,
  Canvas,
  ChatSession,
  Asset,
  AssetVersion,
  CanvasInfo,
  APIChatSession,
  AssetGenerateConfig,
} from '../data/types';
import { dbService } from './db';
import { api } from './api';
import { API_BASE_URL } from './api/client';

interface ProjectCacheEntry {
  info: Project | null;
  assets: ProjectAsset[] | null;
  canvases: Canvas[] | null;
  chatSessions: ChatSession[] | null;
  availableApps: string[] | null;
  lastUpdated: number;
}

// In-memory cache keyed by projectId
const projectCache = new Map<string, ProjectCacheEntry>();

const getCacheEntry = (projectId: string): ProjectCacheEntry => {
  if (!projectCache.has(projectId)) {
    projectCache.set(projectId, {
      info: null,
      assets: null,
      canvases: null,
      chatSessions: null,
      availableApps: null,
      lastUpdated: 0,
    });
  }
  return projectCache.get(projectId)!;
};

const mapApiAssetToProjectAsset = (
  asset: Asset,
  projectId: string,
): ProjectAsset => {
  const currentVersion =
    asset.versions?.find(
      (v: AssetVersion) => v.version_number === asset.current_version,
    ) || asset.versions?.[0];

  const generateConfig = currentVersion
    ? currentVersion.image_generate_config ||
      currentVersion.music_generate_config ||
      currentVersion.video_generate_config ||
      currentVersion.speech_generate_config ||
      currentVersion.text_generate_config
    : null;

  // Resolve duration
  let duration = currentVersion?.duration_seconds;
  if (
    (duration === null || duration === undefined) &&
    currentVersion?.video_generate_config?.duration_seconds
  ) {
    duration = currentVersion.video_generate_config.duration_seconds;
  }

  return {
    id: asset.id,
    type: asset.mime_type.startsWith('video')
      ? 'video'
      : asset.mime_type.startsWith('audio')
        ? 'audio'
        : asset.mime_type.startsWith('text')
          ? 'text'
          : asset.mime_type.startsWith('image')
            ? 'image'
            : 'binary',
    url: `${API_BASE_URL}/users/${projectId}/assets/${asset.id}/view?version=${asset.current_version}`,
    thumbnailUrl: undefined,
    fileName: asset.file_name,
    createdAt: currentVersion?.create_time,
    generateConfig: generateConfig as AssetGenerateConfig | null,
    currentVersion: asset.current_version,
    versions: asset.versions || [],
    duration,
  };
};

const projectService = {
  // --- Granular Fetching Methods ---

  getAvailableApps: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<string[]> => {
    const cache = getCacheEntry(projectId);
    if (!forceRefresh && cache.availableApps) {
      return cache.availableApps;
    }
    try {
      const apps = await api.listApps();
      cache.availableApps = apps;
      return apps;
    } catch (e: unknown) {
      console.error('Failed to list apps', e);
      return cache.availableApps || [];
    }
  },

  getProjectInfo: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<Project> => {
    const cache = getCacheEntry(projectId);

    if (!forceRefresh && cache.info) {
      // Even if cached, update access time in background
      projectService.updateLastAccessed(projectId);
      return cache.info;
    }

    // Try local DB first for offline/quick load support
    try {
      await dbService.init();
    } catch {
      // Ignore DB init errors
    }

    let project = await dbService.get<Project>(projectId);

    if (!project) {
      // If not in local DB, create a placeholder for remote project
      project = {
        id: projectId,
        name: 'External Project',
        sharedWith: [],
        assets: [],
        chatSessions: [],
        canvases: [],
      };
    }

    // Update access time
    project.lastAccessedAt = new Date().toISOString();
    // We don't await this to keep UI snappy, but we need to save it.
    await dbService.set(project);

    cache.info = project;
    return project;
  },

  getAssets: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<ProjectAsset[]> => {
    const cache = getCacheEntry(projectId);

    if (!forceRefresh && cache.assets) {
      return cache.assets;
    }

    try {
      const assets = await api.getAssets(projectId);
      const fullAssets = assets.map((a: Asset) =>
        mapApiAssetToProjectAsset(a, projectId),
      );

      cache.assets = fullAssets;
      return fullAssets;
    } catch (error) {
      console.error(`Failed to fetch assets for project ${projectId}`, error);
      return cache.assets || [];
    }
  },

  getCanvases: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<Canvas[]> => {
    const cache = getCacheEntry(projectId);

    if (!forceRefresh && cache.canvases) {
      return cache.canvases;
    }

    try {
      const canvases = await api.getCanvases(projectId);
      const mappedCanvases = canvases.map((c: CanvasInfo) => ({
        id: c.id,
        name: c.title,
        type: c.canvas_type,
        url:
          c.canvas_type === 'html'
            ? `${API_BASE_URL}/users/${projectId}/canvases/${c.id}/view`
            : undefined,
        videoTimeline:
          c.canvas_type === 'video_timeline' ? c.video_timeline : undefined,
        createdAt: c.create_time,
      }));

      cache.canvases = mappedCanvases;
      return mappedCanvases;
    } catch (error) {
      console.error(`Failed to fetch canvases for project ${projectId}`, error);
      return cache.canvases || [];
    }
  },

  getCanvas: async (
    projectId: string,
    canvasId: string,
  ): Promise<Canvas | null> => {
    try {
      // We don't cache individual detailed fetches separately or update the list cache for simplicity now,
      // but in a real app we might update the cache entry.
      const c = await api.getCanvas(projectId, canvasId);
      if (!c) return null;

      // Infer canvas type if not provided in the response
      const canvasType =
        c.canvas_type || (c.video_timeline ? 'video_timeline' : 'html');

      // Map to Canvas
      return {
        id: c.id,
        name: c.title,
        type: canvasType,
        url:
          canvasType === 'html'
            ? `${API_BASE_URL}/users/${projectId}/canvases/${c.id}/view`
            : undefined,
        videoTimeline: c.video_timeline,
        createdAt: c.create_time,
      };
    } catch (error) {
      console.error(
        `Failed to fetch canvas ${canvasId} for project ${projectId}`,
        error,
      );
      return null;
    }
  },

  // Replaced getChatSessions with getAllChatSessions which fetches from ALL apps
  // and caches the result.
  getAllChatSessions: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<ChatSession[]> => {
    const cache = getCacheEntry(projectId);

    if (!forceRefresh && cache.chatSessions) {
      return cache.chatSessions;
    }

    try {
      const sessions = await api.getAllChatSessions(projectId);

      const mappedSessions = sessions.map((session: APIChatSession) => ({
        id: session.id,
        title: session.id || 'Untitled Chat',
        messages: [],
        lastUpdated: session.lastUpdateTime
          ? new Date(session.lastUpdateTime * 1000).toISOString()
          : new Date().toISOString(),
        appName: session.appName,
      }));

      cache.chatSessions = mappedSessions;
      return mappedSessions;
    } catch (error: unknown) {
      console.error(
        `Failed to fetch chat sessions for project ${projectId}`,
        error,
      );
      return cache.chatSessions || [];
    }
  },

  // Deprecated or alias for backward compat if needed, but better to use getAllChatSessions
  getChatSessions: async (
    projectId: string,
    forceRefresh: boolean = false,
  ): Promise<ChatSession[]> => {
    return projectService.getAllChatSessions(projectId, forceRefresh);
  },

  // --- Composite Method for Backward Compatibility ---

  getProjectById: async (
    id: string,
    forceRefresh: boolean = false,
  ): Promise<Project> => {
    // Fetch all components in parallel (or from cache)
    const [info, assets, canvases, sessions] = await Promise.all([
      projectService.getProjectInfo(id, forceRefresh),
      projectService.getAssets(id, forceRefresh),
      projectService.getCanvases(id, forceRefresh),
      projectService.getAllChatSessions(id, forceRefresh),
    ]);

    // Return a composite object
    return {
      ...info,
      assets,
      canvases,
      chatSessions: sessions,
    };
  },

  getProjects: async (
    filter: 'all' | 'active' | 'archived' = 'active',
  ): Promise<Project[]> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const allProjects = await dbService.getAll<Project>();
    const filteredProjects =
      filter === 'all'
        ? allProjects
        : filter === 'archived'
          ? allProjects.filter((p) => p.isArchived)
          : allProjects.filter((p) => !p.isArchived);

    return filteredProjects.sort((a, b) => {
      const dateA = a.lastAccessedAt ? new Date(a.lastAccessedAt).getTime() : 0;
      const dateB = b.lastAccessedAt ? new Date(b.lastAccessedAt).getTime() : 0;
      if (dateA !== dateB) {
        return dateB - dateA; // Descending order (newest first)
      }
      return a.name.localeCompare(b.name); // Fallback to name
    });
  },

  archiveProject: async (projectId: string): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const project = await dbService.get<Project>(projectId);
    if (project) {
      project.isArchived = true;
      await dbService.set(project);
      // Update cache
      const cache = projectCache.get(projectId);
      if (cache && cache.info) {
        cache.info.isArchived = true;
      }
    }
  },

  unarchiveProject: async (projectId: string): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const project = await dbService.get<Project>(projectId);
    if (project) {
      project.isArchived = false;
      await dbService.set(project);
      // Update cache
      const cache = projectCache.get(projectId);
      if (cache && cache.info) {
        cache.info.isArchived = false;
      }
    }
  },

  deleteProject: async (projectId: string): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    await dbService.remove(projectId);
    projectCache.delete(projectId);
  },

  updateSharedUsers: async (
    projectId: string,
    sharedWith: readonly ProjectUser[],
  ): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const project = await dbService.get<Project>(projectId);
    if (project) {
      project.sharedWith = [...sharedWith];
      await dbService.set(project);

      // Update cache if exists
      const cache = projectCache.get(projectId);
      if (cache && cache.info) {
        cache.info.sharedWith = [...sharedWith];
      }
    }
  },

  updateProjectName: async (projectId: string, name: string): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const project = await dbService.get<Project>(projectId);
    if (project) {
      project.name = name;
      project.lastAccessedAt = new Date().toISOString();
      await dbService.set(project);

      // Update cache if exists
      const cache = projectCache.get(projectId);
      if (cache && cache.info) {
        cache.info.name = name;
        cache.info.lastAccessedAt = project.lastAccessedAt;
      }
    }
  },

  updateLastAccessed: async (projectId: string): Promise<void> => {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    const project = await dbService.get<Project>(projectId);
    if (project) {
      project.lastAccessedAt = new Date().toISOString();
      await dbService.set(project);

      // Update cache if exists
      const cache = projectCache.get(projectId);
      if (cache && cache.info) {
        cache.info.lastAccessedAt = project.lastAccessedAt;
      }
    }
  },

  createProject: async (name: string): Promise<Project> => {
    return api.createProject(name);
  },

  uploadAsset: async (projectId: string, file: File): Promise<ProjectAsset> => {
    const rawAsset = await api.createAsset(projectId, file);
    // Invalidate the cache to force a fresh fetch next time
    const cache = getCacheEntry(projectId);
    cache.assets = null;

    // Map the raw API response to the ProjectAsset type
    const newAsset = mapApiAssetToProjectAsset(rawAsset, projectId);

    return newAsset;
  },

  getAssetTextContent: async (url: string): Promise<string> => {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch text content: ${response.statusText}`);
    }
    return response.text();
  },

  invalidateChatSessionsCache: (projectId: string): void => {
    const cache = getCacheEntry(projectId);
    cache.chatSessions = null;
  },
};

export default projectService;

// Exposed for testing purposes
if (import.meta.env.MODE === 'test') {
  Object.assign(projectService, {
    _resetCache: () => projectCache.clear(),
    _setCacheEntry: (projectId: string, entry: ProjectCacheEntry) => {
      projectCache.set(projectId, entry);
    },
  });
}
