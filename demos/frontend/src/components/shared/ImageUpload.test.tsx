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

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ImageUpload from './ImageUpload';

describe('ImageUpload', () => {
  it('renders the upload placeholder initially', () => {
    render(<ImageUpload onUpload={() => {}} />);
    expect(screen.getByText('+')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders an image when initialImage is provided', () => {
    const imageUrl = 'blob:http://localhost/test.png';
    render(<ImageUpload onUpload={() => {}} initialImage={imageUrl} />);

    const img = screen.getByRole('img');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', imageUrl);
    expect(screen.queryByText('+')).not.toBeInTheDocument();
  });

  it('renders a remove button when onRemove is provided and image exists', () => {
    const imageUrl = 'blob:http://localhost/test.png';
    render(
      <ImageUpload
        onUpload={() => {}}
        initialImage={imageUrl}
        onRemove={() => {}}
      />,
    );

    expect(screen.getByLabelText('Remove image')).toBeInTheDocument();
  });

  it('does not render remove button if onRemove is not provided', () => {
    const imageUrl = 'blob:http://localhost/test.png';
    render(<ImageUpload onUpload={() => {}} initialImage={imageUrl} />);

    expect(screen.queryByLabelText('Remove image')).not.toBeInTheDocument();
  });

  it('calls onRemove when remove button is clicked', () => {
    const handleRemove = vi.fn();
    const imageUrl = 'blob:http://localhost/test.png';

    render(
      <ImageUpload
        onUpload={() => {}}
        initialImage={imageUrl}
        onRemove={handleRemove}
      />,
    );

    const removeButton = screen.getByLabelText('Remove image');
    fireEvent.click(removeButton);

    expect(handleRemove).toHaveBeenCalledTimes(1);
  });
});
