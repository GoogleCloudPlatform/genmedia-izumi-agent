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
import { describe, it, expect } from 'vitest';
import ReactMarkdown from 'react-markdown';
import MarkdownRenderer from './MarkdownRenderer';

describe('MarkdownRenderer', () => {
  it('renders headers correctly using Typography', () => {
    render(
      <ReactMarkdown components={MarkdownRenderer}>
        {'# Header 1\n## Header 2'}
      </ReactMarkdown>,
    );
    expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent(
      'Header 1',
    ); // Mapped to h4
    expect(screen.getByRole('heading', { level: 5 })).toHaveTextContent(
      'Header 2',
    ); // Mapped to h5
  });

  it('renders paragraphs correctly', () => {
    render(
      <ReactMarkdown components={MarkdownRenderer}>
        This is a paragraph.
      </ReactMarkdown>,
    );
    expect(screen.getByText('This is a paragraph.')).toBeInTheDocument();
    expect(screen.getByText('This is a paragraph.').tagName).toBe('P');
  });

  it('renders links correctly', () => {
    render(
      <ReactMarkdown components={MarkdownRenderer}>
        [Link Text](https://example.com)
      </ReactMarkdown>,
    );
    const link = screen.getByRole('link', { name: 'Link Text' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', 'https://example.com');
  });

  it('renders lists correctly', () => {
    const markdown = `
- Item 1
- Item 2
    `;
    render(
      <ReactMarkdown components={MarkdownRenderer}>{markdown}</ReactMarkdown>,
    );
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();
  });

  it('renders code blocks correctly', () => {
    const markdown = '```\nconst x = 1;\n```';
    render(
      <ReactMarkdown components={MarkdownRenderer}>{markdown}</ReactMarkdown>,
    );
    // The code block is rendered inside a pre tag which is inside a Paper component
    // We can check for the text content
    expect(screen.getByText('const x = 1;')).toBeInTheDocument();
  });

  it('renders inline code correctly', () => {
    render(
      <ReactMarkdown components={MarkdownRenderer}>
        Use `variable` here.
      </ReactMarkdown>,
    );
    expect(screen.getByText('variable')).toBeInTheDocument();
  });
});
