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

import { useEffect, useRef } from 'react';
import { Box, IconButton, Button } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useNavigate, useLocation } from 'react-router-dom';
import type { ProjectAsset, Canvas } from '../../data/types';
import ChatInterface from './chat/ChatInterface';
import GenerateInterface from './generate/GenerateInterface';
import { useRouteParams } from '../../hooks/useRouteParams';

interface ChatPanelProps {
  isCollapsed: boolean;
  togglePanel: () => void;
  projectName: string;
  projectId: string;
  projectAssets: readonly ProjectAsset[];
  projectCanvases?: readonly Canvas[];
  onRefreshProject?: () => void;
}

export default function ChatPanel({
  isCollapsed,
  togglePanel,
  // projectName, // Unused now
  projectId,
  projectAssets,
  projectCanvases,
  onRefreshProject,
}: ChatPanelProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { modality } = useRouteParams<{ modality?: string }>(
    '/project/:projectId/generate/:modality',
  );

  const sidebarTab = location.pathname.includes('/generate')
    ? 'generate'
    : 'chat';
  const activeTab = sidebarTab === 'generate' ? 1 : 0;

  const lastChatPath = useRef<string>(`/project/${projectId}/chat`);

  useEffect(() => {
    if (sidebarTab === 'chat') {
      lastChatPath.current = location.pathname;
    }
  }, [sidebarTab, location.pathname]);

  const handleTabChange = (tab: 'chat' | 'generate') => {
    if (tab === 'chat') {
      navigate(lastChatPath.current);
    } else {
      navigate(`/project/${projectId}/generate`);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 1, // Add back some horizontal padding for content
          borderBottom: 1,
          borderColor: 'divider',
          gap: 1,
          minHeight: 49, // Ensure consistent height with TopAppBar and MainContent tabs (48px content + 1px border)
        }}
      >
        {isCollapsed ? (
          <IconButton onClick={togglePanel}>
            <ChevronRightIcon />
          </IconButton>
        ) : (
          <>
            <Button
              onClick={() => handleTabChange('chat')}
              color={sidebarTab === 'chat' ? 'primary' : 'inherit'}
              startIcon={<ChatBubbleOutlineIcon />}
              sx={{
                textTransform: 'none',
                minWidth: 0,
                px: 1,
                py: 0.5,
                fontSize: '0.8rem',
              }}
            >
              Chat
            </Button>
            <Button
              onClick={() => handleTabChange('generate')}
              color={sidebarTab === 'generate' ? 'primary' : 'inherit'}
              startIcon={<AutoAwesomeIcon />}
              sx={{
                textTransform: 'none',
                minWidth: 0,
                px: 1,
                py: 0.5,
                fontSize: '0.8rem',
              }}
            >
              Generate
            </Button>
            <Box sx={{ flexGrow: 1 }} />
            <IconButton onClick={togglePanel}>
              <ChevronLeftIcon />
            </IconButton>
          </>
        )}
      </Box>

      {!isCollapsed && (
        <>
          <Box
            sx={{
              display: activeTab === 0 ? 'flex' : 'none',
              flexGrow: 1,
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <ChatInterface
              key={location.pathname}
              projectId={projectId}
              projectAssets={projectAssets}
              projectCanvases={projectCanvases}
              onRefreshProject={onRefreshProject}
            />
          </Box>

          <Box
            sx={{
              display: activeTab === 1 ? 'flex' : 'none',
              flexGrow: 1,
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <GenerateInterface
              projectId={projectId}
              onRefreshProject={onRefreshProject}
              initialModality={modality}
            />
          </Box>
        </>
      )}
    </Box>
  );
}
