"""Unit tests for RewardCalculator."""

import pytest
from agentgym.reward import RewardCalculator


def test_reward_progress_and_cost():
    calc = RewardCalculator(step_cost=0.01, regression_penalty=0.20)
    # Baseline: 1 of 4 tests passing
    calc.reset(initial_passed_tests={"test_1"}, initial_total_tests=4)

    # Step 1: 3 of 4 tests passing now
    reward, reg, breakdown = calc.compute_step_reward(
        current_passed_tests={"test_1", "test_2", "test_3"},
        total_tests=4,
    )

    # progress = (3/4 - 1/4) = 0.50
    # step_cost = 0.01
    # regression = False
    # reward = 0.50 - 0.01 = 0.49
    assert reward == pytest.approx(0.49, rel=1e-3)
    assert not reg
    assert breakdown["progress"] == 0.50
    assert breakdown["step_cost"] == 0.01
    assert breakdown["regression_penalty"] == 0.0


def test_reward_regression_penalty():
    calc = RewardCalculator(step_cost=0.01, regression_penalty=0.20)
    # Baseline: test_1 passing
    calc.reset(initial_passed_tests={"test_1"}, initial_total_tests=4)

    # Step 1: Agent broke test_1, but passed test_2
    reward, reg, breakdown = calc.compute_step_reward(
        current_passed_tests={"test_2"},
        total_tests=4,
    )

    # pass_rate_t = 0.25, pass_rate_{t-1} = 0.25 -> progress = 0.0
    # step_cost = 0.01
    # regression: test_1 was in ever_passed_tests and is now missing -> reg = True
    # reward = 0.0 - 0.01 - 0.20 = -0.21
    assert reg is True
    assert reward == pytest.approx(-0.21, rel=1e-3)
    assert breakdown["regression_penalty"] == 0.20
