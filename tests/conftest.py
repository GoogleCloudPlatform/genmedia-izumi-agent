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

import os
import sys

# Ensure APP_ENV is set to 'test' BEFORE importing main or config.
# This forces config.py to load .env.test if it exists.
os.environ["APP_ENV"] = "test"

# Add workspace root and demos/backend to path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../demos/backend")))

import pytest
from fastapi.testclient import TestClient

from demos.backend.main import app


@pytest.fixture(scope="module")
def client():
    """Returns a FastAPI TestClient for E2E API testing."""
    with TestClient(app) as client:
        yield client
