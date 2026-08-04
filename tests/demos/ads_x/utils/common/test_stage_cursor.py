"""Tests for the pipeline stage cursor."""

from types import SimpleNamespace

from demos.backend.ads_x.utils.common.common_utils import (
    STAGE_COMPLETED_KEY,
    mark_stage_completed,
)


def _ctx(initial=None):
    return SimpleNamespace(state=dict(initial or {}))


def test_marks_stage():
    ctx = _ctx()
    mark_stage_completed(ctx, "parameters")
    assert ctx.state[STAGE_COMPLETED_KEY] == "parameters"


def test_cursor_advances_forward():
    ctx = _ctx()
    for stage in ("parameters", "user_assets", "strategy", "storyboard"):
        mark_stage_completed(ctx, stage)
    assert ctx.state[STAGE_COMPLETED_KEY] == "storyboard"


def test_cursor_never_rewinds():
    # Re-running an earlier stage (an edit or repair) must not make completed
    # downstream work look undone.
    ctx = _ctx({STAGE_COMPLETED_KEY: "generation"})
    mark_stage_completed(ctx, "storyboard")
    assert ctx.state[STAGE_COMPLETED_KEY] == "generation"


def test_unknown_stage_is_ignored():
    ctx = _ctx({STAGE_COMPLETED_KEY: "strategy"})
    mark_stage_completed(ctx, "not_a_stage")
    assert ctx.state[STAGE_COMPLETED_KEY] == "strategy"


def test_tolerates_missing_context():
    mark_stage_completed(None, "parameters")  # must not raise
    mark_stage_completed(SimpleNamespace(state=None), "parameters")
