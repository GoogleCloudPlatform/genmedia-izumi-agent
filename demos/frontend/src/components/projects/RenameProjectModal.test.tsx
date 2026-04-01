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
import RenameProjectModal from './RenameProjectModal';

describe('RenameProjectModal', () => {
  const mockOnClose = vi.fn();
  const mockOnRename = vi.fn();

  it('should render with current name', () => {
    render(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Old Name"
      />,
    );

    const input = screen.getByLabelText('Project Name');
    expect(input).toHaveValue('Old Name');
  });

  it('should call onRename when Rename button is clicked with new name', async () => {
    render(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Old Name"
      />,
    );

    const input = screen.getByLabelText('Project Name');
    await userEvent.clear(input);
    await userEvent.type(input, 'New Name');

    const renameButton = screen.getByRole('button', { name: 'Rename' });
    await userEvent.click(renameButton);

    expect(mockOnRename).toHaveBeenCalledWith('New Name');
  });

  it('should disable Rename button if name is empty', async () => {
    render(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Old Name"
      />,
    );

    const input = screen.getByLabelText('Project Name');
    await userEvent.clear(input);

    const renameButton = screen.getByRole('button', { name: 'Rename' });
    expect(renameButton).toBeDisabled();
  });

  it('should call onClose if Cancel is clicked', async () => {
    render(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Old Name"
      />,
    );

    const cancelButton = screen.getByRole('button', { name: 'Cancel' });
    await userEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should update input when currentName prop changes', () => {
    const { rerender } = render(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Old Name"
      />,
    );

    rerender(
      <RenameProjectModal
        open={true}
        onClose={mockOnClose}
        onRename={mockOnRename}
        currentName="Updated Name"
      />,
    );

    const input = screen.getByLabelText('Project Name');
    expect(input).toHaveValue('Updated Name');
  });
});
