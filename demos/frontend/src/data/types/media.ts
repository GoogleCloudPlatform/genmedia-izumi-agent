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

// --- Media Generation Enums ---

export const LyriaModel = {
  LYRIA_002: 'lyria-002',
} as const;
export type LyriaModel = (typeof LyriaModel)[keyof typeof LyriaModel];

export const ImagenModel = {
  IMAGEN_4_0_FAST_GENERATE_001: 'imagen-4.0-fast-generate-001',
  IMAGEN_4_0_GENERATE_001: 'imagen-4.0-generate-001',
  IMAGEN_4_0_ULTRA_GENERATE_001: 'imagen-4.0-ultra-generate-001',
} as const;
export type ImagenModel = (typeof ImagenModel)[keyof typeof ImagenModel];

export const ImagenAspectRatio = {
  RATIO_1_1: '1:1',
  RATIO_3_4: '3:4',
  RATIO_4_3: '4:3',
  RATIO_16_9: '16:9',
  RATIO_9_16: '9:16',
} as const;
export type ImagenAspectRatio =
  (typeof ImagenAspectRatio)[keyof typeof ImagenAspectRatio];

export const GeminiImageAspectRatio = {
  RATIO_1_1: '1:1',
  RATIO_3_2: '3:2',
  RATIO_2_3: '2:3',
  RATIO_3_4: '3:4',
  RATIO_4_3: '4:3',
  RATIO_4_5: '4:5',
  RATIO_5_4: '5:4',
  RATIO_9_16: '9:16',
  RATIO_16_9: '16:9',
  RATIO_21_9: '21:9',
} as const;
export type GeminiImageAspectRatio =
  (typeof GeminiImageAspectRatio)[keyof typeof GeminiImageAspectRatio];

export const GeminiImageModel = {
  GEMINI_2_5_FLASH_IMAGE: 'gemini-2.5-flash-image',
  GEMINI_3_PRO_IMAGE: 'gemini-3-pro-image-preview',
} as const;
export type GeminiImageModel =
  (typeof GeminiImageModel)[keyof typeof GeminiImageModel];

export const VeoModel = {
  VEO_3_0_FAST_GENERATE: 'veo-3.0-fast-generate-001',
  VEO_3_0_GENERATE: 'veo-3.0-generate-001',
  VEO_3_1_GENERATE: 'veo-3.1-generate-001',
} as const;
export type VeoModel = (typeof VeoModel)[keyof typeof VeoModel];

export const VeoAspectRatio = {
  RATIO_16_9: '16:9',
  RATIO_9_16: '9:16',
} as const;
export type VeoAspectRatio =
  (typeof VeoAspectRatio)[keyof typeof VeoAspectRatio];

export const VeoDuration = {
  SECONDS_4: 4,
  SECONDS_6: 6,
  SECONDS_8: 8,
} as const;
export type VeoDuration = (typeof VeoDuration)[keyof typeof VeoDuration];

export const VeoResolution = {
  RESOLUTION_720P: '720p',
  RESOLUTION_1080P: '1080p',
} as const;
export type VeoResolution = (typeof VeoResolution)[keyof typeof VeoResolution];

export const SpeechModel = {
  GEMINI_2_5_FLASH_TTS: 'gemini-2.5-flash-tts',
  GEMINI_2_5_PRO_TTS: 'gemini-2.5-pro-tts',
} as const;
export type SpeechModel = (typeof SpeechModel)[keyof typeof SpeechModel];

export const SpeechVoice = {
  ACHERNAR: 'Achernar',
  ACHIRD: 'Achird',
  ALGENIB: 'Algenib',
  ALGIEBA: 'Algieba',
  ALNILAM: 'Alnilam',
  AOEDE: 'Aoede',
  AUTONOE: 'Autonoe',
  CALLIRRHOE: 'Callirrhoe',
  CHARON: 'Charon',
  DESPINA: 'Despina',
  ENCELADUS: 'Enceladus',
  ERINOME: 'Erinome',
  FENRIR: 'Fenrir',
  GACRUX: 'Gacrux',
  IAPETUS: 'Iapetus',
  KORE: 'Kore',
  LAOMEDEIA: 'Laomedeia',
  LEDA: 'Leda',
  ORUS: 'Orus',
  PULCHERRIMA: 'Pulcherrima',
  PUCK: 'Puck',
  RASALGETHI: 'Rasalgethi',
  SADACHBIA: 'Sadachbia',
  SADALTAGER: 'Sadaltager',
  SCHEDAR: 'Schedar',
  SULAFAT: 'Sulafat',
  UMBRIEL: 'Umbriel',
  VINDEMIATRIX: 'Vindemiatrix',
  ZEPHYR: 'Zephyr',
  ZUBENELGENUBI: 'Zubenelgenubi',
} as const;
export type SpeechVoice = (typeof SpeechVoice)[keyof typeof SpeechVoice];

// --- Request Interfaces ---

export interface GenerateMusicRequest {
  prompt: string;
  file_name: string;
  model: LyriaModel;
  negative_prompt?: string | null;
}

export interface GenerateImageWithImagenRequest {
  prompt: string;
  aspect_ratio: ImagenAspectRatio;
  model: ImagenModel;
  file_name: string;
}

export interface GenerateImageWithGeminiRequest {
  prompt: string;
  aspect_ratio: GeminiImageAspectRatio;
  model: GeminiImageModel;
  file_name: string;
  reference_image_filenames?: string[];
}

export interface GenerateSpeechSingleSpeakerRequest {
  prompt: string;
  text: string;
  model: SpeechModel;
  voice_name: SpeechVoice;
  file_name: string;
}

export interface GenerateVideoRequest {
  prompt: string;
  file_name: string;
  model: VeoModel;
  first_frame_filename?: string | null;
  last_frame_filename?: string | null;
  aspect_ratio: VeoAspectRatio;
  duration_seconds: VeoDuration;
  resolution?: VeoResolution | null;
  generate_audio?: boolean;
}
