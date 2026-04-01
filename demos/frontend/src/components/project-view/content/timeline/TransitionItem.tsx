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

import { Box, Tooltip } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import type { Transition } from '../../../../data/types/canvas';
import { PIXELS_PER_SECOND, TRACK_HEIGHT } from './TimelineUtils';

export default function TransitionItem({
  transition,
  startTime,
}: {
  transition: Transition | null;
  startTime: number;
}) {
  if (
    !transition ||
    transition.type === 'none' ||
    transition.duration_seconds <= 0
  ) {
    return null;
  }

  const width = transition.duration_seconds * PIXELS_PER_SECOND;
  // Center the transition marker on the cut point (startTime)
  const left = startTime * PIXELS_PER_SECOND - width / 2;

  return (
    <Tooltip
      title={`${transition.type} transition (${transition.duration_seconds}s)`}
      arrow
    >
      <Box
        sx={{
          position: 'absolute',
          left: left,
          width: width,
          height: TRACK_HEIGHT - 10,
          top: 5,
          zIndex: 20, // On top of clips
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'help',
        }}
      >
        {/* Visual representation of the transition overlay */}
        <Box
          sx={{
            width: '100%',
            height: '100%',
            bgcolor: 'rgba(255, 255, 255, 0.4)',
            border: '1px solid rgba(255, 255, 255, 0.6)',
            borderRadius: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backdropFilter: 'blur(2px)',
          }}
        >
          <Box
            sx={{
              bgcolor: 'white',
              borderRadius: '50%',
              p: 0.5,
              display: 'flex',
              boxShadow: 1,
            }}
          >
            <AutoAwesomeIcon sx={{ fontSize: 14, color: 'primary.main' }} />
          </Box>
        </Box>
      </Box>
    </Tooltip>
  );
}
