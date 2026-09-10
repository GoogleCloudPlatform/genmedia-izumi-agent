"""The Look fallback must be reproducible, not random."""

from demos.backend.ads_x.tools.storyboard.production_tools import _score_look

CANDIDATES = [{"name": f"Look {i}", "tones": [], "keywords": []} for i in range(10)]


def test_unmatched_brief_is_deterministic():
    # No tag overlap -> falls through to the hash-based pick.
    first = _score_look(CANDIDATES, "zzz nothing matches", "qqq")
    for _ in range(20):
        assert _score_look(CANDIDATES, "zzz nothing matches", "qqq") == first


def test_different_briefs_can_differ():
    picks = {_score_look(CANDIDATES, f"brief {i}", "tone")["name"] for i in range(25)}
    assert len(picks) > 1, "hash pick should spread across candidates"


def test_tag_match_still_wins():
    candidates = [
        {"name": "Generic", "tones": [], "keywords": []},
        {"name": "Luxury", "tones": ["premium"], "keywords": ["watch"]},
    ]
    assert _score_look(candidates, "a premium watch", "elegant")["name"] == "Luxury"
