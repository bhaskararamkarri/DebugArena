"""Unit tests for BugFixEnv Gymnasium-style interface."""

from agentgym.env import BugFixEnv


def test_env_reset_and_step():
    env = BugFixEnv(tasks_dir="tasks", max_steps=5, sandbox_mode="local")
    obs = env.reset(task_id="t01_off_by_one")

    assert "description" in obs
    assert "mathutils.py" in obs["files"]
    assert obs["steps_left"] == 5

    # Step 1: Run inspection command
    obs, reward, done, info = env.step({
        "type": "run",
        "cmd": "python -c \"import mathutils; print('ok')\"",
    })
    assert not done
    assert obs["steps_left"] == 4
    assert info["step"] == 1
    assert "ok" in obs["last_output"]

    # Step 2: Apply fix
    ref_fix = env.current_task["reference_fix"]["mathutils.py"]
    obs, reward, done, info = env.step({
        "type": "edit",
        "path": "mathutils.py",
        "content": ref_fix,
    })
    # After reference fix, all tests pass -> done is True
    assert info["all_tests_passed"] is True
    assert done is True
    assert info["pass_rate"] == 1.0

    env.close()


def test_env_feedback_modes_and_blind_leakage_prevention():
    # 1. Blind mode: should strictly mask intermediate reward improvements and test names
    blind_env = BugFixEnv(tasks_dir="tasks", max_steps=5, sandbox_mode="local", feedback_mode="blind")
    obs = blind_env.reset(task_id="t01_off_by_one")

    # Step 1: Run inspection command
    obs, reward, done, info = blind_env.step({
        "type": "run",
        "cmd": "python -c \"import mathutils; print('ok')\"",
    })
    assert not done
    assert reward == 0.0  # Masked intermediate reward
    assert info["step_reward"] == 0.0
    assert info["cumulative_return"] == 0.0
    assert "passed_tests" not in info
    assert "pass_rate" not in info
    # Internal true reward calculator remains intact
    assert len(blind_env.reward_calc.step_rewards) == 1

    # Step 2: Reference fix (terminal step)
    ref_fix = blind_env.current_task["reference_fix"]["mathutils.py"]
    obs, reward, done, info = blind_env.step({
        "type": "edit",
        "path": "mathutils.py",
        "content": ref_fix,
    })
    assert done is True
    # At terminal step, final reward is unmasked
    assert reward > 0.0
    assert info["done"] is True
    assert info["step_reward"] > 0.0
    assert info["cumulative_return"] > 0.0
    blind_env.close()

    # 2. Realistic mode: exposes step reward but hides test names
    real_env = BugFixEnv(tasks_dir="tasks", max_steps=5, sandbox_mode="local", feedback_mode="realistic")
    real_env.reset(task_id="t01_off_by_one")
    obs, reward, done, info = real_env.step({
        "type": "run",
        "cmd": "python -c \"import mathutils; print('ok')\"",
    })
    assert "passed_tests" not in info
    assert "failed_tests" not in info
    assert "breakdown" not in info
    assert "step_reward" in info
    real_env.close()
