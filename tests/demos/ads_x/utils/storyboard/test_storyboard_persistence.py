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

"""Tests for pushing the session storyboard to Creative Studio."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from demos.backend.ads_x.utils.storyboard import storyboard_persistence


def _ctx(state=None):
    base = {"workspace_id": "42"}
    base.update(state or {})
    return SimpleNamespace(state=base)


def _storyboard(**overrides):
    sb = {"campaign_title": "Test Campaign", "scenes": [{"scene_id": "scene_1"}]}
    sb.update(overrides)
    return sb


def _service(returns=None, raises=None):
    """A stand-in storyboard service, patched in where the helper looks it up."""
    service = AsyncMock()
    if raises is not None:
        service.save_storyboard.side_effect = raises
    else:
        service.save_storyboard.return_value = returns
    return (
        patch(
            "mediagent_kit.services.aio.get_storyboard_service", return_value=service
        ),
        service,
    )


async def test_the_storyboard_is_saved_and_its_id_returned():
    patcher, service = _service(returns={"storyboard_id": 17})
    ctx, storyboard = _ctx(), _storyboard()

    with patcher:
        result = await storyboard_persistence.save_to_creative_studio(ctx, storyboard)

    service.save_storyboard.assert_awaited_once()
    assert result == "17"


async def test_the_assigned_id_is_written_back_for_later_callers():
    """The stitch reads this back to revise the record rather than add one."""
    patcher, _ = _service(returns={"storyboard_id": 17})
    ctx, storyboard = _ctx(), _storyboard()

    with patcher:
        await storyboard_persistence.save_to_creative_studio(ctx, storyboard)

    assert ctx.state[storyboard_persistence.CURRENT_STORYBOARD_ID_KEY] == "17"
    assert storyboard["storyboard_id"] == "17"
    assert ctx.state["storyboard"] is storyboard


async def test_workspace_and_session_are_stamped_on_before_saving():
    # Neither is part of the storyboard the agents write, but the backend
    # keys the record by them.
    patcher, service = _service(returns={"storyboard_id": 1})
    ctx, storyboard = _ctx(), _storyboard()

    with patcher:
        await storyboard_persistence.save_to_creative_studio(ctx, storyboard)

    sent = service.save_storyboard.await_args.args[0]
    assert sent["workspace_id"] == "42"
    assert sent["session_id"]


async def test_a_second_save_revises_the_same_record():
    """Create-or-replace: the gate saves, then the stitch saves again."""
    patcher, service = _service(returns={"storyboard_id": 17})
    ctx, storyboard = _ctx(), _storyboard()

    with patcher:
        await storyboard_persistence.save_to_creative_studio(ctx, storyboard)
        await storyboard_persistence.save_to_creative_studio(ctx, storyboard)

    second = service.save_storyboard.await_args.args[0]
    assert second["storyboard_id"] == "17", "the second save must not create a copy"


@pytest.mark.parametrize(
    "returned, expected",
    [
        ({"storyboard_id": 17}, "17"),
        ({"id": 18}, "18"),
        (SimpleNamespace(storyboard_id=19), "19"),
    ],
)
async def test_the_id_is_read_from_either_shape_the_backend_answers_with(
    returned, expected
):
    patcher, _ = _service(returns=returned)

    with patcher:
        result = await storyboard_persistence.save_to_creative_studio(
            _ctx(), _storyboard()
        )

    assert result == expected


# --------------------------------------------------------------------------
# Failure
#
# Creative Studio being unreachable must not cost the session its storyboard:
# the caller either renders it anyway or asks a human to review it.
# --------------------------------------------------------------------------


async def test_a_failed_save_keeps_the_id_the_storyboard_already_had():
    patcher, _ = _service(raises=RuntimeError("backend down"))
    ctx = _ctx()

    with patcher:
        result = await storyboard_persistence.save_to_creative_studio(
            ctx, _storyboard(storyboard_id="7")
        )

    assert result == "7"


async def test_a_failed_save_of_a_new_storyboard_reports_no_id():
    patcher, _ = _service(raises=RuntimeError("backend down"))
    ctx = _ctx()

    with patcher:
        result = await storyboard_persistence.save_to_creative_studio(
            ctx, _storyboard()
        )

    assert result is None
    assert storyboard_persistence.CURRENT_STORYBOARD_ID_KEY not in ctx.state


async def test_an_unresolvable_workspace_does_not_attempt_a_save():
    patcher, service = _service(returns={"storyboard_id": 1})

    with (
        patcher,
        patch.object(
            storyboard_persistence,
            "resolve_workspace_id",
            return_value=("", "no workspace"),
        ),
    ):
        result = await storyboard_persistence.save_to_creative_studio(
            _ctx(), _storyboard()
        )

    service.save_storyboard.assert_not_awaited()
    assert result is None


async def test_a_storyboard_model_object_is_saved_like_a_dict():
    # The native path holds a Storyboard model rather than a plain dict.
    patcher, service = _service(returns=SimpleNamespace(storyboard_id=21))
    ctx = _ctx()
    storyboard = SimpleNamespace(storyboard_id=None, scenes=[])

    with patcher:
        result = await storyboard_persistence.save_to_creative_studio(ctx, storyboard)

    assert result == "21"
    assert storyboard.storyboard_id == "21"
    assert storyboard.workspace_id == "42"
    service.save_storyboard.assert_awaited_once()
