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

"""Global request context variable for propagating tokens and request variables."""

import contextvars
from typing import Any

# Global context var for holding request credentials/context
request_context_var: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "request_context", default=None
)


def set_request_context(user_auth_token: str | None, workspace_id: Any | None) -> contextvars.Token:
    """Sets credentials in the active asyncio/thread context."""
    return request_context_var.set({
        "user_auth_token": user_auth_token,
        "workspace_id": workspace_id,
    })


def reset_request_context(token: contextvars.Token) -> None:
    """Resets credentials context to previous state."""
    request_context_var.reset(token)


def get_request_context() -> dict[str, Any] | None:
    """Retrieves the active request credentials."""
    return request_context_var.get()
