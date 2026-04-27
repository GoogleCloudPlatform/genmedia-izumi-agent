import pytest
from unittest.mock import MagicMock
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
    return context


def test_map_strategy_to_metadata_custom(mock_tool_context):
    from demos.backend.ads_x.tools.strategy.strategy_tools import (
        map_strategy_to_metadata,
    )
    from demos.backend.ads_x.utils.common.common_utils import PARAMETERS_KEY

    # Setup state with Parameters
    mock_tool_context.state[PARAMETERS_KEY] = {
        "campaign_brief": "Test campaign brief",
        "campaign_name": "Test Campaign",
        "template_name": "Custom",
        "campaign_theme": "Modern Theme",
        "campaign_tone": "Energetic",
        "global_visual_style": "Cinematic",
        "global_setting": "Studio",
        "key_message": "Buy this now!",
        "target_audience": "Tech Enthusiasts",
    }

    result = map_strategy_to_metadata(mock_tool_context)

    assert "Strategy context synchronized" in result
    assert "forced_metadata" in mock_tool_context.state
    metadata = mock_tool_context.state["forced_metadata"]
    assert metadata["campaign_title"] == "Test Campaign"
    assert metadata["campaign_theme"] == "Modern Theme"


def test_map_strategy_to_metadata_sanitize(mock_tool_context):
    from demos.backend.ads_x.tools.strategy.strategy_tools import (
        map_strategy_to_metadata,
    )
    from demos.backend.ads_x.utils.common.common_utils import PARAMETERS_KEY

    # Setup state with Parameters and template != Custom
    mock_tool_context.state[PARAMETERS_KEY] = {
        "campaign_brief": "Test campaign brief",
        "campaign_name": "Test Campaign",
        "template_name": "Product Showcase",  # Should trigger sanitization
        "storyline_guidance": {"narrative_arc": "test arc", "scenes": []},
    }

    result = map_strategy_to_metadata(mock_tool_context)

    assert "sanitized" in result
    assert "storyline_guidance" not in mock_tool_context.state[PARAMETERS_KEY]


def test_map_strategy_to_metadata_no_params(mock_tool_context):
    from demos.backend.ads_x.tools.strategy.strategy_tools import (
        map_strategy_to_metadata,
    )

    result = map_strategy_to_metadata(mock_tool_context)

    assert "No parameters found" in result
