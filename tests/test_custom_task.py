"""Unit tests for CustomTask data structure, safe ZIP extraction, and security boundaries."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentgym.custom_task import (
    CustomTask,
    ZipSecurityError,
    compute_file_diff,
    extract_zip_safely,
    generate_custom_task_id,
    list_custom_tasks,
    sanitize_rel_path,
)


def _create_zip_bytes(file_dict: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for k, v in file_dict.items():
            zf.writestr(k, v)
    return buf.getvalue()


def test_sanitize_rel_path():
    assert sanitize_rel_path("src/app.py") == "src/app.py"
    assert sanitize_rel_path("utils\\math.py") == "utils/math.py"
    assert sanitize_rel_path("./main.py") == "main.py"

    with pytest.raises(ZipSecurityError, match="Path traversal"):
        sanitize_rel_path("../evil.py")

    with pytest.raises(ZipSecurityError, match="Path traversal"):
        sanitize_rel_path("src/../../evil.py")

    with pytest.raises(ZipSecurityError, match="Absolute paths"):
        sanitize_rel_path("/etc/passwd")

    with pytest.raises(ZipSecurityError, match="Absolute paths"):
        sanitize_rel_path("C:/Windows/System32/cmd.exe")


def test_extract_zip_safely_valid():
    files = {
        "main.py": "print('hello world')\n",
        "pkg/utils.py": "def add(a, b): return a + b\n",
        "README.md": "# Sample Project\n",
    }
    zip_bytes = _create_zip_bytes(files)
    extracted = extract_zip_safely(zip_bytes)

    assert "main.py" in extracted
    assert "pkg/utils.py" in extracted
    assert "README.md" in extracted
    assert extracted["main.py"] == "print('hello world')\n"


def test_extract_zip_safely_common_prefix_strip():
    files = {
        "repo-main/main.py": "print('hello')",
        "repo-main/helper.py": "def help(): pass",
    }
    zip_bytes = _create_zip_bytes(files)
    extracted = extract_zip_safely(zip_bytes, strip_common_prefix=True)

    assert "main.py" in extracted
    assert "helper.py" in extracted


def test_extract_zip_safely_traversal_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../evil.py", "malicious_code = True")

    with pytest.raises(ZipSecurityError, match="Path traversal"):
        extract_zip_safely(buf.getvalue())


def test_extract_zip_safely_file_count_limit():
    files = {f"file_{i}.txt": f"data_{i}" for i in range(15)}
    zip_bytes = _create_zip_bytes(files)

    with pytest.raises(ZipSecurityError, match="exceeding maximum allowed limit"):
        extract_zip_safely(zip_bytes, max_files=10)


def test_extract_zip_safely_size_limit():
    files = {"large.txt": "A" * 5000}
    zip_bytes = _create_zip_bytes(files)

    with pytest.raises(ZipSecurityError, match="exceeds maximum file limit"):
        extract_zip_safely(zip_bytes, max_file_size=1000)


def test_custom_task_lifecycle(tmp_path: Path):
    tid = generate_custom_task_id()
    assert tid.startswith("custom_")

    task = CustomTask(
        task_id=tid,
        description="Fix the divide by zero bug in calculator.py",
        repo_files={"calculator.py": "def divide(a, b): return a / b\n"},
        tests={"test_calculator.py": "from calculator import divide\n\ndef test_div(): assert divide(4, 2) == 2\n"},
        reference_fix={"calculator.py": "def divide(a, b): return a / b if b != 0 else None\n"},
        suite="custom",
        has_oracle=True,
    )

    custom_dir = str(tmp_path / "custom_tasks")
    saved_path = task.save(custom_tasks_dir=custom_dir)
    assert saved_path.exists()

    loaded = CustomTask.load(tid, custom_tasks_dir=custom_dir)
    assert loaded is not None
    assert loaded.task_id == tid
    assert loaded.description == task.description
    assert loaded.repo_files == task.repo_files
    assert loaded.tests == task.tests
    assert loaded.has_oracle is True

    all_tasks = list_custom_tasks(custom_tasks_dir=custom_dir)
    assert len(all_tasks) == 1
    assert all_tasks[0].task_id == tid


def test_compute_file_diff():
    orig = {
        "app.py": "def foo():\n    return 1\n",
        "unchanged.py": "x = 10\n",
    }
    modified = {
        "app.py": "def foo():\n    return 2\n",
        "unchanged.py": "x = 10\n",
        "new.py": "# newly created file\n",
    }

    diffs = compute_file_diff(orig, modified)
    assert "app.py" in diffs
    assert "-    return 1" in diffs["app.py"]
    assert "+    return 2" in diffs["app.py"]
    assert "unchanged.py" not in diffs
    assert "new.py" in diffs
