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

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Alert } from '@mui/material';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Shown in place of the subtree that failed. */
  fallback: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Keeps one bad subtree from taking down the page.
 *
 * Anything rendered from agent output can surprise us — a field documented as
 * a string arriving as an object is enough to throw during render, and React
 * unmounts the whole tree when that reaches the root.
 */
export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Render failed', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return <Alert severity="warning">{this.props.fallback}</Alert>;
    }
    return this.props.children;
  }
}
