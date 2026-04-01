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
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  ToggleButtonGroup,
  ToggleButton,
  Button,
  IconButton,
  Stack,
  CircularProgress,
  Alert,
  Snackbar,
  FormControlLabel,
  Switch,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ImageIcon from '@mui/icons-material/Image';
import VideocamIcon from '@mui/icons-material/Videocam';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import CloseIcon from '@mui/icons-material/Close';

import {
  LyriaModel,
  ImagenModel,
  ImagenAspectRatio,
  GeminiImageAspectRatio,
  GeminiImageModel,
  VeoModel,
  VeoAspectRatio,
  VeoDuration,
  VeoResolution,
  SpeechModel,
  SpeechVoice,
} from '../../../data/types';
import mediaService from '../../../services/mediaService';
import projectService from '../../../services/projectService';
import ImageUpload from '../../shared/ImageUpload';
import { useNavigate } from 'react-router-dom';

interface GenerateInterfaceProps {
  projectId: string;
  onRefreshProject?: () => void;
  initialModality?: string;
}

// Define state shapes for each modality
interface ImageState {
  prompt: string;
  imageModelProvider: 'imagen' | 'gemini';
  imagenModel: ImagenModel;
  geminiModel: GeminiImageModel;
  imagenAspectRatio: ImagenAspectRatio;
  geminiAspectRatio: GeminiImageAspectRatio;
  referenceImages: File[];
  fileName: string;
}

interface VideoState {
  prompt: string;
  veoModel: VeoModel;
  veoAspectRatio: VeoAspectRatio;
  veoDuration: VeoDuration;
  veoResolution: VeoResolution;
  firstFrame: File | null;
  lastFrame: File | null;
  generateAudio: boolean;
  fileName: string;
}

interface MusicState {
  prompt: string;
  lyriaModel: LyriaModel;
  negativePrompt: string;
  fileName: string;
}

interface SpeechState {
  prompt: string;
  speechModel: SpeechModel;
  speechVoice: SpeechVoice;
  speechText: string;
  fileName: string;
}

// This hook manages the lifecycle of an Object URL for a File object.
// The `react-hooks/set-state-in-effect` rule is disabled here because
// `URL.createObjectURL` is a side effect that must be managed within `useEffect`,
// and updating the state (url and urlFile) from within this effect is
// a necessary part of its intended functionality (creating a reactive URL).
// The dependency array `[file]` ensures the effect only re-runs when the input file changes,
// preventing infinite loops.
const useObjectUrl = (file: File | null) => {
  const [url, setUrl] = useState<string | undefined>(undefined);
  const [urlFile, setUrlFile] = useState<File | null>(null);

  useEffect(() => {
    if (!file) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setUrl(undefined);

      setUrlFile(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);

    setUrl(objectUrl);

    setUrlFile(file);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [file]);

  // If the input file is different from the file that generated the url, return undefined.
  // This prevents returning a stale (and potentially soon-to-be-revoked) URL during render
  // if the `file` prop changes before the `useEffect` has a chance to update the state.
  if (file !== urlFile) {
    return undefined;
  }

  return url;
};

// Memoized component for rendering reference image previews to avoid re-creating Object URLs
const ReferenceImagePreview = ({
  file,
  onRemove,
}: {
  file: File;
  onRemove: () => void;
}) => {
  const imageUrl = useObjectUrl(file);

  if (!imageUrl) return null;

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      <img
        src={imageUrl}
        alt={file.name}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          borderRadius: 4,
        }}
      />
      <IconButton
        size="small"
        onClick={onRemove}
        aria-label="Remove image"
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
    </Box>
  );
};

