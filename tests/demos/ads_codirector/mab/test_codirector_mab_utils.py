# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Comprehensive unit tests for MAB utility functions and agents."""

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ads_codirector.mab import utils as mab_utils
from ads_codirector.utils import common_utils, mab_model
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext


class MockInvocationContext:
    """A minimal mock for InvocationContext that satisfies ADK requirements."""

    def __init__(self):
        self.agent_name = "test_agent"
        self.session = MagicMock()
        self.session.state = {}
        self.session.app_name = "test_app"
        self.session.user_id = "test_user"
        self.session.id = "test_session"
        self.plugin_manager = MagicMock()
        self.plugin_manager.run_before_agent_callback = AsyncMock(return_value=None)
        self.plugin_manager.run_after_agent_callback = AsyncMock(return_value=None)
        self.end_invocation = False

    def model_copy(self, update=None):
        if update:
            for k, v in update.items():
                setattr(self, k, v)
        return self


@pytest.fixture(name="mock_invocation_ctx")
def fixture_mock_invocation_ctx():
    return MockInvocationContext()


@pytest.fixture(name="mock_tool_context")
def fixture_mock_tool_context():
    """Provides a standard mock ToolContext for testing."""
    context = MagicMock()
    context.user_id = "test_user"
    context.state = {
        common_utils.USER_INPUT_KEY: "Test prompt",
        common_utils.STRUCTURED_USER_INPUT_KEY: {"brand": "TestBrand"},
        common_utils.USER_ASSETS_KEY: {},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }
    return context


# --- Core MAB State Tests ---


@pytest.mark.asyncio
async def test_save_mab_state_batch_mode(mock_asset_service, mock_mab_state):
    """Verify save_mab_state handles BATCH_JOB_MODE correctly."""
    with patch.dict(
        os.environ, {"BATCH_JOB_MODE": "True", "ASSET_GCS_ROOT": "custom_root"}
    ):
        await mab_utils.save_mab_state(mock_mab_state, "user123")
        mock_asset_service.save_asset.assert_called_once()
        args, kwargs = mock_asset_service.save_asset.call_args
        assert (
            kwargs["gcs_path_override"]
            == "custom_root/user123/test-exp-123_mab_state.json"
        )


@pytest.mark.asyncio
async def test_load_mab_state_error(mock_asset_service):
    """Verify error handling in load_mab_state."""
    mock_asset_service.get_asset_by_file_name.side_effect = Exception("GCS Down")
    state, asset = await mab_utils.load_mab_state("user1", "exp1")
    assert state is None
    assert asset is None


def test_initialize_bandit_epsilon(mock_mab_state):
    """Verify bandit initialization for EpsilonGreedy."""
    config = {
        "mab": {
            "algorithm": "epsilon_greedy",
            "algorithm_params": {"epsilon_greedy": {"epsilon": 0.5}},
            "arms": {"a": ["1"]},
        }
    }
    bandit = mab_utils._initialize_bandit(config, mock_mab_state)
    from ads_codirector.mab.bandit import EpsilonGreedyBandit

    assert isinstance(bandit, EpsilonGreedyBandit)
    assert bandit.epsilon == 0.5


# --- Agent/Tool Logic Tests ---


@pytest.mark.asyncio
@patch("ads_codirector.mab.utils.save_mab_state", new_callable=AsyncMock)
@patch("utils.adk.get_user_id_from_context", return_value="test_user")
@patch("ads_codirector.mab.utils.get_mab_config")
async def test_initialize_mab_experiment(
    mock_config, _mock_user, _mock_save, mock_tool_context
):
    """Verify experiment initialization and ID generation."""
    mock_config.return_value = {"mab": {"warm_up": False}}
    result = await mab_utils.initialize_mab_experiment(mock_tool_context)
    assert "MAB experiment initialized" in result
    assert common_utils.MAB_EXPERIMENT_ID_KEY in mock_tool_context.state
    assert mock_tool_context.state["mab_iteration"] == -1


