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

import { useState, useCallback } from 'react';
import { Box, Drawer, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ChatPanel from './ChatPanel';
import MainContent from './MainContent';
import TopAppBar from '../shared/TopAppBar';
import ShareModal from '../shared/ShareModal';

import type { Project, Job } from '../../data/types';

export default function ProjectViewLayout({
  project,
  pendingJobs,
  contentTab,
  assetId,
  canvasId,
  onRefreshProject,
}: {
  project: Project;
  pendingJobs?: readonly Job[];
  contentTab?: string;
  assetId?: string;
  canvasId?: string;
  onRefreshProject?: () => void;
}) {
  const navigate = useNavigate();
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);
  // chatPanelActiveTab state removed in favor of URL-driven sidebarTab
  const [drawerWidth, setDrawerWidth] = useState(595);
  const [isResizing, setIsResizing] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);

  const minDrawerWidth = 240;
  const maxDrawerWidth = 1000;

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    document.addEventListener('mouseup', handleMouseUp, true);
    document.addEventListener('mousemove', handleMouseMove, true);
  };

  const handleMouseUp = () => {
    setIsResizing(false);
    document.removeEventListener('mouseup', handleMouseUp, true);
    document.removeEventListener('mousemove', handleMouseMove, true);
  };

  // react-hooks/preserve-manual-memoization: This warning indicates that the React Compiler
  // could not preserve existing manual memoization for this useCallback hook.
  // This is a compiler-specific optimization issue and does not prevent the application
  // from functioning correctly. It is being ignored as per current project guidelines.
  /* eslint-disable react-hooks/preserve-manual-memoization */
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      const newWidth = e.clientX;
      if (newWidth >= minDrawerWidth && newWidth <= maxDrawerWidth) {
        setDrawerWidth(newWidth);
      }
    },
    [minDrawerWidth, maxDrawerWidth, setDrawerWidth],
  );
  /* eslint-enable react-hooks/preserve-manual-memoization */

  const handleGenerateClick = () => {
    navigate(`/project/${project.id}/generate`);
    if (isPanelCollapsed) {
      setIsPanelCollapsed(false); // Ensure panel is open
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <TopAppBar projectName={project.name} />
      <Box sx={{ position: 'absolute', top: '8px', right: '80px' }}>
        <Button variant="contained" onClick={() => setIsShareModalOpen(true)}>
          Share
        </Button>
      </Box>
      <ShareModal
        open={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        project={project}
      />
      <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        <Drawer
          variant="permanent"
          sx={{
            width: isPanelCollapsed ? 64 : drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              position: 'relative',
              width: isPanelCollapsed ? 64 : drawerWidth,
              boxSizing: 'border-box',
              transition: isResizing
                ? 'none'
                : (theme) =>
                    theme.transitions.create('width', {
                      easing: theme.transitions.easing.sharp,
                      duration: theme.transitions.duration.enteringScreen,
                    }),
              overflow: 'hidden',
            },
          }}
        >
          <ChatPanel
            isCollapsed={isPanelCollapsed}
            togglePanel={() => setIsPanelCollapsed(!isPanelCollapsed)}
            projectName={project.name}
            projectId={project.id}
            projectAssets={project.assets}
            projectCanvases={project.canvases || []}
            onRefreshProject={onRefreshProject}
          />
        </Drawer>
        {!isPanelCollapsed && (
          <Box
            onMouseDown={handleMouseDown}
            sx={{
              width: '4px',
              cursor: 'ew-resize',
              backgroundColor: 'divider',
              height: '100%',
              position: 'relative',
              left: '-2px',
              zIndex: 1300,
              '&:hover': {
                backgroundColor: 'text.secondary',
              },
            }}
          />
        )}
        <Box component="main" sx={{ flexGrow: 1, overflow: 'auto' }}>
          <MainContent
            onGenerateClick={handleGenerateClick}
            assets={project.assets}
            canvases={project.canvases || []}
            pendingJobs={pendingJobs}
            contentTab={contentTab}
            assetId={assetId}
            canvasId={canvasId}
          />
        </Box>
      </Box>
    </Box>
  );
}
