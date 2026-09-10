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

"""Validates the Look library against the way it is consumed.

A malformed Look degrades output without raising. Styling that assumes a
subject reaches a product-only campaign and directs the renderer towards a
face that is not in frame, and a reviewer-editable field with no options
behind it presents an empty control.
"""

import re

import pytest

from demos.backend.ads_x.tools.storyboard.look_tools import (
    _EDITABLE,
    _options_for,
)
from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
    _build_art_direction_block,
)
from demos.backend.ads_x.utils.storyboard.production_presets import (
    PRODUCTION_ENCYCLOPEDIA,
    PRODUCTION_LOOKS,
)

# Wording that only makes sense with someone on screen. "Butterfly lighting"
# is a portrait technique, a catchlight is a reflection in an eye, and nothing
# in a product-only ad sweats or addresses the camera.
NEEDS_A_PERSON = re.compile(
    r"butterfly lighting|catchlight|beauty lighting|flattering|sweat|"
    r"direct-to-camera|no-makeup|makeup|complexion|skin",
    re.IGNORECASE,
)

RECIPE_AXES = (
    "style_mode",
    "brand_archetype",
    "character",
    "environment",
    "cinematography",
    "illumination",
    "sonic_landscape",
)


@pytest.mark.parametrize("look", PRODUCTION_LOOKS, ids=lambda lk: lk["name"])
def test_a_look_carries_every_axis_the_recipe_is_read_for(look):
    missing = [axis for axis in RECIPE_AXES if axis not in look["recipe"]]
    assert not missing, f"{look['name']} is missing {missing}"


@pytest.mark.parametrize("look", PRODUCTION_LOOKS, ids=lambda lk: lk["name"])
def test_a_product_only_ad_is_never_directed_at_a_person(look):
    """The real invariant: what reaches the prompt, not what the data holds.

    ``product_mode`` exists to substitute person-oriented styling. Suppressing
    the Cast block alone is not enough, because the general styling carries the
    same wording.
    """
    block = _build_art_direction_block(look["recipe"], include_character=False)
    found = NEEDS_A_PERSON.findall(block)
    assert not found, (
        f"{look['name']} directs a product-only ad with {sorted(set(found))}. "
        "Add a product_mode substitute for the offending styling."
    )


@pytest.mark.parametrize("style_mode", sorted(PRODUCTION_ENCYCLOPEDIA))
def test_every_editable_field_has_options_behind_it(style_mode):
    """set_look offers these fields; an empty menu is a dead control."""
    empty = [f for f in _EDITABLE if not _options_for(f, style_mode)]
    assert not empty, f"{style_mode} offers no options for {empty}"


# --------------------------------------------------------------------------
# Adaptable staging
#
# A Look fixes how a campaign is shot. Applied whole, it also fixes where:
# three unrelated products in one Look opened in the same room, with the same
# camera move and the same score.
# --------------------------------------------------------------------------


def test_the_adaptable_fields_are_staging_not_identity():
    from demos.backend.ads_x.tools.storyboard.production_tools import (
        ADAPTABLE_FIELDS,
    )

    assert set(ADAPTABLE_FIELDS) == {
        "environment",
        "cinematography.movement",
        "cinematography.motion_texture",
        "illumination.key_lighting",
        "sonic_landscape",
    }


def test_every_look_carries_the_fields_that_define_it():
    from demos.backend.ads_x.utils.storyboard import production_presets

    for look in production_presets.PRODUCTION_LOOKS:
        recipe = look["recipe"]
        assert recipe.get("style_mode"), f"{look['name']} has no mode"
        assert recipe.get("illumination"), f"{look['name']} has no lighting"
        assert recipe.get("cinematography", {}).get(
            "optics"
        ), f"{look['name']} has no optics"


def test_the_storyboard_is_told_which_half_to_reinterpret():
    import inspect

    from demos.backend.ads_x.instructions.storyboard import storyboard_instruction

    text = " ".join(
        inspect.getsource(storyboard_instruction.get_ai_director_instruction).split()
    )
    # Identity is appended as a block; restating it made every scene of every
    # campaign open with the same sentence.
    assert "Do NOT restate the identity in your descriptions" in text
    assert "Answer `decide_for_this_campaign`" in text
    assert "they do not share a room" in text


def test_the_art_direction_block_carries_identity_only():
    """A lighting setup and a lens technique are per-scene choices.

    product_mode already substitutes key_lighting and optics for product-only
    campaigns, so neither was ever a fixed property of the Look.
    """
    from demos.backend.ads_x.tools.storyboard import storyboard_repair_tools

    block = storyboard_repair_tools._build_art_direction_block(  # noqa: SLF001
        {
            "style_mode": "COMMERCIAL_PREMIUM",
            "brand_archetype": "Monochrome whites",
            "illumination": {"vibe": "High-Key", "key_lighting": "Butterfly"},
            "cinematography": {"optics": "70mm IMAX", "motion_texture": "Probe Lens"},
        },
        include_character=False,
    )

    assert "Mode:" in block and "Aesthetic:" in block
    assert "Lighting: High-Key" in block and "Optics: 70mm IMAX" in block
    assert "Key Light" not in block
    assert "Texture" not in block
