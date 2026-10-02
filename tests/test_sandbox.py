"""Unit tests for Sandbox execution."""

import sys
from agentgym.sandbox import Sandbox, LocalSandbox


def test_local_sandbox_command_execution():
    sb = LocalSandbox(timeout=5)
    res = sb.run_command(f'"{sys.executable}" -c "print(\'AgentGym Sandbox OK\')"')
    assert res.exit_code == 0
    assert "AgentGym Sandbox OK" in res.stdout
    assert not res.timed_out
    sb.cleanup()


def test_local_sandbox_hidden_tests_isolation():
    sb = LocalSandbox(timeout=5)
    sb.write_files({"module.py": "def add(a, b): return a + b\n"})

    # During normal command execution, hidden tests do not exist
    visible_files = sb.get_files()
    assert "module.py" in visible_files
    assert "test_module.py" not in visible_files

    # Run hidden tests
    test_result = sb.run_tests({"test_module.py": "from module import add\ndef test_add(): assert add(1, 2) == 3\n"})
    assert test_result.pass_rate == 1.0
    assert len(test_result.passed_tests) == 1

    # After tests run, test files must be deleted / invisible to the agent
    post_files = sb.get_files()
    assert "test_module.py" not in post_files
    assert "results.xml" not in post_files
    sb.cleanup()


def test_hidden_tests_unreadable_during_agent_run_command():
    """Proves an agent cannot inspect or read hidden tests via run commands."""
    from agentgym.env import BugFixEnv

    env = BugFixEnv(tasks_dir="tasks", max_steps=5, sandbox_mode="local")
    obs = env.reset(task_id="t01_off_by_one")

    # 1. Agent attempts to list files looking for test files
    obs, reward, done, info = env.step({
        "type": "run",
        "cmd": f'"{sys.executable}" -c "import os; print([f for f in os.listdir(\'.\') if \'test\' in f])"',
    })
    assert "[]" in obs["last_output"]

    # 2. Agent attempts to directly cat / open the hidden test file
    obs, reward, done, info = env.step({
        "type": "run",
        "cmd": f'"{sys.executable}" -c "open(\'test_mathutils.py\').read()"',
    })
    assert "FileNotFoundError" in obs["last_output"]

    env.close()
