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

"""
Abstract interface for a background job runner.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks


class AbstractBackgroundJobRunner(ABC):
    """
    Abstract interface for a background job runner.
    """

    @abstractmethod
    def schedule_job_execution(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Schedules a function to be executed in the background.
        """
        pass


class FastAPIBackgroundJobRunner(AbstractBackgroundJobRunner):
    """
    A concrete implementation of AbstractBackgroundJobRunner that wraps FastAPI's BackgroundTasks.
    """

    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def schedule_job_execution(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Schedules a function to be executed in the background using FastAPI's BackgroundTasks.
        """
        self.background_tasks.add_task(func, *args, **kwargs)
