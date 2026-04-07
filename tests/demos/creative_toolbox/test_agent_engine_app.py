import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import datetime

import pytest
from demos.backend.creative_toolbox.agent_engine_app import (
    AgentEngineApp,
    deploy_agent_engine_app,
)


class TestAgentEngineAppClass(unittest.TestCase):
    def test_set_up(self):
        with patch(
            "demos.backend.creative_toolbox.agent_engine_app.TracerProvider"
        ) as mock_tp:
            with patch(
                "demos.backend.creative_toolbox.agent_engine_app.export.BatchSpanProcessor"
            ) as mock_bsp:
                with patch(
                    "demos.backend.creative_toolbox.agent_engine_app.CloudTraceLoggingSpanExporter"
                ) as mock_exporter:
                    with patch(
                        "demos.backend.creative_toolbox.agent_engine_app.trace.set_tracer_provider"
                    ) as mock_set_tp:
                        # AdkApp might need arguments, let's pass dummy ones if needed
                        # Assuming AdkApp can be initialized with dummy agent
                        app = AgentEngineApp(agent=MagicMock())
                        # Mock super().set_up() to avoid errors
                        with patch(
                            "vertexai.preview.reasoning_engines.AdkApp.set_up"
                        ) as mock_super_set_up:
                            app.set_up()
                            mock_tp.assert_called_once()
                            mock_set_tp.assert_called_once()

    def test_register_feedback(self):
        app = AgentEngineApp(agent=MagicMock())
        app.logger = MagicMock()

        feedback_data = {
            "session_id": "sess_123",
            "feedback_type": "thumb_up",
            "comment": "Great!",
            "scene_index": 0,
            "category": "video",
        }

        # Mock Feedback model if needed, or if it's a standard dict validation
        # Assuming Feedback.model_validate works with valid data
        with patch(
            "demos.backend.creative_toolbox.agent_engine_app.Feedback"
        ) as mock_feedback_cls:
            mock_fb_inst = MagicMock()
            mock_fb_inst.model_dump.return_value = feedback_data
            mock_feedback_cls.model_validate.return_value = mock_fb_inst

            app.register_feedback(feedback_data)
            app.logger.info.assert_called_once()

    def test_register_operations(self):
        app = AgentEngineApp(agent=MagicMock())
        with patch(
            "vertexai.preview.reasoning_engines.AdkApp.register_operations"
        ) as mock_super_reg:
            mock_super_reg.return_value = {"": ["op1"]}
            ops = app.register_operations()
            assert "register_feedback" in ops[""]
            assert "op1" in ops[""]

    def test_clone(self):
        app = AgentEngineApp(agent=MagicMock())
        app._tmpl_attrs = {
            "agent": MagicMock(),
            "enable_tracing": True,
            "session_service_builder": MagicMock(),
            "artifact_service_builder": MagicMock(),
            "env_vars": {},
        }

        with patch("copy.deepcopy") as mock_deepcopy:
            mock_deepcopy.return_value = app._tmpl_attrs["agent"]
            cloned = app.clone()
            assert isinstance(cloned, AgentEngineApp)


@pytest.mark.asyncio
async def test_deploy_agent_engine_app_success():
    with patch("vertexai.init") as mock_vertex_init:
        with patch("builtins.open", mock_open(read_data="req1\nreq2")):
            with patch("vertexai.agent_engines.list") as mock_list:
                with patch("vertexai.agent_engines.create") as mock_create:
                    with patch("vertexai.agent_engines.update") as mock_update:

                        mock_list.return_value = []  # No existing agent

                        mock_remote = MagicMock()
                        mock_remote.resource_name = (
                            "projects/p/locations/l/agentEngines/a"
                        )
                        mock_create.return_value = mock_remote

                        # Mock datetime.datetime.now
                        with patch("datetime.datetime") as mock_datetime:
                            mock_datetime.now.return_value.isoformat.return_value = (
                                "2026-04-01T00:00:00"
                            )

                            # We also need to mock json.dump to avoid writing file or mock open for write
                            # Since we already mocked open for read, we need to handle write as well
                            # Better to use a separate patch or handle it in mock_open

                            m_open = mock_open(read_data="req1\nreq2")
                            with patch("builtins.open", m_open):
                                deploy_agent_engine_app(
                                    project="test-project",
                                    location="us-central1",
                                    agent_name="test-agent",
                                    requirements_file="reqs.txt",
                                )

                                mock_vertex_init.assert_called_once()
                                mock_create.assert_called_once()
                                mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_deploy_agent_engine_app_update():
    with patch("vertexai.init") as mock_vertex_init:
        with patch("builtins.open", mock_open(read_data="req1\nreq2")):
            with patch("vertexai.agent_engines.list") as mock_list:
                with patch("vertexai.agent_engines.create") as mock_create:
                    with patch("vertexai.agent_engines.update") as mock_update:

                        mock_existing = MagicMock()
                        mock_list.return_value = [mock_existing]

                        mock_remote = MagicMock()
                        mock_remote.resource_name = (
                            "projects/p/locations/l/agentEngines/a"
                        )
                        mock_existing.update.return_value = mock_remote

                        m_open = mock_open(read_data="req1\nreq2")
                        with patch("builtins.open", m_open):
                            deploy_agent_engine_app(
                                project="test-project",
                                location="us-central1",
                                agent_name="test-agent",
                                requirements_file="reqs.txt",
                            )

                            mock_vertex_init.assert_called_once()
                            mock_create.assert_not_called()
                            mock_existing.update.assert_called_once()
