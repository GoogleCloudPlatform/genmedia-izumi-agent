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

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import NewProjectModal from './NewProjectModal';

describe('NewProjectModal', () => {
  it('should call onCreate with the project name', async () => {
    const handleCreate = vi.fn();
    const handleClose = vi.fn();

    render(
      <NewProjectModal
        open={true}
        onClose={handleClose}
        onCreate={handleCreate}
      />,
    );

    const input = screen.getByLabelText('Project Name');
    const createButton = screen.getByText('Create');

    await userEvent.type(input, 'My New Project');
    await userEvent.click(createButton);

    expect(handleCreate).toHaveBeenCalledWith('My New Project');
  });

  it('should disable the Create button if the project name is empty', () => {
    const handleCreate = vi.fn();
    const handleClose = vi.fn();

    render(
      <NewProjectModal
        open={true}
        onClose={handleClose}
        onCreate={handleCreate}
      />,
    );

    const createButton = screen.getByText('Create');
    expect(createButton).toBeDisabled();
  });

  it('should call onClose when the Cancel button is clicked', async () => {
    const handleCreate = vi.fn();
    const handleClose = vi.fn();

    render(
      <NewProjectModal
        open={true}
        onClose={handleClose}
        onCreate={handleCreate}
      />,
    );

    const cancelButton = screen.getByText('Cancel');
    await userEvent.click(cancelButton);

    expect(handleClose).toHaveBeenCalled();
  });
});
