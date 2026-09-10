import asyncio
from unittest.mock import patch, AsyncMock


def _run_recipe(**kwargs):
    """Runs the async recipe tool, forcing the deterministic tag-scoring
    fallback so the test never makes a live LLM call for Look selection."""
    from demos.backend.ads_x.tools.storyboard.production_tools import (
        recommend_production_recipe,
    )

    with patch("mediagent_kit.services.aio.get_media_generation_service") as mock_svc:
        mock_svc.return_value.generate_text = AsyncMock(side_effect=Exception("no llm"))
        return asyncio.run(recommend_production_recipe(**kwargs))


def test_recommend_production_recipe_social_native():
    result = _run_recipe(vertical="Social Native")

    assert result["style_mode"] == "SOCIAL_NATIVE"
    assert "cinematography" in result
    # Staging is asked for rather than supplied, so a campaign does not
    # inherit another campaign's setting.
    assert "environment" not in result
    assert "environment" in result["decide_for_this_campaign"]


def test_recommend_production_recipe_commercial_premium():
    result = _run_recipe(vertical="Consumer Tech")

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    assert result["brand_archetype"]


def test_recommend_production_recipe_with_theme():
    result = _run_recipe(vertical="Consumer Tech", campaign_theme="High Tech Sleek")

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    # Should fall back to "Matched to theme" or specific if keywords match
    assert result["look_name"]


def test_a_product_only_campaign_is_not_shown_a_cast():
    """A described cast reaches the storyboard and gets written into scenes.

    The art-direction block already omits it when nobody is on screen; the
    recipe the storyboard reads did not, which put a person into product-only
    ads.
    """
    result = _run_recipe(vertical="Consumer Tech")

    assert "character" not in result
    assert "product_mode" not in result


def test_a_reused_look_is_withheld_the_same_way():
    """The Look is chosen once per session and reused afterwards.

    The cached copy is the full recipe, so returning it directly handed the
    storyboard the staging values the first call had withheld.
    """
    from unittest.mock import MagicMock

    from demos.backend.ads_x.tools.storyboard.production_tools import (
        select_recipe_for_campaign,
    )

    ctx = MagicMock()
    ctx.state = {
        "master_production_recipe": {
            "look_name": "Clean Tech Minimalism",
            "style_mode": "COMMERCIAL_PREMIUM",
            "character": {"actor_vibe": "Tech-Visionary"},
            "environment": {"spatial_context": "Hyper-Modern Lab"},
            "cinematography": {"optics": "70mm IMAX", "movement": "Circular Orbit"},
            "sonic_landscape": "Industrial Minimalist",
        }
    }

    result = asyncio.run(select_recipe_for_campaign(ctx, "Consumer Tech"))

    assert result["look_name"] == "Clean Tech Minimalism"
    assert result["cinematography"] == {"optics": "70mm IMAX"}
    assert "environment" not in result
    assert "sonic_landscape" not in result
    assert "character" not in result
    assert "decide_for_this_campaign" in result
