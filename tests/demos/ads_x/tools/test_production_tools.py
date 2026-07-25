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
    assert "character" in result
    assert "environment" in result
    assert "cinematography" in result


def test_recommend_production_recipe_commercial_premium():
    result = _run_recipe(vertical="Consumer Tech")

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    assert "character" in result


def test_recommend_production_recipe_with_theme():
    result = _run_recipe(vertical="Consumer Tech", campaign_theme="High Tech Sleek")

    assert result["style_mode"] == "COMMERCIAL_PREMIUM"
    # Should fall back to "Matched to theme" or specific if keywords match
    assert "character" in result
