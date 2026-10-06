# DebugArena: Custom Task & Manual Evaluation Mode

## 1. Overview

**Custom Task Mode** transforms DebugArena from a static 100-task benchmark runner into an interactive coding-agent evaluation platform. Users can supply their own coding problems and repositories (via ZIP archive or manual file entry) and allow autonomous coding agents to inspect, edit, and test their code within isolated sandboxes.

Crucially, **no second execution engine was introduced**. All custom evaluations run through the unified pipeline:

```text
Custom Task
    ↓
BenchmarkManager
    ↓
EpisodeRunner
    ↓
BugFixEnv
    ↓
Agent (Nemotron / Mock / API)
    ↓
Sandbox (Docker / Local)
    ↓
Evaluation & RewardCalculator
    ↓
Persistence (runs/<run_id>/)
    ↓
Live Monitor & Episode Replay
```

---

## 2. How to Create a Custom Task

1. Navigate to **🚀 New Evaluation** in the sidebar.
2. At the top of the page, switch **Evaluation Mode** to `🧪 Custom Task`.
3. Enter your **Problem Description / Instructions** (e.g., *"Fix the off-by-one error in mathutils.py"*).
4. Provide the project source code via **Upload ZIP Archive** or **Add / Edit Files Manually**.
5. Select an **Evaluation Oracle** (Hidden Tests, Reference Solution, or Solve Only).
6. Configure the **Model**, **Provider**, **Sandbox Environment**, and **Max Steps**.
7. Click **🚀 RUN CUSTOM TASK**. The execution launches asynchronously in a background daemon thread and automatically switches to **🔴 Live Monitor**.

---

## 3. Uploading Project ZIPs

Users can upload any standard `.zip` archive containing their repository or code files.
- **Automatic Traversal Protection:** Relative path sanitization blocks all directory traversal attempts (`..`) and absolute path specifications (`/`, `C:\`).
- **Archive Bomb Prevention:** Uncompressed archive size is limited to 50 MB, file count is capped at 500 files, and individual file sizes are capped at 10 MB.
- **Root Folder Normalization:** If all files in the ZIP are contained within a single root folder (e.g., `my-repo/app.py`), the prefix is automatically stripped so project files are located at the workspace root.

---

## 4. Providing Hidden Tests & Evaluation Oracles

To prevent self-reported or fabricated benchmark scores, DebugArena enforces an objective evaluation oracle:

### Option A: Hidden Tests (Automated Test Oracle)
- Upload a `tests.zip` or provide a single test script (e.g., `test_solution.py` using `pytest`).
- **Evaluator Isolation Guarantee:** Hidden tests are strictly mounted in the evaluator sandbox during evaluation steps. The agent **NEVER** observes, reads, or accesses these tests in its observation window.

### Option B: Reference Solution
- Provide reference fixed files or patches for upper-bound verification and mock solver validation.

### Option C: Solve Only (No Test Oracle)
- If no automated tests are provided, DebugArena does **not** fabricate a pass rate or score.
- The agent explores and attempts a solution, and the run is explicitly finalized with status `SOLVE ONLY`.

---

## 5. Security & Isolation Model

| Threat Vector | Mitigation Mechanism |
|---|---|
| **Path Traversal / ZIP Slip** | `sanitize_rel_path()` checks every entry before extraction. Any segment containing `..` or leading slashes is rejected with `ZipSecurityError`. |
| **Symlink Escapes** | ZIP member attributes are inspected; `0o120000` symlink bits are rejected immediately. |
| **Archive Bombs** | Strict size ceilings enforced during streaming decompression. |
| **Information Leakage** | Hidden tests are mounted temporarily in `LocalSandbox` during `run_tests()` and deleted immediately; in `DockerSandbox`, tests reside in a separate read-only `/tests` volume never mounted during agent `run_command()`. |
| **Container Isolation** | Docker sandbox enforces `--network none`, `mem_limit="256m"`, `cpu_limit=0.5`, and `pids_limit=128`. |
| **Official Benchmark Isolation** | Custom tasks reside in `custom_tasks/<task_id>/` and are filtered out of official benchmark leaderboard statistics. Official benchmark task count remains strictly 100. |

---

## 6. Execution Lifecycle & Live Monitoring

1. **Launch:** `BenchmarkManager.start_run(config)` allocates a background worker thread and persists `run_state.json`.
2. **Streaming Telemetry:** During execution, `EpisodeRunner` triggers callbacks (`on_step`, `on_episode_start`, `on_episode_end`), populating in-memory ring buffers.
3. **Live UI Updates:** The Streamlit **🔴 Live Monitor** polls every 1.5 seconds, displaying live KPIs, agent actions, modified code, and sandbox execution outputs.
4. **Cooperative Cancellation:** Clicking **🛑 STOP / CANCEL RUN** atomically signals `cancel_event`, cleanly closing sandbox containers and persisting `status: CANCELLED` without JSONL corruption.

---

## 7. Results & Artifacts

All runs persist to `runs/<run_id>/`:
- `run_state.json`: Current and final lifecycle state (`RUNNING`, `COMPLETED`, `CANCELLED`, `FAILED`).
- `summary.json`: Aggregated metrics, pass rates, and episode records.
- `trajectories.jsonl`: Step-by-step trajectory records containing agent actions, observations, rewards, and execution outputs.

### Episode Replay & Diff Viewer
Custom runs can be replayed in **🎬 Episode Replay**, featuring:
- Step-by-step slider scrubber.
- JSON action inspector and sandbox stdout/stderr log viewer.
- **Unified Diff Viewer** comparing initial project files against final agent modifications.

---

## 8. Known Limitations & Operational Guidance

1. **Docker Daemon for Live LLMs:** Live evaluations using remote model APIs (e.g., Nebius / NVIDIA Nemotron) require a running Docker daemon for isolated container execution. `LocalSandbox` is intended for offline baselines and mock solvers.
2. **Framework Support:** Automated test execution currently uses `pytest` within Python environments.
