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
  Typography,
  Button,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  CardContent,
  CardActionArea,
  CircularProgress,
  Stack,
} from '@mui/material';
import AudiotrackIcon from '@mui/icons-material/Audiotrack';
import ImageIcon from '@mui/icons-material/Image';
import VideocamIcon from '@mui/icons-material/Videocam';
import DescriptionIcon from '@mui/icons-material/Description';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import type { ProjectAsset, Job } from '../../../data/types';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

type DisplayItem =
  | ProjectAsset
  | (Job & { isPendingJob: true; createdAt: string; fileName: string });

interface AssetsViewProps {
  items: readonly DisplayItem[];
  viewMode: 'list' | 'grid';
  onAssetClick: (item: DisplayItem) => void;
  onGenerateClick: () => void;
}

function isProjectAsset(item: DisplayItem): item is ProjectAsset {
  return 'type' in item;
}

function isPendingJob(
  item: DisplayItem,
): item is Job & { isPendingJob: true; createdAt: string; fileName: string } {
  return 'isPendingJob' in item && item.isPendingJob === true;
}

const getAssetDisplayName = (item: DisplayItem) => {
  if (isProjectAsset(item)) {
    if (item.fileName) return item.fileName;
    try {
      const urlObj = new URL(item.url);
      const parts = urlObj.pathname.split('/');
      return parts[parts.length - 1];
    } catch {
      const parts = item.url.split('/');
      return parts[parts.length - 1].split('?')[0];
    }
  } else {
    // It's a pending Job
    return item.fileName; // Use the fileName provided by MainContent
  }
};

const getItemIcon = (item: DisplayItem) => {
  if (isProjectAsset(item)) {
    if (item.type === 'image')
      return <ImageIcon fontSize="small" color="action" />;
    if (item.type === 'video')
      return <VideocamIcon fontSize="small" color="action" />;
    if (item.type === 'audio')
      return <AudiotrackIcon fontSize="small" color="action" />;
    if (item.type === 'text')
      return <DescriptionIcon fontSize="small" color="action" />;
    if (item.type === 'binary')
      return <InsertDriveFileIcon fontSize="small" color="action" />;
  } else {
    // It's a pending Job
    const type = item.job_type?.toLowerCase() || '';
    if (type.includes('image')) return <ImageIcon color="disabled" />;
    if (type.includes('video')) return <VideocamIcon color="disabled" />;
    if (
      type.includes('music') ||
      type.includes('audio') ||
      type.includes('speech')
    )
      return <AudiotrackIcon color="disabled" />;
    return <AutoAwesomeIcon color="disabled" />;
  }
  return null;
};

