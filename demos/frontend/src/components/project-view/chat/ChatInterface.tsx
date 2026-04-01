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

import { useState, useEffect, useCallback } from 'react';
import { Box, CircularProgress } from '@mui/material';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import type { ChatSession, ProjectAsset, Canvas } from '../../../data/types';
import chatService from '../../../services/chatService';
import projectService from '../../../services/projectService';
import ChatSessionList from './ChatSessionList';
import ActiveConversation from './ActiveConversation';
import { useRouteParams } from '../../../hooks/useRouteParams';

interface ChatInterfaceProps {
  projectId: string;
  projectAssets: readonly ProjectAsset[];
  projectCanvases?: readonly Canvas[];
  onRefreshProject?: () => void;
}

export default function ChatInterface({
  projectId,
  projectAssets,
  projectCanvases,
  onRefreshProject,
}: ChatInterfaceProps) {
  const { chatSessionId } = useRouteParams<{ chatSessionId?: string }>(
    '/project/:projectId/chat/:chatSessionId',
  );
  const navigate = useNavigate();
  const location = useLocation();

  const [searchParams, setSearchParams] = useSearchParams();
  const [allChatSessions, setAllChatSessions] = useState<ChatSession[]>([]);
  const [availableApps, setAvailableApps] = useState<string[]>([]);
  const [isSelectingAgent, setIsSelectingAgent] = useState(false);
  const [currentAppName, setCurrentAppName] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Handle action=new query param
  useEffect(() => {
    if (searchParams.get('action') === 'new') {
      setIsSelectingAgent(true);
      // Remove the query param to avoid re-triggering
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        newParams.delete('action');
        return newParams;
      });
    }
  }, [searchParams, setSearchParams]);

  // Fetch all apps and then all sessions for the projectId
  const fetchAllSessions = useCallback(async () => {
    try {
      // We can still list apps to populate availableApps for the "New Chat" selection
      const appNames = await projectService.getAvailableApps(projectId);
      setAvailableApps(appNames);

      // Use projectService to fetch (and cache) all chat sessions
      const sessions = await projectService.getAllChatSessions(projectId);
      setAllChatSessions(sessions);
    } catch (error) {
      console.error('Failed to fetch all chat sessions:', error);
      setAllChatSessions([]);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [projectId]);

  useEffect(() => {
    setIsLoadingSessions(true);
    fetchAllSessions();
  }, [fetchAllSessions]);

  useEffect(() => {
    if (chatSessionId && allChatSessions.length > 0) {
      const session = allChatSessions.find((s) => s.id === chatSessionId);
      if (session) {
        setCurrentAppName(session.appName || null);
        setIsSelectingAgent(false);
      }
    } else if (!chatSessionId) {
      setCurrentAppName(null);
    }
  }, [chatSessionId, allChatSessions]);

  const handleResumeChatSession = (session: ChatSession) => {
    setIsSelectingAgent(false);
    navigate(`/project/${projectId}/chat/${session.id}`);
  };

  const handleStartNewChatClick = () => {
    setIsSelectingAgent(true);
    if (chatSessionId) {
      navigate(`/project/${projectId}/chat?action=new`);
    }
  };

  const handleCancelSelection = () => {
    setIsSelectingAgent(false);
  };

  const handleAgentSelect = async (appName: string) => {
    setIsSelectingAgent(false);
    setIsCreatingSession(true);

    try {
      // 1. Create the session
      const session = await chatService.createSession(projectId, appName);

      // 2. Optimistically update local state
      setAllChatSessions((prev) => [...prev, session]);
      setCurrentAppName(session.appName === undefined ? null : session.appName);
      // 3. Navigate immediately, relying on the optimistic update
      navigate(`/project/${projectId}/chat/${session.id}`, {
        state: { isNewSession: true },
      });
    } catch (error) {
      console.error('Failed to start new chat:', error);
      // Optionally, add user-facing error handling here
      setIsCreatingSession(false);
    }
  };

  // Reset creating session state when we have successfully navigated to a session
  useEffect(() => {
    if (chatSessionId && isCreatingSession) {
      setIsCreatingSession(false);
    }
  }, [chatSessionId, isCreatingSession]);

  const handleBackToList = () => {
    navigate(`/project/${projectId}/chat`);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        p: 2,
        overflowY: 'auto',
      }}
    >
      {isLoadingSessions || isCreatingSession ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
          }}
        >
          <CircularProgress />
        </Box>
      ) : !chatSessionId ? (
        <ChatSessionList
          sessions={allChatSessions}
          onSelectSession={handleResumeChatSession}
          onNewChat={handleStartNewChatClick}
          isSelectingAgent={isSelectingAgent}
          availableApps={availableApps}
          onAgentSelect={handleAgentSelect}
          onCancelSelection={handleCancelSelection}
        />
      ) : (
        <ActiveConversation
          projectId={projectId}
          sessionId={chatSessionId}
          appName={currentAppName || ''}
          projectAssets={projectAssets}
          projectCanvases={projectCanvases}
          onBack={handleBackToList}
          onNewChat={handleStartNewChatClick}
          autoGreeting={location.state?.isNewSession ? 'Hi' : undefined}
          onRefreshProject={() => {
            fetchAllSessions();
            if (onRefreshProject) onRefreshProject();
          }}
        />
      )}
    </Box>
  );
}
