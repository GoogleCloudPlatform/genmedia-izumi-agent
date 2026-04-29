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

"""Comprehensive unit tests for multi-armed bandit logic."""

from ads_codirector.mab.bandit import UCBBandit, EpsilonGreedyBandit


def test_ucb_initialization_cold_start():
    """Verify that UCB tries all arms at least once (random selection)."""
    arms = {"dim": ["arm1", "arm2", "arm3"]}
    bandit = UCBBandit(arms=arms)
    selected = bandit.select_arm("dim")
    assert selected in arms["dim"]
    bandit.update_reward(1, {"dim": selected}, {"score": 80})
    selected2 = bandit.select_arm("dim")
    assert selected != selected2


def test_ucb_warm_start_priority():
    """Verify that UCB picks the recommended arm during cold start."""
    arms = {"dim": ["arm1", "arm2", "arm3"]}
    recs = {"dim": "arm3"}
    bandit = UCBBandit(arms=arms, recommendations=recs)
    selected = bandit.select_arm("dim")
    assert selected == "arm3"
    bandit.update_reward(1, {"dim": "arm3"}, {"score": 100})
    selected2 = bandit.select_arm("dim")
    assert selected2 in ["arm1", "arm2"]


def test_factored_reward_assignment():
    """Verify that dimension-specific scores take precedence over global scores."""
    arms = {"creative_strategy": ["informational"]}
    bandit = UCBBandit(arms=arms)
    verification = {"score": 50, "mab_efficacy_scores": {"creative_strategy": 99}}
    bandit.update_reward(1, {"creative_strategy": "informational"}, verification)
    stats = bandit.arm_stats["creative_strategy"]["informational"]
    assert stats["rewards"][0] == 99
    verification_no_efficacy = {"score": 75}
    bandit.update_reward(
        2, {"creative_strategy": "informational"}, verification_no_efficacy
    )
    assert stats["rewards"][1] == 75


def test_epsilon_greedy_exploration():
    """Verify that Epsilon-Greedy performs exploration."""
    arms = {"dim": ["arm1", "arm2"]}
    bandit = EpsilonGreedyBandit(arms=arms, epsilon=1.0)
    bandit.arm_stats = {
        "dim": {"arm1": {"pulls": 10, "rewards": [100] * 10, "total_reward": 1000.0}}
    }
    selections = set()
    for _ in range(100):
        selections.add(bandit.select_arm("dim"))
    assert "arm2" in selections


def test_ucb_factored_update():
    """Verify that UCB independently updates arms using efficacy scores."""
    arms = {
        "creative_strategy": ["informational", "transformational"],
        "narrative_mode": ["analytical", "vignette"],
    }
    bandit = UCBBandit(arms=arms, c=2.0)
    choices = {"creative_strategy": "informational", "narrative_mode": "analytical"}
    verification_result = {
        "score": 90,
        "mab_efficacy_scores": {"creative_strategy": 40, "narrative_mode": 95},
    }
    bandit.update_reward(
        iteration_num=1, mab_choices=choices, verification_result=verification_result
    )
    strat_stats = bandit.arm_stats["creative_strategy"]["informational"]
    assert strat_stats["rewards"][0] == 40
    assert strat_stats["total_reward"] == 40.0
    mode_stats = bandit.arm_stats["narrative_mode"]["analytical"]
    assert mode_stats["rewards"][0] == 95
    assert mode_stats["total_reward"] == 95.0


def test_epsilon_greedy_init():
    """Verify default initialization of EpsilonGreedyBandit."""
    arms = {"dim": ["a", "b"]}
    bandit = EpsilonGreedyBandit(arms=arms)
    assert bandit.epsilon == 0.1
    assert bandit.arm_stats == {}
    assert bandit.iterations == []
    assert bandit.recommendations == {}


def test_epsilon_greedy_no_arms():
    """Verify handling of invalid stage names."""
    bandit = EpsilonGreedyBandit(arms={"dim": ["a"]})
    assert bandit.select_arm("invalid") == ""


def test_epsilon_greedy_exploitation_best_arm():
    """Verify that exploitation picks the arm with the highest average reward."""
    arms = {"dim": ["a", "b"]}
    stats = {
        "dim": {
            "a": {"pulls": 10, "rewards": [10] * 10},  # Avg: 10
            "b": {"pulls": 10, "rewards": [20] * 10},  # Avg: 20
        }
    }
    bandit = EpsilonGreedyBandit(arms=arms, epsilon=0.0, arm_stats=stats)
    # With epsilon 0, it should always pick 'b'
    for _ in range(10):
        assert bandit.select_arm("dim") == "b"


