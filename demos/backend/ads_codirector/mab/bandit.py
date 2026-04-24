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

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class EpsilonGreedyBandit:
    """An Epsilon-Greedy multi-armed bandit."""

    def __init__(
        self,
        arms: dict[str, Any],
        epsilon: float = 0.1,
        arm_stats: dict[str, Any] | None = None,
        iterations: list[dict[str, Any]] | None = None,
        recommendations: dict[str, str] | None = None,
    ):
        self.arms = arms
        self.epsilon = epsilon
        self.arm_stats = arm_stats if arm_stats is not None else {}
        self.iterations = iterations if iterations is not None else []
        self.recommendations = recommendations if recommendations is not None else {}

    def select_arm(self, stage: str) -> str:
        """Selects an arm for a given stage using Epsilon-Greedy."""
        stage_arms = self.arms.get(stage, [])
        if not stage_arms:
            logger.error(f"No arms found for stage: {stage}")
            return ""

        # Check for unpulled arms first
        stage_stats = self.arm_stats.get(stage, {})
        unpulled_arms = [arm for arm in stage_arms if arm not in stage_stats]
        
        if unpulled_arms:
            # PRIORITIZE RECOMMENDED ARM (Warm Start Alignment)
            recommended_arm = self.recommendations.get(stage)
            if recommended_arm and recommended_arm in unpulled_arms:
                logger.info(f"MAB ({stage}): Cold start - selecting recommended arm -> {recommended_arm}")
                return recommended_arm

            selected_arm = random.choice(unpulled_arms)
            logger.info(f"MAB ({stage}): Cold start - randomly selecting untried arm -> {selected_arm}")
            return selected_arm

        if random.random() < self.epsilon:
            # Exploration: Choose a random arm
            selected_arm = random.choice(stage_arms)
            logger.info(f"MAB ({stage}): Exploring with random arm -> {selected_arm}")
            return selected_arm

        # Exploitation: Choose the best-known arm
        best_arm = random.choice(stage_arms)
        max_avg_reward = -1

        # Find the arm with the highest average reward
        for arm in stage_arms:
            arm_stats = stage_stats.get(arm, {"pulls": 0, "rewards": []})
            # This should not happen due to unpulled_arms check above, but as a safety:
            if arm_stats["pulls"] == 0:
                logger.info(f"MAB ({stage}): Exploiting with unpulled arm -> {arm}")
                return arm

            if "rewards" in arm_stats and arm_stats["rewards"]:
                avg_reward = sum(arm_stats["rewards"]) / arm_stats["pulls"]
            else:
                # FALLBACK: Use the seeded 'total_reward' if the list doesn't exist yet.
                avg_reward = arm_stats.get("total_reward", 0) / arm_stats["pulls"]
            
            if avg_reward > max_avg_reward:
                max_avg_reward = avg_reward
                best_arm = arm

        logger.info(f"MAB ({stage}): Exploiting with best arm -> {best_arm} (Avg Reward: {max_avg_reward:.2f})")
        return best_arm

    def update_reward(
        self,
        iteration_num: int,
        mab_choices: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Updates the reward and history for the chosen arms and returns the new state."""
        # FACTORED REWARD: Extract dimension-specific efficacy scores if available
        # This aligns with the 'Independent Credit Assignment' requirement in the paper.
        efficacy_scores = verification_result.get("mab_efficacy_scores", {})
        
        # Robustly extract the global score as fallback
        if isinstance(verification_result, dict):
            global_reward = verification_result.get("score", 0)
            if global_reward == 0 and "video" in verification_result:
                 global_reward = verification_result["video"].get("score", 0)
        else:
            global_reward = getattr(verification_result, "score", 0)

        # Update individual arm statistics
        for stage, arm in mab_choices.items():
            # Use dimension-specific score if present, otherwise fallback to global
            reward_score = efficacy_scores.get(stage, global_reward)

            if stage not in self.arm_stats:
                self.arm_stats[stage] = {}
            if arm not in self.arm_stats[stage]:
                self.arm_stats[stage][arm] = {"pulls": 0, "rewards": []}

            if "rewards" not in self.arm_stats[stage][arm]:
                self.arm_stats[stage][arm]["rewards"] = []
            
            self.arm_stats[stage][arm]["pulls"] += 1
            self.arm_stats[stage][arm]["rewards"].append(reward_score)
            
            # Also maintain total_reward for compatibility with selection logic
            if "total_reward" not in self.arm_stats[stage][arm]:
                self.arm_stats[stage][arm]["total_reward"] = 0.0
            self.arm_stats[stage][arm]["total_reward"] += float(reward_score)

        return {"arm_stats": self.arm_stats, "iterations": self.iterations}

    def get_best_arms(self) -> dict[str, Any]:
        """Returns the best arm for each stage based on average reward from arm_stats."""
        best_arms = {}
        for stage, stage_arms_config in self.arms.items():
            stage_state = self.arm_stats.get(stage, {})
            best_arm = None
            max_avg_reward = -1
            for arm in stage_arms_config:
                arm_stats = stage_state.get(arm, {"pulls": 0, "rewards": []})
                if arm_stats["pulls"] > 0:
                    if "rewards" in arm_stats and arm_stats["rewards"]:
                        avg_reward = sum(arm_stats["rewards"]) / arm_stats["pulls"]
                    else:
                        avg_reward = arm_stats.get("total_reward", 0) / arm_stats["pulls"]
                    
                    if avg_reward > max_avg_reward:
                        max_avg_reward = avg_reward
                        best_arm = arm
            best_arms[stage] = best_arm
        return best_arms


class UCBBandit:
    """A Upper-Confidence-Bound (UCB) multi-armed bandit."""

    def __init__(
        self,
        arms: dict[str, Any],
        c: float = 2.0,
        arm_stats: dict[str, Any] | None = None,
        iterations: list[dict[str, Any]] | None = None,
        recommendations: dict[str, str] | None = None,
    ):
        self.arms = arms
        self.c = c
        self.arm_stats = arm_stats if arm_stats is not None else {}
        self.iterations = iterations if iterations is not None else []
        self.recommendations = recommendations if recommendations is not None else {}

    def select_arm(self, stage: str) -> str:
        """Selects an arm for a given stage using the UCB algorithm."""
        stage_arms = self.arms.get(stage, [])
        if not stage_arms:
            logger.error(f"No arms found for stage: {stage}")
            return ""

        # First, check if there are any arms that have never been pulled.
        # UCB requires that every arm is tried at least once.
        # We pick one randomly among the unpulled arms to avoid deterministic ordering.
        stage_stats = self.arm_stats.get(stage, {})
        unpulled_arms = [arm for arm in stage_arms if arm not in stage_stats]
        
        if unpulled_arms:
            # PRIORITIZE RECOMMENDED ARM (Warm Start Alignment)
            recommended_arm = self.recommendations.get(stage)
            if recommended_arm and recommended_arm in unpulled_arms:
                logger.info(f"MAB ({stage}): Cold start - selecting recommended arm -> {recommended_arm}")
                return recommended_arm

            selected_arm = random.choice(unpulled_arms)
            logger.info(f"MAB ({stage}): Trying unpulled arm (random choice) -> {selected_arm}")
            return selected_arm

        best_arm = random.choice(stage_arms)
        max_ucb_score = -1
        total_pulls_for_stage = sum(stats["pulls"] for stats in stage_stats.values())

        for arm in stage_arms:
            arm_stats = stage_stats[arm]
            num_pulls = arm_stats["pulls"]

            if "rewards" in arm_stats and arm_stats["rewards"]:
                mean_reward = sum(arm_stats["rewards"]) / num_pulls
            else:
                mean_reward = arm_stats.get("total_reward", 0) / num_pulls
            
            exploration_component = self.c * math.sqrt(
                math.log(total_pulls_for_stage) / num_pulls
            )
            ucb_score = mean_reward + exploration_component

            if ucb_score > max_ucb_score:
                max_ucb_score = ucb_score
                best_arm = arm

        logger.info(
            f"MAB ({stage}): Selected best UCB arm -> {best_arm} (Score:"
            f" {max_ucb_score:.2f}, Mean: {mean_reward:.2f})"
        )
        return best_arm

    def update_reward(
        self,
        iteration_num: int,
        mab_choices: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Updates the reward and history for the chosen arms and returns the new state."""
        # FACTORED REWARD: Extract dimension-specific efficacy scores if available
        # This aligns with the 'Independent Credit Assignment' requirement in the paper.
        efficacy_scores = verification_result.get("mab_efficacy_scores", {})
        
        # Robustly extract the global score as fallback
        if isinstance(verification_result, dict):
            global_reward = verification_result.get("score", 0)
            if global_reward == 0 and "video" in verification_result:
                 global_reward = verification_result["video"].get("score", 0)
        else:
            global_reward = getattr(verification_result, "score", 0)

        for stage, arm in mab_choices.items():
            # Use dimension-specific score if present, otherwise fallback to global
            reward_score = efficacy_scores.get(stage, global_reward)

            if stage not in self.arm_stats:
                self.arm_stats[stage] = {}
            if arm not in self.arm_stats[stage]:
                self.arm_stats[stage][arm] = {"pulls": 0, "rewards": []}

            if "rewards" not in self.arm_stats[stage][arm]:
                self.arm_stats[stage][arm]["rewards"] = []
            
            self.arm_stats[stage][arm]["pulls"] += 1
            self.arm_stats[stage][arm]["rewards"].append(reward_score)
            
            # Also maintain total_reward for compatibility with selection logic
            if "total_reward" not in self.arm_stats[stage][arm]:
                self.arm_stats[stage][arm]["total_reward"] = 0.0
            self.arm_stats[stage][arm]["total_reward"] += float(reward_score)

        return {"arm_stats": self.arm_stats, "iterations": self.iterations}
