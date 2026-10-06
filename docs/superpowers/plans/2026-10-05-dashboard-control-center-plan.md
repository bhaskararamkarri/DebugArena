# DebugArena Real-Time Benchmark Control Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the existing DebugArena Streamlit dashboard into a production-grade Real-Time Benchmark Control Center with live run launching, real-time telemetry streaming, graceful cancellation, Wilson CI leaderboards, and deep episode replay across all 100 benchmark tasks.

**Architecture:** A thread-safe `BenchmarkManager` orchestrates the authoritative `EpisodeRunner` in background daemon workers. `EpisodeRunner` is enhanced with non-blocking callback hooks and atomic cancellation checkpoints. Run status is persisted in `runs/<run_id>/run_state.json` alongside standard artifacts (`trajectories.jsonl`, `summary.json`), allowing instant state reconstruction even across Streamlit lifecycle reruns. The Streamlit UI features dedicated views for Evaluation Launching, Live Telemetry, 100-Task Taxonomy Explorer, Comparative Leaderboard, and Step-by-Step Replay.

**Tech Stack:** Python 3.11+, Streamlit, Pandas, Altair, Rich, Pytest, Docker, OpenAI-compatible APIs (Nebius, NVIDIA, OpenRouter).

**Spec:** `docs/superpowers/specs/2026-10-05-dashboard-control-center-design.md`

## Global Constraints
- The dashboard MUST NOT create a second execution engine or duplicate environment/reward/agent/sandbox logic.
- Agent observations must strictly respect `FeedbackAdapter` rules without reward oracle or test name leakage.
- Cancellation must be cooperative and atomic without file corruption or leaving runs falsely marked COMPLETED.
- Static task metadata across all 100 tasks must be cached to keep live 1.5s refresh smooth and responsive.

## Review Focus
- Trajectory JSONL stream integrity during abrupt cancellation: step lines must remain valid JSON without partial line truncations.
- Streamlit page navigation during active background run: returning to Live Monitor must immediately reconstruct telemetry.
- Suite filtering across Core-20, Hard-10, and V2-70: all 100 tasks must be discoverable and filterable.
- Mock agent execution without Docker: local fallback baselines must succeed offline.
- Wilson score interval calculation: sample sizes of 0 or edge proportions (0%, 100%) must compute bounds safely.

---

### Task 1: Runner Callbacks & Cancellation Integration

**Files:**
- Modify: `agentgym/runner.py:24-340`
- Test: `tests/test_runner_callbacks.py`

**Interfaces:**
- Consumes: `BugFixEnv`, `Agent`, `MockAgent`, `CodeJudge`
- Produces: `EpisodeRunner.run_episode(..., on_step=None, cancel_event=None)` and `EpisodeRunner.run_batch(..., cancel_event=None, on_step=None, on_episode_start=None, on_episode_end=None, on_run_progress=None)`

---

### Task 2: Background Benchmark Manager & Persistent Run State

**Files:**
- Create: `agentgym/manager.py`
- Test: `tests/test_benchmark_manager.py`

**Interfaces:**
- Consumes: `EpisodeRunner`, `RunConfig`
- Produces: `BenchmarkManager`, `get_benchmark_manager()`, `RunConfig`, `RunStatus`, `RunState`

---

### Task 3: Dashboard Data Layer & 100-Task Metadata Support

**Files:**
- Create: `dashboard/data.py`
- Test: `tests/test_dashboard_data.py`

**Interfaces:**
- Consumes: `tasks/**/task.json`, `runs/*/summary.json`, `runs/*/run_state.json`
- Produces: `load_all_tasks_meta()`, `load_run_data()`, `load_all_runs_summary()`, `compute_wilson_ci()`

---

### Task 4: Complete Dashboard Control Center Implementation

**Files:**
- Modify: `dashboard/app.py`
- Test: `tests/test_dashboard_app.py`

**Interfaces:**
- Consumes: `agentgym.manager`, `dashboard.data`
- Produces: Multi-page Streamlit Dashboard with New Evaluation, Live Monitor (with autorefresh & cancel), Leaderboard, Task Breakdown, and Episode Replay.

---

### Task 5: End-to-End Mock Benchmark Smoke Test & Cancellation Test

**Files:**
- Test: `tests/test_e2e_control_center.py`

---

### Task 6: Final Documentation & Implementation Report

**Files:**
- Create: `docs/DASHBOARD_CONTROL_CENTER_IMPLEMENTATION_REPORT.md`
