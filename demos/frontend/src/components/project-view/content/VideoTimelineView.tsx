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

import { useState, useMemo, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  IconButton,
  Stack,
  CircularProgress,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { useParams } from 'react-router-dom';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import type {
  Canvas,
  VideoTimelineContent,
  VideoClip,
  AudioClip,
} from '../../../data/types/canvas';
import type { AssetGenerateConfig } from '../../../data/types/assets';
import projectService from '../../../services/projectService';
import {
  organizeAudioTracks,
  PIXELS_PER_SECOND,
  TRACK_HEIGHT,
  AUDIO_TRACK_HEIGHT,
  mapAssetToProjectAsset,
  getClipDuration,
} from './timeline/TimelineUtils';
import Ruler from './timeline/Ruler';
import VideoClipItem from './timeline/VideoClipItem';
import AudioClipItem from './timeline/AudioClipItem';
import TransitionItem from './timeline/TransitionItem';
import TimelineTrack from './timeline/TimelineTrack';
import GenerateConfigPanel from '../../shared/GenerateConfigPanel';

interface VideoTimelineViewProps {
  canvas: Canvas;
  onBack: () => void;
}

export default function VideoTimelineView({
  canvas,
  onBack,
}: VideoTimelineViewProps) {
  const { id: projectId } = useParams();
  const [fetchedContent, setFetchedContent] =
    useState<VideoTimelineContent | null>(null);
  const [selectedClip, setSelectedClip] = useState<
    VideoClip | AudioClip | null
  >(null);
  const [previewVersion, setPreviewVersion] = useState<number>(1);
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null);

  // Initialize loading based on whether we need to fetch
  const [isLoading, setIsLoading] = useState(
    !canvas.videoTimeline && !!projectId,
  );

  useEffect(() => {
    if (selectedClip?.asset) {
      // Disabling lint: This effect syncs internal UI state (previewVersion) with a prop (selectedClip.asset.current_version)
      // while also allowing user interaction to change previewVersion. This is a common pattern for 'controlled' internal state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreviewVersion(selectedClip.asset.current_version);
    }
  }, [selectedClip]);

  useEffect(() => {
    if (!canvas.videoTimeline && projectId) {
      projectService.getCanvas(projectId, canvas.id).then((fullCanvas) => {
        if (fullCanvas?.videoTimeline) {
          setFetchedContent(fullCanvas.videoTimeline);
        }
        setIsLoading(false);
      });
    }
  }, [canvas.id, canvas.videoTimeline, projectId]);

  // Reset media player when selected clip changes
  useEffect(() => {
    if (mediaRef.current) {
      mediaRef.current.load();
      if (
        selectedClip?.asset &&
        (selectedClip.asset.mime_type.startsWith('video') ||
          selectedClip.asset.mime_type.startsWith('audio'))
      ) {
        // Auto-play when selecting a new clip
        mediaRef.current.play().catch(() => {});
      }
    }
  }, [selectedClip]);

  // Ensure content is not null, provide defaults for easier access
  const content: VideoTimelineContent = fetchedContent ||
    canvas.videoTimeline || {
      title: canvas.name,
      video_clips: [],
      audio_clips: [],
      transitions: [],
      transition_in: null,
      transition_out: null,
    };

  // Calculate cumulative start times for video clips
  const videoClipStartTimes = useMemo(() => {
    const times: number[] = [];
    content.video_clips.reduce((acc, clip) => {
      times.push(acc);
      return acc + getClipDuration(clip);
    }, 0);
    return times;
  }, [content.video_clips]);

  // Organize audio clips into tracks
  const audioTracks = useMemo(() => {
    return organizeAudioTracks(content.audio_clips, videoClipStartTimes);
  }, [content.audio_clips, videoClipStartTimes]);

  // Calculate overall timeline duration
  const timelineMaxDuration = useMemo(() => {
    // Video track end (assuming sequential)
    const videoEnd = content.video_clips.reduce(
      (sum, clip) => sum + getClipDuration(clip),
      0,
    );

    // Audio track end (based on start_at + duration)
    const audioEnd = content.audio_clips.reduce((maxEnd, clip) => {
      const videoStartIndex = clip.start_at.video_clip_index;
      const videoStartTime = videoClipStartTimes[videoStartIndex] ?? 0;
      const clipStartTime = videoStartTime + clip.start_at.offset_seconds;
      const clipEndTime = clipStartTime + getClipDuration(clip);
      return Math.max(maxEnd, clipEndTime);
    }, 0);

    return Math.max(videoEnd, audioEnd);
  }, [content.video_clips, content.audio_clips, videoClipStartTimes]);

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          height: '100%',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Preview Logic
  const renderPreview = () => {
    if (!selectedClip) {
      return (
        <Typography color="text.secondary">
          Click on a video or audio clip to preview it
        </Typography>
      );
    }

    const asset = selectedClip.asset;
    let projectAsset = asset ? mapAssetToProjectAsset(asset) : null;

    if (projectAsset) {
      projectAsset = {
        ...projectAsset,
        url: projectAsset.url.replace(
          /version=\d+/,
          `version=${previewVersion}`,
        ),
      };
    }

    // Handle case where video clip has no asset but has frames (using placeholder or first_frame)
    // For simplicity, we focus on playing actual assets.
    // If it's a video clip with only an image (first_frame_asset), we show that.

    let mediaElement = null;

    if (projectAsset) {
      if (projectAsset.type === 'video') {
        mediaElement = (
          <video
            ref={mediaRef as React.RefObject<HTMLVideoElement>}
            src={projectAsset.url}
            controls
            style={{
              maxHeight: '100%',
              maxWidth: '100%',
              objectFit: 'contain',
            }}
          />
        );
      } else if (projectAsset.type === 'audio') {
        mediaElement = (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
              width: '100%',
              px: 4,
            }}
          >
            <VolumeUpIcon sx={{ fontSize: 64, color: 'text.secondary' }} />
            <audio
              ref={mediaRef as React.RefObject<HTMLAudioElement>}
              src={projectAsset.url}
              controls
              style={{ width: '100%' }}
            />
          </Box>
        );
      } else if (projectAsset.type === 'image') {
        mediaElement = (
          <img
            src={projectAsset.url}
            alt={projectAsset.fileName}
            style={{
              maxHeight: '100%',
              maxWidth: '100%',
              objectFit: 'contain',
            }}
          />
        );
      }
    } else {
      // Fallback for missing asset (e.g. failed generation)
      // Maybe check for first_frame_asset if it's a video clip
      const fallbackAsset = (selectedClip as VideoClip).first_frame_asset;
      if (fallbackAsset) {
        const fallbackUrl = mapAssetToProjectAsset(fallbackAsset).url;
        mediaElement = (
          <img
            src={fallbackUrl}
            alt={fallbackAsset.file_name}
            style={{
              maxHeight: '100%',
              maxWidth: '100%',
              objectFit: 'contain',
            }}
          />
        );
      } else {
        mediaElement = (
          <Typography color="error">
            Asset missing or failed to load.
          </Typography>
        );
      }
    }

    // Config Panel logic - extract generate config
    const currentGenerateConfig = asset
      ? (() => {
          const versionData = asset.versions?.find(
            (v) => v.version_number === previewVersion,
          );
          if (versionData) {
            return (versionData.image_generate_config ||
              versionData.music_generate_config ||
              versionData.video_generate_config ||
              versionData.speech_generate_config ||
              versionData.text_generate_config) as AssetGenerateConfig | null;
          }
          return projectAsset?.generateConfig;
        })()
      : null;

    return (
      <Box
        sx={{
          display: 'flex',
          width: '100%',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        {/* Left Side: Media Player */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            p: 2,
            gap: 2,
            overflow: 'hidden',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {mediaElement}
        </Box>

        {/* Right Side: Info Panel */}
        <Box
          sx={{
            width: 320,
            borderLeft: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'background.paper',
            overflowY: 'auto',
          }}
        >
          {/* Clip Details Section */}
          <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
            {asset?.versions && asset.versions.length > 1 && (
              <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                <InputLabel id="timeline-version-select-label">
                  Version
                </InputLabel>
                <Select
                  labelId="timeline-version-select-label"
                  value={previewVersion}
                  label="Version"
                  onChange={(e) => setPreviewVersion(Number(e.target.value))}
                >
                  {[...asset.versions]
                    .sort((a, b) => b.version_number - a.version_number)
                    .map((v) => (
                      <MenuItem key={v.version_number} value={v.version_number}>
                        Version {v.version_number}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            )}

            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
              Clip Details
            </Typography>
            <Stack spacing={1}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  Start Offset
                </Typography>
                <Typography variant="body2">
                  {selectedClip.trim?.offset_seconds?.toFixed(2) || 'N/A'}s
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  Duration
                </Typography>
                <Typography variant="body2">
                  {getClipDuration(selectedClip).toFixed(2)}s
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary">
                  End Trim
                </Typography>
                <Typography variant="body2">
                  {(
                    (selectedClip.trim?.offset_seconds || 0) +
                    getClipDuration(selectedClip)
                  ).toFixed(2)}
                  s
                </Typography>
              </Box>
            </Stack>
          </Box>

          {/* Generation Details Section */}
          {currentGenerateConfig && (
            <>
              <Box
                sx={{
                  p: '8px 16px',
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'action.hover',
                }}
              >
                <Typography variant="subtitle2" fontWeight="bold">
                  Generation Config
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1, p: 2 }}>
                <GenerateConfigPanel
                  config={currentGenerateConfig}
                  onAssetClick={() => {}}
                />
              </Box>
            </>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header / Toolbar */}
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

        <Box sx={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
          <Typography variant="subtitle1" lineHeight={1.2}>
            {content.title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Total Duration: {timelineMaxDuration}s
          </Typography>
        </Box>
      </Paper>

      {/* Preview Area */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          minHeight: 300, // Increased height
          mb: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.default', // Use default background instead of black
        }}
      >
        {renderPreview()}
      </Box>

      {/* Timeline Area */}
      <Paper
        elevation={0}
        variant="outlined"
        sx={{
          flexShrink: 0,
          height: 300,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ overflowX: 'auto', flexGrow: 1 }}>
          <Box sx={{ minWidth: timelineMaxDuration * PIXELS_PER_SECOND + 150 }}>
            <Ruler duration={timelineMaxDuration} />

            <TimelineTrack name="Video" height={TRACK_HEIGHT}>
              {content.video_clips.map((clip, index) => (
                <VideoClipItem
                  key={index}
                  clip={clip}
                  startTime={videoClipStartTimes[index]}
                  onClick={setSelectedClip}
                />
              ))}
              {content.transitions.map((transition, index) => {
                // Transitions sit between clips.
                const clipEndTime =
                  videoClipStartTimes[index] +
                  getClipDuration(content.video_clips[index]);
                return (
                  <TransitionItem
                    key={`trans-${index}`}
                    transition={transition}
                    startTime={clipEndTime}
                  />
                );
              })}
            </TimelineTrack>

            {/* Render dynamically calculated audio tracks */}
            {audioTracks.map((track, trackIndex) => (
              <TimelineTrack
                key={`audio-track-${trackIndex}`}
                name={`Audio ${trackIndex + 1}`}
                height={AUDIO_TRACK_HEIGHT}
              >
                {track.map((item, itemIndex) => (
                  <AudioClipItem
                    key={`audio-clip-${trackIndex}-${itemIndex}`}
                    clip={item.clip}
                    startTime={item.startTime}
                    onClick={setSelectedClip}
                  />
                ))}
              </TimelineTrack>
            ))}

            {/* Empty State if no audio tracks */}
            {audioTracks.length === 0 && (
              <TimelineTrack name="Audio 1" height={AUDIO_TRACK_HEIGHT}>
                <Box />
              </TimelineTrack>
            )}
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
