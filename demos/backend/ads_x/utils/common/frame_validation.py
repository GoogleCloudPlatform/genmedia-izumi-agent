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

"""Checks a generated first frame against the references it was built from.

Prompt text alone does not hold a renderer to a supplied product: given a
product image and a brand logo it merges them, and given a brand name in the
prompt it writes that name onto the product. Both produce a frame showing a
product that does not exist. The checks here run after generation and report
what went wrong, so the caller can regenerate against a specific fault rather
than restating prohibitions.

The inspection is a separate model call carrying one instruction. Adding these
rules to the enrichment prompt instead would place them alongside the art
direction the same call is asked to apply, where they compete for attention.
"""

import json
import logging
import re
from typing import Any, Optional

import mediagent_kit.services.aio
from mediagent_kit.services.types.common import AssetRef

logger = logging.getLogger(__name__)

# Faults the inspector reports, in the wording fed back to a regeneration.
FAULT_ADDED_MARKINGS = (
    "The product carries a marking its reference does not show. Remove only "
    "that marking. Every marking the reference does show stays exactly as it "
    "has it: the wordmark, the product name, any text printed on the product."
)
FAULT_MISSING_MARKINGS = (
    "The product is missing branding its reference shows. Reproduce the "
    "wordmark, product name and any text the reference has, in the same "
    "position and proportion. An unbranded product is not the product."
)
FAULT_LOGO_ON_PRODUCT = (
    "The brand logo is applied to the product. Place it on its own surface, "
    "physically separate, and leave the product bare."
)
FAULT_STUDIO_CUTOUT = (
    "The frame is a product cutout on a plain studio background. Build the "
    "described environment around the product."
)
FAULT_IMPLAUSIBLE_PRODUCT = (
    "The product is rendered at a size it could not be, or floats with "
    "nothing holding it. Place it in the scene at its true size, resting on "
    "or attached to something."
)

_INSPECTION_PROMPT = """You are inspecting one generated advertising frame.

Image 1 is the PRODUCT REFERENCE: the product exactly as it really looks.
{logo_line}Image {frame_index} is the GENERATED FRAME under inspection.

Compare them and answer only about what is visible. Reply with JSON and
nothing else:

{{"added_markings": <true|false>,
  "missing_markings": <true|false>,
  "logo_on_product": <true|false>,
  "studio_cutout": <true|false>,
  "implausible_product": <true|false>}}

added_markings: true only if the product in the generated frame carries a
marking that is ABSENT from the reference - different words, an emblem the
reference does not have, a pattern it does not have. A product whose reference
carries an icon and no words has added markings if words appear on it. This is
NOT about how well an existing marking is drawn: the same wordmark rendered
imperfectly, at a slightly different size, or partly obscured by angle is
false. Judge which markings are present, not how cleanly they are printed.

missing_markings: true if the product reference shows a wordmark, product name
or other printed text and the generated product does not carry it. A branded
product rendered blank is this fault. False when the reference product is
itself unmarked.

logo_on_product: true if a brand logo or wordmark appears printed, embossed,
engraved, stitched or otherwise applied to the product itself. False when the
logo sits on a separate surface such as a card, plate, sign or wall.

studio_cutout: true if the product stands on a plain white or grey studio
sweep with no real environment around it.

implausible_product: true only when the product could not be as shown - it is
several times its real size against the people or furniture beside it, or it
hangs in the air with nothing holding it. Judge this one generously. A hero
close-up, a product large in frame, a bold or unusual angle, an artistic
composition: all fine, all false. Reserve true for what a viewer would read
as a mistake rather than a choice."""


def _parse_verdict(raw: str) -> Optional[dict[str, bool]]:
    """Reads the inspector's JSON, tolerating fenced or padded output."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return {k: bool(v) for k, v in parsed.items()}


async def inspect_first_frame(
    workspace_id: str,
    frame: AssetRef,
    product: AssetRef,
    logo: Optional[AssetRef] = None,
    scene_index: Optional[int] = None,
) -> list[str]:
    """Returns the faults found in a generated frame, empty when it is sound.

    An inspection that cannot be completed returns no faults. The frame is
    already generated, and discarding it because the check failed would trade a
    usable frame for none.
    """
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()

    references = [product]
    logo_line = ""
    if logo is not None:
        references.append(logo)
        logo_line = "Image 2 is the BRAND LOGO supplied for this campaign.\n"
    references.append(frame)

    prompt = _INSPECTION_PROMPT.format(logo_line=logo_line, frame_index=len(references))

    try:
        # generate_text, not generate_text_with_gemini: the latter is absent
        # from the service interface, so under Creative Studio it raises and
        # the gate becomes a silent no-op.
        reply = await mediagen_service.generate_text(
            workspace_id=workspace_id,
            prompt=prompt,
            reference_assets=references,
            purpose=(
                "frame_check"
                if scene_index is None
                else f"frame_check_scene_{scene_index}"
            ),
        )
        verdict = _parse_verdict(reply)
    except Exception as e:  # noqa: BLE001 - inspection must not fail a scene
        logger.warning(f"First-frame inspection did not complete: {e}")
        return []

    if verdict is None:
        logger.warning("First-frame inspection returned no readable verdict.")
        return []

    faults = []
    if verdict.get("added_markings"):
        faults.append(FAULT_ADDED_MARKINGS)
    if verdict.get("missing_markings"):
        faults.append(FAULT_MISSING_MARKINGS)
    if logo is not None and verdict.get("logo_on_product"):
        faults.append(FAULT_LOGO_ON_PRODUCT)
    if verdict.get("studio_cutout"):
        faults.append(FAULT_STUDIO_CUTOUT)
    if verdict.get("implausible_product"):
        faults.append(FAULT_IMPLAUSIBLE_PRODUCT)
    return faults


def corrective_note(faults: list[str]) -> str:
    """Renders faults as an instruction block appended to a regeneration."""
    listed = "\n".join(f"- {fault}" for fault in faults)
    return (
        "\n\nThe previous attempt at this frame was rejected. Correct these "
        f"faults and change nothing else:\n{listed}"
    )


def product_and_logo_references(
    assets: list[Any],
) -> tuple[Optional[str], Optional[str]]:
    """Splits a scene's reference filenames into its product and its logo."""
    product = None
    logo = None
    for name in assets:
        text = str(name)
        if "logo" in text.lower():
            logo = logo or text
        elif not text.startswith("virtual_creator_"):
            product = product or text
    return product, logo
