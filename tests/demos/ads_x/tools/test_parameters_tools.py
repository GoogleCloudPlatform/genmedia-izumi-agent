import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch

# We need to mock mediagent_kit before importing tools if they do side effects,
# but here side effects are inside functions.


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
    return context


@pytest.fixture
def mock_media_gen_service():
    service = MagicMock()
    service.generate_text_with_gemini = AsyncMock()
    return service


@pytest.fixture
def mock_asset_service():
    service = MagicMock()
    service.get_asset_blob = AsyncMock()
    return service


def test_extract_campaign_parameters_success(
    mock_tool_context, mock_media_gen_service, mock_asset_service
):
    from demos.backend.ads_x.tools.parameters.parameters_tools import (
        extract_campaign_parameters,
    )

    # Mock services
    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_media_gen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):

            valid_json = json.dumps(
                {
                    "campaign_brief": "Test campaign brief content",
                    "campaign_name": "Test Campaign",
                    "campaign_theme": "Test Theme",
                    "brand_name": "Test Brand",
                    "objective": "Test Objective",
                    "target_audience": "Test Audience",
                    "narrative_arc": "Test Arc",
                    "scenes": [],
                }
            )
            mock_media_gen_service.generate_text = AsyncMock(return_value=valid_json)

            # Call tool
            import asyncio

            result = asyncio.run(
                extract_campaign_parameters(mock_tool_context, "Test brief content")
            )

            assert result == "Campaign parameters extracted successfully."
            assert "parameters" in mock_tool_context.state
            assert (
                mock_tool_context.state["parameters"]["campaign_name"]
                == "Test Campaign"
            )


def test_extract_campaign_parameters_json_cleaning(
    mock_tool_context, mock_media_gen_service, mock_asset_service
):
    from demos.backend.ads_x.tools.parameters.parameters_tools import (
        extract_campaign_parameters,
    )

    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_media_gen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):

            markdown_json = (
                "```json\n"
                + json.dumps(
                    {
                        "campaign_brief": "Test campaign brief content",
                        "campaign_name": "Test Campaign Mark",
                        "campaign_theme": "Test Theme",
                        "brand_name": "Test Brand",
                        "objective": "Test Objective",
                        "target_audience": "Test Audience",
                        "narrative_arc": "Test Arc",
                        "scenes": [],
                    }
                )
                + "\n```"
            )
            mock_media_gen_service.generate_text = AsyncMock(return_value=markdown_json)

            import asyncio

            result = asyncio.run(
                extract_campaign_parameters(mock_tool_context, "Test brief content")
            )

            assert result == "Campaign parameters extracted successfully."
            assert (
                mock_tool_context.state["parameters"]["campaign_name"]
                == "Test Campaign Mark"
            )


def test_extract_campaign_parameters_fallback_defaults_to_custom(
    mock_tool_context, mock_media_gen_service, mock_asset_service
):
    """When both the primary extraction and the repair turn fail, the
    intelligent fallback MUST default template_name to 'Custom' (creative /
    AI Director mode) rather than forcing a specific template.

    Regression test for the bug where a creative brief was silently routed
    into templated mode in Creative Studio because the fallback called
    suggest_template() (which never returns 'Custom').
    """
    from demos.backend.ads_x.tools.parameters.parameters_tools import (
        extract_campaign_parameters,
    )

    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_media_gen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):
            # Both the primary extract and the repair turn return unparseable
            # output -> force the fallback path.
            mock_media_gen_service.generate_text = AsyncMock(
                return_value="not valid json at all"
            )

            import asyncio

            result = asyncio.run(
                extract_campaign_parameters(
                    mock_tool_context,
                    # A generic creative brief that names no template.
                    "Make a cinematic 15s ad for a coffee brand",
                )
            )

            assert "Robust Mode" in result
            params = mock_tool_context.state["parameters"]
            assert params["template_name"] == "Custom", (
                "fallback must default to Custom (creative), not a forced "
                f"template; got {params['template_name']!r}"
            )


def test_extract_campaign_parameters_fallback_honors_named_template(
    mock_tool_context, mock_media_gen_service, mock_asset_service
):
    """If the user explicitly names a template in the brief, the fallback
    may still honor it (literal match) -- only the auto-suggestion is
    removed."""
    from demos.backend.ads_x.tools.parameters.parameters_tools import (
        extract_campaign_parameters,
    )

    with patch(
        "mediagent_kit.services.aio.get_media_generation_service",
        return_value=mock_media_gen_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ):
            mock_media_gen_service.generate_text = AsyncMock(
                return_value="not valid json at all"
            )

            import asyncio

            # Brief literally names the "Pet Companion" template.
            result = asyncio.run(
                extract_campaign_parameters(
                    mock_tool_context,
                    "Use the Pet Companion template for my dog food ad",
                )
            )

            assert "Robust Mode" in result
            assert (
                mock_tool_context.state["parameters"]["template_name"]
                == "Pet Companion"
            )
