"""Reward computation for AgentGym episodes."""

from typing import Dict, Set, Tuple


class RewardCalculator:
    """Computes step-level rewards and cumulative episode return.

    Specification:
        step_reward = (pass_rate_t - pass_rate_{t-1})
                      - step_cost (default: 0.01)
                      - regression_penalty (default: 0.20) * regression_flag
        episode_return = sum(step_rewards)

    A regression occurs if any test that previously passed now fails.
    """

    def __init__(self, step_cost: float = 0.01, regression_penalty: float = 0.20):
        self.step_cost = step_cost
        self.regression_penalty = regression_penalty
        self.prev_pass_rate = 0.0
        self.ever_passed_tests: Set[str] = set()
        self.prev_passed_tests: Set[str] = set()
        self.step_rewards: list[float] = []

    def reset(self, initial_passed_tests: Set[str], initial_total_tests: int) -> float:
        """Initialize reward state with baseline test results before agent actions."""
        self.ever_passed_tests = set(initial_passed_tests)
        self.prev_passed_tests = set(initial_passed_tests)
        self.prev_pass_rate = len(initial_passed_tests) / max(1, initial_total_tests)
        self.step_rewards = []
        return self.prev_pass_rate

    def compute_step_reward(
        self, current_passed_tests: Set[str], total_tests: int
    ) -> Tuple[float, bool, Dict[str, float]]:
        """Calculate step reward given the current set of passing tests.

        Returns:
            (step_reward, regression_detected, breakdown_dict)
        """
        total = max(1, total_tests)
        pass_rate_t = len(current_passed_tests) / total

        # Progress component
        progress = pass_rate_t - self.prev_pass_rate

        # Regression detection: did any test that previously passed now fail?
        regressed_tests = self.ever_passed_tests - current_passed_tests
        regression_detected = len(regressed_tests) > 0
        reg_penalty = self.regression_penalty if regression_detected else 0.0

        # Step cost
        cost = self.step_cost

        # Net step reward
        step_reward = progress - cost - reg_penalty
        step_reward = round(step_reward, 4)

        self.step_rewards.append(step_reward)

        # Update historical passed tests
        self.ever_passed_tests.update(current_passed_tests)
        self.prev_passed_tests = set(current_passed_tests)
        self.prev_pass_rate = pass_rate_t

        breakdown = {
            "progress": round(progress, 4),
            "step_cost": round(cost, 4),
            "regression_penalty": round(reg_penalty, 4),
            "pass_rate": round(pass_rate_t, 4),
            "regressed_tests_count": len(regressed_tests),
        }

        return step_reward, regression_detected, breakdown

    @property
    def cumulative_return(self) -> float:
        """Sum of all step rewards in this episode."""
        return round(sum(self.step_rewards), 4)
