"""Tests for thread-safe BenchmarkManager and persistent run state tracking."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time

from agentgym.manager import BenchmarkManager, RunConfig, RunStatus, get_benchmark_manager


def test_benchmark_manager_lifecycle(tmp_path: Path):
    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")

    cfg = RunConfig(
        run_id="mgr_test_run",
        model_name="mock_solver",
        task_ids=["t01_off_by_one", "t02_wrong_operator"],
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    assert run_id == "mgr_test_run"

    # Poll until background run completes
    timeout = 30.0
    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < timeout):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)

    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.COMPLETED
    assert state.total_tasks == 2
    assert state.completed_tasks == 2
    assert state.solved_tasks == 2

    # Verify run_state.json was persisted on disk
    state_file = tmp_path / run_id / "run_state.json"
    assert state_file.exists()


def test_benchmark_manager_cancellation(tmp_path: Path):
    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")

    cfg = RunConfig(
        run_id="mgr_cancel_test_run",
        model_name="mock_solver",
        task_ids=["t01_off_by_one", "t02_wrong_operator", "t03_wrong_return", "t04_variable_typo"],
        workers=1,
        max_steps=10,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    # Immediately cancel
    time.sleep(0.05)
    canceled = mgr.cancel_run(run_id)
    assert canceled is True

    # Wait for cancellation to settle
    timeout = 15.0
    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < timeout):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)
    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.CANCELLED


def test_benchmark_manager_disk_reconstruction(tmp_path: Path):
    # Simulate a run with only summary.json and trajectories.jsonl
    run_folder = tmp_path / "offline_run"
    run_folder.mkdir(parents=True)
    summary_file = run_folder / "summary.json"
    summary_file.write_text('{"run_id": "offline_run", "model": "test_m", "total_tasks": 1, "solved_tasks": 1, "success_rate": 1.0, "avg_steps": 2.0, "avg_return": 0.5, "episodes": []}', encoding="utf-8")

    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")
    state = mgr.get_run_state("offline_run")
    assert state is not None
    assert state.status == RunStatus.COMPLETED
    assert state.total_tasks == 1
    assert state.solved_tasks == 1
