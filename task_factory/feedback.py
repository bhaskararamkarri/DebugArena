"""Feedback mode abstractions for Benchmark V2 evaluation observability."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class BaseFeedbackAdapter(ABC):
    """Abstract interface for tailoring environment observations, rewards, and info dictionaries."""

    @abstractmethod
    def filter_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Filters the observation dictionary sent to the agent."""
        pass

    def filter_reward(self, reward: float, done: bool, info: Dict[str, Any]) -> float:
        """Filters or transforms the reward signal exposed to the agent."""
        return reward

    @abstractmethod
    def filter_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Filters the info dictionary returned from step()."""
        pass

    def filter_step(self, reward: float, done: bool, info: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Filters both reward and info for the step return tuple."""
        return self.filter_reward(reward, done, info), self.filter_info(info)


class DiagnosticFeedbackAdapter(BaseFeedbackAdapter):
    """Diagnostic mode (default): Full transparency into test execution, names, and pass rates."""

    def filter_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return dict(observation)

    def filter_reward(self, reward: float, done: bool, info: Dict[str, Any]) -> float:
        return reward

    def filter_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        return dict(info)


class RealisticFeedbackAdapter(BaseFeedbackAdapter):
    """Realistic mode: Masks hidden test names/breakdowns; agent only observes command outputs and exit codes."""

    def filter_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return dict(observation)

    def filter_reward(self, reward: float, done: bool, info: Dict[str, Any]) -> float:
        return reward

    def filter_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        is_terminal = bool(info.get("all_tests_passed") or info.get("submitted") or info.get("ran_out_of_steps"))
        filtered = {
            "task_id": info.get("task_id"),
            "step": info.get("step"),
            "action": info.get("action"),
            "step_reward": info.get("step_reward"),
            "cumulative_return": info.get("cumulative_return"),
            "all_tests_passed": info.get("all_tests_passed"),
            "submitted": info.get("submitted"),
            "ran_out_of_steps": info.get("ran_out_of_steps"),
        }
        if is_terminal:
            filtered["pass_rate"] = info.get("pass_rate")
            filtered["tests_passed"] = info.get("tests_passed")
            filtered["tests_total"] = info.get("tests_total")
        return filtered


class BlindFeedbackAdapter(BaseFeedbackAdapter):
    """Blind mode: Zero-shot evaluation without intermediate hidden-test reward leakage.

    Prevents the agent from exploiting non-zero reward deltas or test pass rates as an oracle.
    """

    def filter_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return dict(observation)

    def filter_reward(self, reward: float, done: bool, info: Dict[str, Any]) -> float:
        # Strictly mask intermediate reward deltas to prevent hidden test oracle probing
        if done:
            return reward
        return 0.0

    def filter_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        is_done = bool(info.get("all_tests_passed") or info.get("submitted") or info.get("ran_out_of_steps") or info.get("done"))
        filtered = {
            "task_id": info.get("task_id"),
            "step": info.get("step"),
            "done": is_done,
        }
        if is_done:
            filtered["step_reward"] = info.get("step_reward")
            filtered["cumulative_return"] = info.get("cumulative_return")
        else:
            filtered["step_reward"] = 0.0
            filtered["cumulative_return"] = 0.0
        return filtered


def get_feedback_adapter(mode: str = "diagnostic") -> BaseFeedbackAdapter:
    """Factory for feedback adapters."""
    m = (mode or "diagnostic").lower()
    if m == "realistic":
        return RealisticFeedbackAdapter()
    elif m == "blind":
        return BlindFeedbackAdapter()
    return DiagnosticFeedbackAdapter()
