"""Product-only ads must not inherit person-oriented art direction.

Suppressing the Cast/Wardrobe/Grooming block is not sufficient: a few Looks
carry person-oriented wording in their *general* styling too, which then asks
the renderer to flatter a face that is not in the shot.
"""

import re

import pytest

from demos.backend.ads_x.tools.storyboard.storyboard_repair_tools import (
    _build_art_direction_block,
)
from demos.backend.ads_x.utils.storyboard.production_presets import PRODUCTION_LOOKS

# Words that only make sense when a person is on screen.
PERSON_LANGUAGE = re.compile(
    r"\b(skin|makeup|make-up|portrait|faces?|facial|hair|complexion|smile)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("look", PRODUCTION_LOOKS, ids=lambda l: l["name"])
def test_no_look_injects_person_language_into_a_product_only_ad(look):
    block = _build_art_direction_block(look["recipe"], include_character=False)
    found = PERSON_LANGUAGE.findall(block)
    assert not found, f"{look['name']} leaks {found} into a product-only ad:\n{block}"


@pytest.mark.parametrize("look", PRODUCTION_LOOKS, ids=lambda l: l["name"])
def test_every_look_still_produces_usable_direction(look):
    block = _build_art_direction_block(look["recipe"], include_character=False)
    assert "Mode:" in block and "Optics:" in block and "Lighting:" in block


def _look(name):
    return next(l for l in PRODUCTION_LOOKS if l["name"] == name)


def test_character_ads_keep_the_original_portrait_direction():
    # The substitution is for product-only ads; a cast ad still wants portrait
    # optics and the Look's own styling.
    block = _build_art_direction_block(
        _look("Organic Wellness")["recipe"], include_character=True
    )
    assert "Portrait Prime" in block
    assert "no-makeup" in block
    assert "Cast:" in block


def test_product_mode_substitutes_optics_and_aesthetic():
    block = _build_art_direction_block(
        _look("Organic Wellness")["recipe"], include_character=False
    )
    assert "Macro Prime" in block
    assert "natural matte finishes" in block
    assert "Cast:" not in block


def test_looks_without_overrides_are_unchanged():
    look = _look("Vibrant CPG Pop")
    assert "product_mode" not in look["recipe"], "fixture assumption"
    block = _build_art_direction_block(look["recipe"], include_character=False)
    assert look["recipe"]["cinematography"]["optics"] in block
