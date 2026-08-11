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

"""Typed exception taxonomy for the mediagent_kit service interfaces.

Each concrete backend implementation (Izumi Native, Creative Studio, future
others) is expected to translate its backend-specific failures into one of
these typed exceptions, so callers can write backend-agnostic error
handling.

Rules:
  1. ``get_asset`` / ``get_timeline`` / ``get_canvas`` translate backend 404
     to ``None`` rather than raising ``NotFoundError`` (not-found is an
     expected outcome on those reads). All other operations raise
     ``NotFoundError`` if the target ID does not exist.
  2. ``generate_*`` and ``stitch_timeline``: on a generation failure
     (e.g. model rejection, content policy), return a terminal
     ``GeneratedAsset`` with ``status="failed"`` and populated
     ``error_message`` — do NOT raise. On transport / auth / validation
     failure (network, 401, 403, 422, 5xx), raise the corresponding
     typed exception.
  3. All other methods raise the corresponding typed exception on failure.
  4. Operations the session may not access raise ``AuthorizationError``
     (a backend MAY raise ``NotFoundError`` instead to avoid leaking
     resource existence).
  5. Calls to capabilities the active backend does not support raise
     ``UnsupportedFeatureError``.

These rules are mirrored in
``unified_media_agent_interface_spec_v1.md §7.4``.
"""


class MediagentError(Exception):
    """Base for every error raised by a mediagent_kit service interface.

    Catching ``MediagentError`` lets callers handle any expected service
    failure without catching unrelated Python exceptions.
    """

    def __init__(
        self,
        message: str = "",
        status_code: int | None = None,
        *args: object,
    ):
        super().__init__(message, *args)
        self.message = message
        self.status_code = status_code


class AuthenticationError(MediagentError):
    """The caller's identity could not be verified (HTTP 401 equivalent).

    Typical causes: missing token, expired token, malformed token.
    """


class AuthorizationError(MediagentError):
    """The caller is authenticated but not allowed to perform this action
    (HTTP 403 equivalent).

    Named ``AuthorizationError`` rather than ``PermissionError`` to avoid
    shadowing Python's builtin ``PermissionError``.
    """


class NotFoundError(MediagentError):
    """The requested resource does not exist (HTTP 404 equivalent).

    NOTE: ``get_asset`` / ``get_timeline`` / ``get_canvas`` translate 404
    to ``None`` rather than raising this. See rule 1 above.
    """


class ValidationError(MediagentError):
    """The request payload failed schema or business-rule validation
    (HTTP 400 / 422 equivalent).

    When raised by an adapter rather than by the caller's own input
    inspection, this typically indicates an adapter bug — the unified
    interface should have produced a valid payload.
    """


class BackendError(MediagentError):
    """The backend service is unhealthy or returned an unexpected error
    (HTTP 5xx, transport failure, parse failure, etc.).

    Distinguish from ``ValidationError`` (our request was bad) and
    ``TimeoutError`` (we gave up waiting).
    """


class TimeoutError(MediagentError):  # noqa: A001 — shadows builtin intentionally
    """A long-running generation or poll loop exceeded its deadline.

    Shadowing the builtin ``TimeoutError`` is intentional: within
    mediagent_kit we want every typed exception to share the
    ``MediagentError`` base, and the existing builtin would not. Code
    that needs the builtin can still ``import builtins`` and reach it
    via ``builtins.TimeoutError``.
    """


class UnsupportedFeatureError(MediagentError):
    """The active backend does not implement the requested capability.

    Callers that want graceful degradation should check
    ``AgentSession.supports(capability)`` before calling, rather than
    relying on ``try/except UnsupportedFeatureError``. See rule 5 above.
    """


__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "BackendError",
    "MediagentError",
    "NotFoundError",
    "TimeoutError",
    "UnsupportedFeatureError",
    "ValidationError",
]
