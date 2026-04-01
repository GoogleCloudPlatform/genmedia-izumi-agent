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

import { useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import type { VideoClip } from '../../../../data/types/canvas';
import {
  PIXELS_PER_SECOND,
  TRACK_HEIGHT,
  mapAssetToProjectAsset,
  getClipDuration,
} from './TimelineUtils';

function useVideoFrames({
  videoUrl,
  trimOffset,
  trimDuration,
  containerWidth,
  frameHeight,
}: {
  videoUrl?: string;
  trimOffset: number;
  trimDuration: number;
  containerWidth: number;
  frameHeight: number;
}) {
  const [frames, setFrames] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    video.crossOrigin = 'anonymous';
    if (videoUrl) video.src = videoUrl;
    video.muted = true;

    const extractFrames = async () => {
      if (!videoUrl || containerWidth <= 0 || trimDuration <= 0) {
        if (isMounted) setFrames([]);
        return;
      }

      setLoading(true);
      const extractedFrames: string[] = [];

      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve();
        video.onerror = (e) => reject(e);
      });

      if (!isMounted) return;

      const aspectRatio = video.videoWidth / video.videoHeight;
      const frameWidth = frameHeight * aspectRatio;

      // Calculate how many frames fit in the container
      const frameCount = Math.ceil(containerWidth / frameWidth);
      // Limit max frames to avoid performance issues
      const safeFrameCount = Math.min(Math.max(frameCount, 1), 20);

      const timeStep = trimDuration / safeFrameCount;

      // Downscale for performance/memory
      canvas.width = video.videoWidth / 4;
      canvas.height = video.videoHeight / 4;

      for (let i = 0; i < safeFrameCount; i++) {
        if (!isMounted) break;

        const seekTime = trimOffset + i * timeStep;
        const safeSeekTime = Math.min(seekTime, video.duration);

        video.currentTime = safeSeekTime;

        await new Promise<void>((resolve) => {
          const onSeeked = () => {
            video.removeEventListener('seeked', onSeeked);
            resolve();
          };
          video.addEventListener('seeked', onSeeked, { once: true });
        });

        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          extractedFrames.push(canvas.toDataURL('image/jpeg', 0.7));
        }
      }

      if (isMounted) {
        setFrames(extractedFrames);
        setLoading(false);
      }

      video.removeAttribute('src');
      video.load();
    };

    extractFrames().catch((err) => {
      console.error('Error extracting frames:', err);
      if (isMounted) setLoading(false);
    });

    return () => {
      isMounted = false;
      video.pause();
      video.removeAttribute('src');
      video.load();
    };
  }, [videoUrl, trimOffset, trimDuration, containerWidth, frameHeight]);

  return { frames, loading };
}

export default function VideoClipItem({
  clip,
  startTime,
  onClick,
}: {
  clip: VideoClip;
  startTime: number;
  onClick?: (clip: VideoClip) => void;
}) {
  const width = getClipDuration(clip) * PIXELS_PER_SECOND;
  const left = startTime * PIXELS_PER_SECOND;

  const currentVersion =
    clip.asset?.versions?.find(
      (v) => v.version_number === clip.asset?.current_version,
    ) || clip.asset?.versions?.[0];
  const generatedFirstFrameAsset =
    currentVersion?.video_generate_config?.first_frame_asset;

  // The asset to *try* and display as a static image first.
  const staticPreviewAsset = clip.first_frame_asset || generatedFirstFrameAsset;

  // Specifically extract frames from the video asset if available
  const videoAsset = clip.asset?.mime_type.startsWith('video')
    ? clip.asset
    : null;
  const videoUrl = videoAsset
    ? mapAssetToProjectAsset(videoAsset).url
    : undefined;

  const { frames } = useVideoFrames({
    videoUrl,
    trimOffset: clip.trim?.offset_seconds || 0,
    trimDuration: getClipDuration(clip),
    containerWidth: width,
    frameHeight: TRACK_HEIGHT - 10,
  });

  return (
    <Box
      onClick={() => onClick?.(clip)}
      sx={{
        position: 'absolute',
        left: left,
        width: width,
        height: TRACK_HEIGHT - 10,
        top: 5,
        bgcolor: 'primary.main',
        borderRadius: 0,
        border: '1px solid',
        borderColor: 'divider',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        color: 'white',
        cursor: 'pointer',
        '&:hover': {
          bgcolor: 'primary.dark',
        },
        opacity: clip.placeholder ? 0.6 : 1,
        borderLeft: '1px solid rgba(255,255,255,0.3)',
        borderRight: '1px solid rgba(255,255,255,0.3)',
      }}
      title={clip.placeholder || staticPreviewAsset?.file_name || 'Video Clip'}
    >
      {frames.length > 0 ? (
        <Box
          sx={{
            display: 'flex',
            width: '100%',
            height: '100%',
            overflow: 'hidden',
          }}
        >
          {frames.map((frame, index) => (
            <img
              key={index}
              src={frame}
              alt={`frame-${index}`}
              style={{
                height: '100%',
                objectFit: 'cover',
                flexGrow: 1,
                minWidth: 0,
              }}
            />
          ))}
        </Box>
      ) : staticPreviewAsset ? (
        <img
          src={mapAssetToProjectAsset(staticPreviewAsset).url}
          alt={staticPreviewAsset.file_name || 'Preview'}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />
      ) : (
        <Typography variant="caption" noWrap sx={{ px: 1 }}>
          {clip.placeholder || 'Video'}
        </Typography>
      )}
      {clip.placeholder && (
        <Typography
          variant="caption"
          sx={{
            position: 'absolute',
            bgcolor: 'rgba(0,0,0,0.7)',
            p: 0.5,
            borderRadius: 0.5,
          }}
        >
          Error
        </Typography>
      )}
    </Box>
  );
}
