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

import { useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  ListItemIcon,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
} from '@mui/material';
import AddCommentIcon from '@mui/icons-material/AddComment';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import type { ChatSession } from '../../../data/types';
import { AGENT_DESCRIPTIONS } from '../../../data/agents';

const TITLE_MAX_LENGTH = 120;

interface ChatSessionListProps {
  sessions: ChatSession[];
  onSelectSession: (session: ChatSession) => void;
  onNewChat: () => void;
  isSelectingAgent: boolean;
  availableApps: string[];
  onAgentSelect: (appName: string) => void;
  onCancelSelection: () => void;
  onRenameSession: (session: ChatSession, title: string) => Promise<void>;
  onDeleteSession: (session: ChatSession) => Promise<void>;
}

const sessionKey = (session: ChatSession) => `${session.appName}-${session.id}`;

export default function ChatSessionList({
  sessions,
  onSelectSession,
  onNewChat,
  isSelectingAgent,
  availableApps,
  onAgentSelect,
  onCancelSelection,
  onRenameSession,
  onDeleteSession,
}: ChatSessionListProps) {
  const [menu, setMenu] = useState<{
    anchor: HTMLElement;
    session: ChatSession;
  } | null>(null);
  const [renaming, setRenaming] = useState<ChatSession | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<ChatSession | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openMenu = (event: MouseEvent<HTMLElement>, session: ChatSession) => {
    setMenu({ anchor: event.currentTarget, session });
  };

  const startRename = () => {
    if (!menu) return;
    setDraftTitle(menu.session.title);
    setRenaming(menu.session);
    setMenu(null);
  };

  const saveRename = async () => {
    const title = draftTitle.trim();
    if (!renaming || !title) return;
    if (title === renaming.title) {
      setRenaming(null);
      return;
    }
    setIsSaving(true);
    try {
      await onRenameSession(renaming, title);
    } catch {
      setError("Couldn't rename the chat. Please try again.");
    } finally {
      setIsSaving(false);
      setRenaming(null);
    }
  };

  const handleRenameKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      void saveRename();
    }
  };

  const askDelete = () => {
    if (!menu) return;
    setPendingDelete(menu.session);
    setMenu(null);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setIsDeleting(true);
    try {
      await onDeleteSession(pendingDelete);
    } catch {
      setError("Couldn't delete the chat. Please try again.");
    } finally {
      setIsDeleting(false);
      setPendingDelete(null);
    }
  };

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
                <ListItemButton
                  onClick={() => onAgentSelect(appName)}
                  sx={{ borderRadius: 1, alignItems: 'flex-start' }}
                >
                  <ListItemText
                    primary={appName}
                    secondary={AGENT_DESCRIPTIONS[appName]}
                    slotProps={{
                      primary: { sx: { fontWeight: 600 } },
                      secondary: { sx: { mt: 0.5, lineHeight: 1.5 } },
                    }}
                  />
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
              <ListItem
                disablePadding
                key={sessionKey(session)}
                secondaryAction={
                  <IconButton
                    edge="end"
                    aria-label={`Chat options for ${session.title}`}
                    onClick={(event) => openMenu(event, session)}
                  >
                    <MoreVertIcon fontSize="small" />
                  </IconButton>
                }
              >
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
                    slotProps={{ primary: { noWrap: true } }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
        </List>
      </Box>

      {/* Focus is not handed back to the row on close, so the dialog opened
          from the menu keeps it. */}
      <Menu
        anchorEl={menu?.anchor}
        open={menu !== null}
        onClose={() => setMenu(null)}
        disableRestoreFocus
      >
        <MenuItem onClick={startRename}>
          <ListItemIcon>
            <EditOutlinedIcon fontSize="small" />
          </ListItemIcon>
          Rename
        </MenuItem>
        <MenuItem onClick={askDelete} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <DeleteOutlineIcon fontSize="small" color="error" />
          </ListItemIcon>
          Delete
        </MenuItem>
      </Menu>

      <Dialog
        open={renaming !== null}
        onClose={() => setRenaming(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Rename chat</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
            slotProps={{
              htmlInput: {
                maxLength: TITLE_MAX_LENGTH,
                'aria-label': 'Chat name',
                onKeyDown: handleRenameKeyDown,
              },
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenaming(null)} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              void saveRename();
            }}
            disabled={isSaving || !draftTitle.trim()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
      >
        <DialogTitle>Delete this chat?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            &ldquo;{pendingDelete?.title}&rdquo; and its messages will be
            removed. Assets it generated stay in the Assets panel.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDelete(null)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              void confirmDelete();
            }}
            disabled={isDeleting}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={error !== null}
        autoHideDuration={4000}
        onClose={() => setError(null)}
        message={error}
      />
    </>
  );
}
