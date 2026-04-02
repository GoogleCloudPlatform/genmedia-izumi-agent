import pytest
from demos.backend.ads_x_template.utils.storyboard.pacing_blueprints import (
    get_pacing_options_json,
    get_blueprint_for_count,
    matches_any_preset,
    get_valid_scene_counts_for_duration,
    get_random_blueprint_for_duration,
    PACING_PRESETS,
)

def test_get_pacing_options_json():
    json_str = get_pacing_options_json()
    assert "12s" in json_str
    assert "15s" in json_str


def test_get_blueprint_for_count_success():
    # 12s, 4 scenes should find a preset
    blueprint = get_blueprint_for_count(12, 4)
    assert len(blueprint) == 4
    assert sum(blueprint) == 12.0


def test_get_blueprint_for_count_fallback():
    # 12s, 5 scenes (not in preset for 12s) should use manual distribution
    blueprint = get_blueprint_for_count(12, 5)
    assert len(blueprint) == 5
    assert sum(blueprint) == 12.0


def test_get_blueprint_for_count_invalid():
    assert get_blueprint_for_count(0, 4) == []
    assert get_blueprint_for_count(12, 0) == []


def test_matches_any_preset():
    # [2.5, 3.5, 3.5, 2.5] is in PACING_PRESETS["12s"][4]
    assert matches_any_preset(12, [2.5, 3.5, 3.5, 2.5]) is True
    assert matches_any_preset(12, [1.0, 1.0, 1.0, 9.0]) is False
    assert matches_any_preset(0, [1.0]) is False


def test_get_valid_scene_counts_for_duration():
    assert get_valid_scene_counts_for_duration(12) == [4]
    counts_15 = get_valid_scene_counts_for_duration(15)
    assert 4 in counts_15
    assert 5 in counts_15
    assert 6 in counts_15
    assert get_valid_scene_counts_for_duration(0) == [4]


def test_get_random_blueprint_for_duration():
    blueprint = get_random_blueprint_for_duration(12)
    assert len(blueprint) == 4
    assert sum(blueprint) == 12.0

    blueprint_zero = get_random_blueprint_for_duration(0)
    assert blueprint_zero == [2.0, 3.0, 4.0, 3.0]
