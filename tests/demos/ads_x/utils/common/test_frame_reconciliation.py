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

"""Tests for reconciling a scene's action with its rendered first frame."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from demos.backend.ads_x.utils.common import frame_reconciliation
from mediagent_kit.services.types.common import AssetRef

DRAFT = (
    "The camera gently dollies across the intricate botanical pigments of the "
    "wooden watercolor box resting on a sun-drenched slate table."
)
REWRITE = (
    "The camera gently dollies along the closed lid of the wooden watercolor "
    "box resting on a sun-drenched slate table, its grain catching the light."
)


FRAME = AssetRef(id="frame-1", asset_type="generated", workspace_id="ws-1")


def _services(reply=REWRITE, raises=None):
    """Patches the service the reconciliation reaches for."""
    mediagen = AsyncMock()
    if raises is not None:
        mediagen.generate_text.side_effect = raises
    else:
        mediagen.generate_text.return_value = reply
    return (
        patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mediagen,
        ),
        patch("mediagent_kit.services.aio.get_asset_service", return_value=AsyncMock()),
        mediagen,
    )


async def _reconcile(action=DRAFT, **kwargs):
    mediagen_patch, asset_patch, mediagen = _services(**kwargs)
    with mediagen_patch, asset_patch:
        result = await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", action, frame=FRAME, duration_seconds=3.0, topic="Hook"
        )
    return result, mediagen


async def test_the_action_is_rewritten_to_match_the_frame():
    result, _ = await _reconcile()

    assert result == REWRITE


async def test_the_frame_is_what_the_call_is_asked_about():
    _, mediagen = await _reconcile()

    kwargs = mediagen.generate_text.await_args.kwargs
    assert kwargs["reference_assets"] == [FRAME]
    prompt = kwargs["prompt"]
    assert DRAFT in prompt, "the drafted action must be what is reconciled"
    assert "Hook" in prompt, "the beat keeps the rewrite on the same intent"
    assert "3 seconds" in prompt, "how much change fits depends on the runtime"


async def test_an_action_that_already_fits_comes_back_unchanged():
    result, _ = await _reconcile(reply=DRAFT)

    assert result == DRAFT


# --------------------------------------------------------------------------
# Falling back
#
# This runs after the frame is paid for. A shot filmed from a slightly wrong
# premise beats no shot, so every failure returns the drafted action.
# --------------------------------------------------------------------------


async def test_a_failed_call_keeps_the_drafted_action():
    result, _ = await _reconcile(raises=RuntimeError("model unavailable"))

    assert result == DRAFT


async def test_an_empty_reply_keeps_the_drafted_action():
    result, _ = await _reconcile(reply="   ")

    assert result == DRAFT


@pytest.mark.parametrize(
    "reply, why",
    [
        ("Pan left.", "a reply this short has dropped the shot"),
        ("word " * 400, "a reply this long has started narrating the frame"),
    ],
)
async def test_a_reply_of_the_wrong_size_is_refused(reply, why):
    result, _ = await _reconcile(reply=reply)

    assert result == DRAFT, why


@pytest.mark.parametrize("missing", [("", FRAME), (DRAFT, None)])
async def test_nothing_to_reconcile_costs_no_call(missing):
    action, frame = missing
    mediagen_patch, asset_patch, mediagen = _services()

    with mediagen_patch, asset_patch:
        result = await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", action, frame=frame, duration_seconds=3.0
        )

    assert result == action
    mediagen.generate_text.assert_not_awaited()


# --------------------------------------------------------------------------
# Art direction
#
# A stored prompt is the action followed by the machine block the Look stamps
# on. Only the action is prose the model should touch.
# --------------------------------------------------------------------------

ART = " [ART DIRECTION (NON-NEGOTIABLE) -> Lighting: golden hour; Optics: T2.0]"


async def test_only_the_action_is_sent_for_rewriting():
    mediagen_patch, asset_patch, mediagen = _services()

    with mediagen_patch, asset_patch:
        await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", DRAFT + ART, frame=FRAME, duration_seconds=3.0
        )

    prompt = mediagen.generate_text.await_args.kwargs["prompt"]
    assert DRAFT in prompt
    assert "ART DIRECTION" not in prompt


async def test_the_art_direction_survives_the_rewrite():
    mediagen_patch, asset_patch, _ = _services()

    with mediagen_patch, asset_patch:
        result = await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", DRAFT + ART, frame=FRAME, duration_seconds=3.0
        )

    assert result == REWRITE + ART


async def test_an_echoed_art_direction_block_is_not_doubled():
    # Asked for the action alone, the model returns the block anyway often
    # enough that trusting it would stamp the Look on twice.
    mediagen_patch, asset_patch, _ = _services(reply=REWRITE + ART)

    with mediagen_patch, asset_patch:
        result = await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", DRAFT + ART, frame=FRAME, duration_seconds=3.0
        )

    assert result == REWRITE + ART
    assert result.count("ART DIRECTION") == 1


async def test_the_length_guard_measures_action_against_action():
    """The block dwarfs the action, so including it hid real rewrites.

    Both fallbacks in the batch-D run were this: a sound rewrite compared
    against a draft two thirds of which was machine direction.
    """
    mediagen_patch, asset_patch, _ = _services(reply=REWRITE)

    with mediagen_patch, asset_patch:
        result = await frame_reconciliation.reconcile_action_with_frame(
            "ws-1", DRAFT + ART * 6, frame=FRAME, duration_seconds=3.0
        )

    assert result.startswith(REWRITE), "a sound rewrite must not be discarded"
