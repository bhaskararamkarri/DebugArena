"""Thread-safe background benchmark manager and persistent run state tracking for DebugArena."""

from __future__ import annotations

import collections
import datetime
import json
import threading
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from agentgym.env import BugFixEnv
from agentgym.runner import EpisodeRunner


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunConfig:
    run_id: str
    model_name: str = "nemotron_nano"
    provider: Optional[str] = None
    suite: str = "all"  # "core", "hard", "v2", "all", "custom"
    task_ids: List[str] = field(default_factory=list)
    workers: int = 4
    max_steps: int = 10
    sandbox_mode: str = "docker"  # "docker", "local"
    feedback_mode: str = "diagnostic"  # "diagnostic", "realistic", "blind"
    use_mock_solver: bool = False
    use_noop_solver: bool = False
    enable_judge: bool = True
    enable_tracing: bool = False
    config_path: str = "config.yaml"
    tasks_dir: str = "tasks"
    runs_dir: str = "runs"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RunState:
    run_id: str
    status: RunStatus = RunStatus.QUEUED
    start_time: str = ""
    end_time: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    solved_tasks: int = 0
    current_task_id: Optional[str] = None
    current_step: int = 0
    current_pass_rate: float = 0.0
    current_reward: float = 0.0
    avg_return: float = 0.0
    avg_steps: float = 0.0
    success_rate: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunState:
        raw = dict(data)
        if "status" in raw and isinstance(raw["status"], str):
            raw["status"] = RunStatus(raw["status"])
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})

    def save(self, runs_dir: str = "runs") -> None:
        p = Path(runs_dir) / self.run_id / "run_state.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, run_id: str, runs_dir: str = "runs") -> Optional[RunState]:
        p = Path(runs_dir) / run_id / "run_state.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return cls.from_dict(json.load(f))
            except Exception:
                pass

        # Fallback reconstruction from summary.json
        sum_p = Path(runs_dir) / run_id / "summary.json"
        if sum_p.exists():
            try:
                with open(sum_p, "r", encoding="utf-8") as f:
                    sd = json.load(f)
                    total = sd.get("total_tasks", 0)
                    solved = sd.get("solved_tasks", 0)
                    succ_rate = sd.get("success_rate", 0.0)
                    avg_ret = sd.get("avg_return", 0.0)
                    avg_st = sd.get("avg_steps", 0.0)
                    return cls(
                        run_id=run_id,
                        status=RunStatus.COMPLETED,
                        start_time="",
                        end_time="",
                        total_tasks=total,
                        completed_tasks=total,
                        solved_tasks=solved,
                        avg_return=avg_ret,
                        avg_steps=avg_st,
                        success_rate=succ_rate,
                        config={
                            "model_name": sd.get("model", ""),
                            "sandbox_mode": sd.get("sandbox_type", "docker"),
                            "protocol": sd.get("protocol", "v2"),
                        },
                    )
            except Exception:
                pass
        return None


