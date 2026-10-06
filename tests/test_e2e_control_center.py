"""End-to-End integration test suite for Real-Time Benchmark Control Center."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentgym.manager import BenchmarkManager, RunConfig, RunStatus
from dashboard.data import load_all_runs, load_single_run_trajectories


def test_e2e_mock_evaluation_flow(tmp_path: Path):
    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")

    cfg = RunConfig(
        run_id="e2e_mock_run_1",
        model_name="mock_solver",
        task_ids=["t01_off_by_one", "t02_wrong_operator", "t03_wrong_return"],
        workers=2,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    assert run_id == "e2e_mock_run_1"

    # Poll and observe live telemetry
    start_time = time.time()
    observed_telemetry = False
    while mgr.is_run_active(run_id) and (time.time() - start_time < 45.0):
        telem = mgr.get_live_telemetry(run_id)
        if telem.get("is_active"):
            observed_telemetry = True
        time.sleep(0.2)

    assert not mgr.is_run_active(run_id)

    # Verify final state
    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.COMPLETED
    assert state.total_tasks == 3
    assert state.completed_tasks == 3
    assert state.solved_tasks == 3
    assert state.success_rate == 1.0

    # Verify run artifacts on disk
    run_dir = tmp_path / run_id
    assert (run_dir / "run_state.json").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "trajectories.jsonl").exists()

    # Verify trajectories loading and integrity
    trajs = load_single_run_trajectories(run_id, str(tmp_path))
    assert len(trajs) >= 3
    for rec in trajs:
        assert rec.get("task_id") in ["t01_off_by_one", "t02_wrong_operator", "t03_wrong_return"]
        assert "action" in rec
        assert "pass_rate" in rec
        assert "reward" in rec

    # Verify dashboard loader sees the completed run
    all_runs = load_all_runs(str(tmp_path))
    assert run_id in all_runs
    assert all_runs[run_id]["summary"]["solved_tasks"] == 3


def test_e2e_cancellation_flow(tmp_path: Path):
    mgr = BenchmarkManager(runs_dir=str(tmp_path), tasks_dir="tasks")

    cfg = RunConfig(
        run_id="e2e_cancel_run",
        model_name="mock_solver",
        task_ids=["t01_off_by_one", "t02_wrong_operator", "t03_wrong_return", "t04_variable_typo"],
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        enable_judge=False,
    )

    run_id = mgr.start_run(cfg)
    time.sleep(0.05)
    canceled = mgr.cancel_run(run_id)
    assert canceled is True

    start_time = time.time()
    while mgr.is_run_active(run_id) and (time.time() - start_time < 30.0):
        time.sleep(0.1)

    assert not mgr.is_run_active(run_id)

    state = mgr.get_run_state(run_id)
    assert state is not None
    assert state.status == RunStatus.CANCELLED

    # Verify JSONL lines are intact and not corrupt
    traj_path = tmp_path / run_id / "trajectories.jsonl"
    if traj_path.exists():
        with open(traj_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    json.loads(line.strip())
