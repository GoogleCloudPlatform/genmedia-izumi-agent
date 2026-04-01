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

import http
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

import google.auth.exceptions
import requests
from google.api_core import exceptions as google_api_exceptions
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

_RETRY_MAX_ATTEMPTS = 3
_RETRY_INITIAL_DELAY_SECONDS = 30.0


RETRIABLE_HTTP_STATUSES = (
    http.HTTPStatus.TOO_MANY_REQUESTS,  # 429
    http.HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
    http.HTTPStatus.BAD_GATEWAY,  # 502
    http.HTTPStatus.SERVICE_UNAVAILABLE,  # 503
    http.HTTPStatus.GATEWAY_TIMEOUT,  # 504
)

RETRIABLE_EXCEPTIONS_WITH_BACKOFF = (
    google_api_exceptions.ResourceExhausted,  # 429
    google_api_exceptions.TooManyRequests,  # 429
    google_api_exceptions.InternalServerError,  # 500
    google_api_exceptions.BadGateway,  # 502
    google_api_exceptions.ServiceUnavailable,  # 503
    google_api_exceptions.GatewayTimeout,  # 504
    google_api_exceptions.DeadlineExceeded,  # 504
)

RETRIABLE_NETWORK_ERRORS = (
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    google.auth.exceptions.TransportError,
    google.auth.exceptions.RefreshError,
)


def is_retriable_http_error(e: requests.exceptions.HTTPError) -> bool:
    """Checks if an HTTPError is retriable."""
    if e.response is None:
        return False
    return e.response.status_code in RETRIABLE_HTTP_STATUSES


def is_retriable_genai_sdk_error(e: Exception) -> bool:
    """Checks if a Google GenAI SDK error is retriable."""
    if isinstance(e, genai_errors.ClientError):
        # 429 is Too Many Requests / Resource Exhausted
        return e.code == http.HTTPStatus.TOO_MANY_REQUESTS
    if isinstance(e, genai_errors.ServerError):
        # Server errors are generally retriable
        return True
    return False


class ImmediateRetriableAPIError(Exception):
    """Exception raised for immediately retriable errors such as Lyria recitation errors."""

    pass


ReturnType = TypeVar("ReturnType")  # Return type of the decorated function


def retry_on_error(
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., ReturnType]], Callable[..., ReturnType]]:
    """
    A decorator for retrying a synchronous function.

    Retries with exponential backoff for a set of retriable exceptions.
    Retries immediately for ImmediateRetriableAPIError.
    """

    def decorator(func: Callable[..., ReturnType]) -> Callable[..., ReturnType]:
        def wrapper(*args: Any, **kwargs: Any) -> ReturnType:
            delay = _RETRY_INITIAL_DELAY_SECONDS
            retries = _RETRY_MAX_ATTEMPTS

            for i in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == retries:
                        logger.error(
                            f"Function {func.__name__} failed after {retries + 1} attempts. Final error: {e}"
                        )
                        raise

                    if isinstance(e, ImmediateRetriableAPIError):
                        logger.warning(
                            f"Function {func.__name__} failed with RetriableAPIError. Retrying immediately..."
                        )
                        continue  # Retry without delay

                    is_http_error_retriable = isinstance(
                        e, requests.exceptions.HTTPError
                    ) and is_retriable_http_error(e)
                    is_api_error_retriable = isinstance(
                        e, RETRIABLE_EXCEPTIONS_WITH_BACKOFF
                    )
                    is_network_error_retriable = isinstance(e, RETRIABLE_NETWORK_ERRORS)
                    is_genai_sdk_error_retriable = is_retriable_genai_sdk_error(e)

                    if (
                        is_http_error_retriable
                        or is_api_error_retriable
                        or is_network_error_retriable
                        or is_genai_sdk_error_retriable
                    ):
                        logger.warning(
                            f"Function {func.__name__} failed with retriable error: {e}. Retrying in {delay:.2f} seconds..."
                        )
                        time.sleep(delay)  # Use time.sleep for synchronous retry
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"Function {func.__name__} failed with an unexpected non-retriable error: {e}"
                        )
                        raise  # Don't retry on unexpected errors
            # This part should ideally not be reached if an exception is always raised on final retry
            raise RuntimeError("Unexpected state in retry_on_error decorator.")

        return wrapper

    return decorator
