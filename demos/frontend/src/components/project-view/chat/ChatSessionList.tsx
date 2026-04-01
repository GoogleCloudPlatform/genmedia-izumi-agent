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
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Divider,
  IconButton,
} from '@mui/material';
import AddCommentIcon from '@mui/icons-material/AddComment';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import type { ChatSession } from '../../../data/types';

interface ChatSessionListProps {
  sessions: ChatSession[];
  onSelectSession: (session: ChatSession) => void;
  onNewChat: () => void;
  isSelectingAgent: boolean;
  availableApps: string[];
  onAgentSelect: (appName: string) => void;
  onCancelSelection: () => void;
}

export default function ChatSessionList({
  sessions,
  onSelectSession,
  onNewChat,
  isSelectingAgent,
  availableApps,
  onAgentSelect,
  onCancelSelection,
}: ChatSessionListProps) {
  if (isSelectingAgent) {
    return (
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton size="small" onClick={onCancelSelection} sx={{ mr: 1 }}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h6">Select Agent</Typography>
        </Box>
        <List>
          {availableApps.length > 0 ? (
            availableApps.map((appName) => (
              <ListItem key={appName} disablePadding>
                <ListItemButton onClick={() => onAgentSelect(appName)}>
                  <ListItemText primary={appName} />
                </ListItemButton>
              </ListItem>
            ))
          ) : (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ textAlign: 'center', mt: 2 }}
            >
              No agents available.
            </Typography>
          )}
        </List>
      </Box>
    );
  }

  if (sessions.length === 0) {
    return (
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 3,
          textAlign: 'center',
          height: '100%',
          opacity: 0.8,
        }}
      >
        <Box
          sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            bgcolor: 'action.hover',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 3,
          }}
        >
          <AutoAwesomeIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        </Box>

        <Typography variant="h6" gutterBottom>
          No chats yet
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 4, maxWidth: 260 }}
        >
          Start a conversation to generate assets, create content, and explore
          ideas.
        </Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<AddCommentIcon />}
          onClick={onNewChat}
          sx={{ borderRadius: 8, px: 4, textTransform: 'none' }}
        >
          Start New Chat
        </Button>
      </Box>
    );
  }

  return (
    <>
      <Box sx={{ p: 2 }}>
        <Button
          variant="contained"
          fullWidth
          startIcon={<AddCommentIcon />}
          onClick={onNewChat}
        >
          New Chat
        </Button>
      </Box>
      <Divider />
      <Box sx={{ width: '100%', mt: 1 }}>
        <Typography
          variant="subtitle2"
          sx={{ px: 2, py: 1, color: 'text.secondary' }}
        >
          Recent Chats
        </Typography>
        <List>
          {[...sessions]
            .sort((a, b) => {
              const dateA = new Date(a.lastUpdated).getTime();
              const dateB = new Date(b.lastUpdated).getTime();
              return dateB - dateA; // Sort in descending order
            })
            .map((session) => (
              <ListItem disablePadding key={session.appName + '-' + session.id}>
                <ListItemButton onClick={() => onSelectSession(session)}>
                  <ListItemText
                    primary={session.title}
                    secondary={`${session.appName} • ${new Date(
                      session.lastUpdated || new Date().toISOString(),
                    ).toLocaleString(undefined, {
                      year: 'numeric',
                      month: 'numeric',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}`}
                  />
                </ListItemButton>
              </ListItem>
            ))}
        </List>
      </Box>
    </>
  );
}
