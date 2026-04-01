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
import type { AudioClip } from '../../../../data/types/canvas';
import {
  PIXELS_PER_SECOND,
  AUDIO_TRACK_HEIGHT,
  getClipDuration,
} from './TimelineUtils';

export default function AudioClipItem({
  clip,
  startTime,
  onClick,
}: {
  clip: AudioClip;
  startTime: number;
  onClick?: (clip: AudioClip) => void;
}) {
  const left = startTime * PIXELS_PER_SECOND;
  const width = getClipDuration(clip) * PIXELS_PER_SECOND;

  const fadeInPx = (clip.fade_in_duration_seconds || 0) * PIXELS_PER_SECOND;
  const fadeOutPx = (clip.fade_out_duration_seconds || 0) * PIXELS_PER_SECOND;
  const height = AUDIO_TRACK_HEIGHT - 10;

  const safeFadeIn = Math.min(fadeInPx, width);
  const safeFadeOut = Math.min(fadeOutPx, width - safeFadeIn);
  const volumeLevelY = 0; // Top of the clip (Full Volume)

  // Define the volume shape (The area representing "Sound")
  let pathData = `M 0 ${height}`; // Start bottom-left

  // Convex Fade In (Rises quickly)
  if (safeFadeIn > 0) {
    // Quadratic Bezier with control point at (0, 0) [Top-Left]
    // This pulls the curve up quickly
    pathData += ` Q 0 ${volumeLevelY}, ${safeFadeIn} ${volumeLevelY}`;
  } else {
    pathData += ` L 0 ${volumeLevelY}`;
  }

  // Sustain
  pathData += ` L ${width - safeFadeOut} ${volumeLevelY}`;

  // Convex Fade Out (Drops slowly then quickly)
  if (safeFadeOut > 0) {
    // Quadratic Bezier with control point at (width, 0) [Top-Right]
    // This keeps the curve high for longer before dropping
    pathData += ` Q ${width} ${volumeLevelY}, ${width} ${height}`;
  } else {
    pathData += ` L ${width} ${height}`;
  }

  pathData += ` L 0 ${height} Z`; // Close path

  // Build the stroke line (just the top edge of the envelope)
  // Use exact same logic as pathData but without the closing loop
  let lineData = `M 0 ${height}`; // Start bottom-left

  if (safeFadeIn > 0) {
    lineData += ` Q 0 ${volumeLevelY}, ${safeFadeIn} ${volumeLevelY}`;
  } else {
    lineData += ` L 0 ${volumeLevelY}`;
  }

  lineData += ` L ${width - safeFadeOut} ${volumeLevelY}`;

  if (safeFadeOut > 0) {
    lineData += ` Q ${width} ${volumeLevelY}, ${width} ${height}`;
  } else {
    lineData += ` L ${width} ${height}`;
  }

  return (
    <Box
      onClick={() => onClick?.(clip)}
      sx={{
        position: 'absolute',
        left: left,
        width: width,
        height: height,
        top: 5,
        bgcolor: '#1a1a1a', // Very dark background (representing silence/empty)
        borderRadius: 0,
        border: '1px solid',
        borderColor: 'divider',
        overflow: 'hidden',
        cursor: 'pointer',
        '&:hover': {
          borderColor: 'primary.main',
        },
        opacity: clip.placeholder ? 0.6 : 1,
      }}
      title={clip.placeholder || clip.asset.file_name || 'Audio Clip'}
    >
      {/* Waveform simulation (Background pattern) */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: 0.2,
          backgroundImage:
            'linear-gradient(90deg, transparent 50%, rgba(255,255,255,0.5) 50%)',
          backgroundSize: '4px 100%',
          zIndex: 0,
        }}
      />

      {/* Volume Shape Visualization */}
      <svg
        width="100%"
        height="100%"
        preserveAspectRatio="none"
        style={{ display: 'block', position: 'relative', zIndex: 1 }}
      >
        {/* The "Sound" Area - using a nicer blue */}
        <path d={pathData} fill="#4682B4" />

        {/* Fade curve outline */}
        <path d={lineData} fill="none" stroke="#87CEEB" strokeWidth="1" />
      </svg>

      {/* Text Overlay */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: 1,
          zIndex: 2,
        }}
      >
        <Typography
          variant="caption"
          noWrap
          sx={{ color: 'white', textShadow: '0px 1px 2px rgba(0,0,0,0.8)' }}
        >
          {clip.placeholder || clip.asset.file_name}
        </Typography>
      </Box>

      {clip.placeholder && (
        <Typography
          variant="caption"
          sx={{
            position: 'absolute',
            top: 2,
            right: 2,
            bgcolor: 'rgba(0,0,0,0.7)',
            p: 0.5,
            borderRadius: 0.5,
            color: 'white',
            zIndex: 3,
          }}
        >
          Error
        </Typography>
      )}
    </Box>
  );
}
