"""The audio track of a UGC clip must be requested, and then recognised.

Two halves of one feature, which had drifted apart:

* the generator decides whether a clip needs its own audio (for UGC and
  lip-sync, where that audio is what ends up on the timeline) - and that
  decision has to reach the model, or the clip comes back silent;
* the stitcher then has to know whether the clip actually has audio, or it
  lays down an empty track.
"""

from types import SimpleNamespace

import pytest

from demos.backend.ads_x.tools.generation.stitching_tools import _clip_carries_audio


def _asset(mime_type="video/mp4", generate_audio=None, with_metadata=True):
    metadata = SimpleNamespace(generate_audio=generate_audio) if with_metadata else None
    return SimpleNamespace(mime_type=mime_type, generation_metadata=metadata)


# --------------------------------------------------------------------------
# The stitcher's side
# --------------------------------------------------------------------------


def test_a_clip_generated_with_audio_is_used():
    assert _clip_carries_audio(_asset(generate_audio=True)) is True


def test_a_clip_generated_without_audio_is_skipped():
    # This is the case the check exists for: laying an empty track over a
    # silent clip is pure waste.
    assert _clip_carries_audio(_asset(generate_audio=False)) is False


@pytest.mark.parametrize(
    "asset",
    [
        _asset(generate_audio=None),  # backend did not report it
        _asset(with_metadata=False),  # uploaded asset, no generation metadata
    ],
)
def test_unknown_is_treated_as_maybe_not_as_no(asset):
    # Erring towards keeping audio preserves the older behaviour; erring the
    # other way would silently drop real audio from uploaded clips.
    assert _clip_carries_audio(asset) is True


def test_a_still_image_never_contributes_audio():
    assert _clip_carries_audio(_asset(mime_type="image/png")) is False
    assert (
        _clip_carries_audio(_asset(mime_type="image/png", generate_audio=True)) is False
    )


def test_a_missing_mime_type_does_not_raise():
    assert _clip_carries_audio(SimpleNamespace()) is False


# --------------------------------------------------------------------------
# The generator's side: the request has to reach the model
# --------------------------------------------------------------------------


def test_the_unified_interface_can_ask_for_audio():
    """Without this parameter the decision cannot leave the caller."""
    import inspect

    from mediagent_kit.services.interfaces import MediaGenerationServiceInterface

    params = inspect.signature(
        MediaGenerationServiceInterface.generate_video
    ).parameters
    assert "generate_audio" in params
    assert params["generate_audio"].default is False, "silent unless asked"


def test_every_implementation_accepts_it():
    import inspect

    from mediagent_kit.services.creative_studio.cs_media_generation_service import (
        CSMediaGenerationService,
    )
    from mediagent_kit.services.izumi.media_generation_service import (
        IzumiMediaGenerationService,
    )

    for impl in (IzumiMediaGenerationService, CSMediaGenerationService):
        params = inspect.signature(impl.generate_video).parameters
        assert "generate_audio" in params, f"{impl.__name__} drops the request"


def test_the_scene_generator_passes_the_flag_it_computes():
    """It used to compute should_generate_audio and then never use it."""
    import inspect

    from demos.backend.ads_x.utils.common import scene_generation_utils

    source = inspect.getsource(scene_generation_utils)
    assert "should_generate_audio = bool(" in source, "fixture assumption"
    assert (
        "generate_audio=should_generate_audio" in source
    ), "the computed decision never reaches generate_video"


def test_generation_metadata_can_carry_the_answer():
    from mediagent_kit.services.types.common import GenerationMetadata

    assert GenerationMetadata(source="izumi").generate_audio is None
    assert GenerationMetadata(source="izumi", generate_audio=True).generate_audio
