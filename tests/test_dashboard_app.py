"""Smoke tests for dashboard components and app integrity."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.data import load_all_runs, load_tasks_metadata, get_suite_task_ids
from agentgym.manager import get_benchmark_manager


def test_dashboard_components_and_imports():
    # Verify manager initializes
    mgr = get_benchmark_manager()
    assert mgr is not None

    # Verify tasks metadata
    tasks = load_tasks_metadata("tasks")
    assert len(tasks) == 100
    suites = get_suite_task_ids(tasks)
    assert "All (100 Tasks)" in suites
    assert "Benchmark V2 (70 Tasks)" in suites
    assert "Core-20 (20 Tasks)" in suites
    assert "Hard-10 (10 Tasks)" in suites

    # Verify runs loading
    runs = load_all_runs("runs")
    assert isinstance(runs, dict)
