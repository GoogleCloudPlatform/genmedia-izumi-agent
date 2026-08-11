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

    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ),
        patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ),
        patch(
            "demos.backend.ads_x.utils.parameters.parameters_model.Parameters.model_validate"
        ) as mock_validate,
        # Isolate casting from Look selection (covered by test_production_tools);
        # this keeps generate_text to the single casting/demographics call.
        patch(
            "demos.backend.ads_x.tools.storyboard.production_tools."
            "select_recipe_for_campaign",
            new_callable=AsyncMock,
            return_value={
                "character": {
                    "actor_vibe": "Test Vibe",
                    "attire": "Test Attire",
                    "grooming": "Test Grooming",
                }
            },
        ),
    ):
        mock_media_gen_service.generate_image_with_gemini = AsyncMock()

        # Setup mock parameters
        mock_params = MagicMock()
        mock_params.generate_virtual_creator = True
        mock_params.creator_description = ""
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


def _run_casting_capture_prompt(
    mock_tool_context, mock_asset_service, mock_media_gen_service, creator_description
):
    """Runs ingest_assets with a virtual creator and returns the casting prompt
    passed to generate_text. select_recipe_for_campaign is mocked with distinct
    markers so we can deterministically assert what the Look contributes."""
    from demos.backend.ads_x.tools.user_assets.user_assets_tools import (
        ingest_assets,
    )

    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service,
        ),
        patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=mock_media_gen_service,
        ),
        patch(
            "demos.backend.ads_x.utils.parameters.parameters_model.Parameters.model_validate"
        ) as mock_validate,
        patch(
            "demos.backend.ads_x.tools.storyboard.production_tools."
            "select_recipe_for_campaign",
            new_callable=AsyncMock,
            return_value={
                "character": {
                    "actor_vibe": "PERSONA_MARKER",
                    "attire": "ATTIRE_MARKER",
                    "grooming": "GROOMING_MARKER",
                }
            },
        ),
    ):
        mock_params = MagicMock()
        mock_params.generate_virtual_creator = True
        mock_params.creator_description = creator_description
        mock_params.campaign_name = "BRAND_MARKER"
        mock_params.campaign_tone = "Sophisticated"
        mock_params.campaign_brief = "Premium product brief"
        mock_params.brief_results.audience.persona = "gourmet lovers"
        mock_params.target_audience = "gourmet lovers"
        mock_validate.return_value = mock_params

        mock_tool_context.state["parameters"] = {"some": "data"}
        mock_asset_service.search_assets = AsyncMock(return_value=[])
        mock_media_gen_service.generate_text = AsyncMock(
            return_value="A 45-year-old male, refined and approachable."
        )
        creator_asset = MagicMock()
        creator_asset.id = "cid"
        creator_asset.versions = []
        mock_media_gen_service.generate_image = AsyncMock(return_value=creator_asset)

        import asyncio

        result = asyncio.run(ingest_assets(mock_tool_context))
        assert result["status"] == "succeeded"
        return mock_media_gen_service.generate_text.call_args.kwargs["prompt"]


def test_casting_prompt_uses_look_wardrobe_not_persona(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    """A: the Look contributes wardrobe/grooming as styling but NOT its persona
    (actor_vibe); with no user description the identity is brand-driven."""
    prompt = _run_casting_capture_prompt(
        mock_tool_context, mock_asset_service, mock_media_gen_service, ""
    )
    assert "ATTIRE_MARKER" in prompt
    assert "GROOMING_MARKER" in prompt
    assert "PERSONA_MARKER" not in prompt  # Look persona must NOT leak in
    assert "brand-appropriate" in prompt.lower()
    assert "BRAND_MARKER" in prompt  # identity anchored to the brand


def test_casting_prompt_respects_explicit_user_description(
    mock_tool_context, mock_asset_service, mock_media_gen_service
):
    """#2 precedence: an explicit user description is marked authoritative and
    passed through verbatim."""
    desc = "a 50-year-old bald man with a grey beard and glasses"
    prompt = _run_casting_capture_prompt(
        mock_tool_context, mock_asset_service, mock_media_gen_service, desc
    )
    assert desc in prompt
    assert "authoritative" in prompt.lower()
