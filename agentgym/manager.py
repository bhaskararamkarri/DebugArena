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
from agentgym.provider import ExecutionMode, ProviderPolicyError, validate_execution_config
from agentgym.runner import EpisodeRunner


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfigView(dict):
    """Dictionary subclass supporting attribute-style dot-access with alias mapping."""

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        if name == "model" and "model_name" in self:
            return self["model_name"]
        if name == "model_name" and "model" in self:
            return self["model"]
        if name == "sandbox_type" and "sandbox_mode" in self:
            return self["sandbox_mode"]
        if name == "sandbox_mode" and "sandbox_type" in self:
            return self["sandbox_type"]
        if name == "timeout" and "timeout_seconds" in self:
            return self["timeout_seconds"]
        if name == "timeout_seconds" and "timeout" in self:
            return self["timeout"]
        return None

    def __setitem__(self, name: str, value: Any) -> None:
        super().__setitem__(name, value)
        if name == "model":
            super().__setitem__("model_name", value)
        elif name == "model_name":
            super().__setitem__("model", value)
        elif name == "sandbox_type":
            super().__setitem__("sandbox_mode", value)
        elif name == "sandbox_mode":
            super().__setitem__("sandbox_type", value)
        elif name == "timeout":
            super().__setitem__("timeout_seconds", value)
        elif name == "timeout_seconds":
            super().__setitem__("timeout", value)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


@dataclass
class RunConfig:
    run_id: str
    model_name: str = "nemotron_nano"
    model: Optional[str] = None
    execution_mode: str = "hackathon"
    provider: Optional[str] = None
    fallback: Optional[str] = None
    suite: str = "all"  # "core", "hard", "v2", "all", "custom"
    task_ids: List[str] = field(default_factory=list)
    workers: int = 4
    max_steps: int = 10
    timeout_seconds: int = 10
    sandbox_mode: str = "docker"  # "docker", "local"
    sandbox_type: Optional[str] = None
    feedback_mode: str = "diagnostic"  # "diagnostic", "realistic", "blind"
    notes: str = ""
    use_mock_solver: bool = False
    use_noop_solver: bool = False
    enable_judge: bool = True
    judge_model: Optional[str] = None
    enable_tracing: bool = False
    config_path: str = "config.yaml"
    tasks_dir: str = "tasks"
    runs_dir: str = "runs"

    def __post_init__(self):
        if self.model and (not self.model_name or self.model_name == "nemotron_nano"):
            self.model_name = self.model
        elif not self.model:
            self.model = self.model_name
        if self.sandbox_type:
            self.sandbox_mode = self.sandbox_type
        elif not self.sandbox_type:
            self.sandbox_type = self.sandbox_mode

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
    config: Any = field(default_factory=dict)
    recent_logs: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.config, ConfigView):
            if isinstance(self.config, dict):
                cfg_dict = dict(self.config)
                if "run_id" not in cfg_dict:
                    cfg_dict["run_id"] = self.run_id
                self.config = ConfigView(cfg_dict)
            else:
                self.config = ConfigView({"run_id": self.run_id})

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        if isinstance(self.config, ConfigView):
            d["config"] = dict(self.config)
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

    def get_active_run(self) -> Optional[RunState]:
        """Returns the currently active running state, or the most recent run state."""
        with self._lock:
            rid = self.get_active_run_id()
            if rid and rid in self._active_states:
                return self._active_states[rid]
            # Check for any active state marked RUNNING
            for state in self._active_states.values():
                if state.status == RunStatus.RUNNING:
                    return state
            # Return latest active state if any exist
            if self._active_states:
                latest_id = list(self._active_states.keys())[-1]
                return self._active_states[latest_id]
            return None

    def get_all_active_runs(self) -> List[RunState]:
        """Returns a list of all currently tracked active run states."""
        with self._lock:
            return list(self._active_states.values())

    def start_run(self, config: RunConfig) -> str:
        """Launches a benchmark run in a background daemon thread."""
        with self._lock:
            # Synchronously validate provider policy before any state persistence or thread launch
            val_res = validate_execution_config(
                execution_mode=config.execution_mode,
                provider=config.provider,
                fallback=config.fallback,
                config_path=config.config_path,
                use_mock_solver=config.use_mock_solver,
                use_noop_solver=config.use_noop_solver,
                model_name=config.model_name,
            )
            config.execution_mode = val_res["execution_mode"]
            config.provider = val_res["provider"]
            config.fallback = val_res["fallback"]

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
            judge_model=config.judge_model,
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
                    action_type = record.get("action", {}).get("type", "unknown")
                    ts = record.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
                    log_line = f"[{ts}] Task {st.current_task_id} step {st.current_step}: action={action_type}, pass_rate={st.current_pass_rate:.2f}, reward={st.current_reward:+.2f}"
                    st.recent_logs.append(log_line)
                    if len(st.recent_logs) > 200:
                        st.recent_logs = st.recent_logs[-200:]
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
                now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    st.current_task_id = task_id
                    st.recent_logs.append(f"[{now_ts}] Starting task {task_id} ({ep_id})")
                    if len(st.recent_logs) > 200:
                        st.recent_logs = st.recent_logs[-200:]
                if run_id in self._event_buffers:
                    self._event_buffers[run_id].append({
                        "type": "episode_start",
                        "task_id": task_id,
                        "episode_id": ep_id,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

        def on_ep_end(ep_summary: Dict[str, Any]):
            with self._lock:
                now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
                if run_id in self._active_states:
                    st = self._active_states[run_id]
                    st.completed_tasks += 1
                    if ep_summary.get("success"):
                        st.solved_tasks += 1
                    st.success_rate = round(st.solved_tasks / max(1, st.completed_tasks), 4)
                    res_str = "SOLVED" if ep_summary.get("success") else "FAILED"
                    st.recent_logs.append(f"[{now_ts}] Completed task {ep_summary.get('task_id')}: {res_str} in {ep_summary.get('steps')} steps (return: {ep_summary.get('return', 0.0):+.2f})")
                    if len(st.recent_logs) > 200:
                        st.recent_logs = st.recent_logs[-200:]
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
                execution_mode=config.execution_mode,
                provider=config.provider,
                fallback=config.fallback,
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
