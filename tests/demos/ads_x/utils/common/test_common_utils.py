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

"""Tests for utilities shared across the ads_x agents and tools."""

from demos.backend.ads_x.utils.common import common_utils


def test_tidy_spacing_closes_the_gap_a_removed_word_leaves():
    """Both the storyboard and the tag stripper drop words mid-sentence."""
    assert (
        common_utils.tidy_spacing("the craftsman lowers the  onto the timber")
        == "the craftsman lowers the onto the timber"
    )
    assert common_utils.tidy_spacing("the tin .") == "the tin."
    assert common_utils.tidy_spacing("  padded  ") == "padded"


def test_tidy_spacing_leaves_ordinary_prose_alone():
    text = "A slow dolly past the armchair, catching the light."
    assert common_utils.tidy_spacing(text) == text


def test_tidy_spacing_keeps_paragraph_breaks():
    # Prompts carry deliberate line structure; only runs of spaces close up.
    assert common_utils.tidy_spacing("line one\n\nline  two") == "line one\n\nline two"
