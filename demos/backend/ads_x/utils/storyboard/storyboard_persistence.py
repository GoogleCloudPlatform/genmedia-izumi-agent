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

"""Pushes the working storyboard to the Creative Studio backend.

While it is being written and revised the storyboard lives in ADK session
state. Creative Studio keeps its own copy, and that copy is what its frontend
renders, so a client sees a storyboard only once something has pushed the
session's copy across.

The push belongs at every point where a client is expected to be looking at
the storyboard: the review checkpoint, where a reviewer is asked to approve
it, and the stitch, where the finished timeline links back to it. Saving is
create-or-replace keyed on the storyboard id, and the id the backend assigns
is written back into state, so the later saves revise the record the first one
created instead of accumulating copies of one campaign.
"""

import logging
from typing import Any, Optional

from google.adk.tools import ToolContext

import mediagent_kit.services.aio

from utils.adk import get_session_id_from_context
from utils.adk import resolve_workspace_id

from ..common import common_utils

logger = logging.getLogger(__name__)

# Session-state key holding the id Creative Studio assigned the storyboard.
CURRENT_STORYBOARD_ID_KEY = "current_storyboard_id"


def _existing_id(storyboard: Any) -> Optional[str]:
    """The id the storyboard already carries, if it has been saved before."""
    if isinstance(storyboard, dict):
        found = storyboard.get("storyboard_id") or storyboard.get("id")
    else:
        found = getattr(storyboard, "storyboard_id", None)
    return str(found) if found else None


def _saved_id(saved: Any) -> Optional[str]:
    """The id out of whatever ``save_storyboard`` returned.

    The service answers with a Storyboard model or a plain dict depending on
    the backend it is talking to, so both shapes are read.
    """
    if saved is None:
        return None
    found = getattr(saved, "storyboard_id", None)
    if not found and isinstance(saved, dict):
        found = saved.get("storyboard_id") or saved.get("id")
    return str(found) if found else None


async def save_to_creative_studio(
    tool_context: ToolContext, storyboard: Any
) -> Optional[str]:
    """Saves ``storyboard`` to Creative Studio and returns the id it now holds.

    A failure is logged and swallowed, returning whatever id the storyboard
    already had. Creative Studio being unreachable is not a reason to abandon
    a storyboard the session has already written: the caller either carries on
    to render it, or asks a human to review it from the session's own copy.
    """
    existing = _existing_id(storyboard)

    workspace_id, ws_error = resolve_workspace_id(tool_context)
    if ws_error:
        logger.warning(f"Storyboard not saved to Creative Studio: {ws_error}")
        return existing

    session_id = get_session_id_from_context(tool_context)

    # The backend keys the record by workspace and session, and neither is
    # part of the storyboard the agents write, so both are stamped on here.
    if isinstance(storyboard, dict):
        storyboard["session_id"] = session_id
        storyboard["workspace_id"] = workspace_id
    else:
        try:
            setattr(storyboard, "session_id", session_id)
            setattr(storyboard, "workspace_id", workspace_id)
        except Exception as attr_err:
            logger.warning(
                f"Could not set session_id/workspace_id on the storyboard: {attr_err}"
            )

    try:
        storyboard_service = mediagent_kit.services.aio.get_storyboard_service()
        saved = await storyboard_service.save_storyboard(storyboard)
    except Exception as save_err:
        logger.warning(f"Storyboard save to Creative Studio failed: {save_err}")
        return existing

    storyboard_id = _saved_id(saved) or existing
    if not storyboard_id:
        return None

    tool_context.state[CURRENT_STORYBOARD_ID_KEY] = storyboard_id
    if isinstance(storyboard, dict):
        storyboard["storyboard_id"] = storyboard_id
        tool_context.state[common_utils.STORYBOARD_KEY] = storyboard
    elif hasattr(storyboard, "storyboard_id"):
        setattr(storyboard, "storyboard_id", storyboard_id)
        tool_context.state[common_utils.STORYBOARD_KEY] = storyboard

    return storyboard_id
