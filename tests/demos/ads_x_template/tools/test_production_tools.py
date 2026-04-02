import pytest
from unittest.mock import MagicMock


def test_recommend_production_recipe_social_native():
    from demos.backend.ads_x_template.tools.storyboard.production_tools import (
        recommend_production_recipe,
    )

    result = recommend_production_recipe(vertical="Social Native")

    assert result["style_mode"] == "SOCIAL_NATIVE"
    assert "character" in result
    assert "environment" in result
    assert "cinematography" in result


def test_recommend_production_recipe_commercial_premium():
    from demos.backend.ads_x_template.tools.storyboard.production_tools import (
        recommend_production_recipe,
    )

    result = recommend_production_recipe(vertical="Consumer Tech")

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    assert "character" in result


def test_recommend_production_recipe_with_theme():
    from demos.backend.ads_x_template.tools.storyboard.production_tools import (
        recommend_production_recipe,
    )

    result = recommend_production_recipe(
        vertical="Consumer Tech", campaign_theme="High Tech Sleek"
    )

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    # Should fall back to "Matched to theme" or specific if keywords match
    assert "character" in result