export default function GenerateInterface({
  projectId,
  onRefreshProject,
  initialModality,
}: GenerateInterfaceProps) {
  const navigate = useNavigate();
  const [outputModality, setOutputModality] = useState(
    initialModality || 'image',
  );

  // Generation State
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationSuccess, setGenerationSuccess] = useState<string | null>(
    null,
  );

  // Centralized state for all modalities
  const [modalityStates, setModalityStates] = useState({
    image: {
      prompt: '',
      imageModelProvider: 'gemini',
      imagenModel: ImagenModel.IMAGEN_4_0_GENERATE_001,
      geminiModel: GeminiImageModel.GEMINI_2_5_FLASH_IMAGE,
      imagenAspectRatio: ImagenAspectRatio.RATIO_16_9,
      geminiAspectRatio: GeminiImageAspectRatio.RATIO_16_9,
      referenceImages: [],
      fileName: '',
    } as ImageState,
    video: {
      prompt: '',
      veoModel: VeoModel.VEO_3_1_GENERATE,
      veoAspectRatio: VeoAspectRatio.RATIO_16_9,
      veoDuration: VeoDuration.SECONDS_6,
      veoResolution: VeoResolution.RESOLUTION_720P,
      firstFrame: null,
      lastFrame: null,
      generateAudio: false,
      fileName: '',
    } as VideoState,
    music: {
      prompt: '',
      lyriaModel: LyriaModel.LYRIA_002,
      negativePrompt: '',
      fileName: '',
    } as MusicState,
    speech: {
      prompt: '',
      speechModel: SpeechModel.GEMINI_2_5_FLASH_TTS,
      speechVoice: SpeechVoice.CHARON,
      speechText: '',
      fileName: '',
    } as SpeechState,
  });

  const updateState = <T extends keyof typeof modalityStates>(
    modality: T,
    newState: Partial<(typeof modalityStates)[T]>,
  ) => {
    setModalityStates((prevState) => ({
      ...prevState,
      [modality]: {
        ...prevState[modality],
        ...newState,
      },
    }));
  };

  const activeState =
    modalityStates[outputModality as keyof typeof modalityStates];

  // Memoize object URLs for video frames to prevent re-creation on every render
  const firstFrameUrl = useObjectUrl(modalityStates.video.firstFrame);
  const lastFrameUrl = useObjectUrl(modalityStates.video.lastFrame);

  const handleModalityChange = (
    _: React.MouseEvent<HTMLElement>,
    newModality: string,
  ) => {
    if (newModality !== null && newModality !== outputModality) {
      setOutputModality(newModality);
      navigate(`/project/${projectId}/generate/${newModality}`);
    }
  };

  const handleReferenceImageUpload = (file: File) => {
    if (modalityStates.image.referenceImages.length < 4) {
      updateState('image', {
        referenceImages: [...modalityStates.image.referenceImages, file],
      });
    }
  };

  const handleRemoveReferenceImage = (index: number) => {
    const newImages = [...modalityStates.image.referenceImages];
    newImages.splice(index, 1);
    updateState('image', { referenceImages: newImages });
  };

  const uploadFileAndGetName = async (file: File): Promise<string> => {
    const asset = await projectService.uploadAsset(projectId, file);
    return asset?.fileName || asset?.url?.split('/').pop() || 'unknown';
  };

  const isGenerateDisabled = () => {
    if (isGenerating) return true;
    // For speech modality, ensure speechText is not empty, as it's the primary input.
    if (outputModality === 'speech') {
      return !modalityStates.speech.speechText.trim();
    }
    // For all other modalities, ensure the prompt is not empty.
    return !activeState.prompt.trim();
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    setGenerationSuccess(null);

    const generationHandlers: Record<string, () => Promise<string>> = {
      image: async () => {
        const state = modalityStates.image;
        const finalFileName =
          state.fileName || `generated_image_${Date.now()}.png`;
        if (state.imageModelProvider === 'imagen') {
          await mediaService.generateImageWithImagen(projectId, {
            prompt: state.prompt,
            aspect_ratio: state.imagenAspectRatio,
            model: state.imagenModel,
            file_name: finalFileName,
          });
        } else {
          const refNames = await Promise.all(
            state.referenceImages.map(uploadFileAndGetName),
          );
          await mediaService.generateImageWithGemini(projectId, {
            prompt: state.prompt,
            aspect_ratio: state.geminiAspectRatio,
            model: state.geminiModel,
            file_name: finalFileName,
            reference_image_filenames: refNames,
          });
        }
        return finalFileName;
      },
      video: async () => {
        const state = modalityStates.video;
        const finalFileName =
          state.fileName || `generated_video_${Date.now()}.mp4`;
        const firstFrameName = state.firstFrame
          ? await uploadFileAndGetName(state.firstFrame)
          : null;
        const lastFrameName = state.lastFrame
          ? await uploadFileAndGetName(state.lastFrame)
          : null;
        await mediaService.generateVideo(projectId, {
          prompt: state.prompt,
          file_name: finalFileName,
          model: state.veoModel,
          aspect_ratio: state.veoAspectRatio,
          duration_seconds: state.veoDuration,
          resolution: state.veoResolution,
          first_frame_filename: firstFrameName,
          last_frame_filename: lastFrameName,
          generate_audio: state.generateAudio,
        });
        return finalFileName;
      },
      music: async () => {
        const state = modalityStates.music;
        const finalFileName =
          state.fileName || `generated_music_${Date.now()}.mp3`;
        await mediaService.generateMusic(projectId, {
          prompt: state.prompt,
          file_name: finalFileName,
          model: state.lyriaModel,
          negative_prompt: state.negativePrompt,
        });
        return finalFileName;
      },
      speech: async () => {
        const state = modalityStates.speech;
        const finalFileName =
          state.fileName || `generated_speech_${Date.now()}.mp3`;
        await mediaService.generateSpeech(projectId, {
          prompt: state.prompt,
          text: state.speechText,
          file_name: finalFileName,
          model: state.speechModel,
          voice_name: state.speechVoice,
        });
        return finalFileName;
      },
    };

    try {
      const handler = generationHandlers[outputModality];
      if (handler) {
        const generatedFileName = await handler();
        if (onRefreshProject) onRefreshProject();
        setGenerationSuccess(
          `Successfully started generation for ${generatedFileName}`,
        );
      } else {
        throw new Error(`Unsupported modality: ${outputModality}`);
      }
    } catch (e: unknown) {
      console.error('Generation failed:', e);
      const errorMessage = e instanceof Error ? e.message : 'Generation failed';
      setGenerationError(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  const renderGenerateOptions = () => {
    return (
      <Stack spacing={3}>
        {outputModality === 'image' && (
          <>
            <FormControl fullWidth>
              <InputLabel>Model Provider</InputLabel>
              <Select
                value={modalityStates.image.imageModelProvider}
                label="Model Provider"
                onChange={(e) =>
                  updateState('image', {
                    imageModelProvider: e.target.value as 'imagen' | 'gemini',
                  })
                }
              >
                <MenuItem value="imagen">Imagen</MenuItem>
                <MenuItem value="gemini">Gemini</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={
                  modalityStates.image.imageModelProvider === 'imagen'
                    ? modalityStates.image.imagenModel
                    : modalityStates.image.geminiModel
                }
                label="Model"
                onChange={(e) => {
                  if (modalityStates.image.imageModelProvider === 'imagen') {
                    updateState('image', {
                      imagenModel: e.target.value as ImagenModel,
                    });
                  } else {
                    updateState('image', {
                      geminiModel: e.target.value as GeminiImageModel,
                    });
                  }
                }}
              >
                {modalityStates.image.imageModelProvider === 'imagen'
                  ? Object.values(ImagenModel).map((m) => (
                      <MenuItem key={m} value={m}>
                        {m}
                      </MenuItem>
                    ))
                  : Object.values(GeminiImageModel).map((m) => (
                      <MenuItem key={m} value={m}>
                        {m}
                      </MenuItem>
                    ))}
              </Select>
            </FormControl>

            <TextField
              label="Prompt"
              multiline
              rows={4}
              fullWidth
              value={modalityStates.image.prompt}
              onChange={(e) => updateState('image', { prompt: e.target.value })}
            />

            {modalityStates.image.imageModelProvider === 'gemini' && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Reference Images (up to 4)
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  {modalityStates.image.referenceImages.length < 4 && (
                    <Box sx={{ width: 100, height: 100 }}>
                      <ImageUpload
                        key={modalityStates.image.referenceImages.length}
                        onUpload={handleReferenceImageUpload}
                        objectFit="contain"
                        paperSx={{
                          bgcolor: 'transparent',
                          border: '1px dashed',
                          borderColor: 'divider',
                        }}
                      />
                    </Box>
                  )}
                  {modalityStates.image.referenceImages.map((image, i) => (
                    <Box
                      sx={{ width: 100, height: 100, position: 'relative' }}
                      key={i}
                    >
                      <ReferenceImagePreview
                        file={image}
                        onRemove={() => handleRemoveReferenceImage(i)}
                      />
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

            <FormControl fullWidth>
              <InputLabel>Aspect Ratio</InputLabel>
              <Select
                value={
                  modalityStates.image.imageModelProvider === 'imagen'
                    ? modalityStates.image.imagenAspectRatio
                    : modalityStates.image.geminiAspectRatio
                }
                label="Aspect Ratio"
                onChange={(e) => {
                  if (modalityStates.image.imageModelProvider === 'imagen') {
                    updateState('image', {
                      imagenAspectRatio: e.target.value as ImagenAspectRatio,
                    });
                  } else {
                    updateState('image', {
                      geminiAspectRatio: e.target
                        .value as GeminiImageAspectRatio,
                    });
                  }
                }}
              >
                {modalityStates.image.imageModelProvider === 'imagen'
                  ? Object.values(ImagenAspectRatio).map((r) => (
                      <MenuItem key={r} value={r}>
                        {r}
                      </MenuItem>
                    ))
                  : Object.values(GeminiImageAspectRatio).map((r) => (
                      <MenuItem key={r} value={r}>
                        {r}
                      </MenuItem>
                    ))}
              </Select>
            </FormControl>
          </>
        )}

        {outputModality === 'video' && (
          <>
            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={modalityStates.video.veoModel}
                label="Model"
                onChange={(e) =>
                  updateState('video', { veoModel: e.target.value as VeoModel })
                }
              >
                {Object.values(VeoModel).map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Prompt"
              multiline
              rows={4}
              fullWidth
              value={modalityStates.video.prompt}
              onChange={(e) => updateState('video', { prompt: e.target.value })}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  First Frame (Optional)
                </Typography>
                <Box>
                  <ImageUpload
                    onUpload={(file) =>
                      updateState('video', { firstFrame: file })
                    }
                    initialImage={firstFrameUrl}
                    onRemove={() => updateState('video', { firstFrame: null })}
                    objectFit="contain"
                    sx={{ paddingTop: '56.25%' }}
                    paperSx={{
                      bgcolor: modalityStates.video.firstFrame
                        ? 'black'
                        : 'transparent',
                      border: modalityStates.video.firstFrame
                        ? 'none'
                        : '1px dashed',
                      borderColor: 'divider',
                    }}
                  />
                </Box>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Last Frame (Optional)
                </Typography>
                <Box>
                  <ImageUpload
                    onUpload={(file) =>
                      updateState('video', { lastFrame: file })
                    }
                    initialImage={lastFrameUrl}
                    onRemove={() => updateState('video', { lastFrame: null })}
                    objectFit="contain"
                    sx={{ paddingTop: '56.25%' }}
                    paperSx={{
                      bgcolor: modalityStates.video.lastFrame
                        ? 'black'
                        : 'transparent',
                      border: modalityStates.video.lastFrame
                        ? 'none'
                        : '1px dashed',
                      borderColor: 'divider',
                    }}
                  />
                </Box>
              </Box>
            </Box>

            <Stack direction="row" spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Aspect Ratio</InputLabel>
                <Select
                  value={modalityStates.video.veoAspectRatio}
                  label="Aspect Ratio"
                  onChange={(e) =>
                    updateState('video', {
                      veoAspectRatio: e.target.value as VeoAspectRatio,
                    })
                  }
                >
                  {Object.values(VeoAspectRatio).map((r) => (
                    <MenuItem key={r} value={r}>
                      {r}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Resolution</InputLabel>
                <Select
                  value={modalityStates.video.veoResolution}
                  label="Resolution"
                  onChange={(e) =>
                    updateState('video', {
                      veoResolution: e.target.value as VeoResolution,
                    })
                  }
                >
                  {Object.values(VeoResolution).map((r) => (
                    <MenuItem key={r} value={r}>
                      {r}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Duration</InputLabel>
                <Select
                  value={modalityStates.video.veoDuration}
                  label="Duration"
                  onChange={(e) =>
                    updateState('video', {
                      veoDuration: e.target.value as unknown as VeoDuration,
                    })
                  }
                >
                  {Object.values(VeoDuration)
                    .filter((x) => typeof x === 'number')
                    .map((r) => (
                      <MenuItem key={r} value={r}>
                        {r}s
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            </Stack>

            <FormControlLabel
              control={
                <Switch
                  checked={modalityStates.video.generateAudio}
                  onChange={(e) =>
                    updateState('video', { generateAudio: e.target.checked })
                  }
                />
              }
              label="Generate Audio"
            />
          </>
        )}

        {outputModality === 'music' && (
          <>
            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={modalityStates.music.lyriaModel}
                label="Model"
                onChange={(e) =>
                  updateState('music', {
                    lyriaModel: e.target.value as LyriaModel,
                  })
                }
              >
                {Object.values(LyriaModel).map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Prompt"
              multiline
              rows={3}
              fullWidth
              value={modalityStates.music.prompt}
              onChange={(e) => updateState('music', { prompt: e.target.value })}
            />
            <TextField
              label="Negative Prompt"
              multiline
              rows={2}
              fullWidth
              value={modalityStates.music.negativePrompt}
              onChange={(e) =>
                updateState('music', { negativePrompt: e.target.value })
              }
            />
          </>
        )}

        {outputModality === 'speech' && (
          <>
            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={modalityStates.speech.speechModel}
                label="Model"
                onChange={(e) =>
                  updateState('speech', {
                    speechModel: e.target.value as SpeechModel,
                  })
                }
              >
                {Object.values(SpeechModel).map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Text to Speak"
              multiline
              rows={4}
              fullWidth
              value={modalityStates.speech.speechText}
              onChange={(e) =>
                updateState('speech', { speechText: e.target.value })
              }
            />
            <TextField
              label="Prompt (Optional instructions)"
              multiline
              rows={2}
              fullWidth
              value={modalityStates.speech.prompt}
              onChange={(e) =>
                updateState('speech', { prompt: e.target.value })
              }
              helperText="E.g. 'Speak excitedly' or 'Whisper'"
            />

            <FormControl fullWidth>
              <InputLabel>Voice</InputLabel>
              <Select
                value={modalityStates.speech.speechVoice}
                label="Voice"
                onChange={(e) =>
                  updateState('speech', {
                    speechVoice: e.target.value as SpeechVoice,
                  })
                }
              >
                {Object.values(SpeechVoice).map((v) => (
                  <MenuItem key={v} value={v}>
                    {v}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </>
        )}
        <TextField
          label="File Name (Optional)"
          value={activeState.fileName}
          onChange={(e) =>
            updateState(outputModality as keyof typeof modalityStates, {
              fileName: e.target.value,
            })
          }
          fullWidth
          size="small"
          sx={{ mt: 3 }}
        />
      </Stack>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        height: '100%',
        position: 'relative',
      }}
    >
      <Box sx={{ flexGrow: 1, p: 3, pb: 10, overflowY: 'auto' }}>
        <ToggleButtonGroup
          value={outputModality}
          exclusive
          onChange={handleModalityChange}
          aria-label="output modality"
          fullWidth
          sx={{ mb: 2 }}
        >
          <ToggleButton value="image">
            <ImageIcon sx={{ mr: 1 }} /> Image
          </ToggleButton>
          <ToggleButton value="video">
            <VideocamIcon sx={{ mr: 1 }} /> Video
          </ToggleButton>
          <ToggleButton value="music">
            <MusicNoteIcon sx={{ mr: 1 }} /> Music
          </ToggleButton>
          <ToggleButton value="speech">
            <RecordVoiceOverIcon sx={{ mr: 1 }} /> Speech
          </ToggleButton>
        </ToggleButtonGroup>

        {renderGenerateOptions()}
      </Box>

      <Box
        sx={{
          p: 3,
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          position: 'sticky',
          bottom: 0,
          zIndex: 10,
          mt: 'auto',
        }}
      >
        <Button
          variant="contained"
          fullWidth
          sx={{ mt: 0 }}
          onClick={handleGenerate}
          disabled={isGenerateDisabled()}
          startIcon={
            isGenerating ? <CircularProgress size={20} /> : <AutoAwesomeIcon />
          }
        >
          {isGenerating ? 'Generating...' : 'Generate'}
        </Button>

        <Snackbar
          open={!!generationSuccess}
          autoHideDuration={6000}
          onClose={() => setGenerationSuccess(null)}
          message={generationSuccess}
        />

        {generationError && (
          <Alert
            severity="error"
            sx={{ mt: 2 }}
            onClose={() => setGenerationError(null)}
          >
            {generationError}
          </Alert>
        )}
      </Box>
    </Box>
  );
}
