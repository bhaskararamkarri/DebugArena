"""Comprehensive security regression tests for host-side filesystem path traversal prevention."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentgym.env import BugFixEnv
from agentgym.sandbox import LocalSandbox
from agentgym.security import PathTraversalSecurityError, SecurityError, safe_path


def test_path_traversal_basic(tmp_path: Path):
    """Test 1: ../evil.txt must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside_file = tmp_path / "evil.txt"

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "../evil.txt")

    assert not outside_file.exists(), "Outside file must not be created."


def test_path_traversal_multi_level(tmp_path: Path):
    """Test 2: ../../evil.txt must fail."""
    ws = tmp_path / "a" / "b" / "workspace"
    ws.mkdir(parents=True)
    outside_file = tmp_path / "evil.txt"

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "../../evil.txt")

    assert not outside_file.exists(), "Outside file must not be created."


def test_path_traversal_nested(tmp_path: Path):
    """Test 3: foo/../../evil.txt must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside_file = tmp_path / "evil.txt"

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "foo/../../evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "a/b/../../../evil.txt")

    assert not outside_file.exists(), "Outside file must not be created."


def test_path_traversal_posix_absolute(tmp_path: Path):
    """Test 4: POSIX absolute path (/etc/evil.txt) must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "/etc/evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "/tmp/evil.txt")


def test_path_traversal_windows_absolute(tmp_path: Path):
    """Test 5: Windows absolute path (C:\\evil.txt) must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, r"C:\Windows\System32\evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "C:/evil.txt")


def test_path_traversal_mixed_separators(tmp_path: Path):
    """Test 6: Mixed separator traversal (..\\..\\evil.txt) must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside_file = tmp_path / "evil.txt"

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, r"..\..\evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, r"foo\..\..\evil.txt")

    assert not outside_file.exists(), "Outside file must not be created."


def test_path_traversal_windows_drive_relative_and_rooted(tmp_path: Path):
    """Test drive-relative and root-anchored variants (\\evil.txt, C:evil.txt)."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, r"\evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "C:evil.txt")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, r"\\server\share\evil.txt")


def test_path_traversal_symlink_escape(tmp_path: Path):
    """Test 7: Symlink escape (workspace/link -> outside) must fail."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "evil.txt"

    link_path = ws / "escape_link"
    try:
        os.symlink(str(outside_dir.resolve()), str(link_path))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted or supported on this system/user privilege level.")

    with pytest.raises(PathTraversalSecurityError):
        safe_path(ws, "escape_link/evil.txt")

    assert not outside_file.exists(), "Outside file must not be created via symlink traversal."


def test_path_traversal_valid_nested_path(tmp_path: Path):
    """Test 8: Valid nested path (src/utils/helper.py) must succeed."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    resolved = safe_path(ws, "src/utils/helper.py")
    assert resolved == ws.resolve() / "src" / "utils" / "helper.py"


def test_path_traversal_valid_root_path(tmp_path: Path):
    """Test 9: Valid root path (app.py) must succeed."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    resolved = safe_path(ws, "app.py")
    assert resolved == ws.resolve() / "app.py"


def test_local_sandbox_write_files_traversal_blocked(tmp_path: Path):
    """Test 10: LocalSandbox.write_files rejects traversal and leaves outside files untouched."""
    sandbox = LocalSandbox()
    try:
        outside_target = sandbox.temp_dir.parent / "pwned.txt"
        if outside_target.exists():
            outside_target.unlink()

        with pytest.raises(SecurityError):
            sandbox.write_files({"../pwned.txt": "malicious payload"})

        assert not outside_target.exists(), "Outside target must not exist after traversal attempt."
    finally:
        sandbox.cleanup()


def test_env_step_edit_traversal_handled_safely(tmp_path: Path):
    """Test 11: BugFixEnv.step handles path traversal in 'edit' action safely without crashing."""
    env = BugFixEnv(tasks_dir="tasks", sandbox_mode="local")
    env.reset("t01_off_by_one")

    outside_target = env.sandbox.temp_dir.parent / "pwned_agent.txt"
    if outside_target.exists():
        outside_target.unlink()

    obs, reward, done, info = env.step({"type": "edit", "path": "../pwned_agent.txt", "content": "bad"})
    assert not outside_target.exists(), "Host filesystem outside sandbox must be untouched."
    assert "Security error" in obs["last_output"] or "Error" in obs["last_output"]
    env.close()
