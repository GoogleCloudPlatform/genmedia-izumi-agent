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

"""Unit tests for the MAB report generator."""

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