@pytest.mark.asyncio
async def test_initialize_mab_experiment_full(mock_asset_service, mock_mab_state):
    """Verify full initialization with assets and warm start."""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "u1"
    ctx.state = {
        common_utils.USER_INPUT_KEY: "Prompt",
        common_utils.STRUCTURED_USER_INPUT_KEY: {"brand": "B"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "p.png": {"semantic_role": "product"}
        },
        common_utils.USER_ASSETS_KEY: {"p.png": "Caption"},
    }
    with (
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"mab": {"warm_up": True}},
        ),
        patch("mediagent_kit.services.aio.get_media_generation_service") as mock_gen,
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch("ads_codirector.mab.utils.save_mab_state"),
    ):
        gen_service = AsyncMock()
        mock_gen.return_value = gen_service
        gen_service.generate_text_with_gemini.return_value = MagicMock(id="a1")
        mock_asset_service.get_asset_blob.return_value = MagicMock(
            content=b'{"recommendations": {"creative_strategy": "informational"}, "reasoning": "R"}'
        )
        msg = await mab_utils.initialize_mab_experiment(ctx)
        assert "initialized" in msg
        assert ctx.state[common_utils.MAB_EXPERIMENT_ID_KEY] is not None


@pytest.mark.asyncio
async def test_initialize_mab_experiment_warm_start_fail(mock_asset_service):
    """Verify fallback when warm start strategic analysis fails."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    ctx.state = {
        common_utils.USER_INPUT_KEY: "P",
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
    }

    gen_service = AsyncMock()
    gen_service.generate_text_with_gemini.side_effect = Exception("LLM Error")

    with (
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"mab": {"warm_up": True}},
        ),
        patch(
            "mediagent_kit.services.aio.get_media_generation_service",
            return_value=gen_service,
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch("ads_codirector.mab.utils.save_mab_state"),
    ):

        msg = await mab_utils.initialize_mab_experiment(ctx)
        assert "fell back to cold start" in msg


@pytest.mark.asyncio
async def test_select_mab_arms_missing_id():
    """Verify error if experiment_id is missing."""
    ctx = MagicMock(spec=ToolContext)
    ctx.state = {}
    with pytest.raises(ValueError, match="MAB experiment_id not found"):
        await mab_utils.select_mab_arms(ctx)


def test_prepare_iteration_state(mock_tool_context):
    """Verify that state is scrubbed between iterations."""
    mock_tool_context.state = {
        "mab_iteration": 0,
        common_utils.STORYLINE_KEY: {"old": "data"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "00_logo.png": "Logo",
            "iter_0_character_collage.png": "Old collage",
        },
    }
    mab_utils.prepare_iteration_state(mock_tool_context)
    assert mock_tool_context.state["mab_iteration"] == 1
    assert mock_tool_context.state[common_utils.STORYLINE_KEY] == {}
    annotated = mock_tool_context.state[common_utils.ANNOTATED_REFERENCE_VISUALS_KEY]
    assert "00_logo.png" in annotated
    assert "iter_0_character_collage.png" not in annotated


@pytest.mark.asyncio
async def test_log_mab_iteration_results_full(mock_asset_service, mock_mab_state):
    """Verify logging of iteration results."""
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "u1"
    ctx.state = {
        common_utils.MAB_EXPERIMENT_ID_KEY: "exp1",
        common_utils.ARMS_SELECTED_KEY: {"a": "1"},
        common_utils.VERIFICATION_RESULT_KEY: {"score": 90},
        common_utils.STORYBOARD_KEY: {"final_video_asset_id": "v1", "scenes": []},
    }
    with (
        patch(
            "ads_codirector.mab.utils.load_mab_state",
            return_value=(mock_mab_state, MagicMock()),
        ),
        patch("ads_codirector.mab.utils.save_mab_state") as mock_save,
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"mab": {"arms": {"a": ["1"]}}},
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        await mab_utils.log_mab_iteration_results(ctx)

        # Verify the state passed to save_mab_state has the new iteration
        saved_state = mock_save.call_args[0][0]
        assert len(saved_state.iterations) == 1


@pytest.mark.asyncio
async def test_log_mab_iteration_results_asset_bloat(
    mock_asset_service, mock_mab_state
):
    """Verify asset bloat removal on the NEW iteration."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    ctx.state = {
        common_utils.MAB_EXPERIMENT_ID_KEY: "exp1",
        common_utils.ARMS_SELECTED_KEY: {"a": "1"},
        common_utils.VERIFICATION_RESULT_KEY: {"score": 90},
        common_utils.STORYBOARD_KEY: {
            "scenes": [
                {
                    "first_frame_generation_history": [
                        {"asset": {"id": "a1", "versions": [1, 2, 3]}}
                    ]
                }
            ]
        },
    }

    with (
        patch(
            "ads_codirector.mab.utils.load_mab_state",
            return_value=(mock_mab_state, MagicMock()),
        ),
        patch("ads_codirector.mab.utils.save_mab_state") as mock_save,
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"mab": {"arms": {"a": ["1"]}}},
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        await mab_utils.log_mab_iteration_results(ctx)
        saved_state = mock_save.call_args[0][0]
        # Verify latest iteration's storyboard was stripped
        history = saved_state.iterations[-1].storyboard["scenes"][0][
            "first_frame_generation_history"
        ]
        assert history[0]["asset"]["versions"] == []


