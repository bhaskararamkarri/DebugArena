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
