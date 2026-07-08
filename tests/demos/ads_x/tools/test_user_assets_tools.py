import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {"workspace_id": "1"}
    return context


@pytest.fixture
def mock_asset_service():
    service = MagicMock()
    service.list_assets = AsyncMock()
    service.get_asset_blob = AsyncMock()
    return service


@pytest.fixture
def mock_media_gen_service():
    service = MagicMock()
    service.generate_text_with_gemini = AsyncMock()
    return service


def test_ingest_assets_generate_virtual_creator(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    from demos.backend.ads_x.tools.user_assets.user_assets_tools import (
        ingest_assets,
    )

    with patch(
        "mediagent_kit.services.aio.get_asset_service", return_value=mock_asset_service
    ):
        with patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ):
            with patch(
                "demos.backend.ads_x.utils.parameters.parameters_model.Parameters.model_validate"
            ) as mock_validate:
                # Removed get_user_id_from_context mock
                mock_media_gen_service.generate_image_with_gemini = AsyncMock()

                # Setup mock parameters
                mock_params = MagicMock()
                mock_params.generate_virtual_creator = True
                mock_params.brief_results.audience.persona = "Tech-savvy youth"
                mock_params.campaign_brief = "New gadget campaign"
                mock_params.target_audience = "Tech-savvy youth"
                mock_validate.return_value = mock_params

                mock_tool_context.state["parameters"] = {"some": "data"}

                # Setup mock assets for ingestion (empty list to focus on virtual creator)
                mock_asset_service.search_assets = AsyncMock(return_value=[])

                # Setup mock for casting text generation
                mock_media_gen_service.generate_text = AsyncMock(
                    return_value="A 25-year-old female, enthusiastic and energetic look."
                )

                # Setup mock for image generation
                mock_creator_asset = MagicMock()
                mock_creator_asset.id = "creator_img_id"
                mock_creator_asset.versions = []
                mock_media_gen_service.generate_image = AsyncMock(
                    return_value=mock_creator_asset
                )

                import asyncio

                result = asyncio.run(ingest_assets(mock_tool_context))

                assert result["status"] == "succeeded"
                mock_media_gen_service.generate_text.assert_called_once()
                mock_media_gen_service.generate_image.assert_called_once()

                from demos.backend.ads_x.utils.common.common_utils import (
                    VIRTUAL_CREATOR_KEY,
                    USER_ASSETS_KEY,
                )

                assert VIRTUAL_CREATOR_KEY in mock_tool_context.state
                metadata = mock_tool_context.state[VIRTUAL_CREATOR_KEY]
                assert "asset_id" not in metadata
                assert metadata["asset_ref"]["id"] == "creator_img_id"
                assert metadata["asset_ref"]["asset_type"] == "generated"

                assert "asset_refs" in mock_tool_context.state
                creator_filename = "virtual_creator_creator_img_id.png"
                assert creator_filename in mock_tool_context.state["asset_refs"]
                assert (
                    mock_tool_context.state["asset_refs"][creator_filename]["id"]
                    == "creator_img_id"
                )

                # Verify key alignment
                assert USER_ASSETS_KEY in mock_tool_context.state
                assert creator_filename in mock_tool_context.state[USER_ASSETS_KEY]


def test_ingest_assets_preserves_existing_state_assets(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    from demos.backend.ads_x.tools.user_assets.user_assets_tools import (
        ingest_assets,
    )
    from demos.backend.ads_x.utils.common.common_utils import USER_ASSETS_KEY

    with patch(
        "mediagent_kit.services.aio.get_asset_service",
        return_value=mock_asset_service,
    ):
        with patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ):
            mock_tool_context.state[USER_ASSETS_KEY] = {
                "download.jpeg": "An image of a mountain car."
            }
            mock_asset_service.search_assets = AsyncMock(return_value=[])

            import asyncio

            result = asyncio.run(ingest_assets(mock_tool_context))

            assert result["status"] == "succeeded"
            assert "download.jpeg" in mock_tool_context.state[USER_ASSETS_KEY]
            assert (
                mock_tool_context.state[USER_ASSETS_KEY]["download.jpeg"]
                == "An image of a mountain car."
            )
