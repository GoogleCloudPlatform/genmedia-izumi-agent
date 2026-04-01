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
  Alert,
  Box,
  Button,
  CircularProgress,
  Snackbar,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ProjectViewLayout from '../components/project-view/ProjectViewLayout';
import type { Job, Project } from '../data/types';
import mediaService from '../services/mediaService';
import projectService from '../services/projectService';

interface JobError {
  id: string;
  message: string;
}

export default function ProjectPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const projectId = id; // Keep as string
  const contentTab = searchParams.get('contentTab');
  const assetId = searchParams.get('assetId');
  const canvasId = searchParams.get('canvasId');
  const [project, setProject] = useState<Project | null>(null);
  const [pendingJobs, setPendingJobs] = useState<Job[]>(
    mediaService.getPendingJobs(),
  );
  const [jobErrors, setJobErrors] = useState<JobError[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const isLoadedRef = useRef(false);

  const loadProject = useCallback(
    async (forceRefresh = false) => {
      if (projectId) {
        try {
          // If loading for the first time, set loading state
          // Otherwise, just update in background
          if (!isLoadedRef.current && !forceRefresh) {
            setLoading(true);
          }

          const fetchedProject = await projectService.getProjectById(
            projectId,
            forceRefresh,
          );
          setProject(fetchedProject);
          isLoadedRef.current = true;
          setError(null);
        } catch (e: unknown) {
          setError('Failed to load project.');
          console.error(e);
        } finally {
          setLoading(false);
        }
      }
    },
    [projectId],
  );

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // Job polling effect
  useEffect(() => {
    if (!projectId) return;

    const pollJobs = async () => {
      // Check local state to see if we *should* poll, but also check service
      // because other components might have added jobs.
      const currentServiceJobs = mediaService.getPendingJobs();
      if (currentServiceJobs.length > 0) {
        const { activeJobs, completedJobs, failedJobs } =
          await mediaService.checkJobStatus(projectId);

        if (completedJobs.length > 0 || failedJobs.length > 0) {
          // If jobs completed or failed, refresh the project assets to get final status
          // Wait for the refresh to complete so the new asset appears BEFORE we remove the pending job
          await loadProject(true);
        }

        setPendingJobs(activeJobs);

        if (failedJobs.length > 0) {
          const newErrors = failedJobs.map((job) => ({
            id: job.id,
            message: `Job for ${job.job_input?.file_name || `Job ${job.id}`} failed: ${job.error_message}`,
          }));
          setJobErrors((prevErrors) => [...prevErrors, ...newErrors]);
        }
      } else if (pendingJobs.length > 0) {
        // If local state has jobs but service doesn't (shouldn't happen if synced), clear local
        setPendingJobs([]);
      }
    };

    // Initial poll to sync state
    setPendingJobs(mediaService.getPendingJobs());

    const intervalId = setInterval(pollJobs, 10000); // Poll every 10 seconds

    return () => clearInterval(intervalId);
  }, [projectId, loadProject, pendingJobs.length]);

  const handleRefreshProject = () => {
    loadProject(true);
    // Also update pending jobs from service in case a generation just started
    setPendingJobs(mediaService.getPendingJobs());
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          textAlign: 'center',
          p: 2,
        }}
      >
        <CircularProgress sx={{ mb: 2 }} />
        <Typography variant="h6">Loading project...</Typography>
      </Box>
    );
  }

  const handleGoBackToProjects = () => {
    navigate('/projects');
  };

  if (error || !project) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          textAlign: 'center',
          p: 2,
        }}
      >
        <ErrorOutlineIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" color="text.primary" gutterBottom>
          Project Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          The project you are looking for does not exist or you do not have
          permission to view it.
        </Typography>
        <Button variant="contained" onClick={handleGoBackToProjects}>
          Go to Projects List
        </Button>
      </Box>
    );
  }

  return (
    <>
      <ProjectViewLayout
        project={project}
        pendingJobs={pendingJobs}
        contentTab={contentTab || undefined}
        assetId={assetId || undefined}
        canvasId={canvasId || undefined}
        onRefreshProject={handleRefreshProject}
      />
      {jobErrors.map((error, index) => (
        <Snackbar
          open
          key={error.id}
          autoHideDuration={6000}
          onClose={() =>
            setJobErrors((prev) => prev.filter((e) => e.id !== error.id))
          }
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          style={{ bottom: `${20 + index * 70}px` }} // Stack snackbars
        >
          <Alert
            onClose={() =>
              setJobErrors((prev) => prev.filter((e) => e.id !== error.id))
            }
            severity="error"
            sx={{ width: '100%' }}
          >
            {error.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
}
