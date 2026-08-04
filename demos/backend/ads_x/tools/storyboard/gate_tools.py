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

"""Human review gates for the ads_x pipeline.

A gate is a long-running tool: calling it suspends the invocation and emits a
function call the frontend can render as an approval control. The run resumes
only when the client answers that call, so the expensive generation stage never
starts on a storyboard nobody approved.

Two things about this mechanism are easy to get wrong:

1. The app must be built with ``ResumabilityConfig(is_resumable=True)``. Without
   it the framework does not pause at all: the tool returns, the pipeline runs
   straight into generation, and nothing reports an error. See
   tests/demos/ads_x/test_gate_resumability.py.
2. A gate is useless unless a client answers it. An unanswered gate hangs the
   run forever, so gates are opt-in via ``ENABLE_HITL_GATES`` and must stay off
   for any frontend that cannot render the approval control.
"""

import logging
from typing import Any, Dict

from google.adk.tools.tool_context import ToolContext

from ...utils.common import common_utils

logger = logging.getLogger(__name__)

ToolResult = common_utils.ToolResult
tool_success = common_utils.tool_success
tool_failure = common_utils.tool_failure

# Session-state key holding the reviewer's verdict on the storyboard.
STORYBOARD_DECISION_KEY = "storyboard_decision"

ACCEPT = "accept"
MODIFY = "modify"
REGENERATE = "regenerate"
VALID_DECISIONS = (ACCEPT, MODIFY, REGENERATE)


# Marker that _build_art_direction_block appends to every generated prompt.
ART_DIRECTION_MARKER = "[ART DIRECTION (NON-NEGOTIABLE)"


def split_art_direction(description: str) -> tuple[str, str]:
    """Separates a prompt's human-readable action from its art-direction block.

    Prompts carry several hundred characters of machine direction appended
    inline. A reviewer needs to read the action, so the two are returned apart
    rather than making every client parse the marker itself.
    """
    if not description:
        return "", ""
    head, marker, tail = description.partition(ART_DIRECTION_MARKER)
    if not marker:
        return description.strip(), ""
    return head.strip(), (marker + tail).strip()


def _scene_digest(storyboard: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Compact per-scene view for the approval UI."""
    digest = []
    for scene in storyboard.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        video = scene.get("video_prompt") or {}
        voiceover = scene.get("voiceover_prompt") or {}
        action, art_direction = split_art_direction(video.get("description") or "")
        digest.append(
            {
                "scene_id": scene.get("scene_id"),
                "topic": scene.get("topic"),
                "action": action,
                "art_direction": art_direction,
                "voiceover": voiceover.get("text"),
                "duration_seconds": video.get("duration_seconds"),
                "rendered": bool(video.get("asset_id")),
            }
        )
    return digest


async def await_storyboard_approval(tool_context: ToolContext) -> ToolResult:
    """Pauses for human review of the storyboard before any media is generated.

    Call this once the storyboard is complete and before generating media. The
    run suspends here until the reviewer responds; do not call it again for a
    storyboard that has already been answered.

    The response is expected to carry a ``decision`` of "accept", "modify" or
    "regenerate", and may carry free-text ``guidance`` describing the requested
    changes.
    """
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        return tool_failure(
            "There is no storyboard to review yet. Build the storyboard first."
        )

    # Clear any previous verdict so a re-gate cannot read a stale approval.
    tool_context.state[STORYBOARD_DECISION_KEY] = None

    logger.info(
        "Storyboard gate: awaiting review of %d scene(s).",
        len(storyboard.get("scenes") or []),
    )

    # The payload the frontend renders. The real answer arrives later, as the
    # client's function response; this is only the pending placeholder.
    return tool_success(
        {
            "status": "awaiting_human_review",
            "campaign_title": storyboard.get("campaign_title"),
            "scenes": _scene_digest(storyboard),
            "expected_response": {
                "decision": list(VALID_DECISIONS),
                "guidance": "optional free text describing requested changes",
            },
        }
    )


async def record_storyboard_decision(
    tool_context: ToolContext, decision: str, guidance: str = ""
) -> ToolResult:
    """Records the reviewer's verdict on the storyboard.

    Call this immediately after the review gate returns, passing the decision
    exactly as the reviewer gave it. Generation stays blocked until the verdict
    is "accept".

    Args:
        decision: One of "accept", "modify" or "regenerate".
        guidance: Any free-text direction the reviewer supplied.
    """
    normalised = (decision or "").strip().lower()
    if normalised not in VALID_DECISIONS:
        return tool_failure(
            f"Unknown decision '{decision}'. Expected one of "
            f"{', '.join(VALID_DECISIONS)}."
        )

    tool_context.state[STORYBOARD_DECISION_KEY] = {
        "decision": normalised,
        "guidance": guidance.strip(),
    }
    logger.info("Storyboard gate: reviewer chose '%s'.", normalised)

    if normalised == ACCEPT:
        return tool_success("Storyboard approved. Generation may proceed.")
    return tool_success(
        f"Storyboard marked '{normalised}'. Apply the requested changes, then "
        "seek approval again before generating."
    )


def storyboard_is_approved(state: Any) -> bool:
    """Whether the storyboard in ``state`` carries an explicit approval."""
    decision = None
    try:
        decision = state.get(STORYBOARD_DECISION_KEY)
    except AttributeError:
        return False
    return isinstance(decision, dict) and decision.get("decision") == ACCEPT
