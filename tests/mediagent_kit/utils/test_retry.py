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
import requests
from google.api_core import exceptions as google_api_exceptions

from mediagent_kit.utils.retry import (
    retry_on_error,
    ImmediateRetriableAPIError,
    _RETRY_MAX_ATTEMPTS,
)


def test_retry_on_error_success_first_time():
    """Verifies function succeeds on first attempt without retry delays."""
    mock_func = unittest.mock.MagicMock(return_value="success")

    @retry_on_error()
    def my_func():
        return mock_func()

    result = my_func()
    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_on_error_success_after_failure():
    """Verifies function retries and succeeds on a subsequent attempt."""
    mock_func = unittest.mock.MagicMock(
        side_effect=[
            google_api_exceptions.ServiceUnavailable("Service unavailable"),
            google_api_exceptions.ServiceUnavailable("Service unavailable"),
            "success",
        ]
    )

    @retry_on_error()
    def my_func():
        return mock_func()

    with unittest.mock.patch("time.sleep") as mock_sleep:
        result = my_func()

    assert result == "success"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2


def test_retry_on_error_permanent_failure():
    """Verifies function throws error after exhausting all retries."""
    mock_func = unittest.mock.MagicMock(
        side_effect=google_api_exceptions.ServiceUnavailable("Service unavailable")
    )

    @retry_on_error()
    def my_func():
        return mock_func()

    with unittest.mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(google_api_exceptions.ServiceUnavailable):
            my_func()

    assert mock_func.call_count == _RETRY_MAX_ATTEMPTS + 1
    assert mock_sleep.call_count == _RETRY_MAX_ATTEMPTS


def test_retry_on_error_non_retriable_error():
    """Verifies function fails immediately on a non-retriable error (e.g., ValueError)."""
    mock_func = unittest.mock.MagicMock(side_effect=ValueError("Non-retriable error"))

    @retry_on_error()
    def my_func():
        return mock_func()

    with unittest.mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            my_func()

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_retry_on_error_immediate_retriable_error():
    """Verifies ImmediateRetriableAPIError retries immediately without time.sleep."""
    mock_func = unittest.mock.MagicMock(
        side_effect=[
            ImmediateRetriableAPIError("Lyria recitation error"),
            "success",
        ]
    )

    @retry_on_error()
    def my_func():
        return mock_func()

    with unittest.mock.patch("time.sleep") as mock_sleep:
        result = my_func()

    assert result == "success"
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 0  # Should not sleep for ImmediateRetriableAPIError


def test_retry_on_error_retriable_http_error():
    """Verifies that retriable HTTP errors are caught and retried."""
    # Create a mock response with a 503 status
    mock_response = unittest.mock.MagicMock()
    mock_response.status_code = 503
    http_error = requests.exceptions.HTTPError("Service unavailable", response=mock_response)

    mock_func = unittest.mock.MagicMock(
        side_effect=[
            http_error,
            "success",
        ]
    )

    @retry_on_error()
    def my_func():
        return mock_func()

    with unittest.mock.patch("time.sleep") as mock_sleep:
        result = my_func()

    assert result == "success"
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1
