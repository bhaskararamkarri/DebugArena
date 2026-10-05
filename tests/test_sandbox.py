"""Unit tests for Sandbox execution (Docker and Local)."""

import sys
import pytest
from agentgym.sandbox import Sandbox, LocalSandbox, DockerSandbox


def test_local_sandbox_command_execution():
    sb = LocalSandbox(timeout=5)
    res = sb.run_command(f'"{sys.executable}" -c "print(\'DebugArena Sandbox OK\')"')
    assert res.exit_code == 0
    assert "DebugArena Sandbox OK" in res.stdout
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

    mode = "docker" if Sandbox.is_docker_available() else "local"
    env = BugFixEnv(tasks_dir="tasks", max_steps=5, sandbox_mode=mode)
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
    assert "FileNotFoundError" in obs["last_output"] or "No such file" in obs["last_output"]

    # 3. Agent attempts to read /tests_hidden (which is not mounted during run commands)
    obs, reward, done, info = env.step({
        "type": "run",
        "cmd": f'"{sys.executable}" -c "import os; print(os.path.exists(\'/tests_hidden\'))"',
    })
    assert "False" in obs["last_output"]

    env.close()


def test_local_sandbox_timeout_interruption():
    """Proves sandbox terminates runaway processes and enforces execution timeouts."""
    sb = LocalSandbox(timeout=2)
    res = sb.run_command(f'"{sys.executable}" -c "import time; time.sleep(10)"')
    assert res.timed_out
    assert res.exit_code != 0
    assert "timed out" in res.stderr.lower()
    sb.cleanup()


def test_docker_sandbox_probe_and_execution():
    """Proves Docker container runs Linux, Python 3, and returns correct stdout/exit codes."""
    if not Sandbox.is_docker_available():
        pytest.skip("Docker daemon not available")

    sb = DockerSandbox(timeout=5)
    res = sb.run_command("uname -s && python3 --version && whoami")
    assert res.exit_code == 0
    assert "Linux" in res.stdout
    assert "Python 3" in res.stdout
    assert "root" in res.stdout
    assert sb.sandbox_type == "docker"
    assert sb.get_image_digest().startswith("sha256:")
    sb.cleanup()


def test_docker_sandbox_network_blocked():
    """Proves network calls fail completely in the Docker sandbox."""
    if not Sandbox.is_docker_available():
        pytest.skip("Docker daemon not available")

    sb = DockerSandbox(timeout=5)
    res = sb.run_command('python3 -c "import urllib.request as u; u.urlopen(\'https://example.com\', timeout=3)"')
    assert res.exit_code != 0
    assert "URLError" in res.stdout or "Temporary failure in name resolution" in res.stdout
    sb.cleanup()


def test_docker_sandbox_host_files_unreachable():
    """Proves host paths and environment files (.env) cannot be reached from the container."""
    if not Sandbox.is_docker_available():
        pytest.skip("Docker daemon not available")

    sb = DockerSandbox(timeout=5)
    # Attempt to traverse into host or read host paths
    res = sb.run_command('python3 -c "import os; print(os.path.exists(\'/host\'), os.path.exists(\'/app/.env\'), os.path.exists(\'../.env\'))"')
    assert "False False False" in res.stdout
    sb.cleanup()


def test_docker_sandbox_fork_bomb_contained():
    """Proves pids_limit restricts runaway process forks safely within container limits."""
    if not Sandbox.is_docker_available():
        pytest.skip("Docker daemon not available")

    sb = DockerSandbox(timeout=5, pids_limit=128)
    res = sb.run_command('python3 -c "import os; [os.fork() for _ in range(200)]"')
    # Must fail or trigger resource unavailable error inside container without crashing host
    assert res.exit_code != 0 or "Resource temporarily unavailable" in res.stdout or "BlockingIOError" in res.stdout or "OSError" in res.stdout
    sb.cleanup()


def test_docker_sandbox_hidden_tests_ro_isolation():
    """Proves hidden tests execute read-only during run_tests and are inaccessible during run_command."""
    if not Sandbox.is_docker_available():
        pytest.skip("Docker daemon not available")

    sb = DockerSandbox(timeout=5)
    sb.write_files({"calc.py": "def multiply(a, b): return a * b\n"})

    # During run_command, /tests_hidden does not exist
    res = sb.run_command('python3 -c "import os; print(os.path.exists(\'/tests_hidden\'))"')
    assert "False" in res.stdout

    # Run tests mounted read-only
    test_res = sb.run_tests({"test_calc.py": "from calc import multiply\ndef test_mul(): assert multiply(3, 4) == 12\n"})
    assert test_res.pass_rate == 1.0
    assert len(test_res.passed_tests) == 1

    # After tests finish, container and test files are cleaned
    visible = sb.get_files()
    assert "calc.py" in visible
    assert "test_calc.py" not in visible
    assert "results.xml" not in visible
    sb.cleanup()