def test_epsilon_greedy_fallback_to_total_reward():
    """Verify fallback to 'total_reward' when 'rewards' list is missing."""
    arms = {"dim": ["a"]}
    stats = {"dim": {"a": {"pulls": 5, "total_reward": 50.0}}}  # Avg: 10
    bandit = EpsilonGreedyBandit(arms=arms, epsilon=0.0, arm_stats=stats)
    assert bandit.select_arm("dim") == "a"


def test_epsilon_greedy_update_reward_nested():
    """Verify reward extraction from nested video dict."""
    bandit = EpsilonGreedyBandit(arms={"dim": ["a"]})
    verification = {"video": {"score": 85}}
    bandit.update_reward(1, {"dim": "a"}, verification)
    assert bandit.arm_stats["dim"]["a"]["rewards"][0] == 85


def test_epsilon_greedy_update_reward_object():
    """Verify reward extraction from object with .score attribute."""

    class MockResult:
        def __init__(self, score):
            self.score = score

    bandit = EpsilonGreedyBandit(arms={"dim": ["a"]})
    bandit.update_reward(1, {"dim": "a"}, MockResult(92))
    assert bandit.arm_stats["dim"]["a"]["rewards"][0] == 92


def test_epsilon_greedy_get_best_arms():
    """Verify get_best_arms returns correct mapping."""
    arms = {"s1": ["a", "b"], "s2": ["c", "d"]}
    stats = {
        "s1": {"a": {"pulls": 1, "rewards": [10]}, "b": {"pulls": 1, "rewards": [20]}},
        "s2": {
            "c": {"pulls": 1, "total_reward": 50},
            "d": {"pulls": 1, "total_reward": 10},
        },
    }
    bandit = EpsilonGreedyBandit(arms=arms, arm_stats=stats)
    best = bandit.get_best_arms()
    assert best == {"s1": "b", "s2": "c"}


def test_ucb_no_arms():
    """Verify UCB handling of invalid stage names."""
    bandit = UCBBandit(arms={"dim": ["a"]})
    assert bandit.select_arm("invalid") == ""


def test_ucb_score_calculation():
    """Verify UCB score formula logic."""
    arms = {"dim": ["a", "b"]}
    stats = {
        "dim": {
            "a": {"pulls": 2, "rewards": [10, 10]},
            "b": {"pulls": 8, "rewards": [20] * 8},
        }
    }
    bandit = UCBBandit(arms=arms, arm_stats=stats, c=2.0)
    assert bandit.select_arm("dim") == "b"
    bandit.c = 100.0
    assert bandit.select_arm("dim") == "a"


def test_ucb_fallback_total_reward():
    """Verify UCB fallback to total_reward."""
    arms = {"dim": ["a"]}
    stats = {"dim": {"a": {"pulls": 1, "total_reward": 100}}}
    bandit = UCBBandit(arms=arms, arm_stats=stats)
    assert bandit.select_arm("dim") == "a"


def test_epsilon_greedy_cold_start_recommendation():
    """Verify that EpsilonGreedy prioritizes recommended arm in cold start."""
    arms = {"dim": ["a", "b"]}
    recs = {"dim": "b"}
    bandit = EpsilonGreedyBandit(arms=arms, recommendations=recs)
    assert bandit.select_arm("dim") == "b"


def test_epsilon_greedy_exploitation_safety():
    """Verify safety check if pulls is 0 during exploitation."""
    arms = {"dim": ["a"]}
    # Force exploitation with stats but pulls=0 (shouldn't happen but for coverage)
    stats = {"dim": {"a": {"pulls": 0}}}
    bandit = EpsilonGreedyBandit(arms=arms, epsilon=0.0, arm_stats=stats)
    assert bandit.select_arm("dim") == "a"


def test_ucb_cold_start_recommendation():
    """Verify that UCB prioritizes recommended arm in cold start."""
    arms = {"dim": ["a", "b"]}
    recs = {"dim": "b"}
    bandit = UCBBandit(arms=arms, recommendations=recs)
    assert bandit.select_arm("dim") == "b"


def test_ucb_mean_reward_fallback():
    """Verify UCB score calculation fallback to total_reward."""
    arms = {"dim": ["a"]}
    stats = {"dim": {"a": {"pulls": 1, "total_reward": 100}}}
    bandit = UCBBandit(arms=arms, arm_stats=stats)
    assert bandit.select_arm("dim") == "a"


def test_ucb_empty_arms_error():
    """Verify UCB error handling for empty stage arms."""
    bandit = UCBBandit(arms={})
    assert bandit.select_arm("missing") == ""


def test_ucb_update_reward_variants():
    """Verify UCB reward extraction variants."""
    bandit = UCBBandit(arms={"dim": ["a"]})
    bandit.update_reward(1, {"dim": "a"}, {"video": {"score": 70}})
    assert bandit.arm_stats["dim"]["a"]["rewards"][0] == 70
    bandit.update_reward(2, {"dim": "a"}, {})
    assert bandit.arm_stats["dim"]["a"]["rewards"][1] == 0
