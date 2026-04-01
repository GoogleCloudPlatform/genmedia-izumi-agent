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

import {
  Modal,
  Box,
  IconButton,
  Typography,
  Fade,
  Backdrop,
  CircularProgress,
  Button,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ArrowBackIosNewIcon from '@mui/icons-material/ArrowBackIosNew';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DownloadIcon from '@mui/icons-material/Download';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useRef, useEffect, useState, useCallback } from 'react';

import projectService from '../../services/projectService';
import type { ProjectAsset, AssetGenerateConfig } from '../../data/types';

import GenerateConfigPanel from './GenerateConfigPanel';

interface AssetModalProps {
  open: boolean;
  onClose: () => void;
  asset: ProjectAsset | null;
  allAssets: readonly ProjectAsset[];
  onNavigate: (direction: 'prev' | 'next') => void;
  onAssetClick: (assetId: string) => void;
}

const getAssetDisplayName = (asset: ProjectAsset) => {
  if (asset.fileName) return asset.fileName;
  try {
    const urlObj = new URL(asset.url);
    const parts = urlObj.pathname.split('/');
    return parts[parts.length - 1];
  } catch {
    const parts = asset.url.split('/');
    return parts[parts.length - 1].split('?')[0];
  }
};

export default function AssetModal({
  open,
  onClose,
  asset,
  allAssets,
  onNavigate,
  onAssetClick,
}: AssetModalProps) {
  const mediaRef = useRef<
    HTMLVideoElement | HTMLAudioElement | HTMLImageElement
  >(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [loadingText, setLoadingText] = useState(false);
  const [isMediaLoading, setIsMediaLoading] = useState(false);
  const [showConfig, setShowConfig] = useState(true);
  const [selectedVersion, setSelectedVersion] = useState<number>(
    asset?.currentVersion || 1,
  );

  const imageRefCallback = useCallback((node: HTMLImageElement | null) => {
    mediaRef.current = node;
    if (node && node.complete) {
      setIsMediaLoading(false);
    }
  }, []);

  useEffect(() => {
    if (asset) {
      // Disabling lint: This effect syncs internal UI state (selectedVersion) with a prop (asset.currentVersion)
      // while also allowing user interaction to change selectedVersion. This is a common pattern for 'controlled' internal state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedVersion(asset.currentVersion);
    }
  }, [asset]);

  const currentUrl = asset
    ? asset.url.replace(/version=\d+/, `version=${selectedVersion}`)
    : '';

  const downloadUrl = currentUrl
    ? currentUrl.replace('/view', '/download')
    : '';

  const currentGenerateConfig = asset
    ? (() => {
        const versionData = asset.versions?.find(
          (v) => v.version_number === selectedVersion,
        );
        if (!versionData) return asset.generateConfig;

        return (versionData.image_generate_config ||
          versionData.music_generate_config ||
          versionData.video_generate_config ||
          versionData.speech_generate_config ||
          versionData.text_generate_config) as AssetGenerateConfig | null;
      })()
    : null;

  useEffect(() => {
    // Reset loading state when URL changes for non-text/binary assets
    if (asset && asset.type !== 'text' && asset.type !== 'binary') {
      const element = mediaRef.current;
      // Check if image is already loaded (e.g. from cache) to avoid race condition
      // where onLoad fires before this effect runs.
      if (
        asset.type === 'image' &&
        element &&
        (element as HTMLImageElement).complete
      ) {
        // Disabling lint: This setState ensures the loading spinner is not shown if the image
        // is already loaded from cache, preventing a flickering UI. It's an intentional
        // synchronous update to avoid a race condition with the onload event.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setIsMediaLoading(false);
        return;
      }

      setIsMediaLoading(true);
    }
  }, [currentUrl, asset]);

  useEffect(() => {
    const mediaElement = mediaRef.current;
    if (!open && mediaElement) {
      if (
        mediaElement instanceof HTMLVideoElement ||
        mediaElement instanceof HTMLAudioElement
      ) {
        mediaElement.pause();
        mediaElement.currentTime = 0;
      }
    }
  }, [open]);

  useEffect(() => {
    if (open && asset?.type === 'text' && currentUrl) {
      // Use setTimeout to avoid synchronous state update warning during render phase
      const timer = setTimeout(() => {
        setLoadingText(true);
        projectService
          .getAssetTextContent(currentUrl)
          .then((text) => {
            setTextContent(text);
            setLoadingText(false);
          })
          .catch((err) => {
            console.error('Failed to load text', err);
            setTextContent('Failed to load content.');
            setLoadingText(false);
          });
      }, 0);
      return () => clearTimeout(timer);
    } else {
      setTimeout(() => setTextContent(null), 0);
    }
  }, [asset, open, currentUrl]);

  const currentIndex = asset
    ? allAssets.findIndex((a) => a.id === asset.id)
    : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = asset ? currentIndex < allAssets.length - 1 : false;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowLeft') {
        if (hasPrev) {
          onNavigate('prev');
        }
      } else if (event.key === 'ArrowRight') {
        if (hasNext) {
          onNavigate('next');
        }
      }
    };

    if (open) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onNavigate, hasPrev, hasNext]);

  if (!asset) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      closeAfterTransition
      slots={{ backdrop: Backdrop }}
      slotProps={{
        backdrop: {
          timeout: 500,
          sx: {
            backgroundColor: 'rgba(15, 17, 23, 0.95)', // Deep dark background
            backdropFilter: 'blur(4px)',
          },
        },
      }}
    >
      <Fade in={open}>
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            outline: 'none',
            p: 2,
          }}
        >
          {/* Header / Close Button */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'center',
              width: '100%',
              mb: 2,
              zIndex: 10,
            }}
          >
            {asset && asset.versions && asset.versions.length > 1 && (
              <FormControl size="small" sx={{ mr: 2, minWidth: 120 }}>
                <InputLabel
                  id="version-select-label"
                  sx={{ color: 'rgba(255,255,255,0.7)' }}
                >
                  Version
                </InputLabel>
                <Select
                  labelId="version-select-label"
                  value={selectedVersion}
                  label="Version"
                  onChange={(e) => setSelectedVersion(Number(e.target.value))}
                  sx={{
                    color: 'white',
                    '.MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255,255,255,0.3)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255,255,255,0.5)',
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'primary.main',
                    },
                    '.MuiSvgIcon-root': { color: 'white' },
                  }}
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
            {downloadUrl && (
              <IconButton
                href={downloadUrl}
                download
                target="_blank"
                sx={{
                  color: 'white',
                  bgcolor: 'rgba(255,255,255,0.1)',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
                  mr: 1,
                }}
                title="Download Asset"
              >
                <DownloadIcon />
              </IconButton>
            )}
            {currentGenerateConfig && (
              <IconButton
                onClick={() => setShowConfig(!showConfig)}
                sx={{
                  color: showConfig ? 'primary.main' : 'white',
                  bgcolor: 'rgba(255,255,255,0.1)',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
                  mr: 1,
                }}
                title="Toggle Configuration"
              >
                <InfoOutlinedIcon />
              </IconButton>
            )}
            <IconButton
              onClick={onClose}
              sx={{
                color: 'white',
                bgcolor: 'rgba(255,255,255,0.1)',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
              }}
            >
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Main Content Area */}
          <Box
            sx={{
              flexGrow: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
              overflow: 'hidden', // Prevent overflow
              position: 'relative',
            }}
          >
            {/* Prev Button */}
            <IconButton
              onClick={() => onNavigate('prev')}
              disabled={!hasPrev}
              sx={{
                color: 'white',
                p: 2,
                position: { xs: 'absolute', md: 'static' },
                left: { xs: 10, md: 'auto' },
                zIndex: 5,
                bgcolor: { xs: 'rgba(0,0,0,0.5)', md: 'transparent' },
                '&:disabled': { opacity: 0.3, bgcolor: 'transparent' },
                '&:hover': {
                  bgcolor: {
                    xs: 'rgba(0,0,0,0.7)',
                    md: 'rgba(255,255,255,0.05)',
                  },
                },
              }}
            >
              <ArrowBackIosNewIcon fontSize="large" />
            </IconButton>

            {/* Split Container */}
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'row',
                width: '100%',
                height: '100%',
                overflow: 'hidden',
                gap: 2,
                px: { md: 6 }, // Space for arrows
              }}
            >
              {/* Asset Viewer */}
              <Box
                sx={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  overflow: asset.type === 'text' ? 'auto' : 'hidden',
                  minWidth: 0, // Allow flex item to shrink
                  position: 'relative',
                }}
              >
                {isMediaLoading && (
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
                      bgcolor: 'rgba(0,0,0,0.5)',
                      zIndex: 2,
                    }}
                  >
                    <CircularProgress />
                  </Box>
                )}
                {asset.type === 'video' ? (
                  <video
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    src={currentUrl}
                    controls
                    autoPlay
                    onLoadedData={() => setIsMediaLoading(false)}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      width: 'auto',
                      height: 'auto',
                      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                      borderRadius: '8px',
                      display: isMediaLoading ? 'none' : 'block',
                    }}
                  />
                ) : asset.type === 'audio' ? (
                  <audio
                    ref={mediaRef as React.RefObject<HTMLAudioElement>}
                    src={currentUrl}
                    controls
                    autoPlay
                    onLoadedData={() => setIsMediaLoading(false)}
                    style={{
                      width: '500px',
                      maxWidth: '100%',
                      display: isMediaLoading ? 'none' : 'block',
                    }}
                  />
                ) : asset.type === 'text' ? (
                  <Box
                    sx={{
                      bgcolor: 'background.paper',
                      color: 'text.primary',
                      p: 4,
                      borderRadius: 2,
                      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                      maxWidth: '800px',
                      width: '100%',
                      maxHeight: '70vh',
                      overflowY: 'auto',
                    }}
                  >
                    {loadingText ? (
                      <Box
                        sx={{ display: 'flex', justifyContent: 'center', p: 4 }}
                      >
                        <CircularProgress />
                      </Box>
                    ) : (
                      <pre
                        style={{
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          margin: 0,
                        }}
                      >
                        {textContent}
                      </pre>
                    )}
                  </Box>
                ) : asset.type === 'binary' ? (
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      p: 4,
                      color: 'white',
                      bgcolor: 'rgba(255,255,255,0.05)',
                      borderRadius: 2,
                    }}
                  >
                    <InsertDriveFileIcon
                      sx={{ fontSize: 80, mb: 2, opacity: 0.7 }}
                    />
                    <Typography variant="h6" gutterBottom>
                      Preview not available
                    </Typography>
                    <Button
                      variant="contained"
                      startIcon={<DownloadIcon />}
                      href={currentUrl}
                      download
                      target="_blank"
                      sx={{ mt: 2 }}
                    >
                      Download File
                    </Button>
                  </Box>
                ) : (
                  <img
                    ref={imageRefCallback}
                    src={currentUrl}
                    onLoad={() => setIsMediaLoading(false)}
                    alt="asset"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      width: 'auto',
                      height: 'auto',
                      objectFit: 'contain',
                      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                      borderRadius: '8px',
                      display: isMediaLoading ? 'none' : 'block',
                    }}
                  />
                )}
              </Box>

              {/* Config Panel */}
              {currentGenerateConfig && showConfig && (
                <Fade in={showConfig}>
                  <Paper
                    sx={{
                      width: 350,
                      display: { xs: 'none', md: 'flex' },
                      flexDirection: 'column',
                      bgcolor: 'background.paper',
                      borderRadius: 2,
                      overflow: 'hidden',
                      boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                    }}
                  >
                    <Box
                      sx={{
                        p: 2,
                        borderBottom: 1,
                        borderColor: 'divider',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <Typography variant="subtitle1" fontWeight="bold">
                        Generation Details
                      </Typography>
                    </Box>
                    <Box sx={{ p: 2, overflowY: 'auto', flexGrow: 1 }}>
                      <GenerateConfigPanel
                        config={currentGenerateConfig}
                        onAssetClick={onAssetClick}
                      />
                    </Box>
                  </Paper>
                </Fade>
              )}
            </Box>

            {/* Next Button */}
            <IconButton
              onClick={() => onNavigate('next')}
              disabled={!hasNext}
              sx={{
                color: 'white',
                p: 2,
                position: { xs: 'absolute', md: 'static' },
                right: { xs: 10, md: 'auto' },
                zIndex: 5,
                bgcolor: { xs: 'rgba(0,0,0,0.5)', md: 'transparent' },
                '&:disabled': { opacity: 0.3, bgcolor: 'transparent' },
                '&:hover': {
                  bgcolor: {
                    xs: 'rgba(0,0,0,0.7)',
                    md: 'rgba(255,255,255,0.05)',
                  },
                },
              }}
            >
              <ArrowForwardIosIcon fontSize="large" />
            </IconButton>
          </Box>

          {/* Footer Info */}
          <Box
            sx={{
              mt: 2,
              textAlign: 'center',
              color: 'text.secondary',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography variant="h6" color="text.primary">
              {getAssetDisplayName(asset)}
            </Typography>
            <Typography variant="body2">
              {currentIndex + 1} / {allAssets.length}
            </Typography>
          </Box>
        </Box>
      </Fade>
    </Modal>
  );
}
