import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json


@pytest.fixture
def mock_tool_context():
    context = MagicMock()
    context.state = {}
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


def test_ingest_assets_existing_descriptions(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    from demos.backend.ads_x_template.tools.user_assets.user_assets_tools import (
        ingest_assets,
    )

    with patch(
        "mediagent_kit.services.aio.get_asset_service", return_value=mock_asset_service
    ):
        with patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ):

            # Setup mock assets
            asset_image = MagicMock()
            asset_image.file_name = "user_upload/image1.jpg"
            asset_image.mime_type = "image/jpeg"
            asset_image.id = "img_id_1"

            asset_desc = MagicMock()
            asset_desc.file_name = "user_upload/image1_description.txt"
            asset_desc.mime_type = "text/plain"
            asset_desc.id = "desc_id_1"

            mock_asset_service.list_assets.return_value = [asset_image, asset_desc]

            mock_blob = MagicMock()
            mock_blob.content = b"Existing description of image 1"
            mock_asset_service.get_asset_blob.return_value = mock_blob

            import asyncio

            result = asyncio.run(ingest_assets(mock_tool_context))

            assert result["status"] == "succeeded"
            from demos.backend.ads_x_template.utils.common.common_utils import (
                USER_ASSETS_KEY,
            )

            assert "user_upload/image1.jpg" in mock_tool_context.state[USER_ASSETS_KEY]
            assert (
                mock_tool_context.state[USER_ASSETS_KEY]["user_upload/image1.jpg"]
                == "Existing description of image 1"
            )
            mock_media_gen_service.generate_text_with_gemini.assert_not_called()


def test_ingest_assets_generate_descriptions(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    from demos.backend.ads_x_template.tools.user_assets.user_assets_tools import (
        ingest_assets,
    )

    with patch(
        "mediagent_kit.services.aio.get_asset_service", return_value=mock_asset_service
    ):
        with patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ):

            asset_image = MagicMock()
            asset_image.file_name = "user_upload/image2.jpg"
            asset_image.mime_type = "image/jpeg"
            asset_image.id = "img_id_2"

            mock_asset_service.list_assets.return_value = [asset_image]

            mock_generated_asset = MagicMock()
            mock_generated_asset.id = "generated_desc_id"
            mock_media_gen_service.generate_text_with_gemini.return_value = (
                mock_generated_asset
            )

            mock_blob = MagicMock()
            mock_blob.content = b"Generated description of image 2"
            mock_asset_service.get_asset_blob.return_value = mock_blob

            import asyncio

            result = asyncio.run(ingest_assets(mock_tool_context))

            assert result["status"] == "succeeded"
            mock_media_gen_service.generate_text_with_gemini.assert_called_once()
            from demos.backend.ads_x_template.utils.common.common_utils import (
                USER_ASSETS_KEY,
            )

            assert "user_upload/image2.jpg" in mock_tool_context.state[USER_ASSETS_KEY]


def test_ingest_assets_generate_virtual_creator(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    from demos.backend.ads_x_template.tools.user_assets.user_assets_tools import (
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
                "demos.backend.ads_x_template.utils.parameters.parameters_model.Parameters.model_validate"
            ) as mock_validate:
                with patch(
                    "demos.backend.ads_x_template.tools.user_assets.user_assets_tools.get_user_id_from_context",
                    return_value="test_user",
                ):

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
                    mock_asset_service.list_assets.return_value = []

                    # Setup mock for casting text generation
                    mock_casting_asset = MagicMock()
                    mock_casting_asset.id = "casting_desc_id"
                    mock_media_gen_service.generate_text_with_gemini.return_value = (
                        mock_casting_asset
                    )

                    mock_casting_blob = MagicMock()
                    mock_casting_blob.content = (
                        b"A 25-year-old female, enthusiastic and energetic look."
                    )
                    mock_asset_service.get_asset_blob.return_value = mock_casting_blob

                    # Setup mock for image generation
                    mock_creator_asset = MagicMock()
                    mock_creator_asset.id = "creator_img_id"
                    mock_creator_asset.versions = []
                    mock_media_gen_service.generate_image_with_gemini.return_value = (
                        mock_creator_asset
                    )

                    import asyncio

                    result = asyncio.run(ingest_assets(mock_tool_context))

                    assert result["status"] == "succeeded"
                    mock_media_gen_service.generate_text_with_gemini.assert_called_once()
                    mock_media_gen_service.generate_image_with_gemini.assert_called_once()

                    from demos.backend.ads_x_template.utils.common.common_utils import (
                        VIRTUAL_CREATOR_KEY,
                    )

                    assert VIRTUAL_CREATOR_KEY in mock_tool_context.state
