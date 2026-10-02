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