export default function AssetsView({
  items,
  viewMode,
  onAssetClick,
  onGenerateClick,
}: AssetsViewProps) {
  const hasContent = items.length > 0;

  if (!hasContent) {
    return (
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Your generated assets will appear here.
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
          Generate some now.
        </Typography>
        <Button variant="contained" onClick={onGenerateClick}>
          Generate Assets
        </Button>
      </Box>
    );
  }

  if (viewMode === 'list') {
    return (
      <TableContainer
        component={Paper}
        sx={{ maxHeight: 'calc(100vh - 200px)', overflow: 'auto' }}
      >
        <Table stickyHeader aria-label="assets table">
          <TableHead>
            <TableRow>
              <TableCell width={80}>Preview</TableCell>
              <TableCell>Name</TableCell>
              <TableCell width={80}>Type</TableCell>
              <TableCell width={190}>Modified At</TableCell>
              <TableCell width={100} align="right">
                Action
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={item.id}
                hover={!isPendingJob(item)}
                onClick={() => isProjectAsset(item) && onAssetClick(item)}
                sx={{ cursor: isPendingJob(item) ? 'default' : 'pointer' }}
              >
                <TableCell>
                  <Box
                    sx={{
                      width: 60,
                      height: 60,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: isPendingJob(item)
                        ? 'action.hover'
                        : 'background.default',
                      borderRadius: 1,
                      overflow: 'hidden',
                    }}
                  >
                    {isPendingJob(item) ? (
                      <CircularProgress size={24} />
                    ) : isProjectAsset(item) && item.type === 'video' ? (
                      item.thumbnailUrl ? (
                        <img
                          src={item.thumbnailUrl}
                          alt="thumb"
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'contain',
                          }}
                        />
                      ) : (
                        <VideocamIcon color="action" />
                      )
                    ) : isProjectAsset(item) && item.type === 'audio' ? (
                      <AudiotrackIcon color="action" />
                    ) : isProjectAsset(item) && item.type === 'text' ? (
                      <DescriptionIcon color="action" />
                    ) : isProjectAsset(item) && item.type === 'binary' ? (
                      <InsertDriveFileIcon color="action" />
                    ) : (
                      isProjectAsset(item) && (
                        <img
                          src={item.url}
                          alt="thumb"
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'contain',
                          }}
                        />
                      )
                    )}
                  </Box>
                </TableCell>
                <TableCell component="th" scope="row">
                  <Typography
                    variant="body2"
                    color={
                      isPendingJob(item) ? 'text.secondary' : 'text.primary'
                    }
                  >
                    {getAssetDisplayName(item)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {getItemIcon(item)}
                    <Typography
                      variant="caption"
                      sx={{ textTransform: 'capitalize' }}
                      color={
                        isPendingJob(item) ? 'text.secondary' : 'text.primary'
                      }
                    >
                      {isPendingJob(item) ? 'Pending' : item.type}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Typography
                    variant="body2"
                    color={
                      isPendingJob(item) ? 'text.secondary' : 'text.primary'
                    }
                  >
                    {item.createdAt
                      ? new Date(item.createdAt).toLocaleString(undefined, {
                          year: 'numeric',
                          month: 'numeric',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {isPendingJob(item) ? (
                    <Button size="small" disabled>
                      Processing
                    </Button>
                  ) : (
                    <Button size="small">View</Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 3,
      }}
    >
      {items.map((item) => (
        <Card
          key={item.id}
          sx={{
            cursor: isPendingJob(item) ? 'default' : 'pointer',
            opacity: isPendingJob(item) ? 0.7 : 1,
          }}
          onClick={() => isProjectAsset(item) && onAssetClick(item)}
        >
          <CardActionArea disabled={isPendingJob(item)}>
            <Box
              sx={{
                height: 160,
                bgcolor: isPendingJob(item)
                  ? 'action.hover'
                  : 'background.default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                position: 'relative',
                flexDirection: isPendingJob(item) ? 'column' : 'row',
                gap: isPendingJob(item) ? 2 : 0,
              }}
            >
              {isPendingJob(item) ? (
                <CircularProgress />
              ) : isProjectAsset(item) && item.type === 'video' ? (
                item.thumbnailUrl ? (
                  <>
                    <img
                      src={item.thumbnailUrl}
                      alt="thumb"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain',
                      }}
                    />
                    <VideocamIcon
                      sx={{
                        position: 'absolute',
                        color: 'white',
                        fontSize: 40,
                        opacity: 0.8,
                      }}
                    />
                  </>
                ) : (
                  <VideocamIcon color="action" sx={{ fontSize: 40 }} />
                )
              ) : isProjectAsset(item) && item.type === 'audio' ? (
                <AudiotrackIcon color="action" sx={{ fontSize: 40 }} />
              ) : isProjectAsset(item) && item.type === 'text' ? (
                <DescriptionIcon color="action" sx={{ fontSize: 40 }} />
              ) : isProjectAsset(item) && item.type === 'binary' ? (
                <InsertDriveFileIcon color="action" sx={{ fontSize: 40 }} />
              ) : (
                isProjectAsset(item) && (
                  <img
                    src={item.url}
                    alt="thumb"
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain',
                    }}
                  />
                )
              )}
            </Box>
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography
                variant="body2"
                noWrap
                title={getAssetDisplayName(item)}
                color={isPendingJob(item) ? 'text.secondary' : 'text.primary'}
              >
                {getAssetDisplayName(item)}
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ textTransform: 'capitalize' }}
              >
                {isPendingJob(item)
                  ? 'Generating...'
                  : isProjectAsset(item)
                    ? item.type
                    : ''}
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
    </Box>
  );
}
