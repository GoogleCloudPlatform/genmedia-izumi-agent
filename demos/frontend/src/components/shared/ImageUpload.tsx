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
import { Box, Typography, Paper, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import type { SxProps, Theme } from '@mui/material';

interface ImageUploadProps {
  onUpload: (file: File) => void;
  initialImage?: string; // New prop for initial image URL
  onRemove?: () => void; // New prop for removing the image
  objectFit?: 'cover' | 'contain';
  sx?: SxProps<Theme>;
  paperSx?: SxProps<Theme>;
}

export default function ImageUpload({
  onUpload,
  initialImage,
  onRemove,
  objectFit = 'cover',
  sx,
  paperSx,
}: ImageUploadProps) {
  const [image, setImage] = useState<string | null>(initialImage || null);
  const [file, setFile] = useState<File | null>(null);
  const [prevInitialImage, setPrevInitialImage] = useState(initialImage);

  // Sync derived state
  if (initialImage !== prevInitialImage) {
    setImage(initialImage || null);
    setPrevInitialImage(initialImage);
  }

  useEffect(() => {
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  }, [file]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      onUpload(selectedFile);
    }
  };

  return (
    <Box
      sx={{
        width: '100%',
        paddingTop: '100%',
        position: 'relative',
        ...sx,
      }}
    >
      <Paper
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: image && objectFit === 'contain' ? 'black' : 'grey.200',
          cursor: 'pointer',
          overflow: 'hidden',
          ...paperSx,
        }}
        component="label"
      >
        {image ? (
          <>
            <img
              src={image}
              alt="preview"
              style={{ width: '100%', height: '100%', objectFit }}
            />
            {onRemove && (
              <IconButton
                size="small"
                aria-label="Remove image"
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  onRemove();
                  setImage(null);
                  setFile(null);
                }}
                sx={{
                  position: 'absolute',
                  top: 4,
                  right: 4,
                  bgcolor: 'rgba(0, 0, 0, 0.6)',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'rgba(0, 0, 0, 0.8)',
                  },
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </>
        ) : (
          <Typography variant="h4" color="text.secondary">
            +
          </Typography>
        )}
        <input
          type="file"
          accept="image/*"
          hidden
          onChange={handleFileChange}
        />
      </Paper>
    </Box>
  );
}
