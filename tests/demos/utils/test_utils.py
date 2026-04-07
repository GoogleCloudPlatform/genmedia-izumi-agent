import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from utils.typing import Feedback
from utils.tracing import CloudTraceLoggingSpanExporter
from utils.adk import get_user_id_from_context, get_session_id_from_context


def test_feedback_model():
    f = Feedback(score=5, invocation_id="123")
    assert f.score == 5
    assert f.invocation_id == "123"
    assert f.log_type == "feedback"
    assert f.service_name == "agents"
    assert f.user_id == ""

    with pytest.raises(ValidationError):
        Feedback(score="not a number", invocation_id="123")


@patch("utils.tracing.CloudTraceSpanExporter")
def test_cloud_trace_logging_span_exporter_init(mock_base_exporter_cls):
    with patch("utils.tracing.storage.Client") as mock_storage_client_cls:
        mock_storage_client = MagicMock()
        mock_storage_client_cls.return_value = mock_storage_client

        exporter = CloudTraceLoggingSpanExporter()
        assert exporter.storage_client == mock_storage_client


@patch("utils.tracing.CloudTraceSpanExporter.export")
def test_exporter_export_small_payload(mock_super_export):
    with patch("utils.tracing.storage.Client") as mock_storage_client_cls:
        mock_storage_client = MagicMock()
        mock_storage_client_cls.return_value = mock_storage_client

        exporter = CloudTraceLoggingSpanExporter()
        exporter.project_id = "test-project"

        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 123
        mock_span_context.span_id = 456
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.to_json.return_value = '{"attributes": {"small": "value"}}'

        with patch.object(exporter, "logger") as mock_logger:
            exporter.export([mock_span])

            assert mock_logger.info.call_count == 1
            mock_super_export.assert_called_once()


def test_get_user_id_from_context_success():
    mock_context = MagicMock()
    mock_context._invocation_context.session.user_id = "user_1"
    assert get_user_id_from_context(mock_context) == "user_1"


def test_get_user_id_from_context_fallback():
    assert get_user_id_from_context(None) == "default_user_agent_engine"


def test_get_session_id_from_context_success():
    mock_context = MagicMock()
    mock_context._invocation_context.session.session_id = "session_1"
    assert get_session_id_from_context(mock_context) == "session_1"


def test_get_session_id_from_context_fallback():
    assert get_session_id_from_context(None) == "default_session"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_display_asset_success(mock_get_asset_service):
    mock_asset_service = MagicMock()
    mock_get_asset_service.return_value = mock_asset_service

    mock_asset = MagicMock()
    mock_asset.current.gcs_uri = "gs://bucket/file.mp4"
    mock_asset.mime_type = "video/mp4"
    mock_asset.file_name = "file.mp4"
    # Wait, get_asset_by_id seems to be async if we await it in adk.py
    # In adk.py: asset = await asset_service.get_asset_by_id(asset_id)
    # So we must make the mock async!

    async def mock_get_asset(*args, **kwargs):
        return mock_asset

    mock_asset_service.get_asset_by_id = mock_get_asset

    mock_tool_context = MagicMock()

    # save_artifact is also async in ADK?
    # In adk.py: await tool_context.save_artifact(filename=asset.file_name, artifact=part)
    # So it is async!
    async def mock_save_artifact(*args, **kwargs):
        return None

    mock_tool_context.save_artifact = mock_save_artifact

    from utils.adk import display_asset

    result = await display_asset(mock_tool_context, "asset_123")

    assert "available as a tool artifact" in result


@pytest.mark.asyncio
async def test_blob_interceptor_callback_no_contents():
    mock_callback_context = MagicMock()
    mock_llm_request = MagicMock()
    mock_llm_request.contents = []

    from utils.adk import blob_interceptor_callback

    result = await blob_interceptor_callback(mock_callback_context, mock_llm_request)
    assert result is None


def test_get_user_id_from_context_exception():
    class BadContext:
        @property
        def _invocation_context(self):
            raise Exception("Access denied")

    assert get_user_id_from_context(BadContext()) == "default_user_agent_engine"


def test_get_session_id_from_context_exception():
    class BadContext:
        @property
        def _invocation_context(self):
            raise Exception("Access denied")

    assert get_session_id_from_context(BadContext()) == "default_session"


@pytest.mark.asyncio
@patch("mediagent_kit.services.aio.get_asset_service")
async def test_blob_interceptor_callback_with_blob(mock_get_asset_service):
    mock_callback_context = MagicMock()
    mock_llm_request = MagicMock()

    mock_part = MagicMock()
    mock_part.inline_data.mime_type = "image/png"
    mock_part.inline_data.data = b"fake data"
    mock_part.inline_data.display_name = "test.png"

    mock_content = MagicMock()
    mock_content.role = "user"
    mock_content.parts = [mock_part]

    mock_llm_request.contents = [mock_content]

    mock_asset_service_inst = MagicMock()
    mock_get_asset_service.return_value = mock_asset_service_inst

    async def mock_save_asset(*args, **kwargs):
        return "asset_id_123"

    mock_asset_service_inst.save_asset = mock_save_asset

    from utils.adk import blob_interceptor_callback

    result = await blob_interceptor_callback(mock_callback_context, mock_llm_request)
    assert result is None


@patch("utils.tracing.CloudTraceSpanExporter.export")
def test_exporter_export_large_payload(mock_super_export):
    with patch("utils.tracing.storage.Client") as mock_storage_client_cls:
        mock_storage_client = MagicMock()
        mock_storage_client_cls.return_value = mock_storage_client

        exporter = CloudTraceLoggingSpanExporter()
        exporter.project_id = "test-project"

        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 123
        mock_span_context.span_id = 456
        mock_span.get_span_context.return_value = mock_span_context

        large_value = "x" * (260 * 1024)
        mock_span.to_json.return_value = json.dumps(
            {"attributes": {"large": large_value}}
        )

        with patch.object(exporter, "store_in_gcs") as mock_store_gcs:
            mock_store_gcs.return_value = "gs://test-bucket/spans/456.json"

            with patch.object(exporter, "logger") as mock_logger:
                exporter.export([mock_span])

                mock_store_gcs.assert_called_once()
                mock_super_export.assert_called_once()
