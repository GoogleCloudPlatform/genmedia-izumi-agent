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

"""Rewrites a scene's action to begin from the frame that was rendered.

The storyboard writes a scene's opening frame and its action in one pass,
before either exists, so both describe a moment the author imagined. The image
model then renders its own reading of the frame, and the two part company: the
frame holds a closed paint box while the action dollies across the pigments
inside it, or the brush is a millimetre above the paper while the action has
already painted the landscape. Asked to film that, the model either contradicts
the frame it was handed or invents what the action needs.

Enrichment is already given the rendered frame and told it wins, and it is not
enough. Rewording an action is a small edit; overturning its premise is not,
and the instruction to do so competes with the art direction that same call
exists to apply. So the reconciliation is asked on its own, of a call that has
nothing else to weigh: here is the frame, here is the action, make the action
start here.
"""

import logging
from typing import Optional

import mediagent_kit.services.aio
from mediagent_kit.services.types.common import AssetRef

logger = logging.getLogger(__name__)

# A stored prompt is the action followed by the machine art direction the Look
# stamps onto it. Only the action is reconciled: the block is not prose the
# model should be rewriting, and leaving it in makes the reply longer than the
# rewrite it is measured against. Spelled out here as it is in gate_tools and
# look_tools, which each keep their own copy.
ART_DIRECTION_MARKER = "[ART DIRECTION (NON-NEGOTIABLE)"

_RECONCILE_PROMPT = """The attached image is the first frame of a video shot.
Below is the action drafted for that shot.

The action was written before the frame existed, so it may assume something
the frame does not show: an object that is not there, a state that differs (a
container open that is in fact closed), or a position other than where the
frame puts it.

Rewrite the action so it begins from exactly what the frame shows.

- Keep the intent: the same beat, the same subject, the same camera move and
  the same optical and lighting language.
- Where the action and the frame disagree, the frame is right. An object the
  frame does not show cannot be lifted, poured or opened; one it shows does
  not vanish.
- The shot runs about {duration} seconds. Do not describe more change than
  that allows: a movement that begins is better than a task that completes.
- Do not describe the frame. Describe what happens next.
- Do not name any brand.

Reply with the rewritten action and nothing else. If the action already starts
from what the frame shows, reply with it unchanged.

{topic_line}ACTION:
{action}"""


async def reconcile_action_with_frame(
    workspace_id: str,
    action: str,
    frame: Optional[AssetRef],
    duration_seconds: float,
    topic: str = "",
) -> str:
    """Returns the action rewritten to start from the frame in ``frame``.

    The original action is returned unchanged when the rewrite cannot be
    completed. A shot filmed from a slightly wrong premise is worth more than
    no shot, and this runs after the frame is already paid for.
    """
    if not action or frame is None:
        return action

    head, marker, tail = action.partition(ART_DIRECTION_MARKER)
    # The block is appended with a single leading space; restore it, since the
    # split takes the separator with the head.
    art_direction = f" {marker}{tail}" if marker else ""
    action_only = head.strip()
    if not action_only:
        return action

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    prompt = _RECONCILE_PROMPT.format(
        duration=f"{duration_seconds:g}",
        topic_line=f"BEAT: {topic}\n\n" if topic else "",
        action=action_only,
    )

    try:
        # generate_text, not generate_text_with_gemini: the latter is absent
        # from the service interface, so under Creative Studio it raises and
        # this whole step becomes a silent no-op.
        rewritten = (
            await mediagen_service.generate_text(
                workspace_id=workspace_id,
                prompt=prompt,
                reference_assets=[frame],
            )
        ).strip()
    except Exception as e:  # noqa: BLE001 - reconciliation must not fail a scene
        logger.warning(f"First-frame reconciliation did not complete: {e}")
        return action

    if not rewritten:
        logger.warning("First-frame reconciliation returned nothing.")
        return action

    # A reply far shorter than the draft has dropped the shot rather than
    # rewritten it, and one far longer has started narrating the frame.
    if not 0.4 * len(action_only) <= len(rewritten) <= 3 * len(action_only):
        logger.warning(
            f"First-frame reconciliation returned {len(rewritten)} characters "
            f"against {len(action_only)}; keeping the drafted action."
        )
        return action

    # The model is asked for the action alone, but echoes the block it was not
    # given often enough to be worth stripping rather than trusting.
    rewritten = rewritten.partition(ART_DIRECTION_MARKER)[0].strip()
    if not rewritten:
        return action

    if rewritten != action_only:
        logger.info("Scene action rewritten to start from its rendered frame.")
    return rewritten + art_direction
