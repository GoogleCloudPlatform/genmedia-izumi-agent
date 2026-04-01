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
  Container,
  Card,
  CardActionArea,
  CardContent,
  Typography,
  Button,
  Box,
  CircularProgress,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  TextField, // Import TextField
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useEffect, useState, useMemo, useCallback } from 'react'; // Import useMemo, useCallback
import projectService from '../../services/projectService';
import type { Project } from '../../data/types';
import NewProjectModal from './NewProjectModal';
import RenameProjectModal from './RenameProjectModal';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

export default function ProjectGrid() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [projectToRename, setProjectToRename] = useState<Project | null>(null);
  const [viewArchived, setViewArchived] = useState(false);
  const [filterText, setFilterText] = useState(''); // State for filter text
  const navigate = useNavigate();

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null,
  );

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const fetchedProjects = await projectService.getProjects(
        viewArchived ? 'archived' : 'active',
      );
      setProjects(fetchedProjects);
      setError(null);
    } catch (error) {
      setError('Error fetching projects.');
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  }, [viewArchived]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreateProject = async (name: string) => {
    try {
      const newProject = await projectService.createProject(name);
      setIsModalOpen(false);
      navigate(`/project/${newProject.id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  const handleMenuClick = (
    event: React.MouseEvent<HTMLElement>,
    projectId: string,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedProjectId(projectId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedProjectId(null);
  };

  const handleArchiveProject = async () => {
    if (selectedProjectId) {
      try {
        await projectService.archiveProject(selectedProjectId);
        handleMenuClose();
        fetchProjects();
      } catch (error) {
        console.error('Failed to archive project:', error);
      }
    }
  };

  const handleUnarchiveProject = async () => {
    if (selectedProjectId) {
      try {
        await projectService.unarchiveProject(selectedProjectId);
        handleMenuClose();
        fetchProjects();
      } catch (error) {
        console.error('Failed to unarchive project:', error);
      }
    }
  };

  const handleRenameProject = () => {
    if (selectedProjectId) {
      const project = projects.find((p) => p.id === selectedProjectId);
      if (project) {
        setProjectToRename(project);
        setIsRenameModalOpen(true);
        handleMenuClose();
      }
    }
  };

  const confirmRenameProject = async (newName: string) => {
    if (projectToRename && newName) {
      try {
        await projectService.updateProjectName(projectToRename.id, newName);
        setIsRenameModalOpen(false);
        setProjectToRename(null);
        fetchProjects();
      } catch (error) {
        console.error('Failed to rename project:', error);
      }
    }
  };

  const handleDeleteProject = async () => {
    if (selectedProjectId) {
      if (window.confirm('Are you sure you want to delete this project?')) {
        try {
          await projectService.deleteProject(selectedProjectId);
          handleMenuClose();
          fetchProjects();
        } catch (error) {
          console.error('Failed to delete project:', error);
        }
      }
    }
  };

  // Filtered projects based on filterText
  const filteredProjects = useMemo(() => {
    if (!filterText) {
      return projects;
    }
    const lowerCaseFilter = filterText.toLowerCase();
    return projects.filter((project) =>
      project.name.toLowerCase().includes(lowerCaseFilter),
    );
  }, [projects, filterText]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 64px)', // Adjust for TopAppBar height
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 64px)', // Adjust for TopAppBar height
        }}
      >
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Container sx={{ mt: 4, mb: 10, flexGrow: 1 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2, // Reduce margin-bottom to make space for filter
          }}
        >
          <Typography variant="h4" component="h1">
            {viewArchived ? 'Archived Projects' : 'Projects'}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              color="inherit"
              onClick={() => setViewArchived(!viewArchived)}
            >
              {viewArchived ? 'View Active Projects' : 'View Archived Projects'}
            </Button>
            {!viewArchived && (
              <Button variant="contained" onClick={() => setIsModalOpen(true)}>
                New Project
              </Button>
            )}
          </Box>
        </Box>

        {/* Filter Text Field */}
        <TextField
          label="Filter projects by name"
          variant="outlined"
          fullWidth
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          sx={{ mb: 4 }}
        />

        {filteredProjects.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '60vh',
              textAlign: 'center',
              border: '2px dashed',
              borderColor: 'divider',
              borderRadius: 4,
              p: 4,
              backgroundColor: 'background.paper',
            }}
          >
            {viewArchived ? (
              <>
                <ArchiveIcon
                  sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }}
                />
                <Typography variant="h5" gutterBottom color="text.primary">
                  No Archived Projects
                </Typography>
              </>
            ) : (
              <>
                <AddCircleOutlineIcon
                  sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }}
                />
                <Typography variant="h5" gutterBottom color="text.primary">
                  No Projects Yet
                </Typography>
                {filterText ? (
                  <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ mb: 4, maxWidth: 500 }}
                  >
                    No projects found matching "{filterText}".
                  </Typography>
                ) : (
                  <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ mb: 4, maxWidth: 500 }}
                  >
                    Create your first project to start generating amazing media
                    assets with our AI-powered tools.
                  </Typography>
                )}
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => setIsModalOpen(true)}
                  sx={{ px: 4, py: 1.5, fontSize: '1.1rem' }}
                >
                  Create New Project
                </Button>
              </>
            )}
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {filteredProjects.map((project) => (
              <Box
                key={project.id}
                sx={{
                  flexBasis: {
                    xs: 'calc(100% / 1 - 16px)',
                    sm: 'calc(100% / 2 - 16px)',
                    md: 'calc(100% / 3 - 16px)',
                    lg: 'calc(100% / 4 - 16px)',
                  },
                  maxWidth: {
                    xs: 'calc(100% / 1 - 16px)',
                    sm: 'calc(100% / 2 - 16px)',
                    md: 'calc(100% / 3 - 16px)',
                    lg: 'calc(100% / 4 - 16px)',
                  },
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <Card
                  sx={{
                    height: 250,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative',
                  }}
                >
                  <CardActionArea
                    component={RouterLink}
                    to={`/project/${project.id}`}
                    sx={{
                      flexGrow: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'stretch',
                      justifyContent: 'flex-start',
                    }}
                  >
                    {' '}
                    <CardContent sx={{ pr: 6 }}>
                      <Typography gutterBottom variant="h5" component="div">
                        {project.name}
                      </Typography>
                    </CardContent>
                    {/*
                  <CardContent>
                    {project.sharedWith.length > 0 ? (
                      <AvatarGroup max={4}>
                        {project.sharedWith.map((user: User) => (
                          <Avatar
                            key={user.name}
                            src={user.profilePhotoUrl || undefined}
                          >
                            {user.name.charAt(0)}
                          </Avatar>
                        ))}
                      </AvatarGroup>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Not Shared
                      </Typography>
                    )}
                  </CardContent>
                  */}
                  </CardActionArea>
                  <Box
                    sx={{ position: 'absolute', top: 4, right: 4, zIndex: 10 }}
                  >
                    <IconButton
                      size="small"
                      aria-label="Project Actions"
                      onClick={(e) => handleMenuClick(e, project.id)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </Box>
                </Card>
              </Box>
            ))}
          </Box>
        )}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={handleRenameProject}>
            <ListItemIcon>
              <EditIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Rename</ListItemText>
          </MenuItem>
          {viewArchived ? (
            <MenuItem onClick={handleUnarchiveProject}>
              <ListItemIcon>
                <UnarchiveIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Unarchive</ListItemText>
            </MenuItem>
          ) : (
            <MenuItem onClick={handleArchiveProject}>
              <ListItemIcon>
                <ArchiveIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Archive</ListItemText>
            </MenuItem>
          )}
          <MenuItem onClick={handleDeleteProject}>
            <ListItemIcon>
              <DeleteIcon fontSize="small" color="error" />
            </ListItemIcon>
            <ListItemText sx={{ color: 'error.main' }}>Delete</ListItemText>
          </MenuItem>
        </Menu>
        <NewProjectModal
          open={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onCreate={handleCreateProject}
        />
        <RenameProjectModal
          open={isRenameModalOpen}
          onClose={() => setIsRenameModalOpen(false)}
          onRename={confirmRenameProject}
          currentName={projectToRename?.name || ''}
        />
      </Container>
      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[200]
              : theme.palette.grey[800],
          position: 'fixed',
          bottom: 0,
          width: '100%',
          zIndex: (theme) => theme.zIndex.appBar - 1,
        }}
      >
        <Container maxWidth="sm">
          <Typography variant="caption" color="text.secondary" align="center">
            Note: This application currently lacks robust authentication. Anyone
            with access to this server and knowledge of your project ID may be
            able to view your project content.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}
