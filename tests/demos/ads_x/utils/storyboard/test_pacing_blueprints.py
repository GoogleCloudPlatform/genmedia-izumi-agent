import pytest
from demos.backend.ads_x.utils.storyboard.pacing_blueprints import (
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
    # [3.0, 3.0, 3.0, 3.0] is in PACING_PRESETS["12s"][4]
    assert matches_any_preset(12, [3.0, 3.0, 3.0, 3.0]) is True
    assert matches_any_preset(12, [1.0, 1.0, 1.0, 9.0]) is False
    assert matches_any_preset(0, [1.0]) is False


def test_get_valid_scene_counts_for_duration():
    assert get_valid_scene_counts_for_duration(12) == [4]
    counts_15 = get_valid_scene_counts_for_duration(15)
    assert 4 in counts_15
    assert 5 in counts_15
    # Six scenes would need 18s once no scene may fall below three seconds.
    assert 6 not in counts_15
    assert get_valid_scene_counts_for_duration(0) == [4]


def test_get_random_blueprint_for_duration():
    blueprint = get_random_blueprint_for_duration(12)
    assert len(blueprint) == 4
    assert sum(blueprint) == 12.0

    # The fallback has to be renderable too; a 2s scene is not.
    blueprint_zero = get_random_blueprint_for_duration(0)
    assert blueprint_zero == [3.0, 3.0, 3.0, 3.0]


# ---------------------------------------------------------------------------
# Renderable minimum
#
# No video model renders a clip shorter than three seconds. Veo accepts 4, 6
# or 8 and rejects anything else outright; Omni accepts whole seconds from 3
# to 10. A scene planned below three seconds cannot be produced as planned by
# either, so nothing should plan one.
# ---------------------------------------------------------------------------

MIN_SCENE_SECONDS = 3.0


def test_no_pacing_preset_plans_a_scene_below_the_minimum():
    from demos.backend.ads_x.utils.storyboard.pacing_blueprints import (
        PACING_PRESETS,
    )

    for duration, by_count in PACING_PRESETS.items():
        for arrays in by_count.values():
            for array in arrays:
                assert min(array) >= MIN_SCENE_SECONDS, (
                    f"{duration} preset {array} plans a scene shorter than "
                    "any model can render"
                )


def test_every_pacing_preset_still_sums_to_its_target():
    from demos.backend.ads_x.utils.storyboard.pacing_blueprints import (
        PACING_PRESETS,
    )

    for duration, by_count in PACING_PRESETS.items():
        target = float(duration.rstrip("s"))
        for arrays in by_count.values():
            for array in arrays:
                assert (
                    abs(sum(array) - target) < 0.05
                ), f"{duration} preset {array} sums to {sum(array)}"


def test_no_template_plans_a_scene_below_the_minimum():
    from demos.backend.ads_x.utils.storyboard.template_library import (
        get_all_templates,
    )

    for template in get_all_templates():
        durations = [s.duration_seconds for s in template.scene_structure or []]
        if not durations:
            continue
        assert min(durations) >= MIN_SCENE_SECONDS, (
            f"template '{template.template_name}' plans a " f"{min(durations)}s scene"
        )


def test_every_template_matches_its_declared_duration():
    from demos.backend.ads_x.utils.storyboard.template_library import (
        get_all_templates,
    )

    for template in get_all_templates():
        durations = [s.duration_seconds for s in template.scene_structure or []]
        if not durations:
            continue
        assert abs(sum(durations) - template.target_duration_seconds) < 0.05, (
            f"template '{template.template_name}' declares "
            f"{template.target_duration_seconds}s but its scenes sum to "
            f"{sum(durations)}s"
        )


def test_generated_blueprints_are_renderable():
    from demos.backend.ads_x.utils.storyboard.pacing_blueprints import (
        get_random_blueprint_for_duration,
    )

    for target in (0, 10, 12, 15, 18, 24, 30):
        for _ in range(25):
            assert min(get_random_blueprint_for_duration(float(target))) >= (
                MIN_SCENE_SECONDS
            )


def test_no_look_asks_the_music_model_to_sing():
    """Lyria 3 renders vocals when asked for them, and vocals compete with the
    voiceover the bed plays beneath."""
    from demos.backend.ads_x.utils.storyboard.production_presets import (
        PRODUCTION_LOOKS,
    )

    for look in PRODUCTION_LOOKS:
        sonic = (look.get("recipe") or {}).get("sonic_landscape") or ""
        assert "vocal" not in sonic.lower(), (
            f"Look '{look.get('name')}' asks for vocals in its music bed: " f"{sonic}"
        )
