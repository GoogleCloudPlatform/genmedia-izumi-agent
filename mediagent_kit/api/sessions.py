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

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from google.adk.sessions.session import Session
from google.adk.sessions.base_session_service import BaseSessionService

from mediagent_kit.services.aio import get_session_service
from mediagent_kit.services import _get_service_factory

logger = logging.getLogger(__name__)

router = APIRouter()

# Source: https://github.com/google/adk-python/blob/0094eea3cadf5fe2e960cc558e467dd2131de1b7/src/google/adk/cli/cli_eval.py#L52
EVAL_SESSION_ID_PREFIX = "___eval___session___"


def get_api_session_service() -> BaseSessionService:
    return get_session_service()


@router.get(
    "/users/{user_id}/sessions",
    response_model=list[Session],
    tags=["Sessions"],
)
async def list_sessions(
    user_id: str,
    session_service: Annotated[BaseSessionService, Depends(get_api_session_service)],
    app_name: str | None = None,
) -> list[Session]:
    """
    Lists all sessions for a specific user.
    """
    if not app_name:
        config = _get_service_factory().get_config()
        app_name = config.agent_engine_id or "mediagent"

    response = await session_service.list_sessions(app_name=app_name, user_id=user_id)

    filtered_sessions = []
    for session in response.sessions:
        if not session.id.startswith(EVAL_SESSION_ID_PREFIX):
            filtered_sessions.append(session)
        else:
            logger.info(
                f"Filtered out session {session.id} as it is an evaluation session."
            )

    return filtered_sessions
