"""End-to-end integration tests for Custom Task evaluation mode in DebugArena."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentgym.custom_task import CustomTask, generate_custom_task_id
from agentgym.manager import BenchmarkManager, RunConfig, RunStatus
from dashboard.data import is_custom_run, load_all_runs, load_single_run_trajectories


def test_e2e_custom_task_with_oracle(tmp_path: Path):
    custom_tasks_dir = tmp_path / "custom_tasks"
    runs_dir = tmp_path / "runs"

    tid = generate_custom_task_id()
    task = CustomTask(
        task_id=tid,
        description="Fix the off-by-one error in buggy.py so sum_to_n(n) sums from 1 to n inclusive.",
        repo_files={
            "buggy.py": "def sum_to_n(n):\n    return sum(range(n))\n"
        },
        tests={
            "test_buggy.py": (
                "from buggy import sum_to_n\n\n"
                "def test_base():\n    assert sum_to_n(1) == 1\n\n"
                "def test_larger():\n    assert sum_to_n(5) == 15\n"
            )
        },
        reference_fix={
            "buggy.py": "def sum_to_n(n):\n    return sum(range(n + 1))\n"
        },
        suite="custom",
        has_oracle=True,
    )
    task.save(str(custom_tasks_dir))

    # Initialize BenchmarkManager pointing to our test directories
    mgr = BenchmarkManager(runs_dir=str(runs_dir), tasks_dir=str(custom_tasks_dir))

    cfg = RunConfig(
        run_id=tid,
        model_name="mock_solver",
        suite="custom",
        task_ids=[tid],
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    assert run_id == tid

    # Poll until background run completes
    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < 30.0):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)

    # Verify Run State
    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.COMPLETED
    assert state.total_tasks == 1
    assert state.completed_tasks == 1
    assert state.solved_tasks == 1
    assert state.success_rate == 1.0

    # Verify files created on disk
    run_folder = runs_dir / run_id
    assert (run_folder / "run_state.json").exists()
    assert (run_folder / "summary.json").exists()
    assert (run_folder / "trajectories.jsonl").exists()

    # Verify trajectory details & hidden test isolation
    trajs = load_single_run_trajectories(run_id, str(runs_dir))
    assert len(trajs) >= 1
    for step_rec in trajs:
        # Verify hidden test content is NEVER in step record prompt or files
        prompt_str = str(step_rec.get("prompt", ""))
        assert "assert sum_to_n(5) == 15" not in prompt_str

    # Verify summary JSON
    with open(run_folder / "summary.json", "r", encoding="utf-8") as f:
        sum_data = json.load(f)
    assert sum_data.get("solved_tasks") == 1
    assert sum_data.get("success_rate") == 1.0

    # Verify dashboard loader tags it as custom run
    all_runs = load_all_runs(str(runs_dir))
    assert run_id in all_runs
    assert all_runs[run_id]["is_custom"] is True


def test_e2e_custom_task_solve_only_mode(tmp_path: Path):
    custom_tasks_dir = tmp_path / "custom_tasks"
    runs_dir = tmp_path / "runs"

    tid = generate_custom_task_id()
    # Create task with NO tests (Solve Only)
    task = CustomTask(
        task_id=tid,
        description="Refactor math helper to be cleaner.",
        repo_files={
            "helper.py": "def calculate():\n    return 42\n"
        },
        tests={},
        reference_fix={},
        suite="custom",
        has_oracle=False,
    )
    task.save(str(custom_tasks_dir))

    mgr = BenchmarkManager(runs_dir=str(runs_dir), tasks_dir=str(custom_tasks_dir))

    cfg = RunConfig(
        run_id=tid,
        model_name="mock_noop",
        suite="custom",
        task_ids=[tid],
        workers=1,
        max_steps=3,
        sandbox_mode="local",
        use_noop_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)

    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < 30.0):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)

    # Verify summary does not fabricate score
    run_folder = runs_dir / run_id
    with open(run_folder / "summary.json", "r", encoding="utf-8") as f:
        sum_data = json.load(f)

    episodes = sum_data.get("episodes", [])
    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.get("status") == "SOLVE_ONLY"
    assert ep.get("solve_only") is True
    assert ep.get("has_oracle") is False


def test_e2e_custom_task_cancellation(tmp_path: Path):
    custom_tasks_dir = tmp_path / "custom_tasks"
    runs_dir = tmp_path / "runs"

    tid = generate_custom_task_id()
    task = CustomTask(
        task_id=tid,
        description="Long running custom task.",
        repo_files={"app.py": "x = 1\n"},
        tests={"test_app.py": "from app import x\ndef test_x(): assert x == 1\n"},
        suite="custom",
        has_oracle=True,
    )
    task.save(str(custom_tasks_dir))

    mgr = BenchmarkManager(runs_dir=str(runs_dir), tasks_dir=str(custom_tasks_dir))

    cfg = RunConfig(
        run_id=tid,
        model_name="mock_solver",
        suite="custom",
        task_ids=[tid],
        workers=1,
        max_steps=10,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    time.sleep(0.02)
    canceled = mgr.cancel_run(run_id)
    assert canceled is True

    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < 15.0):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)
    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.CANCELLED
