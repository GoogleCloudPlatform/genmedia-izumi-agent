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

"""
PARANOID UNIT TEST: Instruction Template Integrity
This test meticulously verifies that every placeholder in every instruction template
is correctly resolved given a representative session state.
"""

import re
import pytest

from ads_codirector.utils import common_utils

# Import all instruction modules
from ads_codirector.instructions.mab import (
    creative_director_instruction,
    mab_warm_up_instruction,
)
from ads_codirector.instructions.pre_production import (
    casting_instruction,
    creative_brief_instruction,
    storyboard_instruction,
    storyline_instruction,
    storyline_refinement_instruction,
    voiceover_script_instruction,
)
from ads_codirector.instructions.verifier import (
    storyline_verifier_instruction,
    video_verifier_instruction,
    keyframe_verifier_instruction,
)
from ads_codirector.instructions import (
    parameters_instruction,
    root_instruction,
    user_assets_instruction,
)


@pytest.fixture(name="mock_state")
def fixture_mock_state():
    """Provides a comprehensive mock state for template resolution tests."""
    return {
        # Core Keys
        common_utils.USER_INPUT_KEY: "Sample User Prompt",
        common_utils.STRUCTURED_USER_INPUT_KEY: {"brand": "Quux"},
        common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: {"asset.png": "meta"},
        common_utils.CREATIVE_CONFIG_KEY: {"strategy": "info"},
        common_utils.CREATIVE_BRIEF_KEY: "Long Brief Text",
        common_utils.CREATIVE_DIRECTION_KEY: {
            "storyline_instruction": "STORY_INSTR",
            "keyframe_instruction": "FRAME_INSTR",
            "video_instruction": "VIDEO_INSTR",
            "audio_instruction": "AUDIO_INSTR",
        },
        # Flattened Keys (Expected by new implementation)
        common_utils.CD_STORYLINE_KEY: "STORY_INSTR",
        common_utils.CD_KEYFRAME_KEY: "FRAME_INSTR",
        common_utils.CD_VIDEO_KEY: "VIDEO_INSTR",
        common_utils.CD_AUDIO_KEY: "AUDIO_INSTR",
        common_utils.THEORETICAL_DEFS_KEY: {"dim": "def"},
        common_utils.CASTING_KEY: {"present": True},
        common_utils.STORYBOARD_KEY: {"scenes": []},
        common_utils.STORYLINE_KEY: {"scenes": []},
        common_utils.REFINEMENT_HISTORY_KEY: [],
        common_utils.MAB_ITERATION_KEY: 0,
        # Temp Keys
        "temp:asset_inventory_list": "ITEM 1, ITEM 2",
        "temp:storyline_instruction": "DYNAMIC_SL_INSTR",
        "temp:storyline_done": False,
        "file_name": "asset_01.png",
        # Legacy/Raw Keys (used in some verifiers or MAB instructions)
        "user_prompt": "Sample User Prompt",
        "structured_constraints": {"brand": "Quux"},
        "creative_brief": "Long Brief Text",
        "creative_configuration": {"strategy": "info"},
        "creative_direction": {
            "storyline_instruction": "STORY_INSTR",
            "keyframe_instruction": "FRAME_INSTR",
            "video_instruction": "VIDEO_INSTR",
            "audio_instruction": "AUDIO_INSTR",
        },
        "theoretical_definitions": {"dim": "def"},
        "annotated_reference_visuals": {"asset.png": "meta"},
        "storyline": {"scenes": []},
        "storyboard": {"scenes": []},
        "num_iterations": 5,
        "mab_iteration": 0,
    }


def _check_resolution(template_name, template_text, state):
    """Helper to resolve a template and verify NO placeholders remain."""
    resolved = common_utils.resolve_template(template_text, state)
    unresolved = re.findall(r"\{[a-zA-Z0-9_.:-]+\}", resolved)
    assert (
        not unresolved
    ), f"Template '{template_name}' has unresolved placeholders: {unresolved}"
    return resolved


@pytest.mark.asyncio
async def test_all_instruction_resolutions(mock_state):
    """Meticulously test every major instruction template."""
    static_templates = {
        "creative_director": creative_director_instruction.INSTRUCTION,
        "casting": casting_instruction.INSTRUCTION,
        "creative_brief": creative_brief_instruction.INSTRUCTION,
        "storyboard": storyboard_instruction.INSTRUCTION,
        "storyline": storyline_instruction.INSTRUCTION,
        "storyline_refinement": storyline_refinement_instruction.INSTRUCTION,
        "voiceover_script": voiceover_script_instruction.INSTRUCTION,
        "storyline_verifier": storyline_verifier_instruction.INSTRUCTION,
        "video_verifier": video_verifier_instruction.INSTRUCTION,
        "keyframe_verifier": keyframe_verifier_instruction.INSTRUCTION,
        "parameters": parameters_instruction.INSTRUCTION,
        "root": root_instruction.INSTRUCTION,
        "user_assets": user_assets_instruction.INSTRUCTION,
    }
    for name, text in static_templates.items():
        _check_resolution(name, text, mock_state)

    dynamic_text = mab_warm_up_instruction.get_warm_start_instruction(
        user_prompt=mock_state[common_utils.USER_INPUT_KEY],
        structured_constraints=mock_state[common_utils.STRUCTURED_USER_INPUT_KEY],
    )
    _check_resolution("mab_warm_up", dynamic_text, mock_state)


def test_specific_nested_failure_case(mock_state):
    """Verify that dot-notation works with resolve_template."""
    template = "Style: {creative_direction.keyframe_instruction}"
    resolved = common_utils.resolve_template(template, mock_state)
    assert "{creative_direction.keyframe_instruction}" not in resolved
    assert "FRAME_INSTR" in resolved


def test_brand_integrity_mandate_presence():
    """Verify that the keyframe verifier contains the strict naming mandate."""
    template = keyframe_verifier_instruction.INSTRUCTION
    assert "BRAND INTEGRITY MANDATE" in template
    assert "official product name" in template
    assert "DO NOT invent, guess, or creatively modify" in template


def test_user_assets_filename_resolution():
    """Verify that the asset ingestion prompt resolves the specific filename."""
    template = user_assets_instruction.INSTRUCTION
    resolved = template.replace("{file_name}", "114_logo.png")
    assert "114_logo.png" in resolved
    assert "{file_name}" not in resolved
    assert "FILENAME INTEGRITY MANDATE" in resolved
    assert "FOREGROUND FOCUS MANDATE" in resolved
    assert "COMPLETELY IGNORE the background" in resolved