@pytest.mark.asyncio
async def test_get_and_store_version_error(mock_asset_service, mock_mab_state):
    """Verify error handling in asset version lookup."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    ctx.state = {
        common_utils.MAB_EXPERIMENT_ID_KEY: "exp1",
        common_utils.STORYBOARD_KEY: {
            "scenes": [{"first_frame_prompt": {"asset_id": "bad1"}}]
        },
    }
    mock_asset_service.get_asset_by_id.side_effect = Exception("Metadata Fail")

    with (
        patch(
            "ads_codirector.mab.utils.load_mab_state",
            return_value=(mock_mab_state, MagicMock()),
        ),
        patch("ads_codirector.mab.utils.save_mab_state"),
        patch("ads_codirector.mab.utils.get_mab_config", return_value={}),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        await mab_utils.log_mab_iteration_results(ctx)


def test_get_theoretical_definitions_missing():
    """Verify fallback if definition is missing."""
    ctx = MagicMock(spec=ToolContext)
    ctx.state = {common_utils.ARMS_SELECTED_KEY: {"creative_strategy": "invalid_arm"}}
    defs = mab_utils.get_theoretical_definitions(ctx)
    assert defs["creative_strategy"] == "No definition found."


@pytest.mark.asyncio
async def test_flatten_creative_direction_success():
    """Verify spreading nested instructions into state."""
    ctx = MagicMock()
    ctx.state = {
        common_utils.CREATIVE_DIRECTION_KEY: {
            "storyline_instruction": "SI",
            "keyframe_instruction": "KI",
            "video_instruction": "VI",
            "audio_instruction": "AI",
        }
    }
    result = await mab_utils.flatten_creative_direction(ctx)
    assert result["status"] == "succeeded"
    assert ctx.state[common_utils.CD_STORYLINE_KEY] == "SI"
    assert ctx.state[common_utils.CD_KEYFRAME_KEY] == "KI"


# --- Report Generation Tests ---


@pytest.mark.asyncio
async def test_create_standalone_html_report_empty(mock_asset_service, mock_mab_state):
    """Verify None returned if no iterations."""
    ctx = MagicMock(spec=ToolContext)
    with patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"):
        res = await mab_utils._create_standalone_html_report(ctx, mock_mab_state)
        assert res is None


@pytest.mark.asyncio
async def test_create_standalone_html_report_with_data(mock_mab_state):
    """Verify download and rendering flow."""
    ctx = MagicMock()
    mock_mab_state.iterations = [
        mab_model.MabIterationLog(
            iteration_num=1,
            project_folder_id="u1",
            arms_selected={},
            verifier_results={},
            artifact_uri="u",
            verifiers={},
            storyboard={"scenes": []},
            arm_stats={},
        )
    ]

    mock_service = AsyncMock()
    # Mock list_assets and get_asset_blob
    mock_service.list_assets.return_value = []
    mock_service.get_asset_blob.return_value = MagicMock(content=b"data")

    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch("ads_codirector.mab.report_generator.generate_html_report") as mock_gen,
    ):

        res = await mab_utils._create_standalone_html_report(ctx, mock_mab_state)
        assert res is not None
        assert "/mab_report_" in str(res)
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_create_standalone_html_report_deep_data(mock_mab_state):
    """Verify downloading all asset types for the report."""
    ctx = MagicMock()
    # Correct structure for MabIterationLog and Storyboard
    mock_mab_state.iterations = [
        mab_model.MabIterationLog(
            iteration_num=1,
            project_folder_id="u1",
            arms_selected={},
            verifier_results={},
            artifact_uri="u",
            verifiers={},
            character_collage_asset_id="coll1",
            storyboard={
                "final_video_asset_id": "v1",
                "scenes": [
                    {
                        "first_frame_prompt": {"asset_id": "f1"},
                        "first_frame_generation_history": [
                            {
                                "asset": {
                                    "id": "h1",
                                    "file_name": "h1.png",
                                    "current_version": 1,
                                }
                            }
                        ],
                    }
                ],
                "voiceover_generation_history": [
                    {
                        "asset": {
                            "id": "vo1",
                            "file_name": "vo1.mp3",
                            "current_version": 1,
                        }
                    }
                ],
                "background_music_generation_history": [
                    {
                        "asset": {
                            "id": "bg1",
                            "file_name": "bg1.mp3",
                            "current_version": 1,
                        }
                    }
                ],
            },
            arm_stats={},
        )
    ]

    mock_service = AsyncMock()
    mock_service.get_asset_by_id.side_effect = lambda aid: MagicMock(
        id=aid, file_name=f"{aid}.ext", current_version=1
    )
    mock_service.get_asset_blob.return_value = MagicMock(content=b"data")
    mock_service.list_assets.return_value = []

    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch(
            "ads_codirector.mab.report_generator.generate_html_report",
            return_value="<html></html>",
        ),
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", MagicMock()),
    ):

        res = await mab_utils._create_standalone_html_report(ctx, mock_mab_state)
        assert res is not None

        # collage, vo1, bg1, v1, f1, h1
        expected_ids = ["coll1", "vo1", "bg1", "v1", "f1", "h1"]
        called_ids = [
            call.kwargs.get("asset_id")
            for call in mock_service.get_asset_blob.call_args_list
        ]
        for eid in expected_ids:
            assert eid in called_ids


@pytest.mark.asyncio
async def test_upload_html_report_success(tmp_path):
    """Verify report upload logic."""
    report_file = tmp_path / "report.html"
    report_file.write_text("<html></html>")

    ctx = MagicMock()
    ctx.save_artifact = AsyncMock()

    mock_service = AsyncMock()
    mock_service.save_asset.return_value = MagicMock(id="asset123")

    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):
        res = await mab_utils._upload_html_report(ctx, report_file)
        assert res["status"] == "succeeded"
        mock_service.save_asset.assert_called_once()
        ctx.save_artifact.assert_called_once()


@pytest.mark.asyncio
async def test_upload_html_report_missing(tmp_path):
    """Verify failure if file doesn't exist."""
    ctx = MagicMock(spec=ToolContext)
    res = await mab_utils._upload_html_report(ctx, tmp_path / "missing.html")
    assert res["status"] == "failed"


