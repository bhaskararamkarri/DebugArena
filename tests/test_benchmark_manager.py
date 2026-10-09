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


def test_config_view_and_run_config_aliases():
    """Verify ConfigView attribute dot-access and RunConfig alias harmonization."""
    from agentgym.manager import ConfigView, RunState

    cfg = RunConfig(
        run_id="alias_run",
        model="nvidia/nemotron-3-super-120b-a12b",
        sandbox_type="local",
        timeout_seconds=15,
        notes="Testing aliases",
    )
    assert cfg.model_name == "nvidia/nemotron-3-super-120b-a12b"
    assert cfg.sandbox_mode == "local"
    assert cfg.timeout_seconds == 15

    state = RunState(
        run_id="alias_run",
        status=RunStatus.RUNNING,
        config=cfg.to_dict(),
    )
    assert isinstance(state.config, ConfigView)
    assert state.config.run_id == "alias_run"
    assert state.config.model == "nvidia/nemotron-3-super-120b-a12b"
    assert state.config.model_name == "nvidia/nemotron-3-super-120b-a12b"
    assert state.config.sandbox_type == "local"
    assert state.config.sandbox_mode == "local"
    assert state.config.timeout == 15
    assert state.config.timeout_seconds == 15


def test_benchmark_manager_get_active_run_and_recent_logs(tmp_path: Path):
    """Verify get_active_run, get_all_active_runs, and log population."""
    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")

    # When no runs exist
    assert mgr.get_active_run() is None
    assert mgr.get_all_active_runs() == []

    cfg = RunConfig(
        run_id="active_poll_run",
        model_name="mock_solver",
        task_ids=["t01_off_by_one"],
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    active = mgr.get_active_run()
    assert active is not None
    assert active.run_id == "active_poll_run"
    assert active.config.run_id == "active_poll_run"

    all_active = mgr.get_all_active_runs()
    assert len(all_active) == 1
    assert all_active[0].run_id == "active_poll_run"

    # Wait for completion
    timeout = 15.0
    start = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start < timeout):
        time.sleep(0.1)

    completed_state = mgr.get_run_state(run_id)
    assert completed_state is not None
    assert completed_state.status == RunStatus.COMPLETED
    assert len(completed_state.recent_logs) > 0


def test_custom_task_title_and_id_generation():
    """Verify CustomTask title extraction and ID generation with prefix."""
    from agentgym.custom_task import CustomTask, generate_custom_task_id

    cid = generate_custom_task_id("My Custom Problem!")
    assert cid.startswith("custom_my_custom_problem_")

    task = CustomTask(
        task_id=cid,
        description="Fix edge case in binary search algorithm when array is empty.\nAdditional details here.",
        repo_files={"search.py": "def bsearch(): pass"},
    )
    assert task.title.startswith("Fix edge case in binary search")
