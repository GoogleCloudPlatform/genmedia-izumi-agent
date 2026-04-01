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

import { Typography, Box, Paper, ListItem } from '@mui/material';
import type { Components } from 'react-markdown';
import React from 'react';

interface CustomCodeProps extends React.HTMLAttributes<HTMLElement> {
  inline?: boolean;
}

const MarkdownRenderer: Components = {
  h1: (props) => <Typography variant="h4">{props.children}</Typography>,
  h2: (props) => <Typography variant="h5">{props.children}</Typography>,
  h3: (props) => <Typography variant="h6">{props.children}</Typography>,
  h4: (props) => <Typography variant="subtitle1">{props.children}</Typography>,
  h5: (props) => <Typography variant="subtitle2">{props.children}</Typography>,
  h6: (props) => <Typography variant="body1">{props.children}</Typography>,
  p: (props) => (
    <Typography variant="body1" sx={{ mb: 1, '&:last-child': { mb: 0 } }}>
      {props.children}
    </Typography>
  ),
  a: (props) => (
    <Typography component="a" color="primary" href={props.href}>
      {props.children}
    </Typography>
  ),
  ul: (props) => (
    <Box
      component="ul"
      sx={{ listStyleType: 'disc', listStylePosition: 'inside', pl: 2, my: 1 }}
    >
      {props.children}
    </Box>
  ),
  ol: (props) => (
    <Box
      component="ol"
      sx={{
        listStyleType: 'decimal',
        listStylePosition: 'inside',
        pl: 2,
        my: 1,
      }}
    >
      {props.children}
    </Box>
  ),
  li: (props) => (
    <ListItem sx={{ display: 'list-item', pl: 1 }} dense>
      {props.children}
    </ListItem>
  ),
  blockquote: (props) => (
    <Paper sx={{ p: 2, my: 2, bgcolor: 'grey.200' }}>
      <Typography component="blockquote">{props.children}</Typography>
    </Paper>
  ),
  pre: (props) => (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        my: 2,
        bgcolor: 'grey.900',
        color: 'common.white',
        overflowX: 'auto',
        borderRadius: 2,
      }}
    >
      {props.children}
    </Paper>
  ),
  code: (props: CustomCodeProps) => {
    const { inline, children } = props;
    if (inline) {
      return (
        <Box
          component="code"
          sx={{
            bgcolor: 'rgba(0, 0, 0, 0.06)',
            color: 'text.primary',
            px: 0.6,
            py: 0.2,
            borderRadius: 1,
            fontFamily: 'monospace',
            fontSize: '0.875em',
            display: 'inline',
          }}
        >
          {children}
        </Box>
      );
    }
    return (
      <Typography
        component="code"
        sx={{ fontFamily: 'monospace', fontSize: '0.875rem', color: 'inherit' }}
      >
        {children}
      </Typography>
    );
  },
};

export default MarkdownRenderer;
