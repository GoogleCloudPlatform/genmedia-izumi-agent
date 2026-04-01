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
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from '@mui/material';

interface RenameProjectModalProps {
  open: boolean;
  onClose: () => void;
  onRename: (newName: string) => void;
  currentName: string;
}

export default function RenameProjectModal({
  open,
  onClose,
  onRename,
  currentName,
}: RenameProjectModalProps) {
  const [name, setName] = useState(currentName);
  const [prevCurrentName, setPrevCurrentName] = useState(currentName);

  // Sync state from props if prop changes (derived state pattern)
  if (currentName !== prevCurrentName) {
    setName(currentName);
    setPrevCurrentName(currentName);
  } else if (open && name !== currentName && prevCurrentName === currentName) {
    // If opened and name is stale (optional, but 'open' usually resets?)
    // Actually, standard pattern is just syncing to prop.
    // The useEffect was resetting on 'open' too.
    // Let's assume resetting on currentName change is enough, or we need to track 'open'.
  }

  // If we want to reset name when modal opens:
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setName(currentName);
    }
  }

  const handleRename = () => {
    if (name.trim() && name.trim() !== currentName) {
      onRename(name.trim());
    } else {
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Rename Project</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Please enter a new name for the project.
        </DialogContentText>
        <TextField
          autoFocus
          margin="dense"
          label="Project Name"
          type="text"
          fullWidth
          variant="standard"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleRename()}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleRename} disabled={!name.trim()}>
          Rename
        </Button>
      </DialogActions>
    </Dialog>
  );
}
