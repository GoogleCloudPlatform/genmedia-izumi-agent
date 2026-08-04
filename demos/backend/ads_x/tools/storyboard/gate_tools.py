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
        # Escalating breaks the surrounding review loop. Anything else leaves it
        # running, so the storyboard comes back for another look once the
        # requested changes have been applied.
        tool_context.actions.escalate = True
        return tool_success("Storyboard approved. Generation may proceed.")

    return tool_success(
        f"Storyboard marked '{normalised}'. Apply the requested changes, then "
        "seek approval again — the reviewer sees the storyboard once more "
        "before anything is generated."
    )


def storyboard_is_approved(state: Any) -> bool:
    """Whether the storyboard in ``state`` carries an explicit approval."""
    decision = None
    try:
        decision = state.get(STORYBOARD_DECISION_KEY)
    except AttributeError:
        return False
    return isinstance(decision, dict) and decision.get("decision") == ACCEPT


# --------------------------------------------------------------------------
# Strategy gate (Stage A)
# --------------------------------------------------------------------------

STRATEGY_DECISION_KEY = "strategy_decision"


async def await_strategy_approval(tool_context: ToolContext) -> ToolResult:
    """Pauses for human review of the campaign strategy before any scene exists.

    Call this once the brief has been read, assets catalogued, strategy mapped
    and a visual Look chosen. The run suspends here until the reviewer responds.

    This is the cheapest possible place to catch a misunderstanding: nothing has
    been written or rendered yet, so a correction here costs nothing, while the
    same correction after generation costs a full re-render.
    """
    parameters = tool_context.state.get(common_utils.PARAMETERS_KEY)
    if not isinstance(parameters, dict) or not parameters:
        return tool_failure(
            "There is no campaign strategy to review yet. Extract the brief first."
        )

    tool_context.state[STRATEGY_DECISION_KEY] = None

    recipe = tool_context.state.get("master_production_recipe") or {}
    assets = tool_context.state.get(common_utils.USER_ASSETS_KEY) or {}

    return tool_success(
        {
            "status": "awaiting_human_review",
            "stage": "strategy",
            "campaign": {
                "name": parameters.get("campaign_name"),
                "audience": parameters.get("target_audience"),
                "duration": parameters.get("target_duration"),
                "orientation": parameters.get("target_orientation"),
                "theme": parameters.get("campaign_theme"),
                "tone": parameters.get("campaign_tone"),
                "key_message": parameters.get("key_message"),
                "vertical": parameters.get("vertical"),
            },
            "look": {
                "name": recipe.get("look_name"),
                "aesthetic": recipe.get("brand_archetype"),
            },
            "features_a_person": bool(parameters.get("generate_virtual_creator")),
            "creator_description": parameters.get("creator_description") or None,
            "uploaded_assets": sorted(assets) if isinstance(assets, dict) else [],
            "expected_response": {
                "decision": list(VALID_DECISIONS),
                "guidance": "optional free text describing requested changes",
            },
        }
    )


async def record_strategy_decision(
    tool_context: ToolContext, decision: str, guidance: str = ""
) -> ToolResult:
    """Records the reviewer's verdict on the campaign strategy.

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

    tool_context.state[STRATEGY_DECISION_KEY] = {
        "decision": normalised,
        "guidance": guidance.strip(),
    }
    logger.info("Strategy gate: reviewer chose '%s'.", normalised)

    if normalised == ACCEPT:
        tool_context.actions.escalate = True
        return tool_success("Strategy approved. Building the storyboard.")

    return tool_success(
        f"Strategy marked '{normalised}'. Apply the requested changes, then "
        "seek approval again before the storyboard is written."
    )


def strategy_is_approved(state: Any) -> bool:
    """Whether the campaign strategy in ``state`` carries an explicit approval."""
    try:
        decision = state.get(STRATEGY_DECISION_KEY)
    except AttributeError:
        return False
    return isinstance(decision, dict) and decision.get("decision") == ACCEPT


# --------------------------------------------------------------------------
# Final cut gate (Stage C)
# --------------------------------------------------------------------------

FINAL_DECISION_KEY = "final_cut_decision"


async def await_final_cut_approval(tool_context: ToolContext) -> ToolResult:
    """Pauses for human review of the finished video.

    Call this once the video has been stitched. Unlike the earlier checkpoints
    this one does not protect a budget — the render is already paid for. It
    exists because some faults only become visible in the finished cut: a clip
    that does not match its prompt, a beat that lands wrong, a scene that reads
    differently in sequence than it did on paper.

    The reviewer can ask for individual scenes to be re-rendered; the video is
    then restitched and comes back for another look.
    """
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY)
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        return tool_failure("There is no storyboard, so there is nothing to review.")

    final_ref = tool_context.state.get("final_video_asset_ref")
    final_id = tool_context.state.get("final_video_asset_id")
    if not (final_ref or final_id):
        return tool_failure(
            "No stitched video yet. Generate the media and stitch it first."
        )

    tool_context.state[FINAL_DECISION_KEY] = None

    clips = []
    for scene in storyboard.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        video = scene.get("video_prompt") or {}
        action, _ = split_art_direction(video.get("description") or "")
        clips.append(
            {
                "scene_id": scene.get("scene_id"),
                "topic": scene.get("topic"),
                "action": action,
                "duration_seconds": video.get("duration_seconds"),
                "asset_id": video.get("asset_id"),
            }
        )

    return tool_success(
        {
            "status": "awaiting_human_review",
            "stage": "final_cut",
            "final_video": {"asset_id": final_id, "asset_ref": final_ref},
            "clips": clips,
            "expected_response": {
                "decision": list(VALID_DECISIONS),
                "guidance": (
                    "optional free text, e.g. 'scene_2 is too dark, re-render it'"
                ),
            },
        }
    )


async def record_final_cut_decision(
    tool_context: ToolContext, decision: str, guidance: str = ""
) -> ToolResult:
    """Records the reviewer's verdict on the finished video.

    Args:
        decision: One of "accept", "modify" or "regenerate".
        guidance: Any free-text direction, such as which clips to re-render.
    """
    normalised = (decision or "").strip().lower()
    if normalised not in VALID_DECISIONS:
        return tool_failure(
            f"Unknown decision '{decision}'. Expected one of "
            f"{', '.join(VALID_DECISIONS)}."
        )

    tool_context.state[FINAL_DECISION_KEY] = {
        "decision": normalised,
        "guidance": guidance.strip(),
    }
    logger.info("Final cut gate: reviewer chose '%s'.", normalised)

    if normalised == ACCEPT:
        tool_context.actions.escalate = True
        return tool_success("Final cut approved. The campaign is done.")

    return tool_success(
        f"Final cut marked '{normalised}'. Re-render the clips they called out, "
        "restitch, and show them the result."
    )


def final_cut_is_approved(state: Any) -> bool:
    """Whether the finished video in ``state`` carries an explicit approval."""
    try:
        decision = state.get(FINAL_DECISION_KEY)
    except AttributeError:
        return False
    return isinstance(decision, dict) and decision.get("decision") == ACCEPT
