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

import { dbService } from '../db';
import type { Project } from '../../data/types';

export const projectsApi = {
  async getProjects() {
    try {
      await dbService.init();
    } catch {
      // Ignore if already open or handle error
    }
    console.log(`[API] Fetching projects from IndexedDB`);
    return dbService.getAll();
  },

  async getProjectById(id: string) {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    return dbService.get(id);
  },

  async createProject(name: string) {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    console.log(`[API] Creating new project: "${name}"`);
    const newProjectId = `project_${Date.now()}`;
    const newProject = {
      id: newProjectId,
      name,
      sharedWith: [],
      assets: [],
      chatSessions: [],
      canvases: [],
      lastAccessedAt: new Date().toISOString(),
    };
    await dbService.set(newProject);
    return newProject;
  },

  async updateProject(project: Project) {
    try {
      await dbService.init();
    } catch {
      // Ignore
    }
    return dbService.set(project);
  },
};
