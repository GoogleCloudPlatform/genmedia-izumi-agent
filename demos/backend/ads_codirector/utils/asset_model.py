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

"""Model for annotated reference visuals."""

from typing import Literal

import pydantic

from . import common_utils


class AnnotatedAsset(pydantic.BaseModel):
    """Annotated reference visual with semantic roles."""

    file_name: str = pydantic.Field(description="The original filename of the asset.")
    caption: str = pydantic.Field(
        description="A detailed visual description of the primary product or subject."
    )
    semantic_role: Literal["product", "logo", "character"] = pydantic.Field(
        description="The semantic role of the asset in the campaign."
    )


DESCRIPTION = common_utils.describe_pydantic_model(AnnotatedAsset)
