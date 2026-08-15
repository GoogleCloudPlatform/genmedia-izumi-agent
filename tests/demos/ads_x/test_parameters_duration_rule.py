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

"""Guards the duration rule against example leakage.

The rule used to read: Extract if mentioned (e.g., "15s"). Default to `12s`.
A brief naming no duration then came back as 15s, because the only concrete
value in the rule was the example and the model copied it. It happened on
roughly one run in three, which made it look like a model quirk rather than a
prompt defect. Keep concrete durations out of the rule except the default.
"""

import re

from demos.backend.ads_x.instructions.parameters import parameters_instruction


def _duration_rule() -> str:
    for line in parameters_instruction.INSTRUCTION.splitlines():
        if line.strip().startswith("- **Duration**"):
            return line
    raise AssertionError("the duration rule is gone; this guard needs updating")


def test_the_rule_states_the_default():
    assert "12s" in _duration_rule()


def test_the_rule_offers_no_other_duration_to_copy():
    durations = set(re.findall(r"\b\d+\s*s\b", _duration_rule()))
    assert durations <= {"12s"}, (
        f"the duration rule mentions {sorted(durations)}; a value other than "
        "the default is liable to be copied into a brief that named none"
    )
