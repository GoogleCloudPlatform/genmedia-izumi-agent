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

import { useState } from 'react';
import {
  Typography,
  Box,
  Paper,
  CircularProgress,
  IconButton,
  Divider,
} from '@mui/material';
import BrushIcon from '@mui/icons-material/Brush';
import type { Canvas } from '../../../data/types';
import VideoTimelineView from './VideoTimelineView';

interface CanvasViewProps {
  canvases: readonly Canvas[];
  selectedCanvas: Canvas | null;
  onCanvasClick: (canvas: Canvas) => void;
  onBackToCanvasList: () => void;
}

interface HtmlCanvasDetailViewProps {
  canvas: Canvas;
  onBack: () => void;
}

function HtmlCanvasDetailView({ canvas, onBack }: HtmlCanvasDetailViewProps) {
  const [isLoading, setIsLoading] = useState(true);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Paper
        elevation={0}
        variant="outlined"
        sx={{
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          mb: 2,
        }}
      >
        <IconButton onClick={onBack} size="small">
          <Typography variant="button">Back</Typography>
        </IconButton>

        <Divider orientation="vertical" flexItem />

        <Typography variant="subtitle1" lineHeight={1.2}>
          {canvas.name}
        </Typography>
      </Paper>
      <Box
        sx={{
          position: 'relative',
          width: '100%',
          height: 'calc(100vh - 200px)',
          bgcolor: 'background.paper',
        }}
      >
        {isLoading && (
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
              zIndex: 1,
            }}
          >
            <CircularProgress />
          </Box>
        )}
        {canvas.url && (
          <iframe
            src={canvas.url}
            onLoad={() => setIsLoading(false)}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              opacity: isLoading ? 0 : 1,
              transition: 'opacity 0.3s ease-in-out',
            }}
            title={canvas.name}
          />
        )}
      </Box>
    </Box>
  );
}

export default function CanvasView({
  canvases,
  selectedCanvas,
  onCanvasClick,
  onBackToCanvasList,
}: CanvasViewProps) {
  if (canvases.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <BrushIcon sx={{ fontSize: 80, color: 'text.secondary' }} />
        <Typography variant="h6" gutterBottom>
          No canvases yet.
        </Typography>
        <Typography variant="body1">
          Your created canvases will appear here.
        </Typography>
      </Box>
    );
  }

  if (selectedCanvas) {
    if (selectedCanvas.type === 'video_timeline') {
      return (
        <VideoTimelineView
          key={selectedCanvas.id}
          canvas={selectedCanvas}
          onBack={onBackToCanvasList}
        />
      );
    }
    return (
      <HtmlCanvasDetailView
        key={selectedCanvas.id}
        canvas={selectedCanvas}
        onBack={onBackToCanvasList}
      />
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 2,
      }}
    >
      {canvases.map((canvas) => (
        <Box
          key={canvas.id}
          sx={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            p: 1,
            boxSizing: 'border-box',
            minHeight: '200px',
          }}
        >
          <Paper
            sx={{
              p: 1,
              textAlign: 'center',
              flexGrow: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              cursor: 'pointer',
            }}
            onClick={() => onCanvasClick(canvas)}
          >
            <Typography variant="h6">{canvas.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {canvas.type === 'video_timeline'
                ? 'Video Project'
                : 'HTML Canvas'}
            </Typography>
          </Paper>
        </Box>
      ))}
    </Box>
  );
}
