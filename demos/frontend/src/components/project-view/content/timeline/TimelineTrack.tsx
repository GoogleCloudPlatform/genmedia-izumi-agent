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

import { Box, Typography } from '@mui/material';

export default function TimelineTrack({
  children,
  name,
  height,
}: {
  children: React.ReactNode;
  name: string;
  height: number;
}) {
  return (
    <Box
      sx={{
        position: 'relative',
        height: height,
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        display: 'flex',
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          width: 150,
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          px: 2,
          bgcolor: 'action.hover',
          zIndex: 10,
        }}
      >
        <Typography variant="body2" fontWeight="bold" noWrap>
          {name}
        </Typography>
      </Box>
      <Box sx={{ position: 'relative', flexGrow: 1, overflow: 'hidden' }}>
        {children}
      </Box>
    </Box>
  );
}
