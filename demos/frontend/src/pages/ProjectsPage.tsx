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

import ProjectGrid from '../components/projects/ProjectGrid';
import TopAppBar from '../components/shared/TopAppBar';
import { Box } from '@mui/material';

export default function ProjectsPage() {
  return (
    <Box>
      <TopAppBar />
      <Box sx={{ height: 'calc(100vh - 64px)', overflowY: 'auto' }}>
        <ProjectGrid />
      </Box>
    </Box>
  );
}