@pytest.mark.asyncio
async def test_finalize_and_save_reports_full_flow(mock_mab_state):
    """Verify full orchestration of report generation."""
    ctx = MagicMock()
    ctx.state = {common_utils.MAB_EXPERIMENT_ID_KEY: "exp1"}

    # Mock full config
    config = {"generate_html_report": True, "generate_canvas_report": True}

    with (
        patch(
            "ads_codirector.mab.utils.load_mab_state",
            return_value=(mock_mab_state, MagicMock()),
        ),
        patch("ads_codirector.mab.utils.get_mab_config", return_value=config),
        patch(
            "ads_codirector.mab.utils._create_standalone_html_report",
            return_value="/tmp/report.html",
        ),
        patch(
            "ads_codirector.mab.utils._upload_html_report",
            return_value={"status": "succeeded"},
        ),
        patch(
            "ads_codirector.mab.utils._create_canvas_report",
            return_value={"status": "succeeded", "result": "c1"},
        ),
        patch(
            "ads_codirector.mab.utils.upload_log_to_gcs",
            return_value={"status": "succeeded"},
        ),
        patch("shutil.rmtree"),
        patch("mediagent_kit.services.aio.get_asset_service") as mock_asset_service,
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        # Mock save_asset for JSON report
        mock_asset_service.return_value.save_asset.return_value = MagicMock(id="j1")

        res = await mab_utils.finalize_and_save_reports(ctx)
        assert res["status"] == "succeeded"
        assert "HTML Report" in res["result"]
        assert "Canvas Report" in res["result"]


@pytest.mark.asyncio
async def test_create_canvas_report_full(mock_mab_state):
    """Verify canvas report creation and asset resolution."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    mock_service = AsyncMock()
    mock_service.list_assets.return_value = [MagicMock(id="a1", file_name="logo.png")]

    mock_canvas = AsyncMock()
    mock_canvas.create_canvas.return_value = MagicMock(id="canvas123")

    with (
        patch(
            "ads_codirector.mab.report_generator.generate_html_report",
            return_value='<img src="asset://logo.png">',
        ),
        patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_service,
        ),
        patch(
            "mediagent_kit.services.aio.get_canvas_service", return_value=mock_canvas
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        res = await mab_utils._create_canvas_report(ctx, mock_mab_state)
        assert res["status"] == "succeeded"
        assert "canvas123" in res["result"]
        mock_canvas.create_canvas.assert_called_once()
        # Verify asset ID was resolved
        args, kwargs = mock_canvas.create_canvas.call_args
        assert "a1" in kwargs["html"].asset_ids


@pytest.mark.asyncio
async def test_create_canvas_report_error(mock_mab_state):
    """Verify error handling in canvas creation."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    mock_canvas = AsyncMock()
    mock_canvas.create_canvas.side_effect = Exception("Canvas API Down")

    mock_asset_service_obj = AsyncMock()
    mock_asset_service_obj.list_assets.return_value = []

    with (
        patch(
            "ads_codirector.mab.report_generator.generate_html_report",
            return_value="<html></html>",
        ),
        patch(
            "mediagent_kit.services.aio.get_asset_service",
            return_value=mock_asset_service_obj,
        ),
        patch(
            "mediagent_kit.services.aio.get_canvas_service", return_value=mock_canvas
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):

        res = await mab_utils._create_canvas_report(ctx, mock_mab_state)
        assert res["status"] == "failed"
        assert "Canvas API Down" in res["error_message"]


@pytest.mark.asyncio
async def test_upload_log_to_gcs_success(mock_mab_state):
    """Verify log upload."""
    ctx = MagicMock()
    ctx.user_id = "u1"
    ctx.session.user_id = "u1"
    ctx.state = {common_utils.MAB_EXPERIMENT_ID_KEY: "exp1"}
    ctx.save_artifact = AsyncMock()

    with (
        patch(
            "ads_codirector.mab.utils.load_mab_state",
            return_value=(mock_mab_state, MagicMock()),
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch("builtins.open", MagicMock()),
        patch.object(Path, "exists", return_value=True),
    ):
        res = await mab_utils.upload_log_to_gcs(ctx)
        assert res["status"] == "succeeded"
        assert ctx.save_artifact.called


# --- Specialized Agent Tests ---


@pytest.mark.asyncio
async def test_asset_inventory_preparer(mock_invocation_ctx):
    """Verify that the inventory string is correctly formatted for the Storyboard agent."""
    preparer = mab_utils.AssetInventoryPreparer(name="test_preparer")
    mock_invocation_ctx.session.state = {
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {
            "prod.png": {"semantic_role": "product"},
            "logo.jpg": {"semantic_role": "logo"},
            "plain.webp": "Just a caption",
        }
    }
    events = []
    async for event in preparer.run_async(mock_invocation_ctx):
        events.append(event)
    assert len(events) > 0
    inventory_str = mock_invocation_ctx.session.state.get(
        "temp:asset_inventory_list", ""
    )
    assert "- prod.png (Role: product)" in inventory_str
    assert "- logo.jpg (Role: logo)" in inventory_str
    assert "- plain.webp (Role: unknown)" in inventory_str


@pytest.mark.asyncio
async def test_storyboard_instruction_resolution():
    """Verify that storyboard instruction placeholders are resolved."""
    mock_invocation_ctx_raw = MagicMock()
    mock_invocation_ctx_raw.session.state = {
        "temp:asset_inventory_list": "- product_01.png (Role: product)",
        common_utils.STORYLINE_KEY: "Scene 1: Action",
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {},
        common_utils.CREATIVE_CONFIG_KEY: {},
        common_utils.CREATIVE_DIRECTION_KEY: {},
        common_utils.MAB_ITERATION_KEY: 0,
    }
    mock_invocation_ctx_raw.session.app_name = "test_app"
    mock_invocation_ctx_raw.session.user_id = "test_user"
    mock_invocation_ctx_raw.session.id = "test_session"
    ctx = ReadonlyContext(mock_invocation_ctx_raw)
    instruction = mab_utils.get_storyboard_instruction_with_mab(ctx)
    if hasattr(instruction, "__await__"):
        instruction = await instruction
    assert "{temp:asset_inventory_list}" not in instruction
    assert "- product_01.png (Role: product)" in instruction


@pytest.mark.asyncio
async def test_get_storyboard_instruction_with_mab_r2v():
    """Verify r2v constraint injection."""
    ctx = MagicMock()
    ctx.session.state = {}
    with (
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"logo_scene_mode": "r2v"},
        ),
        patch(
            "ads_codirector.utils.common_utils.resolve_template",
            side_effect=lambda x, y: x,
        ),
    ):
        instr = await mab_utils.get_storyboard_instruction_with_mab(ctx)
        assert "Reference-to-Video" in instr


@pytest.mark.asyncio
async def test_storyline_loop_instruction_resolution(mock_invocation_ctx):
    """Verify that storyline loop agent resolves placeholders in stored templates."""
    mock_invocation_ctx.session.state = {
        "creative_brief": "A great campaign",
        "annotated_reference_visuals": "Rustic lock",
        "creative_configuration": {},
        "creative_direction": {"storyline_instruction": "Instruction text"},
    }
    selector = mab_utils.StorylineLoopInstructionSelector(name="test_selector")
    async for _ in selector.run_async(mock_invocation_ctx):
        pass
    stored_instruction = mock_invocation_ctx.session.state.get(
        "temp:storyline_instruction"
    )
    assert stored_instruction is not None
    assert "{creative_brief}" not in stored_instruction
    assert "A great campaign" in stored_instruction


@pytest.mark.asyncio
async def test_storyline_loop_instruction_selector_refiner():
    """Verify refiner instruction selection."""
    agent = mab_utils.StorylineLoopInstructionSelector(name="selector")
    ctx = MagicMock()
    ctx.session.state = {
        "temp:storyline_done": False,
        common_utils.REFINEMENT_HISTORY_KEY: [{"attempt": 0, "stage": "storyline"}],
        "temp:storyline_prompt_type": "executor",
    }

    with patch(
        "ads_codirector.utils.common_utils.resolve_template", side_effect=lambda x, y: x
    ):
        async for _ in agent._run_async_impl(ctx):
            pass
        assert "temp:storyline_instruction" in ctx.session.state
        assert "temp:storyline_prompt_type" in ctx.session.state


@pytest.mark.asyncio
async def test_storyline_refinement_checker_done():
    """Verify escalation when threshold reached."""
    agent = mab_utils.StorylineRefinementChecker(name="checker")
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.state = {
        common_utils.STORYLINE_KEY: {"scenes": []},
        "storyline_evaluation": {"score": 90},
        common_utils.REFINEMENT_HISTORY_KEY: [],
        "mab_iteration": 0,
    }
    ctx.session.user_id = "u1"
    with (
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={"self_refinement": {"storyline": {"score_threshold": 80}}},
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
        patch("mediagent_kit.services.aio.get_asset_service"),
    ):

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        assert events[0].actions.escalate is True
        assert ctx.session.state["temp:storyline_done"] is True


@pytest.mark.asyncio
async def test_storyline_refinement_checker_max_attempts():
    """Verify escalation when max attempts reached."""
    agent = mab_utils.StorylineRefinementChecker(name="checker")
    ctx = MagicMock()
    ctx.user_id = "u1"
    ctx.session = MagicMock()
    ctx.session.user_id = "u1"
    ctx.session.state = {
        common_utils.STORYLINE_KEY: {"scenes": []},
        "storyline_evaluation": {"score": 50},  # Below threshold
        common_utils.REFINEMENT_HISTORY_KEY: [
            {"stage": "storyline"},
            {"stage": "storyline"},
            {"stage": "storyline"},
        ],  # 3 attempts
        "mab_iteration": 0,
    }

    with (
        patch(
            "ads_codirector.mab.utils.get_mab_config",
            return_value={
                "self_refinement": {
                    "storyline": {"score_threshold": 80, "max_attempts": 3}
                }
            },
        ),
        patch("mediagent_kit.services.aio.get_asset_service"),
    ):

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        assert events[0].actions.escalate is True
        assert ctx.session.state["temp:storyline_done"] is True


class MockAgent(BaseAgent):
    """Simple agent for testing that yields a predefined list of events."""

    event_to_yield: Any = None

    async def _run_async_impl(
        self, parent_context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield self.event_to_yield

    async def _run_live_impl(
        self, parent_context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield self.event_to_yield


@pytest.mark.asyncio
async def test_escalation_shielding(mock_invocation_ctx):
    """Verify that escalation is cleared for parent but preserved for child."""
    orig_event = Event(author="test_agent", actions=EventActions(escalate=True))
    sub_agent = MockAgent(name="sub_agent", event_to_yield=orig_event)
    filter_agent = mab_utils.LocalEscalationFilter(
        name="test_filter", sub_agents=[sub_agent]
    )
    results = []
    async for event in filter_agent.run_async(mock_invocation_ctx):
        results.append(event)
    assert len(results) == 1
    assert results[0].actions.escalate is False
    assert orig_event.actions.escalate is True
    assert results[0] is not orig_event


@pytest.mark.asyncio
async def test_normal_event_passthrough(mock_invocation_ctx):
    """Verify that normal events are passed through without modification."""
    normal_event = Event(author="test_agent", actions=EventActions(escalate=False))
    sub_agent = MockAgent(name="sub_agent", event_to_yield=normal_event)
    filter_agent = mab_utils.LocalEscalationFilter(
        name="test_filter", sub_agents=[sub_agent]
    )
    results = []
    async for event in filter_agent.run_async(mock_invocation_ctx):
        results.append(event)
    assert len(results) == 1
    assert results[0].author == "test_agent"
    assert results[0].actions.escalate is False
    assert results[0] is normal_event


# --- Saver Agent Tests ---


@pytest.mark.asyncio
async def test_storyboard_saver():
    """Verify storyboard saving."""
    agent = mab_utils.StoryboardSaver(name="saver")
    ctx = MagicMock()
    ctx.session.state = {
        common_utils.STORYBOARD_KEY: {"scenes": []},
        "mab_iteration": 0,
    }
    ctx.session.user_id = "u1"

    mock_service = AsyncMock()
    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):
        async for _ in agent._run_async_impl(ctx):
            pass
        mock_service.save_asset.assert_called_once()
        assert "storyboard.json" in mock_service.save_asset.call_args[1]["file_name"]


@pytest.mark.asyncio
async def test_creative_brief_saver():
    """Verify creative brief saving."""
    agent = mab_utils.CreativeBriefSaver(name="saver")
    ctx = MagicMock()
    ctx.session.state = {
        common_utils.CREATIVE_BRIEF_KEY: "Brief content",
        common_utils.MAB_ITERATION_KEY: 0,
    }

    mock_service = AsyncMock()
    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):
        async for _ in agent._run_async_impl(ctx):
            pass
        mock_service.save_asset.assert_called_once()


@pytest.mark.asyncio
async def test_creative_direction_saver():
    """Verify creative direction saving."""
    agent = mab_utils.CreativeDirectionSaver(name="saver")
    ctx = MagicMock()
    ctx.session.state = {
        common_utils.CREATIVE_DIRECTION_KEY: {"storyline_instruction": "SI"},
        common_utils.MAB_ITERATION_KEY: 0,
    }

    mock_service = AsyncMock()
    with (
        patch(
            "mediagent_kit.services.aio.get_asset_service", return_value=mock_service
        ),
        patch("ads_codirector.utils.common_utils.get_user_id", return_value="u1"),
    ):
        async for _ in agent._run_async_impl(ctx):
            pass
        mock_service.save_asset.assert_called_once()
