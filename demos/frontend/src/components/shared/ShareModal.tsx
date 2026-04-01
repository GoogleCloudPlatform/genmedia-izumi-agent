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
  Modal,
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  Avatar,
  ListItemText,
  Select,
  MenuItem,
  FormControl,
  type SelectChangeEvent,
  CircularProgress,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import type { Project, ProjectUser, Role } from '../../data/types';
import { currentUser } from '../../data/user';
import userService from '../../services/userService';
import projectService from '../../services/projectService';

interface ShareModalProps {
  open: boolean;
  onClose: () => void;
  project: Project;
}

const style = {
  position: 'absolute' as const,
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  minWidth: 500,
  maxWidth: 800,
  bgcolor: 'background.paper',
  boxShadow: 24,
  p: 4,
  borderRadius: 2,
};

const isValidEmail = (email: string) => {
  return /\S+@\S+\.\S+/.test(email);
};

export default function ShareModal({
  open,
  onClose,
  project,
}: ShareModalProps) {
  const [sharedUsers, setSharedUsers] = useState(project.sharedWith);
  const [inputValue, setInputValue] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSharedUsers(project.sharedWith);
    setHasChanges(false);
    setError(null);
    setInputValue('');
  }, [project.sharedWith, open]);

  const currentUserRole = project.sharedWith.find(
    (u) => u.id === currentUser.id,
  )?.role;
  const isEditor = currentUserRole === 'editor';

  const handleRoleChange = (userId: number, newRole: Role) => {
    const updatedUsers = sharedUsers.map((user) =>
      user.id === userId ? { ...user, role: newRole } : user,
    );
    setSharedUsers(updatedUsers);
    setHasChanges(true);
  };

  const handleRemoveUser = (userId: number) => {
    const updatedUsers = sharedUsers.filter((user) => user.id !== userId);
    setSharedUsers(updatedUsers);
    setHasChanges(true);
  };

  const handleAddUser = async () => {
    if (!isValidEmail(inputValue)) {
      setError('Please enter a valid email address.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const user = await userService.findUserByEmail(inputValue);
      if (sharedUsers.some((u) => u.id === user.id)) {
        setError(`${user.name} is already in the project.`);
      } else {
        const newUser: ProjectUser = { ...user, role: 'viewer' };
        setSharedUsers([...sharedUsers, newUser]);
        setInputValue('');
        setHasChanges(true);
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError('An unexpected error occurred.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await projectService.updateSharedUsers(project.id, sharedUsers);
      console.log('Project shared successfully');
      onClose();
    } catch (error) {
      console.error('Error saving sharing settings:', error);
    }
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose}>
      <Box sx={style}>
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
            color: (theme) => theme.palette.grey[500],
          }}
        >
          <CloseIcon />
        </IconButton>
        <Typography variant="h6" component="h2">
          Share &quot;{project.name}&quot;
        </Typography>

        {isEditor ? (
          <>
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  fullWidth
                  id="email"
                  label="Email Address"
                  name="email"
                  autoComplete="email"
                  autoFocus
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  error={!!error}
                  helperText={error}
                />
                <Button onClick={handleAddUser} disabled={isLoading}>
                  {isLoading ? <CircularProgress size={24} /> : 'Add'}
                </Button>
              </Box>
            </Box>

            <List sx={{ mt: 2 }}>
              {sharedUsers.map((user) => (
                <ListItem key={user.id} disablePadding sx={{ mb: 2 }}>
                  <ListItemAvatar>
                    <Avatar
                      src={user.profilePhotoUrl || undefined}
                      alt={user.name}
                    >
                      {!user.profilePhotoUrl && <AccountCircleIcon />}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={user.name}
                    secondary={`${user.email}`}
                    sx={{ wordBreak: 'break-word', mr: 2 }}
                  />
                  <>
                    <FormControl size="small" sx={{ minWidth: 100, mr: 1 }}>
                      <Select
                        value={user.role}
                        onChange={(e: SelectChangeEvent) =>
                          handleRoleChange(user.id, e.target.value as Role)
                        }
                      >
                        <MenuItem value="editor">Editor</MenuItem>
                        <MenuItem value="viewer">Viewer</MenuItem>
                      </Select>
                    </FormControl>
                    <Button
                      size="small"
                      onClick={() => handleRemoveUser(user.id)}
                    >
                      Remove
                    </Button>
                  </>
                </ListItem>
              ))}
            </List>

            <Box
              sx={{
                mt: 3,
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 1,
              }}
            >
              <Button onClick={handleCancel}>Cancel</Button>
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={!hasChanges}
              >
                Save
              </Button>
            </Box>
          </>
        ) : (
          <Box sx={{ mt: 2 }}>
            <Typography sx={{ mb: 2 }}>
              You must be an editor to share this project.
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={onClose}>Close</Button>
            </Box>
          </Box>
        )}
      </Box>
    </Modal>
  );
}