class BenchmarkManager:
    """Singleton background manager for launching, monitoring, and canceling runs."""

    def __init__(self, runs_dir: str = "runs", tasks_dir: str = "tasks"):
        self.runs_dir = Path(runs_dir)
        self.tasks_dir = Path(tasks_dir)
        self._lock = threading.RLock()
        self._active_runs: Dict[str, threading.Thread] = {}
        self._cancel_events: Dict[str, threading.Event] = {}
        self._active_states: Dict[str, RunState] = {}
        self._event_buffers: Dict[str, Deque[Dict[str, Any]]] = {}
        self._recent_step_records: Dict[str, Dict[str, Any]] = {}

    def is_run_active(self, run_id: str) -> bool:
        with self._lock:
            thread = self._active_runs.get(run_id)
            if thread and thread.is_alive():
                return True
            return False

    def get_active_run_id(self) -> Optional[str]:
        with self._lock:
            for rid, t in self._active_runs.items():
                if t.is_alive():
                    return rid
            return None

    def start_run(self, config: RunConfig) -> str:
        """Launches a benchmark run in a background daemon thread."""
        with self._lock:
            run_id = config.run_id
            if self.is_run_active(run_id):
                raise RuntimeError(f"Run '{run_id}' is already active.")

            # Resolve task list if not provided
            task_ids = list(config.task_ids)
            if not task_ids or task_ids == ["all"]:
                probe_env = BugFixEnv(tasks_dir=str(self.tasks_dir))
                task_ids = probe_env.list_task_ids(suite=config.suite)

            now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            state = RunState(
                run_id=run_id,
                status=RunStatus.RUNNING,
                start_time=now_iso,
                total_tasks=len(task_ids),
                completed_tasks=0,
                solved_tasks=0,
                config=config.to_dict(),
            )

            state.save(runs_dir=str(self.runs_dir))
            self._active_states[run_id] = state
            self._cancel_events[run_id] = threading.Event()
            self._event_buffers[run_id] = collections.deque(maxlen=100)

            thread = threading.Thread(
                target=self._run_worker,
                args=(config, task_ids),
                name=f"benchmark-worker-{run_id}",
                daemon=True,
            )
            self._active_runs[run_id] = thread
            thread.start()

            return run_id

    def cancel_run(self, run_id: str) -> bool:
        """Requests cooperative cancellation for an active run."""
        with self._lock:
            cancel_evt = self._cancel_events.get(run_id)
            if cancel_evt:
                cancel_evt.set()
                if run_id in self._active_states:
                    self._active_states[run_id].status = RunStatus.CANCELLED
                    self._active_states[run_id].save(runs_dir=str(self.runs_dir))
                return True
            return False

    def _run_worker(self, config: RunConfig, task_ids: List[str]) -> None:
        run_id = config.run_id
        cancel_evt = self._cancel_events.get(run_id)

        runner = EpisodeRunner(
            tasks_dir=str(self.tasks_dir),
            runs_dir=str(self.runs_dir),
            config_path=config.config_path,
            enable_judge=config.enable_judge,
            enable_tracing=config.enable_tracing,
        )

        def on_step(record: Dict[str, Any]):
            with self._lock:
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    st.current_task_id = record.get("task_id")
                    st.current_step = record.get("step", 0)
                    st.current_pass_rate = record.get("pass_rate", 0.0)
                    st.current_reward = record.get("reward", 0.0)
                if run_id in self._event_buffers:
                    self._event_buffers[run_id].append({
                        "type": "step",
                        "task_id": record.get("task_id"),
                        "step": record.get("step"),
                        "action_type": record.get("action", {}).get("type"),
                        "pass_rate": record.get("pass_rate"),
                        "reward": record.get("reward"),
                        "timestamp": record.get("timestamp"),
                    })
                self._recent_step_records[run_id] = record

        def on_ep_start(task_id: str, ep_id: str):
            with self._lock:
                if run_id in self._active_states:
                    self._active_states[run_id].current_task_id = task_id
                if run_id in self._event_buffers:
                    self._event_buffers[run_id].append({
                        "type": "episode_start",
                        "task_id": task_id,
                        "episode_id": ep_id,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

        def on_ep_end(ep_summary: Dict[str, Any]):
            with self._lock:
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    st.completed_tasks += 1
                    if ep_summary.get("success"):
                        st.solved_tasks += 1
                    st.success_rate = round(st.solved_tasks / max(1, st.completed_tasks), 4)
                    st.save(runs_dir=str(self.runs_dir))
                if run_id in self._event_buffers:
                    self._event_buffers[run_id].append({
                        "type": "episode_end",
                        "task_id": ep_summary.get("task_id"),
                        "success": ep_summary.get("success"),
                        "steps": ep_summary.get("steps"),
                        "return": ep_summary.get("return"),
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

        try:
            results = runner.run_batch(
                task_ids=task_ids,
                model_name=config.model_name,
                run_id=run_id,
                workers=config.workers,
                max_steps=config.max_steps,
                sandbox_mode=config.sandbox_mode,
                feedback_mode=config.feedback_mode,
                use_mock_solver=config.use_mock_solver,
                use_noop_solver=config.use_noop_solver,
                cancel_event=cancel_evt,
                on_step=on_step,
                on_episode_start=on_ep_start,
                on_episode_end=on_ep_end,
            )

            now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with self._lock:
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    is_canceled = cancel_evt.is_set() if cancel_evt else False
                    st.status = RunStatus.CANCELLED if is_canceled else RunStatus.COMPLETED
                    st.end_time = now_iso
                    st.completed_tasks = len(results)
                    st.solved_tasks = sum(1 for r in results if r.get("success"))
                    st.success_rate = round(st.solved_tasks / max(1, len(results)), 4) if results else 0.0
                    st.avg_return = round(sum(r.get("return", 0.0) for r in results) / max(1, len(results)), 4) if results else 0.0
                    st.avg_steps = round(sum(r.get("steps", 0) for r in results) / max(1, len(results)), 2) if results else 0.0
                    st.save(runs_dir=str(self.runs_dir))

        except Exception as e:
            now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with self._lock:
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    st.status = RunStatus.FAILED
                    st.end_time = now_iso
                    st.error = str(e)
                    st.save(runs_dir=str(self.runs_dir))

    def get_run_state(self, run_id: str) -> Optional[RunState]:
        with self._lock:
            if run_id in self._active_states:
                return self._active_states[run_id]
        return RunState.load(run_id, runs_dir=str(self.runs_dir))

    def get_live_telemetry(self, run_id: str) -> Dict[str, Any]:
        """Returns instantaneous live telemetry snapshot for Streamlit."""
        with self._lock:
            st = self._active_states.get(run_id) or RunState.load(run_id, runs_dir=str(self.runs_dir))
            events = list(self._event_buffers.get(run_id, []))
            latest_step = self._recent_step_records.get(run_id, {})
            is_active = self.is_run_active(run_id)

            return {
                "run_id": run_id,
                "is_active": is_active,
                "state": st.to_dict() if st else None,
                "recent_events": events,
                "latest_step_record": latest_step,
            }


_GLOBAL_BENCHMARK_MANAGER: Optional[BenchmarkManager] = None
_INIT_LOCK = threading.Lock()


def get_benchmark_manager(runs_dir: str = "runs", tasks_dir: str = "tasks") -> BenchmarkManager:
    global _GLOBAL_BENCHMARK_MANAGER
    with _INIT_LOCK:
        if _GLOBAL_BENCHMARK_MANAGER is None:
            _GLOBAL_BENCHMARK_MANAGER = BenchmarkManager(runs_dir=runs_dir, tasks_dir=tasks_dir)
        return _GLOBAL_BENCHMARK_MANAGER
