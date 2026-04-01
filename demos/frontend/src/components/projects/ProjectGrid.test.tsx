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

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import ProjectGrid from './ProjectGrid';
import projectService from '../../services/projectService';
import type { Project } from '../../data/types';

vi.mock('../../services/projectService');

describe('ProjectGrid', () => {
  const mockProjects: Project[] = [
    {
      id: '1',
      name: 'Project Alpha',
      lastAccessedAt: '2023-01-01T00:00:00Z',
      isArchived: false,
    } as Project,
    {
      id: '2',
      name: 'Project Beta',
      lastAccessedAt: '2023-01-02T00:00:00Z',
      isArchived: false,
    } as Project,
  ];

  const mockArchivedProjects: Project[] = [
    {
      id: '3',
      name: 'Project Charlie',
      lastAccessedAt: '2023-01-03T00:00:00Z',
      isArchived: true,
    } as Project,
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (projectService.getProjects as vi.Mock).mockImplementation((filter) => {
      if (filter === 'archived') {
        return Promise.resolve(mockArchivedProjects);
      }
      return Promise.resolve(mockProjects);
    });
    (projectService.archiveProject as vi.Mock).mockResolvedValue(undefined);
    (projectService.unarchiveProject as vi.Mock).mockResolvedValue(undefined);
    (projectService.deleteProject as vi.Mock).mockResolvedValue(undefined);
    (projectService.updateProjectName as vi.Mock).mockResolvedValue(undefined);
    window.confirm = vi.fn(() => true); // Mock window.confirm
  });

  const renderWithRouter = (ui: React.ReactElement) => {
    return render(<MemoryRouter>{ui}</MemoryRouter>);
  };

  it('should display a list of projects', async () => {
    renderWithRouter(<ProjectGrid />);

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
    });
  });

  it('should filter projects based on user input', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const filterInput = screen.getByLabelText('Filter projects by name');
    await userEvent.type(filterInput, 'Alpha');

    expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    expect(screen.queryByText('Project Beta')).not.toBeInTheDocument();
  });

  it('should navigate to project page on card click', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const projectCard = screen.getByText('Project Alpha').closest('a');
    expect(projectCard).toHaveAttribute('href', '/project/1');
  });

  it('should open NewProjectModal when "New Project" is clicked', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const newProjectButton = screen.getByText('New Project');
    await userEvent.click(newProjectButton);

    // The test will fail if the modal is not found. We can assert its title is present.
    expect(await screen.findByText('Create New Project')).toBeInTheDocument();
  });

  it('should call archiveProject when archive is clicked', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const menuButton = screen.getAllByRole('button', {
      name: /project actions/i,
    })[0];
    await userEvent.click(menuButton);

    const archiveButton = await screen.findByText('Archive');
    await userEvent.click(archiveButton);

    expect(projectService.archiveProject).toHaveBeenCalledWith('1');
  });

  it('should call unarchiveProject when unarchive is clicked', async () => {
    renderWithRouter(<ProjectGrid />);

    // Wait for the initial active projects to load and display
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    // Switch to archived view
    const viewArchivedButton = screen.getByText('View Archived Projects');
    await userEvent.click(viewArchivedButton);

    await waitFor(() =>
      expect(screen.getByText('Project Charlie')).toBeInTheDocument(),
    );

    const menuButton = screen.getAllByRole('button', {
      name: /project actions/i,
    })[0];
    await userEvent.click(menuButton);

    const unarchiveButton = await screen.findByText('Unarchive');
    await userEvent.click(unarchiveButton);

    expect(projectService.unarchiveProject).toHaveBeenCalledWith('3');
  });

  it('should call delete a project', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const menuButton = screen.getAllByRole('button', {
      name: /project actions/i,
    })[0];
    await userEvent.click(menuButton);

    const deleteButton = await screen.findByText('Delete');
    await userEvent.click(deleteButton);

    await waitFor(() =>
      expect(projectService.deleteProject).toHaveBeenCalledWith('1'),
    );
  });

  it('should open the rename modal', async () => {
    renderWithRouter(<ProjectGrid />);
    await waitFor(() =>
      expect(screen.getByText('Project Alpha')).toBeInTheDocument(),
    );

    const menuButton = screen.getAllByRole('button', {
      name: /project actions/i,
    })[0];
    await userEvent.click(menuButton);

    const renameButton = await screen.findByText('Rename');
    await userEvent.click(renameButton);

    expect(await screen.findByText('Rename Project')).toBeInTheDocument();
  });
});
