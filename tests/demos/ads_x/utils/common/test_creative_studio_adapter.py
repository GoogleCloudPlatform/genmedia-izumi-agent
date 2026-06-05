import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from google.adk.tools.tool_context import ToolContext
import os

from ads_x.utils.common.creative_studio_adapter import (
    CreativeStudioAdapter,
    with_creative_studio_adapter,
    get_active_adapter,
)
from ads_x.utils.common import common_utils


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {
        "user_id": "test-user",
        "workspace_id": "workspace-123",
        "user_auth_token": "auth-token-xyz",
        common_utils.PARAMETERS_KEY: {
            "template_name": "Custom",
            "session_id": "session-456",
        }
    }
    return context


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
async def test_decorator_binds_active_adapter(mock_factory_cls, mock_tool_context):
    # Force standard config
    mock_config = MagicMock()
    mock_config.use_creative_studio = False
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    @with_creative_studio_adapter
    async def dummy_tool(tool_context):
        adapter = get_active_adapter()
        assert adapter is not None
        assert adapter.tool_context == tool_context
        return "ok"

    res = await dummy_tool(mock_tool_context)
    assert res == "ok"
    assert get_active_adapter() is None


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
async def test_decorator_auto_saves_on_changes(mock_factory_cls, mock_tool_context):
    # Enable Creative Studio
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    # Initial state with storyboard
    mock_tool_context.state[common_utils.STORYBOARD_KEY] = {"campaign_title": "Initial"}

    @with_creative_studio_adapter
    async def mutating_tool(tool_context):
        # Mutate the storyboard inside the tool
        tool_context.state[common_utils.STORYBOARD_KEY]["campaign_title"] = "Mutated"
        return "done"

    with patch.object(CreativeStudioAdapter, "save_storyboard", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "storyboard-id-999"
        
        res = await mutating_tool(mock_tool_context)
        assert res == "done"
        
        # Ensure auto-save was triggered
        mock_save.assert_called_once_with(
            {"campaign_title": "Mutated"},
            mock_tool_context.state[common_utils.PARAMETERS_KEY]
        )
        assert mock_tool_context.state["current_storyboard_id"] == "storyboard-id-999"
        assert mock_tool_context.state[common_utils.PARAMETERS_KEY]["storyboard_id"] == "storyboard-id-999"


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
async def test_decorator_does_not_save_if_no_changes(mock_factory_cls, mock_tool_context):
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    mock_tool_context.state[common_utils.STORYBOARD_KEY] = {"campaign_title": "No Change"}

    @with_creative_studio_adapter
    async def non_mutating_tool(tool_context):
        return "no-op"

    with patch.object(CreativeStudioAdapter, "save_storyboard", new_callable=AsyncMock) as mock_save:
        res = await non_mutating_tool(mock_tool_context)
        assert res == "no-op"
        mock_save.assert_not_called()


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
@patch("ads_x.utils.common.creative_studio_adapter.httpx.AsyncClient")
async def test_save_storyboard_post_and_put(mock_client_cls, mock_factory_cls, mock_tool_context):
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    # Mock HTTP client
    mock_client = MagicMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    # POST returns created storyboard ID
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"id": "storyboard-id-888"}
    mock_client.post = AsyncMock(return_value=mock_post_resp)

    # PUT returns success
    mock_put_resp = MagicMock()
    mock_client.put = AsyncMock(return_value=mock_put_resp)

    adapter = CreativeStudioAdapter(mock_tool_context)
    storyboard_dict = {"background_music_prompt": {"description": "Ambient score"}, "scenes": []}
    
    storyboard_id = await adapter.save_storyboard(storyboard_dict, mock_tool_context.state[common_utils.PARAMETERS_KEY])
    
    assert storyboard_id == "storyboard-id-888"
    mock_client.post.assert_called_once()
    mock_client.put.assert_called_once()


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
@patch("ads_x.utils.common.creative_studio_adapter.httpx.AsyncClient")
async def test_get_storyboard_queries_and_maps(mock_client_cls, mock_factory_cls, mock_tool_context):
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    # Mock HTTP client
    mock_client = MagicMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": "storyboard-id-777",
        "template_name": "Custom",
        "bg_music_description": "Upbeat music",
        "bg_music_asset_id": "music-asset-123",
        "scenes": [
            {
                "topic": "Intro",
                "duration_seconds": 4.0,
                "first_frame_media_item_id": "frame-123",
                "first_frame_description": "Visual description",
                "first_frame_generated_url": "https://...",
                "video_description": "Motion description",
                "video_duration_seconds": 4.0,
                "voiceover_text": "Script text",
                "voiceover_gender": "female",
                "voiceover_description": "Happy speak",
                "transition_type": "fade",
                "transition_duration": 0.5,
                "audio_ambient_description": "birds chirping",
                "audio_sfx_description": "whoosh",
            }
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_resp)

    adapter = CreativeStudioAdapter(mock_tool_context)
    res = await adapter.get_storyboard("storyboard-id-777")
    
    assert res["template_name"] == "Custom"
    assert res["bg_music_asset_id"] == "music-asset-123"
    assert len(res["scenes"]) == 1
    assert res["scenes"][0]["topic"] == "Intro"
    assert res["scenes"][0]["first_frame_prompt"]["assets"][0] == "asset://frame-123"
    assert res["scenes"][0]["voiceover_prompt"]["gender"] == "female"


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
async def test_transient_text_generation_and_blob_retrieval(mock_factory_cls, mock_tool_context):
    mock_config = MagicMock()
    mock_config.use_creative_studio = True
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    adapter = CreativeStudioAdapter(mock_tool_context)

    # Mock the media generation service
    mock_mediagen = MagicMock()
    mock_asset = MagicMock()
    mock_asset.id = "test-text-asset-id"
    mock_asset.file_name = "test_transient.txt"
    mock_asset.mime_type = "text/plain"
    mock_asset._content = b"Hello in-memory world"
    
    mock_mediagen.generate_text_with_gemini = AsyncMock(return_value=mock_asset)
    adapter._mediagen_service_inst = mock_mediagen
    
    # 1. Generate text asset
    asset = await adapter.generate_text_with_gemini(
        file_name="test_transient.txt",
        prompt="Say hello",
    )
    assert asset.id == "test-text-asset-id"
    assert asset._content == b"Hello in-memory world"

    # 2. Retrieve transient blob in-memory
    blob = await adapter.get_asset_blob(asset.id)
    assert blob.content == b"Hello in-memory world"
    assert blob.file_name == "test_transient.txt"
    assert blob.mime_type == "text/plain"


@pytest.mark.asyncio
@patch("ads_x.utils.common.creative_studio_adapter._get_service_factory")
async def test_decorator_generic_arguments_resolution(mock_factory_cls, mock_tool_context):
    # Force standard config
    mock_config = MagicMock()
    mock_config.use_creative_studio = False
    
    mock_factory = MagicMock()
    mock_factory.get_config.return_value = mock_config
    mock_factory_cls.return_value = mock_factory

    @with_creative_studio_adapter
    async def my_callback(llm_request, callback_context):
        adapter = get_active_adapter()
        assert adapter is not None
        assert adapter.tool_context == callback_context
        return "ok"

    # Call with keyword arguments only (as ADK does for before_model callbacks)
    res = await my_callback(llm_request="some-req", callback_context=mock_tool_context)
    assert res == "ok"
    assert get_active_adapter() is None

