# Technical Specification: DebugArena Real-Time Benchmark Control Center

## 1. Executive Summary & Goals

DebugArena is a 100-task autonomous coding-agent benchmark (Core-20, Hard-10, Benchmark V2-70).
This specification describes the incremental transformation of the existing Streamlit dashboard (`dashboard/app.py`) into a production-grade **Real-Time Benchmark Control Center**.

The Control Center provides:
1. **Interactive Run Configuration & Launching**: Select suites (Core-20, Hard-10, V2-70, All-100, or custom subsets), models (Nemotron-3-Nano, Super, custom), providers (Nebius, NVIDIA, OpenRouter, Mock), sandbox mode (Docker/Local), feedback modes (Diagnostic, Realistic, Blind), workers, max steps, and judge options.
2. **Real-Time Benchmark Monitoring**: Sub-second live progress tracking, current task/step execution details, active agent actions, pass rates, rewards, elapsed time, and cooperative graceful cancellation.
3. **Deep Post-Run Analysis & Replay**: Comprehensive Leaderboard with 95% Wilson confidence intervals, Model × Task matrices, failure category diagnostics, step-by-step episode replay with side-by-side file diffs, and task taxonomy exploration.
4. **Strict Single Execution Engine Compliance**: The dashboard never duplicates environment, sandbox, reward, or agent logic; all benchmark execution is delegated to `agentgym.runner.EpisodeRunner`.

---

## 2. Architecture & Data Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      Streamlit Control Center                          │
│   [🚀 New Eval]   [🔴 Live Monitor]   [🏆 Leaderboard]   [🎬 Replay]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ triggers / queries
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            BenchmarkManager (Singleton in agentgym/manager.py)         │
│   - Thread-safe Execution in Background Daemon Worker                  │
│   - Cooperative Cancellation via threading.Event                       │
│   - In-Memory Event Ring Buffer & Active Telemetry Snapshot            │
│   - Persistent Run State Management (runs/<run_id>/run_state.json)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ orchestrates
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                EpisodeRunner (agentgym/runner.py)                      │
│   - on_step / on_episode_start / on_episode_end callbacks              │
│   - ThreadPoolExecutor across tasks with cancellation checkpoints      │
│   - BugFixEnv → Agent / MockAgent → Sandbox (Docker/Local) → Reward    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ writes
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        runs/<run_id>/ Artifacts                        │
│   - run_state.json        (STATUS: RUNNING, COMPLETED, CANCELLED, etc) │
│   - trajectories.jsonl    (streamed step-by-step thread-safely)        │
│   - summary.json          (final aggregated metrics & episode records) │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details & APIs

### 3.1 `agentgym/runner.py` Callback & Cancellation Enhancements
Extend `EpisodeRunner` and `run_batch` with optional callbacks and cancellation support:
- `cancel_event: Optional[threading.Event]`: Checked prior to launching new tasks and between episode steps.
- `on_step: Optional[Callable[[Dict[str, Any]], None]]`: Invoked on each step with the completed step record.
- `on_episode_start: Optional[Callable[[str, str], None]]`: Invoked when a task episode starts `(task_id, episode_id)`.
- `on_episode_end: Optional[Callable[[Dict[str, Any]], None]]`: Invoked when a task finishes.
- `on_run_progress: Optional[Callable[[int, int, Dict[str, Any]], None]]`: Invoked with `(completed_count, total_count, latest_summary)`.

### 3.2 `agentgym/manager.py` (BenchmarkManager)
Thread-safe controller managing background execution:
- `RunConfig`: Dataclass specifying `run_id`, `model_name`, `provider`, `suite`, `task_ids`, `workers`, `max_steps`, `sandbox_mode`, `feedback_mode`, `use_mock_solver`, `use_noop_solver`, `enable_judge`, `enable_tracing`.
- `RunStatus`: Enum (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`).
- `RunState`: Persisted to `runs/<run_id>/run_state.json` containing metadata, timing, status, and task progress.
- `BenchmarkManager`:
  - `start_run(config: RunConfig) -> str`
  - `cancel_run(run_id: str) -> bool`
  - `get_active_run_id() -> Optional[str]`
  - `get_run_state(run_id: str) -> Optional[RunState]`
  - `get_live_telemetry(run_id: str) -> Dict[str, Any]`

### 3.3 Dashboard Modules & Pages (`dashboard/`)
- `dashboard/data.py`: Cached readers for `load_all_runs`, `load_run_state`, `load_tasks_metadata`, `compute_wilson_ci`, and format helpers.
- `dashboard/app.py`: Streamlit multi-page control center:
  1. **🚀 Launch Benchmark**: Parameter form, task multiselect/suite presets, validation, and execution trigger.
  2. **🔴 Live Monitor**: Automatic autorefresh (1.5s interval while RUNNING), progress bar, live metrics (elapsed time, tasks solved/failed, current task, step, agent action, reward sparkline), event log feed, and **🛑 Cancel Run** button.
  3. **🏆 Leaderboard & Standings**: Model comparisons across all 100 tasks with Wilson CIs, pass rates, returns, and judge quality.
  4. **📊 Task Breakdown & Taxonomy**: 100-task matrix, difficulty/bug-type distributions, and failure mode analyzer.
  5. **🎬 Episode Replay & Inspection**: Replay selector, step slider, LLM prompt inspection, JSON action, code diff viewer, sandbox stdout/stderr, and judge assessment.

---

## 4. Security, Isolation & Feedback Integrity

1. **Information Leakage Prevention**: Agent observations remain strictly filtered by `FeedbackAdapter` (diagnostic, realistic, blind). Dashboard telemetry does not leak hidden test names or test implementations into agent context.
2. **Container Security**: Docker sandbox enforces `--network none`, `mem_limit="256m"`, `cpu_limit=0.5`, and `pids_limit=128`.
3. **Cooperative Cancellation**: Cancellation sets an atomic event; workers finalize active steps cleanly and close sandboxes to prevent orphan containers or file locks.

---

## 5. Verification Plan

1. **Unit Tests**:
   - `tests/test_runner_callbacks.py`: Test callbacks, step logging, and cancellation event in `EpisodeRunner`.
   - `tests/test_benchmark_manager.py`: Test `BenchmarkManager` background execution, lifecycle transitions, state reconstruction, and cancellation.
   - `tests/test_dashboard_data.py`: Test task metadata loading across all 100 tasks and run state reconstruction.
2. **Mock Execution Smoke Test**:
   - Execute a 3-task mock benchmark run via `BenchmarkManager`.
   - Verify `run_state.json`, `trajectories.jsonl`, and `summary.json` generation.
   - Verify cancellation on an active mock run.
3. **Integration Report**:
   - Generate `docs/DASHBOARD_CONTROL_CENTER_IMPLEMENTATION_REPORT.md`.
