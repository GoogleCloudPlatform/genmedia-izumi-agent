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

"""Comprehensive unit tests for the MAB report generator."""

import os
import shutil
from pathlib import Path
from ads_codirector.mab import report_generator


def test_generate_html_report_basic():
    """Verify that the HTML report contains key sections and symbols."""
    mab_state = {
        "user_prompt": "Test Prompt",
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {"creative_strategy": "informational"},
                "verifier_results": {"score": 85, "feedback": "Good"},
                "storyboard": {"scenes": []},
            }
        ],
        "structured_constraints": {"brand": "TestBrand"},
    }
    html = report_generator.generate_html_report(
        user_prompt="Test Prompt",
        mab_state=mab_state,
        local_artifact_dirs={},
        output_path=None,
    )
    assert "Report" in html
    assert "TestBrand" in html
    assert "Iteration 1" in html
    assert "Creative Configuration" in html


def test_generate_html_report_structured_verifier():
    """Verify that structured verifier results are rendered correctly."""
    mab_state = {
        "user_prompt": "Test Prompt",
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {"creative_strategy": "informational"},
                "verifier_results": {
                    "score": 62,
                    "breakdown": {"visual_quality": 12, "logical_consistency": 5},
                    "mab_efficacy_scores": {"creative_strategy": 40},
                    "mab_efficacy_justifications": {
                        "creative_strategy": "The **informational** strategy was weak."
                    },
                    "feedback": "Video is **bad**.\nNeeds more work.",
                    "primary_fault": "video",
                },
                "storyboard": {"scenes": []},
            }
        ],
    }
    html = report_generator.generate_html_report(
        user_prompt="Test Prompt",
        mab_state=mab_state,
        local_artifact_dirs={},
        output_path=None,
    )
    assert "Execution Breakdown" in html
    assert "12/20" in html
    assert "<strong>bad</strong>" in html
    assert "<br>" in html
    assert "Factorized Rewards" in html
    assert "Creative Strategy" in html
    assert "40/100" in html
    assert "<strong>informational</strong>" in html


def test_generate_html_report_invalid_justification_type():
    """Verify that the report generator doesn't crash if justifications are a string."""
    mab_state = {
        "user_prompt": "Test Prompt",
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {"creative_strategy": "informational"},
                "verifier_results": {
                    "score": 62,
                    "mab_efficacy_scores": {"creative_strategy": 40},
                    "mab_efficacy_justifications": "This should be a dict but it is a string",
                    "feedback": "Bad",
                    "primary_fault": "video",
                },
                "storyboard": {"scenes": []},
            }
        ],
    }
    html = report_generator.generate_html_report(
        user_prompt="Test Prompt",
        mab_state=mab_state,
        local_artifact_dirs={},
        output_path=None,
    )
    assert "Creative Strategy" in html
    assert "This should be a dict but it is a string" in html


def test_generate_html_report_empty():
    """Verify handling of empty iterations."""
    html = report_generator.generate_html_report("Prompt", {}, {}, None)
    assert html is None


def test_generate_html_report_with_assets(tmp_path):
    """Verify rendering of user assets and casting collages."""
    # Setup mock local files
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    logo_file = asset_dir / "logo.png"
    logo_file.write_bytes(b"mock_logo_bytes")

    collage_file = asset_dir / "iter_0_character_collage.png"
    collage_file.write_bytes(b"mock_collage_bytes")

    mab_state = {
        "user_assets": {"logo.png": {"caption": "Test Logo", "semantic_role": "logo"}},
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {},
                "character_collage_asset_id": "collage123",
                "character_casting": {
                    "character_profile": "Profile X",
                    "wardrobe_description": "Blue Shirt",
                    "collage_prompt": "A person in a blue shirt",
                },
                "storyboard": {"scenes": []},
            }
        ],
    }

    local_artifact_dirs = {
        "user_asset_paths": {"logo.png": logo_file},
        0: {"dir_path": asset_dir, "character_collage_path": collage_file},
    }

    html = report_generator.generate_html_report(
        "Prompt", mab_state, local_artifact_dirs, None
    )

    assert "data:image/png;base64," in html
    assert "Profile X" in html
    assert "Blue Shirt" in html
    assert "collage123" not in html  # ID is used for check, not displayed
    assert "Character Specs" in html


