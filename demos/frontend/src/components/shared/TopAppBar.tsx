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
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Box,
  ListItemIcon,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import MovieIcon from '@mui/icons-material/Movie';
import Settings from '@mui/icons-material/Settings';
import Logout from '@mui/icons-material/Logout';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';

import { currentUser } from '../../data/user';

interface TopAppBarProps {
  projectName?: string;
}

export default function TopAppBar({ projectName }: TopAppBarProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        color: 'text.primary',
      }}
    >
      <Toolbar variant="dense">
        <MovieIcon
          sx={{
            display: { xs: 'none', md: 'flex' },
            mr: 1,
            color: 'primary.main',
          }}
        />
        <Typography
          variant="h6"
          noWrap
          component={RouterLink}
          to="/projects"
          sx={{
            mr: 2,
            display: { xs: 'none', md: 'flex' },
            fontWeight: 700,
            letterSpacing: '.1rem',
            color: 'inherit',
            textDecoration: 'none',
          }}
        >
          Izumi Studio
        </Typography>

        {projectName && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ mx: 1, color: 'text.secondary' }}>
              /
            </Typography>
            <Typography variant="subtitle1" sx={{ fontWeight: 500 }}>
              {projectName}
            </Typography>
          </Box>
        )}

        <Box sx={{ flexGrow: 1 }} />
        <IconButton onClick={handleMenu} sx={{ p: 0 }}>
          <Avatar
            alt={currentUser.name}
            src={currentUser.profilePhotoUrl || undefined}
          >
            {!currentUser.profilePhotoUrl && <AccountCircleIcon />}
          </Avatar>
        </IconButton>
        <Menu
          id="menu-appbar"
          anchorEl={anchorEl}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          keepMounted
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          open={open}
          onClose={handleClose}
        >
          <MenuItem onClick={handleClose} component={RouterLink} to="/settings">
            <ListItemIcon>
              <Settings fontSize="small" />
            </ListItemIcon>
            Settings
          </MenuItem>
          <MenuItem onClick={handleClose} component={RouterLink} to="/login">
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            Logout
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
