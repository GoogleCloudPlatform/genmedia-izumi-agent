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

import { createTheme, alpha } from '@mui/material/styles';

// Color Palette suitable for creative tools (Dark Theme)
const palette = {
  mode: 'dark' as const,
  primary: {
    main: '#6366F1', // Indigo
    light: '#818CF8',
    dark: '#4F46E5',
    contrastText: '#FFFFFF',
  },
  secondary: {
    main: '#EC4899', // Pink/Magenta for accents
    light: '#F472B6',
    dark: '#DB2777',
    contrastText: '#FFFFFF',
  },
  background: {
    default: '#0F1117', // Very dark blue-grey, almost black
    paper: '#1E212B', // Slightly lighter
  },
  text: {
    primary: '#F3F4F6',
    secondary: '#9CA3AF',
  },
  action: {
    hover: alpha('#6366F1', 0.08),
    selected: alpha('#6366F1', 0.16),
  },
};

const theme = createTheme({
  palette,
  typography: {
    fontFamily: '"Outfit", sans-serif',
    h1: {
      fontWeight: 700,
    },
    h2: {
      fontWeight: 700,
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
    button: {
      textTransform: 'none', // More modern look
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 12, // More playful/modern than 4
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: '#374151 #0F1117',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            backgroundColor: '#0F1117',
            width: '8px',
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: 8,
            backgroundColor: '#374151',
            minHeight: 24,
            border: '2px solid #0F1117',
          },
          '&::-webkit-scrollbar-thumb:focus, & *::-webkit-scrollbar-thumb:focus':
            {
              backgroundColor: '#4B5563',
            },
          '&::-webkit-scrollbar-thumb:active, & *::-webkit-scrollbar-thumb:active':
            {
              backgroundColor: '#4B5563',
            },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover':
            {
              backgroundColor: '#4B5563',
            },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        containedPrimary: {
          background: `linear-gradient(45deg, ${palette.primary.main} 30%, ${palette.primary.light} 90%)`,
          '&:hover': {
            background: `linear-gradient(45deg, ${palette.primary.dark} 30%, ${palette.primary.main} 90%)`,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none', // Remove default gradient in dark mode
          backgroundColor: palette.background.paper,
          border: '1px solid rgba(255, 255, 255, 0.05)',
          boxShadow:
            '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: alpha(palette.background.default, 0.8),
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          boxShadow: 'none',
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: palette.background.default,
          borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.2)',
            },
          },
        },
      },
    },
  },
});

export default theme;
