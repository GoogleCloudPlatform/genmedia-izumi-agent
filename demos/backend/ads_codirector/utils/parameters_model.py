# Copyright 2025 Google LLC
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

"""Model containing ad parameters."""

from typing import Literal

import pydantic

from . import common_utils


class Parameters(pydantic.BaseModel):
    """Structured constraints (p_user_hat)."""

    brand: str = pydantic.Field(
        description="The brand name or identity identified from the user input."
    )
    product: str = pydantic.Field(
        description="The primary product or service being advertised."
    )
    demographics: str = pydantic.Field(
        description="Target audience and demographic information."
    )
    campaign_name: str = pydantic.Field(
        description=(
            "A short, descriptive name for the campaign."
            " If none is provided, you MUST deduce it from the campaign brief itself."
        )
    )
    target_duration: str = pydantic.Field(
        description=(
            "Target duration of the final video in seconds."
            " If none is provided, you MUST default to '30s'."
        ),
        default="30s",
    )
    target_orientation: Literal["landscape", "portrait"] = pydantic.Field(
        description=(
            "Target orientation of the final video (one of 'landscape' or 'portrait')."
            " If none is provided, you MUST default to 'landscape'."
        ),
        default="landscape",
    )


DESCRIPTION = common_utils.describe_pydantic_model(Parameters)