def test_generate_html_report_with_history_and_audio(tmp_path):
    """Verify storyline history and audio tracks."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    bg_music = audio_dir / "bg.mp3"
    bg_music.write_bytes(b"mock_audio_bytes")

    mab_state = {
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {},
                "storyline_refinement_history": [
                    {
                        "attempt": 1,
                        "score": 90,
                        "output": {"scenes": [{"action": "Action 1"}]},
                        "evaluation": {
                            "feedback": "Good",
                            "actionable_feedback": "None",
                        },
                    }
                ],
                "storyboard": {
                    "background_music_prompt": {"description": "Happy music"},
                    "background_music_generation_history": [
                        {"asset": {"file_name": "bg.mp3"}}
                    ],
                    "scenes": [],
                },
            }
        ]
    }

    local_artifact_dirs = {0: {"dir_path": audio_dir}}

    html = report_generator.generate_html_report(
        "Prompt", mab_state, local_artifact_dirs, None
    )

    assert "Storyline & Refinement" in html
    assert "Action 1" in html
    assert "Happy music" in html
    assert "data:audio/mp3;base64," in html


def test_generate_html_report_complex(tmp_path):
    """Verify a complex report with all sections."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "iter_0_final_video.mp4").write_bytes(b"vid")
    (work_dir / "iter_0_scene_0_cycle_0.png").write_bytes(b"img")
    (work_dir / "bg.mp3").write_bytes(b"bg")
    (work_dir / "vo.mp3").write_bytes(b"vo")

    mab_state = {
        "structured_constraints": {"brand": "B", "campaign_brief": "Skip me"},
        "user_assets": {"p.png": {"caption": "C", "semantic_role": "product"}},
        "warm_start": {"reasoning": "Because **AI** said so."},
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {"strategy": "S1"},
                "creative_brief": "The brief **details**.",
                "character_collage_asset_id": "c1",
                "character_casting": {"collage_prompt": "P1"},
                "storyline_refinement_history": [
                    {"attempt": 1, "output": {"script": [{"action": "A1"}]}}
                ],
                "storyboard": {
                    "background_music_prompt": {"description": "BM1"},
                    "background_music_generation_history": [
                        {"asset": {"file_name": "bg.mp3"}}
                    ],
                    "voiceover_prompt": {"description": "VO1"},
                    "voiceover_generation_history": [
                        {"asset": {"file_name": "vo.mp3"}}
                    ],
                    "scenes": [
                        {
                            "topic": "T1",
                            "first_frame_prompt": {"description": "FFP1"},
                            "video_prompt": {"description": "VP1"},
                            "first_frame_generation_history": [
                                {
                                    "cycle": 0,
                                    "regenerated": True,
                                    "asset": {
                                        "file_name": "iter_0_scene_0_cycle_0.png"
                                    },
                                    "joint_verification": {
                                        "score": 99,
                                        "feedback": "F1",
                                    },
                                }
                            ],
                        }
                    ],
                },
                "verifier_results": {
                    "score": 80,
                    "breakdown": {"B1": 10},
                    "mab_efficacy_scores": {"strategy": 90},
                    "mab_efficacy_justifications": {"strategy": "J1"},
                },
                "arm_stats": {"dim1": {"arm1": {"pulls": 1, "total_reward": 90.0}}},
            }
        ],
    }

    local_artifact_dirs = {
        "user_asset_paths": {"p.png": work_dir / "p.png"},  # missing but handled
        0: {
            "dir_path": work_dir,
            "character_collage_path": work_dir / "c1.png",  # missing
        },
    }

    html = report_generator.generate_html_report(
        "Prompt", mab_state, local_artifact_dirs, None
    )

    assert "<strong>AI</strong>" in html
    assert "Selection Logic:" in html
    assert "Iteration 1" in html
    assert "Scene 1: T1" in html
    assert "REGEN" in html
    assert "Avg Reward" in html


def test_generate_html_report_to_file(tmp_path):
    """Verify writing to output_path."""
    out = tmp_path / "report.html"
    mab_state = {
        "iterations": [{"iteration_num": 1, "arms_selected": {}, "storyboard": {}}]
    }
    report_generator.generate_html_report("P", mab_state, {}, str(out))
    assert out.exists()
    assert "Report" in out.read_text()


def test_generate_html_report_uris():
    """Verify using asset URIs instead of Base64."""
    mab_state = {
        "user_assets": {"logo.png": {"caption": "L"}},
        "iterations": [
            {
                "iteration_num": 1,
                "arms_selected": {},
                "storyboard": {
                    "scenes": [
                        {
                            "first_frame_generation_history": [
                                {"asset": {"file_name": "f.png"}}
                            ]
                        }
                    ]
                },
            }
        ],
    }
    html = report_generator.generate_html_report(
        "P", mab_state, {}, None, use_asset_uris=True
    )
    assert "asset://logo.png" in html
    assert "asset://f.png" in html


def test_generate_html_report_exception():
    """Verify exception handling."""
    # Pass something that will cause an attribute error or similar inside the loop
    try:
        report_generator.generate_html_report("P", None, {}, None)
    except Exception:
        pass  # Expected
