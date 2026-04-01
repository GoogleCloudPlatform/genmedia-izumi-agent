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

import { useState, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Tabs,
  Tab,
  ToggleButton,
  ToggleButtonGroup,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import ViewListIcon from '@mui/icons-material/ViewList';
import GridViewIcon from '@mui/icons-material/GridView';
import SortIcon from '@mui/icons-material/Sort';
import FilterListIcon from '@mui/icons-material/FilterList';
import CheckIcon from '@mui/icons-material/Check';
import AssetModal from '../shared/AssetModal';
import type { ProjectAsset, Canvas, Job } from '../../data/types';
import { JobStatus } from '../../data/types';
import AssetsView from './content/AssetsView';
import CanvasView from './content/CanvasView';
import WorkflowView from './content/WorkflowView';

interface MainContentProps {
  onGenerateClick: () => void;
  assets: readonly ProjectAsset[];
  canvases: readonly Canvas[];
  pendingJobs?: readonly Job[];
  contentTab?: string;
  assetId?: string;
  canvasId?: string;
}

type DisplayItem =
  | ProjectAsset
  | (Job & { isPendingJob: true; createdAt: string; fileName: string }); // Augment Job with required fields for DisplayItem

type SortField = 'createdAt' | 'name';
type SortDirection = 'asc' | 'desc';

export default function MainContent({
  onGenerateClick,
  assets,
  canvases,
  pendingJobs,
  contentTab,
  assetId,
  canvasId,
}: MainContentProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab =
    contentTab === 'canvas' ? 1 : contentTab === 'workflow' ? 2 : 0;

  const [viewMode, setViewMode] = useState<'list' | 'grid'>('grid');

  // Sort & Filter State
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(
    null,
  );
  const [sortOption, setSortOption] = useState<{
    field: SortField;
    direction: SortDirection;
  }>({ field: 'createdAt', direction: 'desc' });
  const [filterType, setFilterType] = useState<string>('all');

  // Processing Logic - Moved up to be used in derived state
  const processedDisplayItems = useMemo(() => {
    // Cast pending jobs to DisplayItem and add temporary creation time for sorting
    const jobsAsDisplayItems: DisplayItem[] = (pendingJobs || [])
      .filter(
        (job) =>
          job.status !== JobStatus.COMPLETED && job.status !== JobStatus.FAILED,
      ) // Only show active pending jobs
      .map((job) => ({
        ...job,
        // Provide a consistent 'createdAt' and 'fileName' for sorting purposes
        // For pending jobs, use `created_at` or current time, and file_name from job_input
        createdAt: job.created_at || new Date().toISOString(),
        fileName:
          job.job_input?.file_name ||
          `Generating ${job.job_type.replace(/_/g, ' ').toLowerCase()}...`,
        isPendingJob: true, // Custom flag to identify pending jobs
      }));

    let combinedItems: DisplayItem[] = [...assets, ...jobsAsDisplayItems];

    // Filter
    if (filterType !== 'all') {
      combinedItems = combinedItems.filter((item) => {
        if ('job_type' in item) {
          // It's a Job
          const jobType = item.job_type.toLowerCase();
          if (filterType === 'image' && jobType.includes('image')) return true;
          if (filterType === 'video' && jobType.includes('video')) return true;
          if (
            filterType === 'audio' &&
            (jobType.includes('music') || jobType.includes('speech'))
          )
            return true;
          return false;
        } else {
          // It's a ProjectAsset
          return item.type === filterType;
        }
      });
    }

    // Sort
    combinedItems.sort((a, b) => {
      const getValue = (item: DisplayItem, field: SortField) => {
        if (field === 'createdAt') {
          return 'createdAt' in item && item.createdAt
            ? new Date(item.createdAt).getTime()
            : 0;
        } else {
          // field === 'name'
          return 'fileName' in item && item.fileName
            ? item.fileName.toLowerCase()
            : 'job_type' in item
              ? item.job_input?.file_name?.toLowerCase() || ''
              : '';
        }
      };

      const valA = getValue(a, sortOption.field);
      const valB = getValue(b, sortOption.field);

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortOption.direction === 'asc' ? valA - valB : valB - valA;
      } else if (typeof valA === 'string' && typeof valB === 'string') {
        return sortOption.direction === 'asc'
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }
      return 0;
    });

    return combinedItems;
  }, [assets, pendingJobs, sortOption, filterType]);

  const processedCanvases = useMemo(() => {
    const result = [...canvases];

    // Sort
    result.sort((a, b) => {
      if (sortOption.field === 'createdAt') {
        const dateA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const dateB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return sortOption.direction === 'asc' ? dateA - dateB : dateB - dateA;
      } else {
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        return sortOption.direction === 'asc'
          ? nameA.localeCompare(nameB)
          : nameB.localeCompare(a.name);
      }
    });

    return result;
  }, [canvases, sortOption]);

  // Derived State
  const selectedCanvas = useMemo(() => {
    if (contentTab === 'canvas' && canvasId) {
      return canvases.find((c) => c.id === canvasId) || null;
    }
    return null;
  }, [contentTab, canvasId, canvases]);

  const selectedAsset = useMemo(() => {
    if (contentTab === 'assets' && assetId) {
      // Find in the combined list now
      const foundItem = processedDisplayItems.find(
        (item) => 'id' in item && item.id === assetId,
      );
      // Ensure it's a ProjectAsset (not a pending job) before returning
      return 'id' in (foundItem || {}) && 'type' in (foundItem || {})
        ? (foundItem as ProjectAsset)
        : null;
    }
    return null;
  }, [contentTab, assetId, processedDisplayItems]);

  const modalOpen = !!selectedAsset;

  const handleChange = (_: React.SyntheticEvent, newValue: number) => {
    const tabName =
      newValue === 0 ? 'assets' : newValue === 1 ? 'canvas' : 'workflow';
    navigate(`${location.pathname}?contentTab=${tabName}`);
  };

  const handleViewModeChange = (
    _: React.MouseEvent<HTMLElement>,
    newViewMode: 'list' | 'grid',
  ) => {
    if (newViewMode !== null) {
      setViewMode(newViewMode);
    }
  };

  const handleAssetClick = (item: DisplayItem) => {
    if ('isPendingJob' in item && item.isPendingJob) return; // Cannot click pending jobs
    navigate(`${location.pathname}?contentTab=assets&assetId=${item.id}`);
  };

  const handleAssetIdClick = (targetAssetId: string) => {
    navigate(`${location.pathname}?contentTab=assets&assetId=${targetAssetId}`);
  };

  const handleModalClose = () => {
    navigate(`${location.pathname}?contentTab=assets`);
  };

  const handleNavigateAssets = (direction: 'prev' | 'next') => {
    const currentList = processedDisplayItems.filter(
      (item) => !('isPendingJob' in item),
    ) as ProjectAsset[]; // Navigate only within actual assets
    if (selectedAsset) {
      const currentIndex = currentList.findIndex(
        (a) => a.id === selectedAsset.id,
      );
      let nextAsset: ProjectAsset | undefined;
      if (direction === 'next' && currentIndex < currentList.length - 1) {
        nextAsset = currentList[currentIndex + 1];
      } else if (direction === 'prev' && currentIndex > 0) {
        nextAsset = currentList[currentIndex - 1];
      }
      if (nextAsset) {
        navigate(
          `${location.pathname}?contentTab=assets&assetId=${nextAsset.id}`,
        );
      }
    }
  };

  const handleCanvasClick = (canvas: Canvas) => {
    navigate(`${location.pathname}?contentTab=canvas&canvasId=${canvas.id}`);
  };

  const handleBackToCanvasList = () => {
    navigate(`${location.pathname}?contentTab=canvas`);
  };

  // Sort & Filter Handlers
  const handleSortClick = (event: React.MouseEvent<HTMLElement>) => {
    setSortAnchorEl(event.currentTarget);
  };
  const handleSortClose = () => {
    setSortAnchorEl(null);
  };
  const handleSortSelect = (field: SortField, direction: SortDirection) => {
    setSortOption({ field, direction });
    handleSortClose();
  };

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };
  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };
  const handleFilterSelect = (type: string) => {
    setFilterType(type);
    handleFilterClose();
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          px: 2,
        }}
      >
        <Tabs
          value={activeTab}
          onChange={handleChange}
          aria-label="main content tabs"
          sx={{ flexGrow: 1 }}
        >
          <Tab label="Assets" />
          <Tab label="Canvas" />
          <Tab label="Workflow" />
        </Tabs>

        {(activeTab === 0 || activeTab === 1) && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Sort Menu */}
            <Tooltip title="Sort">
              <IconButton onClick={handleSortClick} size="small">
                <SortIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={sortAnchorEl}
              open={Boolean(sortAnchorEl)}
              onClose={handleSortClose}
            >
              <MenuItem
                onClick={() => handleSortSelect('createdAt', 'desc')}
                selected={
                  sortOption.field === 'createdAt' &&
                  sortOption.direction === 'desc'
                }
              >
                <ListItemText>Newest First</ListItemText>
                {sortOption.field === 'createdAt' &&
                  sortOption.direction === 'desc' && (
                    <ListItemIcon>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                  )}
              </MenuItem>
              <MenuItem
                onClick={() => handleSortSelect('createdAt', 'asc')}
                selected={
                  sortOption.field === 'createdAt' &&
                  sortOption.direction === 'asc'
                }
              >
                <ListItemText>Oldest First</ListItemText>
                {sortOption.field === 'createdAt' &&
                  sortOption.direction === 'asc' && (
                    <ListItemIcon>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                  )}
              </MenuItem>
              <MenuItem
                onClick={() => handleSortSelect('name', 'asc')}
                selected={
                  sortOption.field === 'name' && sortOption.direction === 'asc'
                }
              >
                <ListItemText>Name (A-Z)</ListItemText>
                {sortOption.field === 'name' &&
                  sortOption.direction === 'asc' && (
                    <ListItemIcon>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                  )}
              </MenuItem>
              <MenuItem
                onClick={() => handleSortSelect('name', 'desc')}
                selected={
                  sortOption.field === 'name' && sortOption.direction === 'desc'
                }
              >
                <ListItemText>Name (Z-A)</ListItemText>
                {sortOption.field === 'name' &&
                  sortOption.direction === 'desc' && (
                    <ListItemIcon>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                  )}
              </MenuItem>
            </Menu>

            {/* Filter Menu (Only for Assets) */}
            {activeTab === 0 && (
              <>
                <Tooltip title="Filter">
                  <IconButton onClick={handleFilterClick} size="small">
                    <FilterListIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Menu
                  anchorEl={filterAnchorEl}
                  open={Boolean(filterAnchorEl)}
                  onClose={handleFilterClose}
                >
                  <MenuItem
                    onClick={() => handleFilterSelect('all')}
                    selected={filterType === 'all'}
                  >
                    <ListItemText>All Types</ListItemText>
                    {filterType === 'all' && (
                      <ListItemIcon>
                        <CheckIcon fontSize="small" />
                      </ListItemIcon>
                    )}
                  </MenuItem>
                  <MenuItem
                    onClick={() => handleFilterSelect('image')}
                    selected={filterType === 'image'}
                  >
                    <ListItemText>Images</ListItemText>
                    {filterType === 'image' && (
                      <ListItemIcon>
                        <CheckIcon fontSize="small" />
                      </ListItemIcon>
                    )}
                  </MenuItem>
                  <MenuItem
                    onClick={() => handleFilterSelect('video')}
                    selected={filterType === 'video'}
                  >
                    <ListItemText>Videos</ListItemText>
                    {filterType === 'video' && (
                      <ListItemIcon>
                        <CheckIcon fontSize="small" />
                      </ListItemIcon>
                    )}
                  </MenuItem>
                  <MenuItem
                    onClick={() => handleFilterSelect('audio')}
                    selected={filterType === 'audio'}
                  >
                    <ListItemText>Audio</ListItemText>
                    {filterType === 'audio' && (
                      <ListItemIcon>
                        <CheckIcon fontSize="small" />
                      </ListItemIcon>
                    )}
                  </MenuItem>
                  <MenuItem
                    onClick={() => handleFilterSelect('text')}
                    selected={filterType === 'text'}
                  >
                    <ListItemText>Text</ListItemText>
                    {filterType === 'text' && (
                      <ListItemIcon>
                        <CheckIcon fontSize="small" />
                      </ListItemIcon>
                    )}
                  </MenuItem>
                </Menu>
              </>
            )}

            {/* View Mode Toggle (Only for Assets) */}
            {activeTab === 0 && (
              <ToggleButtonGroup
                value={viewMode}
                exclusive
                onChange={handleViewModeChange}
                aria-label="view mode"
                size="small"
                sx={{ ml: 1 }}
              >
                <Tooltip title="Grid View">
                  <ToggleButton value="grid" aria-label="grid view">
                    <GridViewIcon fontSize="small" />
                  </ToggleButton>
                </Tooltip>
                <Tooltip title="List View">
                  <ToggleButton value="list" aria-label="list view">
                    <ViewListIcon fontSize="small" />
                  </ToggleButton>
                </Tooltip>
              </ToggleButtonGroup>
            )}
          </Box>
        )}
      </Box>
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3 }}>
        {activeTab === 0 && (
          <AssetsView
            items={processedDisplayItems}
            viewMode={viewMode}
            onAssetClick={handleAssetClick}
            onGenerateClick={onGenerateClick}
          />
        )}
        {activeTab === 1 && (
          <CanvasView
            canvases={processedCanvases}
            selectedCanvas={selectedCanvas}
            onCanvasClick={handleCanvasClick}
            onBackToCanvasList={handleBackToCanvasList}
          />
        )}
        {activeTab === 2 && <WorkflowView />}
      </Box>
      <AssetModal
        open={modalOpen}
        onClose={handleModalClose}
        asset={selectedAsset}
        allAssets={
          processedDisplayItems.filter(
            (item) => !('isPendingJob' in item),
          ) as ProjectAsset[]
        }
        onNavigate={handleNavigateAssets}
        onAssetClick={handleAssetIdClick}
      />
    </Box>
  );
}
