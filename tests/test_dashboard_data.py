"""Tests for Dashboard Data Layer and 100-Task Metadata."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.data import (
    compute_wilson_ci,
    format_model_label,
    get_available_models,
    get_available_providers,
    get_suite_task_ids,
    load_all_runs,
    load_tasks_metadata,
)


def test_compute_wilson_ci():
    assert compute_wilson_ci(0, 0) == "N/A"
    ci_full = compute_wilson_ci(10, 10)
    assert "%" in ci_full
    ci_half = compute_wilson_ci(5, 10)
    assert "%" in ci_half


def test_format_model_label():
    assert "Reference" in format_model_label("baseline_mock_solver", "mock")
    assert "No-op" in format_model_label("baseline_noop_core", "mock")
    assert format_model_label("run1", "nvidia/nemotron-nano-4b") == "nemotron-nano-4b"


def test_load_all_100_tasks_metadata():
    tasks = load_tasks_metadata("tasks")
    assert len(tasks) == 100, f"Expected exactly 100 benchmark tasks, found {len(tasks)}"

    core_tasks = [t for t, d in tasks.items() if d.get("suite") == "Core-20" or t.startswith("t")]
    hard_tasks = [t for t, d in tasks.items() if d.get("suite") == "Hard-10" or t.startswith("h")]
    v2_tasks = [t for t, d in tasks.items() if d.get("suite") == "V2-70" or t.startswith("v")]

    assert len(core_tasks) == 20
    assert len(hard_tasks) == 10
    assert len(v2_tasks) == 70

    suite_map = get_suite_task_ids(tasks)
    assert len(suite_map["All (100 Tasks)"]) == 100
    assert len(suite_map["Benchmark V2 (70 Tasks)"]) == 70
    assert len(suite_map["Core-20 (20 Tasks)"]) == 20
    assert len(suite_map["Hard-10 (10 Tasks)"]) == 10


def test_get_available_models_and_providers():
    models = get_available_models("config.yaml")
    assert len(models) >= 2
    providers = get_available_providers("config.yaml")
    assert "nebius" in providers or "openrouter" in providers or "mock" in providers


def test_load_all_runs(tmp_path: Path):
    run_dir = tmp_path / "test_run_1"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text('{"run_id": "test_run_1", "model": "test_m", "total_tasks": 2, "solved_tasks": 2, "success_rate": 1.0, "avg_steps": 2.0, "avg_return": 0.5, "episodes": []}', encoding="utf-8")
    (run_dir / "run_state.json").write_text('{"run_id": "test_run_1", "status": "completed", "total_tasks": 2, "completed_tasks": 2, "solved_tasks": 2}', encoding="utf-8")

    runs = load_all_runs(str(tmp_path))
    assert "test_run_1" in runs
    assert runs["test_run_1"]["summary"]["total_tasks"] == 2
    assert runs["test_run_1"]["state"]["status"] == "completed"
