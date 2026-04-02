# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest.mock
import pytest
from fastapi import BackgroundTasks

from mediagent_kit.utils.background_job_runner import FastAPIBackgroundJobRunner


def test_fastapi_background_job_runner_schedule():
    """Verifies that FastAPIBackgroundJobRunner delegates task to BackgroundTasks."""
    # Create mock BackgroundTasks
    mock_background_tasks = unittest.mock.MagicMock(spec=BackgroundTasks)

    # Initialize the runner with the mock
    runner = FastAPIBackgroundJobRunner(mock_background_tasks)

    # Define a dummy function to schedule
    def dummy_func(arg1, arg2):
        pass

    # Schedule execution
    runner.schedule_job_execution(dummy_func, "value1", arg2="value2")

    # Verify add_task was called with correct arguments
    mock_background_tasks.add_task.assert_called_once_with(
        dummy_func, "value1", arg2="value2"
    )
