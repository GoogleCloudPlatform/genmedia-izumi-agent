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

"""Unit tests for multi-armed bandit logic."""

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
