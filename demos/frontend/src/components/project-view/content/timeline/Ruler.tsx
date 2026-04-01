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
import { PIXELS_PER_SECOND, RULER_HEIGHT, formatTime } from './TimelineUtils';

export default function Ruler({ duration }: { duration: number }) {
  const ticks = [];
  const labels = [];
  const extendedDuration = Math.ceil(duration); // Match exact duration rounded up to nearest second

  for (let i = 0; i <= extendedDuration; i++) {
    const isMajor = i % 5 === 0;

    // Time Labels
    if (isMajor) {
      labels.push(
        <Typography
          key={`label-${i}`}
          variant="caption"
          sx={{
            position: 'absolute',
            top: 0, // Aligned at the very top of the new smaller ruler
            left: i * PIXELS_PER_SECOND + 4,
            color: 'rgba(255, 255, 255, 0.7)',
            fontFamily: 'monospace',
            fontSize: '0.75rem',
            lineHeight: 1,
            whiteSpace: 'nowrap',
            zIndex: 2,
          }}
        >
          {formatTime(i)}
        </Typography>,
      );
    }

    // Tick Marks
    const tickHeight = isMajor ? '100%' : '50%';
    const tickColor = isMajor
      ? 'rgba(255, 255, 255, 0.4)'
      : 'rgba(255, 255, 255, 0.15)';

    ticks.push(
      <Box
        key={`tick-${i}`}
        sx={{
          position: 'absolute',
          left: i * PIXELS_PER_SECOND,
          top: 0,
          height: tickHeight,
          width: '1px', // Explicit pixel width
          bgcolor: tickColor,
          zIndex: 1,
        }}
      />,
    );
  }

  return (
    <Box
      sx={{
        height: RULER_HEIGHT,
        ml: '150px',
        position: 'relative',
        bgcolor: '#202020',
        minWidth: extendedDuration * PIXELS_PER_SECOND,
        overflow: 'hidden',
        borderBottom: '1px solid #444',
      }}
    >
      {ticks}
      {labels}
    </Box>
  );
}
