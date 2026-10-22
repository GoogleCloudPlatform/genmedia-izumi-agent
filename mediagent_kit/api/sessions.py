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

import asyncio
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.adk.sessions.session import Session
from google.api_core import exceptions as gcp_exceptions
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from mediagent_kit.services.aio import (
    FirestoreSessionService,
    get_firestore_session_service,
)
from mediagent_kit.services.aio.firestore_session_service import (
    DERIVED_SESSION_TITLE_KEY,
    SESSION_TITLE_KEY,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Source: https://github.com/google/adk-python/blob/0094eea3cadf5fe2e960cc558e467dd2131de1b7/src/google/adk/cli/cli_eval.py#L52
EVAL_SESSION_ID_PREFIX = "___eval___session___"

# Messages that carry no subject. The frontend opens every new chat with one.
_GREETINGS = frozenset({"hi", "hello", "hey"})
# Markdown emphasis, heading and quote markers, which a title shows literally.
_MARKDOWN_MARKERS = re.compile(r"[*_`#>]+")
TITLE_MAX_CHARS = 60


class RenameSessionRequest(BaseModel):
    """Body of a request to rename a session."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    app_name: str
    title: str = Field(max_length=120)


def get_session_service() -> FirestoreSessionService:
    return get_firestore_session_service()


def derive_session_title(texts: list[str]) -> str | None:
    """Returns a title taken from the first user message with a subject.

    Greetings are skipped and markdown markers removed. A message longer than
    ``TITLE_MAX_CHARS`` is cut at a word boundary and ends with an ellipsis.
    Returns None when no message has a subject.
    """
    for text in texts:
        line = " ".join(_MARKDOWN_MARKERS.sub(" ", text).split())
        if not line or line.lower().strip(" !.?,") in _GREETINGS:
            continue
        if len(line) <= TITLE_MAX_CHARS:
            return line
        clipped = line[:TITLE_MAX_CHARS].rsplit(" ", 1)[0].rstrip(" ,.;:-")
        return f"{clipped}…"
    return None


async def _backfill_title(
    session_service: FirestoreSessionService, session: Session
) -> None:
    """Derives a title for an untitled session and stores it."""
    try:
        texts = await session_service.list_opening_user_texts(
            app_name=session.app_name, user_id=session.user_id, session_id=session.id
        )
        title = derive_session_title(texts)
        if not title:
            return
        session.state[DERIVED_SESSION_TITLE_KEY] = title
        await session_service.set_session_title(
            app_name=session.app_name,
            user_id=session.user_id,
            session_id=session.id,
            title=title,
            derived=True,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        # A missing title must not fail the listing.
        logger.warning("Could not derive a title for session %s: %s", session.id, e)


@router.get(
    "/workspaces/{workspace_id}/sessions",
    response_model=list[Session],
    tags=["Sessions"],
)
async def list_sessions(
    workspace_id: str,
    session_service: Annotated[FirestoreSessionService, Depends(get_session_service)],
) -> list[Session]:
    """
    Lists all sessions for a specific user.

    A session with no title is given one from its first user message with a
    subject. It is stored as the derived title, so later listings do not derive
    it again and a chosen title still takes precedence.
    """
    response = await session_service.list_sessions(user_id=workspace_id)

    filtered_sessions = []
    for session in response.sessions:
        if not session.id.startswith(EVAL_SESSION_ID_PREFIX):
            filtered_sessions.append(session)
        else:
            logger.info(
                f"Filtered out session {session.id} as it is an evaluation session."
            )

    untitled = [
        s
        for s in filtered_sessions
        if not s.state.get(SESSION_TITLE_KEY)
        and not s.state.get(DERIVED_SESSION_TITLE_KEY)
    ]
    if untitled:
        await asyncio.gather(*(_backfill_title(session_service, s) for s in untitled))

    return filtered_sessions


@router.patch(
    "/workspaces/{workspace_id}/sessions/{session_id}",
    tags=["Sessions"],
)
async def rename_session(
    workspace_id: str,
    session_id: str,
    request: RenameSessionRequest,
    session_service: Annotated[FirestoreSessionService, Depends(get_session_service)],
) -> dict[str, str]:
    """
    Sets the name a session is listed under.
    """
    title = " ".join(request.title.split())
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    try:
        await session_service.set_session_title(
            app_name=request.app_name,
            user_id=workspace_id,
            session_id=session_id,
            title=title,
        )
    except gcp_exceptions.NotFound as e:
        raise HTTPException(status_code=404, detail="Session not found") from e

    return {"id": session_id, "title": title}
