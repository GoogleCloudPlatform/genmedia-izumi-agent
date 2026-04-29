# Copyright 2026 Google LLC
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

import pytest
from unittest.mock import patch, AsyncMock
from ads_codirector.utils import mab_model


@pytest.fixture
def mock_asset_service():
    with patch("mediagent_kit.services.aio.get_asset_service") as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_mab_state():
    return mab_model.MabExperimentState(
        experiment_id="test-exp-123",
        user_prompt="Test",
        structured_constraints={},
        user_assets={},
        arm_stats={},
        iterations=[],
    )
