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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from demos.backend.ads_x.utils.common import frame_validation
from mediagent_kit.services.types.common import AssetRef

FRAME = AssetRef(id="frame-1", asset_type="generated", workspace_id="ws")
PRODUCT = AssetRef(id="product-1", asset_type="uploaded", workspace_id="ws")
LOGO = AssetRef(id="logo-1", asset_type="uploaded", workspace_id="ws")


def _service_returning(text: str):
    """Wires the mediagen service to return one inspection verdict."""
    mediagen = AsyncMock()
    mediagen.generate_text.return_value = text
    return mediagen, AsyncMock()


def test_product_and_logo_references_are_separated():
    product, logo = frame_validation.product_and_logo_references(
        ["70_stereotypical.png", "70_logo.png"]
    )
    assert product == "70_stereotypical.png"
    assert logo == "70_logo.png"


def test_a_scene_without_a_logo_reports_none():
    product, logo = frame_validation.product_and_logo_references(["46_product.png"])
    assert product == "46_product.png"
    assert logo is None


def test_a_cast_creator_is_not_mistaken_for_the_product():
    product, logo = frame_validation.product_and_logo_references(
        ["virtual_creator_ab12.png", "10_stereotypical.png"]
    )
    assert product == "10_stereotypical.png"
    assert logo is None


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_a_sound_frame_reports_no_faults(mock_mediagen, mock_assets):
    mediagen, assets = _service_returning(
        '{"added_markings": false, "logo_on_product": false, "studio_cutout": false}'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)
    assert faults == []


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_each_fault_is_reported(mock_mediagen, mock_assets):
    mediagen, assets = _service_returning(
        '```json\n{"added_markings": true, "logo_on_product": true, '
        '"studio_cutout": true}\n```'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)
    assert len(faults) == 3
    assert any("marking its reference does not show" in f for f in faults)
    assert any("applied to the product" in f for f in faults)
    assert any("cutout on a plain studio background" in f for f in faults)


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_logo_placement_is_not_judged_without_a_logo(mock_mediagen, mock_assets):
    """A scene carrying no logo cannot have applied one, whatever is reported."""
    mediagen, assets = _service_returning(
        '{"added_markings": false, "logo_on_product": true, "studio_cutout": false}'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT)
    assert faults == []


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_an_unreadable_verdict_keeps_the_frame(mock_mediagen, mock_assets):
    """The frame already exists; an inspection failure must not discard it."""
    mediagen, assets = _service_returning("the model replied in prose")
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)
    assert faults == []


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_an_inspection_error_keeps_the_frame(mock_mediagen, mock_assets):
    mediagen = AsyncMock()
    mediagen.generate_text_with_gemini.side_effect = RuntimeError("no quota")
    mock_mediagen.return_value = mediagen
    mock_assets.return_value = AsyncMock()

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)
    assert faults == []


def test_the_corrective_note_carries_every_fault():
    note = frame_validation.corrective_note(
        [frame_validation.FAULT_ADDED_MARKINGS, frame_validation.FAULT_STUDIO_CUTOUT]
    )
    assert "rejected" in note
    assert note.count("- ") == 2
    assert "change nothing else" in note


# --------------------------------------------------------------------------
# Product plausibility
#
# A product rendered at several times its real size, or floating unsupported,
# is filmed as faithfully as a sound frame would be. The bar is deliberately
# high: a hero close-up is a choice, not a fault, and every rejection costs a
# regeneration.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_an_impossible_product_is_reported(mock_mediagen, mock_assets):
    mediagen, assets = _service_returning(
        '{"added_markings": false, "logo_on_product": false, '
        '"studio_cutout": false, "implausible_product": true}'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)

    assert len(faults) == 1
    assert "size it could not be" in faults[0]
    assert "resting on or attached to something" in faults[0]


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_a_bold_composition_is_not_a_fault(mock_mediagen, mock_assets):
    # The inspector is asked to judge this one generously; an absent key and a
    # false one must both read as sound.
    mediagen, assets = _service_returning(
        '{"added_markings": false, "logo_on_product": false, ' '"studio_cutout": false}'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)

    assert faults == []


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_the_verdict_is_filed_under_its_scene(mock_mediagen, mock_assets):
    # A panel of frame_check files is only readable if each names its scene.
    mediagen, assets = _service_returning('{"added_markings": false}')
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    await frame_validation.inspect_first_frame(
        "ws", FRAME, PRODUCT, LOGO, scene_index=2
    )

    assert mediagen.generate_text.await_args.kwargs["purpose"] == "frame_check_scene_2"


def test_the_inspector_is_told_where_the_bar_sits():
    prompt = " ".join(frame_validation._INSPECTION_PROMPT.split())
    assert "implausible_product" in prompt
    assert "generously" in prompt, "a tight bar here spends regenerations"
    assert "hero close-up" in prompt, "name what is not a fault"


# --------------------------------------------------------------------------
# Markings, in both directions
#
# The check began as a one-way ratchet: it reported markings the reference did
# not have, and its remedy said to remove text. A wordmark rendered slightly
# imperfectly read as "added", and the regeneration stripped the branding, so
# a Dior bottle came back blank.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
@patch("mediagent_kit.services.aio.get_media_generation_service")
async def test_a_blank_product_is_reported(mock_mediagen, mock_assets):
    mediagen, assets = _service_returning(
        '{"added_markings": false, "missing_markings": true, '
        '"logo_on_product": false, "studio_cutout": false}'
    )
    mock_mediagen.return_value, mock_assets.return_value = mediagen, assets

    faults = await frame_validation.inspect_first_frame("ws", FRAME, PRODUCT, LOGO)

    assert len(faults) == 1
    assert "missing branding" in faults[0]


def test_removing_a_stray_marking_does_not_mean_removing_all_text():
    note = frame_validation.corrective_note([frame_validation.FAULT_ADDED_MARKINGS])

    assert "Remove only that marking" in note
    assert "stays exactly as it has it" in note


def test_the_inspector_separates_absent_from_badly_drawn():
    prompt = " ".join(frame_validation._INSPECTION_PROMPT.split())

    assert "missing_markings" in prompt
    # The false positive that stripped a real wordmark.
    assert "NOT about how well an existing marking is drawn" in prompt
    assert "rendered imperfectly" in prompt
