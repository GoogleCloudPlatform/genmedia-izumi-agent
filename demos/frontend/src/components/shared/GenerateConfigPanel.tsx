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

import { Box, Typography, Chip, Stack, Paper, ButtonBase } from '@mui/material';
import { API_BASE_URL } from '../../services/api/client';
import type {
  AssetGenerateConfig,
  Asset,
  AssetImageGenerateConfig,
  AssetVideoGenerateConfig,
  AssetSpeechGenerateConfig,
} from '../../data/types/assets';

interface GenerateConfigPanelProps {
  config: AssetGenerateConfig;
  onAssetClick: (assetId: string) => void;
}

function AssetPreview({
  asset,
  label,
  onClick,
}: {
  asset: Asset;
  label?: string;
  onClick: (assetId: string) => void;
}) {
  const assetUrl = `${API_BASE_URL}/users/${asset.user_id}/assets/${asset.id}/view`;

  return (
    <ButtonBase
      onClick={() => onClick(asset.id)}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        width: 100,
        gap: 0.5,
        alignItems: 'flex-start',
        textAlign: 'left',
      }}
    >
      {label && (
        <Typography
          variant="caption"
          fontWeight="bold"
          color="text.secondary"
          noWrap
          sx={{ width: '100%' }}
        >
          {label}
        </Typography>
      )}
      <Box
        sx={{
          width: 100,
          height: 100,
          borderRadius: 1,
          overflow: 'hidden',
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.default',
          transition: 'transform 0.2s',
          '&:hover': {
            transform: 'scale(1.02)',
            borderColor: 'primary.main',
          },
        }}
      >
        <img
          src={assetUrl}
          alt={asset.file_name}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </Box>
      <Typography
        variant="caption"
        noWrap
        title={asset.file_name}
        sx={{ width: '100%' }}
      >
        {asset.file_name}
      </Typography>
    </ButtonBase>
  );
}

export default function GenerateConfigPanel({
  config,
  onAssetClick,
}: GenerateConfigPanelProps) {
  // Type guards or simple checks
  const isImageConfig = (
    c: AssetGenerateConfig,
  ): c is AssetImageGenerateConfig => 'reference_images' in c;
  const isVideoConfig = (
    c: AssetGenerateConfig,
  ): c is AssetVideoGenerateConfig =>
    'first_frame_asset' in c || 'last_frame_asset' in c;
  const isSpeechConfig = (
    c: AssetGenerateConfig,
  ): c is AssetSpeechGenerateConfig => 'voice' in c;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, p: 1 }}>
      {/* Model Info */}
      {config.model && (
        <Box>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            Model
          </Typography>
          <Box>
            <Chip
              label={config.model}
              size="small"
              variant="outlined"
              sx={{ borderRadius: 1 }}
            />
          </Box>
        </Box>
      )}

      {/* Speech Specific: Voice */}
      {isSpeechConfig(config) && (
        <Box>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            Voice
          </Typography>
          <Typography variant="body2">{config.voice}</Typography>
        </Box>
      )}

      {/* Prompt */}
      <Box>
        <Typography variant="caption" color="text.secondary" gutterBottom>
          {isSpeechConfig(config) ? 'Spoken Text' : 'Prompt'}
        </Typography>
        <Paper
          variant="outlined"
          sx={{
            p: 1.5,
            bgcolor: 'action.hover',
            border: 'none',
          }}
        >
          <Typography
            variant="body2"
            sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {isSpeechConfig(config) ? config.spoken_text : config.prompt}
          </Typography>
        </Paper>
      </Box>

      {/* Image References */}
      {isImageConfig(config) &&
        config.reference_images &&
        config.reference_images.length > 0 && (
          <Box>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Reference Images
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              sx={{ overflowX: 'auto', pb: 1 }}
            >
              {config.reference_images.map((img) => (
                <AssetPreview key={img.id} asset={img} onClick={onAssetClick} />
              ))}
            </Stack>
          </Box>
        )}

      {/* Video Frames */}
      {isVideoConfig(config) &&
        (config.first_frame_asset || config.last_frame_asset) && (
          <Box>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Key Frames
            </Typography>
            <Stack direction="row" spacing={2}>
              {config.first_frame_asset && (
                <AssetPreview
                  asset={config.first_frame_asset}
                  label="First Frame"
                  onClick={onAssetClick}
                />
              )}
              {config.last_frame_asset && (
                <AssetPreview
                  asset={config.last_frame_asset}
                  label="Last Frame"
                  onClick={onAssetClick}
                />
              )}
            </Stack>
          </Box>
        )}
    </Box>
  );
}
