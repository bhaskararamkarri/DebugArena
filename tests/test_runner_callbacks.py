"""Tests for EpisodeRunner callback hooks and cancellation support."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import threading
from typing import Any, Dict, List

from agentgym.runner import EpisodeRunner


def test_runner_callbacks(tmp_path: Path):
    runner = EpisodeRunner(tasks_dir="tasks", runs_dir=str(tmp_path), enable_judge=False)

    steps_received: List[Dict[str, Any]] = []
    episodes_started: List[tuple[str, str]] = []
    episodes_ended: List[Dict[str, Any]] = []
    progress_updates: List[tuple[int, int]] = []

    def on_step(rec: Dict[str, Any]):
        steps_received.append(rec)

    def on_ep_start(tid: str, epid: str):
        episodes_started.append((tid, epid))

    def on_ep_end(summary: Dict[str, Any]):
        episodes_ended.append(summary)

    def on_progress(done: int, total: int, last_summary: Dict[str, Any]):
        progress_updates.append((done, total))

    results = runner.run_batch(
        task_ids=["t01_off_by_one", "t02_wrong_operator"],
        model_name="mock_solver",
        run_id="test_cb_run",
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        on_step=on_step,
        on_episode_start=on_ep_start,
        on_episode_end=on_ep_end,
        on_run_progress=on_progress,
    )

    assert len(results) == 2
    assert len(episodes_started) == 2
    assert len(episodes_ended) == 2
    assert len(steps_received) > 0
    assert len(progress_updates) == 2
    assert all(r.get("success") for r in results)


def test_runner_cancellation(tmp_path: Path):
    runner = EpisodeRunner(tasks_dir="tasks", runs_dir=str(tmp_path), enable_judge=False)

    cancel_evt = threading.Event()
    cancel_evt.set()

    results = runner.run_batch(
        task_ids=["t01_off_by_one", "t02_wrong_operator", "t03_wrong_return"],
        model_name="mock_solver",
        run_id="test_cancel_run",
        workers=1,
        max_steps=5,
        sandbox_mode="local",
        use_mock_solver=True,
        cancel_event=cancel_evt,
    )

    assert len(results) == 0
