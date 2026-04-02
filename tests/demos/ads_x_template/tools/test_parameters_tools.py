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
    from demos.backend.ads_x_template.tools.parameters.parameters_tools import (
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

            # Setup mock behavior
            mock_asset = MagicMock()
            mock_asset.id = "extraction_asset_id"
            mock_media_gen_service.generate_text_with_gemini.return_value = mock_asset

            mock_blob = MagicMock()
            # Valid JSON matching schema
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
            mock_blob.content = valid_json.encode()
            mock_asset_service.get_asset_blob.return_value = mock_blob

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
    from demos.backend.ads_x_template.tools.parameters.parameters_tools import (
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

            mock_asset = MagicMock()
            mock_media_gen_service.generate_text_with_gemini.return_value = mock_asset

            mock_blob = MagicMock()
            # JSON wrapped in markdown
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
            mock_blob.content = markdown_json.encode()
            mock_asset_service.get_asset_blob.return_value = mock_blob

            import asyncio

            result = asyncio.run(
                extract_campaign_parameters(mock_tool_context, "Test brief content")
            )

            assert result == "Campaign parameters extracted successfully."
            assert (
                mock_tool_context.state["parameters"]["campaign_name"]
                == "Test Campaign Mark"
            )
