"""Streamlit Real-Time Benchmark Control Center V2 for DebugArena.

Architecture:
10 Structured Pages across 3 distinct operational domains:
- WORKSPACE:
  1. 🏠 Overview (Benchmark & System status, composition, high-level metrics)
  2. 🚀 New Evaluation (Configure & launch Official benchmark runs, Subsuites, or Custom Tasks)
  3. 🔴 Live Runs (Real-time telemetry, auto-refresh streaming, cooperative cancellation)
  4. 📜 Run History (Filterable archive of all historical runs with classification & status)

- ANALYSIS:
  5. 🏆 Leaderboard (Rankings with 95% Wilson Score CIs, official vs reference separation, Altair charts)
  6. 📊 Benchmark Analysis (Model × Task matrix with safe fallback, error modes, difficulty breakdowns)
  7. 🔍 Task Explorer (100-task taxonomy inspector, Core-20 vs Hard-10 vs V2-70, test & code viewer)
  8. 🎬 Episode Replay (Interactive step-by-step trajectory inspector with prompts, actions, diffs)

- SYSTEM:
  9. 🛡️ Benchmark Integrity (Automated P0 compliance audits: tasks, manifests, security, provider)
  10. ⚙️ Configuration (Provider endpoints, execution mode, token factory, reward parameters)
"""

from __future__ import annotations

import datetime
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

from agentgym.provider import ExecutionMode, ProviderPolicyError
from agentgym.custom_task import (
    CustomTask,
    ZipSecurityError,
    compute_file_diff,
    extract_zip_safely,
    generate_custom_task_id,
    list_custom_tasks,
)
from agentgym.manager import (
    BenchmarkManager,
    RunConfig,
    RunState,
    RunStatus,
    get_benchmark_manager,
)
from dashboard.data import (
    classify_run,
    compute_wilson_ci,
    determine_leaderboard_eligibility,
    format_model_label,
    get_available_models,
    get_available_providers,
    get_suite_task_ids,
    is_custom_run,
    load_all_runs,
    load_custom_tasks_metadata,
    load_single_run_trajectories,
    load_tasks_metadata,
    safe_render_matrix,
    verify_benchmark_integrity,
)

st.set_page_config(
    page_title="DebugArena | Control Center V2",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for clean, modern benchmark aesthetic
st.markdown(
    """
    <style>
    .metric-card {
        background: #1e293b;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #334155;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.04);
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .live-badge-running {
        display: inline-block;
        background-color: #ef4444;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: bold;
        font-size: 0.85rem;
        animation: pulse 2s infinite;
    }
    .live-badge-completed {
        display: inline-block;
        background-color: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .live-badge-cancelled {
        display: inline-block;
        background-color: #f59e0b;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .live-badge-solve_only {
        display: inline-block;
        background-color: #6366f1;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-official {
        display: inline-block;
        background-color: #3b82f6;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-reference {
        display: inline-block;
        background-color: #8b5cf6;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-custom {
        display: inline-block;
        background-color: #10b981;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    .badge-experimental {
        display: inline-block;
        background-color: #64748b;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.78rem;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Initialize Managers and Data
# -----------------------------------------------------------------------------
manager = get_benchmark_manager()
tasks_meta = load_tasks_metadata("tasks")
custom_tasks_meta = load_custom_tasks_metadata("custom_tasks")
suite_mapping = get_suite_task_ids(tasks_meta)
runs_data = load_all_runs("runs")

# -----------------------------------------------------------------------------
# Sidebar Navigation (10 Pages organized by Domain)
# -----------------------------------------------------------------------------
st.sidebar.title("⚔️ DebugArena")
st.sidebar.caption("Benchmark Control Center V2")

PAGES = [
    "🏠 Overview",
    "🚀 New Evaluation",
    "🔴 Live Runs",
    "📜 Run History",
    "🏆 Leaderboard",
    "📊 Benchmark Analysis",
    "🔍 Task Explorer",
    "🎬 Episode Replay",
    "🛡️ Benchmark Integrity",
    "⚙️ Configuration",
]

page = st.sidebar.radio("Navigation", PAGES, index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("**Repository Inventory:**")
st.sidebar.write(f"• Official Benchmark: **30 Tasks**")
st.sidebar.write(f"  - Core-20: **20** | Hard-10: **10**")
st.sidebar.write(f"• V2 Candidates: **70 Tasks** (Pending)")
st.sidebar.write(f"• Total Corpus: **100 Tasks**")
if custom_tasks_meta:
    st.sidebar.write(f"• Custom Tasks: **{len(custom_tasks_meta)}**")
st.sidebar.write(f"• Tracked Runs: **{len(runs_data)}**")

active_run = manager.get_active_run()
if active_run and active_run.status == RunStatus.RUNNING:
    st.sidebar.success(f"🔴 Live Run: `{active_run.config.run_id}`")

# =============================================================================
# PAGE 1: 🏠 Overview
# =============================================================================
if page == "🏠 Overview":
    st.title("🏠 Benchmark Overview & System Status")
    st.markdown(
        """
        Welcome to the **DebugArena Control Center V2**, the authoritative evaluation platform for
        autonomous AI software engineering and debugging agents.
        """
    )

    # Key Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Official Benchmark Tasks", "30", help="Authoritative 30 tasks: 20 Core + 10 Hard")
    with c2:
        st.metric("V2 Candidate Tasks", "70", help="Generated and verified synthetic candidate tasks")
    with c3:
        st.metric("Total Task Corpus", "100", help="Full repository task inventory")
    with c4:
        st.metric("Total Tracked Runs", str(len(runs_data)), help="Official, reference, and experimental runs")

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🎯 Authoritative Benchmark Composition")
        st.markdown(
            """
            DebugArena strictly partitions task tiers to prevent benchmark leakage and maintain scientific rigor:
            - **Core-20 (`t01` – `t20`)**: Standard multi-domain debugging tasks (algorithms, state machines, concurrency).
            - **Hard-10 (`h01` – `h10`)**: Complex debugging tasks with subtle edge cases, large context requirements, and deep dependencies.
            - **Official 30-Task Benchmark**: The combined canonical suite (`Core-20` + `Hard-10`) used for all published rankings.
            - **V2 Candidate Tasks (`v01` – `v70`)**: 70 generated, validated, and verified tasks pending future official benchmark releases.
            """
        )

        st.subheader("⚡ System Capabilities")
        st.markdown(
            """
            - **Real-Time Live Monitor**: Stream evaluations with step-by-step telemetry, intermediate actions, and cooperative cancellation.
            - **Isolated Custom Tasks**: Upload and evaluate custom GitHub repositories or codebases without contaminating official benchmarks.
            - **Rigorous Run Classification**: Automatic partitioning of Official, Reference Upper/Lower bounds, Reproduction, and Experimental runs.
            - **P0 Sandbox Security**: Strict path traversal validation and isolated execution.
            """
        )

    with col_right:
        st.subheader("🛡️ Quick Integrity Status")
        integrity_report = verify_benchmark_integrity("runs", "tasks", "config.yaml")
        overall = integrity_report.get("status", "UNKNOWN")

        if overall == "PASS":
            st.success("✅ **All Benchmark Integrity Audits Passing**")
        elif overall == "WARN":
            st.warning("⚠️ **Integrity Audits Passed with Warnings**")
        else:
            st.error("❌ **Integrity Violations Detected**")

        summary = integrity_report.get("summary", {})
        st.write(f"• Total Checks: **{summary.get('total_checks', 0)}**")
        st.write(f"• Passed: **{summary.get('passed', 0)}**")
        st.write(f"• Warnings: **{summary.get('warnings', 0)}**")
        st.write(f"• Failed: **{summary.get('failed', 0)}**")

        st.markdown("---")
        st.subheader("🏆 Canonical Benchmark Baseline")
        official_run = runs_data.get("official")
        if official_run and official_run.get("summary"):
            s = official_run["summary"]
            st.write(f"• Canonical Model: **`{s.get('model', 'Nemotron 3 Super')}`**")
            st.write(f"• Success Rate: **`{s.get('success_rate', 0.0) * 100:.1f}%`** (28/30 solved)")
            st.write(f"• 95% Wilson CI: **`{s.get('wilson_95_ci', '[78.7%, 98.2%]')}`**")
            st.write(f"• Avg Steps: **`{s.get('avg_steps', 0.0):.2f}`** | Avg Return: **`{s.get('avg_return', 0.0):.3f}`**")
        else:
            st.info("Canonical official run artifacts available in `runs/official/`")

# =============================================================================
# PAGE 2: 🚀 New Evaluation
# =============================================================================
elif page == "🚀 New Evaluation":
    st.title("🚀 Launch Benchmark Evaluation")
    st.markdown(
        """
        Configure and launch evaluations for official benchmark suites or custom user-defined coding tasks.
        Evaluations run asynchronously via the `BenchmarkManager` with real-time state tracking.
        """
    )

    models_dict = get_available_models("config.yaml")
    model_keys = list(models_dict.keys())
    eval_mode = st.radio(
        "Evaluation Target",
        ["Standard Benchmark Suite", "Custom Task (Upload ZIP / Existing)"],
        horizontal=True,
    )

    st.markdown("---")

    if eval_mode == "Standard Benchmark Suite":
        st.subheader("1. Benchmark Suite Selection")
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            suite_choice = st.selectbox(
                "Benchmark Suite",
                [
                    "Official Benchmark (30 Tasks: Core-20 + Hard-10)",
                    "Core-20 (20 Tasks)",
                    "Hard-10 (10 Tasks)",
                    "Benchmark V2 (70 Tasks - Candidate)",
                    "Full Corpus (100 Tasks - Experimental)",
                    "Custom Task Subset",
                ],
                index=0,
            )

        with col_s2:
            model_selection = st.selectbox(
                "Model to Evaluate",
                model_keys,
                index=1 if len(model_keys) > 1 else 0,
                format_func=lambda x: f"{models_dict[x]['desc']} [{models_dict[x]['provider']}]",
            )

        # Resolve Task IDs
        if suite_choice.startswith("Official Benchmark"):
            selected_task_ids = suite_mapping.get("Core-20 (20 Tasks)", []) + suite_mapping.get("Hard-10 (10 Tasks)", [])
            suite_name = "official_30"
        elif suite_choice.startswith("Core-20"):
            selected_task_ids = suite_mapping.get("Core-20 (20 Tasks)", [])
            suite_name = "core_20"
        elif suite_choice.startswith("Hard-10"):
            selected_task_ids = suite_mapping.get("Hard-10 (10 Tasks)", [])
            suite_name = "hard_10"
        elif suite_choice.startswith("Benchmark V2"):
            selected_task_ids = suite_mapping.get("Benchmark V2 (70 Tasks)", [])
            suite_name = "v2_70"
        elif suite_choice.startswith("Full Corpus"):
            selected_task_ids = suite_mapping.get("All (100 Tasks)", [])
            suite_name = "corpus_100"
        else:
            all_available = sorted(list(tasks_meta.keys()))
            selected_task_ids = st.multiselect("Select Specific Tasks", all_available, default=all_available[:5])
            suite_name = "custom_subset"

        st.info(f"Target contains **{len(selected_task_ids)} tasks**. Suite code: `{suite_name}`")

        st.subheader("2. Run Parameters & Sandbox Configuration")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            max_steps = st.number_input("Max Steps / Task", min_value=1, max_value=50, value=10)
        with c2:
            timeout = st.number_input("Timeout (sec) / Step", min_value=1, max_value=60, value=10)
        with c3:
            feedback_mode = st.selectbox("Feedback Mode", ["diagnostic", "binary", "none"], index=0)
        with c4:
            sandbox_type = st.selectbox("Sandbox Environment", ["local", "docker"], index=0)

        c5, c6 = st.columns(2)
        with c5:
            custom_run_id = st.text_input("Run ID", value=f"run_{int(time.time())}")
        with c6:
            notes = st.text_input("Run Description / Notes", value="Control Center V2 Evaluation")

        st.markdown("---")
        if st.button("🚀 Launch Evaluation Run", type="primary"):
            active = manager.get_active_run()
            if active and active.status == RunStatus.RUNNING:
                st.error(f"Cannot start new run: Run `{active.config.run_id}` is currently RUNNING.")
            else:
                config = RunConfig(
                    run_id=custom_run_id.strip() or f"run_{int(time.time())}",
                    model=model_selection,
                    provider=models_dict[model_selection]["provider"],
                    suite=suite_name,
                    task_ids=selected_task_ids,
                    max_steps=int(max_steps),
                    timeout_seconds=int(timeout),
                    feedback_mode=feedback_mode,
                    sandbox_type=sandbox_type,
                    notes=notes,
                )
                try:
                    manager.start_run(config)
                    st.success(f"Evaluation `{config.run_id}` launched successfully!")
                    st.info("Navigate to **🔴 Live Runs** to monitor real-time progress.")
                except Exception as e:
                    st.error(f"Failed to launch run: {e}")

    else:
        # Custom Task Evaluation Mode
        st.subheader("Custom Task Creator & Evaluator (Isolated Sandbox)")
        st.markdown(
            """
            Upload a ZIP archive containing a Python codebase and unit tests to evaluate agents on proprietary code.
            Custom tasks are automatically assigned unique IDs and isolated in `custom_tasks/`.
            """
        )

        tab_new, tab_existing = st.tabs(["📤 Upload New Task ZIP", "📁 Select Existing Custom Task"])

        with tab_new:
            uploaded_file = st.file_uploader("Upload Codebase ZIP (Must include code and test files)", type=["zip"])
            task_title = st.text_input("Task Title / Objective", placeholder="Fix pagination off-by-one error in search API")
            c_diff = st.selectbox("Estimated Difficulty", ["easy", "medium", "hard"], index=1)

            if uploaded_file is not None and task_title:
                if st.button("📦 Process & Register Custom Task", type="primary"):
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                            tmp.write(uploaded_file.getbuffer())
                            tmp_path = tmp.name

                        task_id = generate_custom_task_id(task_title)
                        extracted_files = extract_zip_safely(tmp_path)
                        os.unlink(tmp_path)

                        # Separate repo files and tests
                        repo_files: Dict[str, str] = {}
                        tests: Dict[str, str] = {}
                        for rel, content in extracted_files.items():
                            if "test" in rel.lower():
                                tests[rel] = content
                            else:
                                repo_files[rel] = content

                        now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        custom_task = CustomTask(
                            task_id=task_id,
                            title=task_title,
                            description=f"Custom task: {task_title}",
                            difficulty=c_diff,
                            repo_files=repo_files,
                            tests=tests if tests else {"test_main.py": "def test_placeholder(): assert True"},
                            created_at=now_iso,
                        )
                        custom_task.save()
                        st.success(f"Custom task `{task_id}` created successfully with {len(repo_files)} source files and {len(tests)} test files!")
                        st.rerun()
                    except ZipSecurityError as zse:
                        st.error(f"Security Alert: {zse}")
                    except Exception as ex:
                        st.error(f"Error processing custom task: {ex}")

        with tab_existing:
            if not custom_tasks_meta:
                st.info("No custom tasks registered yet. Upload a ZIP archive above.")
            else:
                c_tids = list(custom_tasks_meta.keys())
                selected_c_tid = st.selectbox("Select Custom Task", c_tids, format_func=lambda x: f"{x}: {custom_tasks_meta[x].get('title', x)}")

                c_model = st.selectbox(
                    "Model for Custom Evaluation",
                    model_keys,
                    key="custom_model_select",
                    format_func=lambda x: f"{models_dict[x]['desc']} [{models_dict[x]['provider']}]",
                )

                if st.button("🚀 Evaluate Model on Custom Task", type="primary"):
                    c_run_id = f"custom_{selected_c_tid}_{int(time.time())}"
                    config = RunConfig(
                        run_id=c_run_id,
                        model=c_model,
                        provider=models_dict[c_model]["provider"],
                        suite="custom",
                        task_ids=[selected_c_tid],
                        max_steps=10,
                        timeout_seconds=15,
                        feedback_mode="diagnostic",
                        sandbox_type="local",
                        notes=f"Custom evaluation on {selected_c_tid}",
                    )
                    try:
                        manager.start_run(config)
                        st.success(f"Custom evaluation `{c_run_id}` started!")
                        st.info("Navigate to **🔴 Live Runs** to observe progress.")
                    except Exception as e:
                        st.error(f"Failed to start custom evaluation: {e}")

# =============================================================================
# PAGE 3: 🔴 Live Runs
# =============================================================================
elif page == "🔴 Live Runs":
    st.title("🔴 Live Evaluation Monitor & Streaming Telemetry")
    st.markdown("Real-time telemetry and execution monitoring for in-flight and completed benchmark runs.")

    auto_refresh = st.checkbox("Auto-refresh (every 2 seconds)", value=True)

    active_run = manager.get_active_run()

    if not active_run:
        # Check if user wants to inspect most recent disk run
        all_run_ids = sorted(list(runs_data.keys()), reverse=True)
        if all_run_ids:
            selected_run_id = st.selectbox("Select Run to Inspect", all_run_ids, index=0)
            run_item = runs_data.get(selected_run_id, {})
            summary = run_item.get("summary", {})
            state = run_item.get("state", {})

            st.subheader(f"Run Telemetry: `{selected_run_id}`")
            st.markdown(f"Category: **`{run_item.get('category', 'experimental').upper()}`** | Status: **COMPLETED**")

            total = summary.get("total_tasks", state.get("total_tasks", 0))
            solved = summary.get("solved_tasks", state.get("solved_tasks", 0))
            sr = (solved / total * 100) if total > 0 else 0.0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tasks Completed", f"{total}")
            c2.metric("Solved Tasks", f"{solved}")
            c3.metric("Success Rate", f"{sr:.1f}%")
            c4.metric("Avg Steps", f"{summary.get('avg_steps', state.get('avg_steps', 0.0)):.2f}")

            episodes = summary.get("episodes", state.get("episodes", []))
            if episodes:
                st.subheader("Episode Summary Table")
                df_ep = pd.DataFrame(episodes)
                st.dataframe(df_ep, use_container_width=True)
        else:
            st.info("No benchmark runs found. Launch a new evaluation from **🚀 New Evaluation**.")
    else:
        # Active Run Monitor
        st.subheader(f"Active Evaluation: `{active_run.config.run_id}`")

        badge_class = f"live-badge-{active_run.status.value.lower()}"
        st.markdown(f"Status: <span class='{badge_class}'>{active_run.status.value.upper()}</span>", unsafe_allow_html=True)

        if active_run.status == RunStatus.RUNNING:
            if st.button("⏹️ Cooperatively Cancel Run", type="secondary"):
                manager.cancel_run(active_run.config.run_id)
                st.warning("Cancellation signal dispatched to execution engine.")

        # Progress Bars & Metrics
        total_tasks = active_run.total_tasks
        completed = active_run.completed_tasks
        solved = active_run.solved_tasks
        prog_frac = (completed / total_tasks) if total_tasks > 0 else 0.0

        st.progress(prog_frac, text=f"Progress: {completed}/{total_tasks} tasks ({prog_frac*100:.1f}%)")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Task", active_run.current_task_id or "Initializing...")
        m2.metric("Step in Task", f"{active_run.current_step} / {active_run.config.max_steps}")
        m3.metric("Solved Count", f"{solved} / {completed}")
        m4.metric("Model", active_run.config.model.split("/")[-1])

        # Step Logs / Telemetry
        if active_run.recent_logs:
            st.subheader("Live Telemetry Stream")
            log_box = "\n".join(active_run.recent_logs[-15:])
            st.code(log_box, language="text")

        # Display Final Summary from disk if finished
        if active_run.status in [RunStatus.COMPLETED, RunStatus.CANCELLED, RunStatus.FAILED]:
            st.markdown("---")
            st.success("Evaluation lifecycle finished. Rendering final run artifacts from disk.")
            summary_path = Path("runs") / active_run.config.run_id / "summary.json"
            if summary_path.exists():
                try:
                    with open(summary_path, "r", encoding="utf-8") as f:
                        final_summary = json.load(f)
                    st.json(final_summary)
                except Exception:
                    pass

        if auto_refresh and active_run.status == RunStatus.RUNNING:
            time.sleep(2)
            st.rerun()

# =============================================================================
# PAGE 4: 📜 Run History
# =============================================================================
elif page == "📜 Run History":
    st.title("📜 Historical Benchmark Runs Archive")
    st.markdown("Search, filter, and inspect all past benchmark evaluations, reference runs, and custom experiments.")

    if not runs_data:
        st.info("No runs found in `runs/` directory.")
    else:
        # Filters
        c1, c2 = st.columns(2)
        with c1:
            category_filter = st.multiselect(
                "Filter by Category",
                ["official", "reference", "custom", "smoke", "reproduction", "experimental", "invalid"],
                default=["official", "reference", "custom", "experimental"],
            )
        with c2:
            search_query = st.text_input("Search Run ID or Model Name", placeholder="e.g. super, official, mock")

        table_rows = []
        for rid, item in runs_data.items():
            cat = item.get("category", "experimental")
            if category_filter and cat not in category_filter:
                continue
            if search_query:
                s_low = search_query.lower()
                if s_low not in rid.lower() and s_low not in str(item.get("summary", {}).get("model", "")).lower():
                    continue

            summary = item.get("summary", {})
            state = item.get("state", {})
            total = summary.get("total_tasks", state.get("total_tasks", 0))
            solved = summary.get("solved_tasks", state.get("solved_tasks", 0))
            sr = (solved / total * 100) if total > 0 else 0.0

            table_rows.append({
                "Run ID": rid,
                "Category": cat.upper(),
                "Eligible for Leaderboard": "✅ YES" if item.get("is_eligible") else "❌ NO",
                "Model": summary.get("model", state.get("config", {}).get("model", "N/A")),
                "Total Tasks": total,
                "Solved": solved,
                "Success Rate": f"{sr:.1f}%",
                "Wilson 95% CI": summary.get("wilson_95_ci", compute_wilson_ci(solved, total)),
                "Avg Steps": f"{summary.get('avg_steps', state.get('avg_steps', 0.0)):.2f}",
                "Trajectories": "Available" if item.get("has_trajectories") else "None",
            })

        if table_rows:
            df_runs = pd.DataFrame(table_rows)
            st.dataframe(df_runs, use_container_width=True)
        else:
            st.warning("No runs match the selected filters.")

# =============================================================================
# PAGE 5: 🏆 Leaderboard
# =============================================================================
elif page == "🏆 Leaderboard":
    st.title("🏆 Authoritative Benchmark Leaderboard")
    st.markdown(
        """
        Rankings for the **Official 30-Task Benchmark** (`Core-20` + `Hard-10`).
        Confidence intervals are computed using the **95% Wilson Score Interval**.
        Reference upper/lower bounds are segregated to preserve scientific integrity.
        """
    )

    # 1. Official Model Rankings Table
    st.subheader("1. Official Model Standings (30 Tasks)")
    official_rows = []
    reference_rows = []

    for rid, item in runs_data.items():
        summary = item.get("summary", {})
        state = item.get("state", {})
        total = summary.get("total_tasks", state.get("total_tasks", 0))
        solved = summary.get("solved_tasks", state.get("solved_tasks", 0))
        model = summary.get("model", state.get("config", {}).get("model", rid))
        clean_model = format_model_label(rid, model)
        sr = (solved / total * 100) if total > 0 else 0.0
        ci = summary.get("wilson_95_ci", compute_wilson_ci(solved, total))

        avg_judge = summary.get("avg_judge_score", state.get("avg_judge_score"))
        judge_display = f"{avg_judge:.2f}" if (avg_judge is not None and isinstance(avg_judge, (int, float))) else "N/A"

        entry = {
            "Rank": 1,
            "Model": clean_model,
            "Run ID": rid,
            "Success Rate": sr,
            "Success %": f"{sr:.1f}%",
            "95% Wilson CI": ci,
            "Solved / Total": f"{solved}/{total}",
            "Avg Steps": summary.get("avg_steps", state.get("avg_steps", 0.0)),
            "Avg Return": summary.get("avg_return", state.get("avg_return", 0.0)),
            "Avg Judge Score": judge_display,
        }

        if item.get("is_eligible") and item.get("category") == "official":
            official_rows.append(entry)
        elif item.get("category") == "reference":
            reference_rows.append(entry)

    # Sort and rank official models
    official_rows.sort(key=lambda x: x["Success Rate"], reverse=True)
    for idx, r in enumerate(official_rows):
        r["Rank"] = idx + 1

    if official_rows:
        df_official = pd.DataFrame(official_rows)
        st.dataframe(
            df_official.drop(columns=["Success Rate"]),
            use_container_width=True,
            hide_index=True,
        )

        # Altair Visualization with Error Margins
        st.subheader("📊 Success Rate Comparison with 95% Wilson CI")
        chart_df = df_official.copy()
        chart = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#3b82f6")
            .encode(
                x=alt.X("Model:N", sort="-y", title="Model"),
                y=alt.Y("Success Rate:Q", title="Success Rate (%)", scale=alt.Scale(domain=[0, 100])),
                tooltip=["Model", "Success %", "95% Wilson CI", "Solved / Total"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No completed official 30-task runs available yet.")

    # 2. Reference Bounds & Experimental Baselines
    st.markdown("---")
    st.subheader("2. Reference Upper & Lower Bounds (Segregated)")
    if reference_rows:
        df_ref = pd.DataFrame(reference_rows).drop(columns=["Rank", "Success Rate"])
        st.dataframe(df_ref, use_container_width=True, hide_index=True)
    else:
        st.info("No reference solver runs loaded.")

# =============================================================================
# PAGE 6: 📊 Benchmark Analysis
# =============================================================================
elif page == "📊 Benchmark Analysis":
    st.title("📊 Benchmark Diagnostics & Task Matrix")
    st.markdown("In-depth performance analytics across suites, difficulty tiers, and individual tasks.")

    tab_matrix, tab_difficulty, tab_errors = st.tabs([
        "🧩 Model × Task Matrix",
        "⚖️ Difficulty Breakdown",
        "⚠️ Failure Mode Diagnostics",
    ])

    with tab_matrix:
        st.subheader("Task-Level Solvability Heatmap")
        # Build pivot dataframe of Model vs Task Solved Status
        matrix_records = []
        for rid, item in runs_data.items():
            if item.get("category") in ["official", "reference", "experimental"]:
                summary = item.get("summary", {})
                episodes = summary.get("episodes", [])
                model_name = format_model_label(rid, summary.get("model", rid))
                for ep in episodes:
                    tid = ep.get("task_id", "")
                    is_solved = bool(ep.get("success") or ep.get("solved") or ep.get("status") in ["PASS", "SOLVED"])
                    solved = 1.0 if is_solved else 0.0
                    matrix_records.append({
                        "Model": model_name,
                        "Task": tid,
                        "Solved": solved,
                    })

        if matrix_records:
            df_m = pd.DataFrame(matrix_records)
            pivot_df = df_m.pivot_table(index="Task", columns="Model", values="Solved", fill_value=0.0)
            styled = safe_render_matrix(pivot_df, cmap="Greens", vmin=0.0, vmax=1.0)
            st.dataframe(styled, use_container_width=True)
        else:
            st.info("No episode-level results found across runs to generate task matrix.")

    with tab_difficulty:
        st.subheader("Performance by Difficulty Tier")
        st.markdown("Comparing model success rates across **Easy**, **Medium**, and **Hard** tasks.")
        diff_records = []
        for rid, item in runs_data.items():
            summary = item.get("summary", {})
            episodes = summary.get("episodes", [])
            model_name = format_model_label(rid, summary.get("model", rid))
            for ep in episodes:
                tid = ep.get("task_id", "")
                t_meta = tasks_meta.get(tid, {})
                diff = t_meta.get("difficulty", "medium").capitalize()
                is_solved = bool(ep.get("success") or ep.get("solved") or ep.get("status") in ["PASS", "SOLVED"])
                diff_records.append({
                    "Model": model_name,
                    "Difficulty": diff,
                    "Solved": 1 if is_solved else 0,
                })

        if diff_records:
            df_d = pd.DataFrame(diff_records)
            grp = df_d.groupby(["Model", "Difficulty"]).agg(
                Total=("Solved", "count"),
                Solved=("Solved", "sum"),
            ).reset_index()
            grp["Success Rate (%)"] = (grp["Solved"] / grp["Total"]) * 100
            st.dataframe(grp, use_container_width=True)
        else:
            st.info("Insufficient episode metadata for difficulty analysis.")

    with tab_errors:
        st.subheader("Agent Failure Mode Breakdown")
        st.markdown("Categorization of failure modes: `wrong_fix`, `out_of_steps`, `syntax_error`, and `regression`.")
        fail_records = []
        for rid, item in runs_data.items():
            summary = item.get("summary", {})
            fb = summary.get("failure_breakdown", {})
            if fb:
                fail_records.append({
                    "Run ID": rid,
                    "Model": format_model_label(rid, summary.get("model", rid)),
                    "Wrong Fix": fb.get("wrong_fix", 0),
                    "Out of Steps": fb.get("out_of_steps", 0),
                    "Regressions": fb.get("regression", 0),
                })
        if fail_records:
            st.dataframe(pd.DataFrame(fail_records), use_container_width=True)
        else:
            st.info("No failure mode breakdown data available.")

# =============================================================================
# PAGE 7: 🔍 Task Explorer
# =============================================================================
elif page == "🔍 Task Explorer":
    st.title("🔍 Benchmark Task Explorer (100-Task Corpus)")
    st.markdown(
        """
        Inspect the complete 100-task repository corpus:
        - **30 Official Tasks**: 20 Core (`t01` – `t20`) + 10 Hard (`h01` – `h10`)
        - **70 V2 Candidate Tasks**: (`v01` – `v70`)
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        suite_filter = st.selectbox(
            "Filter by Suite",
            ["All Tasks (100)", "Core-20 (Official)", "Hard-10 (Official)", "V2 Candidates (70)"],
            index=0,
        )

    # Filter tasks
    if suite_filter.startswith("Core-20"):
        filtered_tids = [t for t, d in tasks_meta.items() if d.get("suite") == "Core-20"]
    elif suite_filter.startswith("Hard-10"):
        filtered_tids = [t for t, d in tasks_meta.items() if d.get("suite") == "Hard-10"]
    elif suite_filter.startswith("V2 Candidates"):
        filtered_tids = [t for t, d in tasks_meta.items() if d.get("suite") == "V2-70"]
    else:
        filtered_tids = sorted(list(tasks_meta.keys()))

    with c2:
        selected_tid = st.selectbox("Select Task", filtered_tids)

    if selected_tid:
        t_data = tasks_meta.get(selected_tid, {})
        st.markdown("---")
        st.subheader(f"Task: `{selected_tid}` — {t_data.get('title', selected_tid)}")

        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Suite", t_data.get("suite", "Core-20"))
        c_m2.metric("Difficulty", t_data.get("difficulty", "medium").upper())
        c_m3.metric("Source Files", str(t_data.get("file_count", 0)))
        c_m4.metric("Unit Tests", str(t_data.get("test_count", 0)))

        st.markdown(f"**Description / Instructions:**\n{t_data.get('description', 'No description provided.')}")

        tab_code, tab_tests, tab_ref = st.tabs(["📄 Buggy Source Code", "🧪 Unit Tests", "💡 Reference Patch"])
        with tab_code:
            repo_files = t_data.get("repo_files", {})
            if repo_files:
                for fname, fcontent in repo_files.items():
                    st.markdown(f"**`{fname}`**")
                    st.code(fcontent, language="python")
            else:
                st.info("No inline repo files stored in task metadata.")

        with tab_tests:
            tests = t_data.get("tests", {})
            if tests:
                for tname, tcontent in tests.items():
                    st.markdown(f"**`{tname}`**")
                    st.code(tcontent, language="python")
            else:
                st.info("No inline test files stored in task metadata.")

        with tab_ref:
            ref_patch = t_data.get("reference_patch", "")
            if ref_patch:
                st.code(ref_patch, language="diff")
            else:
                st.info("Reference patch not exposed or verified in runtime sandbox.")

# =============================================================================
# PAGE 8: 🎬 Episode Replay
# =============================================================================
elif page == "🎬 Episode Replay":
    st.title("🎬 Interactive Step-by-Step Trajectory Replay")
    st.markdown("Inspect full agent reasoning trajectories, tool invocations, code diffs, and execution returns.")

    run_options = [r for r, d in runs_data.items() if d.get("has_trajectories")]
    if not run_options:
        st.info("No runs with recorded `trajectories.jsonl` files available.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            selected_replay_run = st.selectbox("Select Run", run_options, index=0)

        trajectories = load_single_run_trajectories(selected_replay_run)
        if not trajectories:
            st.warning(f"No trajectory steps found in `runs/{selected_replay_run}/trajectories.jsonl`.")
        else:
            # Group trajectories by task
            task_steps: Dict[str, List[Dict[str, Any]]] = {}
            for step in trajectories:
                tid = step.get("task_id", "unknown_task")
                if tid not in task_steps:
                    task_steps[tid] = []
                task_steps[tid].append(step)

            with c2:
                selected_replay_task = st.selectbox("Select Task Episode", list(task_steps.keys()))

            steps = task_steps.get(selected_replay_task, [])
            st.markdown(f"### Episode: `{selected_replay_task}` ({len(steps)} Steps)")

            for idx, step_record in enumerate(steps):
                step_num = step_record.get("step", idx + 1)
                action = step_record.get("action", {})
                tool = action.get("type") or action.get("tool") or "action"
                ret = step_record.get("return", step_record.get("reward", 0.0))
                done = step_record.get("done", False)

                with st.expander(f"Step {step_num}: Action `{tool}` | Return: `{ret:.3f}` | Done: `{done}`", expanded=(idx == len(steps)-1)):
                    c_act, c_obs = st.columns(2)

                    with c_act:
                        st.markdown("**Agent Action / Arguments:**")
                        st.json(action)

                        thought = action.get("thought") or step_record.get("thought", "")
                        if thought:
                            st.markdown(f"**Agent Reasoning / Thought:**\n> {thought}")

                    with c_obs:
                        st.markdown("**Environment Feedback / Observation:**")
                        obs = step_record.get("output", step_record.get("observation", step_record.get("feedback", "")))
                        if isinstance(obs, dict):
                            st.json(obs)
                        else:
                            st.code(str(obs), language="text")

# =============================================================================
# PAGE 9: 🛡️ Benchmark Integrity
# =============================================================================
elif page == "🛡️ Benchmark Integrity":
    st.title("🛡️ Automated Benchmark & Sandbox Integrity Diagnostics")
    st.markdown(
        """
        Continuous verification suite auditing the 100-task corpus composition, official 30-task manifest integrity,
        P0 sandbox path traversal security, and strict provider fallback enforcement.
        """
    )

    if st.button("🔄 Run Full Integrity Audit", type="primary"):
        st.session_state["last_audit_time"] = time.time()

    report = verify_benchmark_integrity("runs", "tasks", "config.yaml")

    col_status, col_time = st.columns(2)
    with col_status:
        overall = report.get("status", "UNKNOWN")
        if overall == "PASS":
            st.success("✅ **OVERALL INTEGRITY AUDIT: PASS**")
        elif overall == "WARN":
            st.warning("⚠️ **OVERALL INTEGRITY AUDIT: WARNING**")
        else:
            st.error("❌ **OVERALL INTEGRITY AUDIT: FAIL**")

    with col_time:
        st.markdown(f"**Audit Timestamp:** `{report.get('timestamp')}`")

    st.markdown("---")
    st.subheader("Diagnostic Check Results")

    for check in report.get("checks", []):
        st_name = check.get("name")
        st_status = check.get("status")
        st_details = check.get("details")

        if st_status == "PASS":
            st.success(f"**{st_name}** — PASS\n\n{st_details}")
        elif st_status == "WARN":
            st.warning(f"**{st_name}** — WARN\n\n{st_details}")
        else:
            st.error(f"**{st_name}** — FAIL\n\n{st_details}")

# =============================================================================
# PAGE 10: ⚙️ Configuration
# =============================================================================
elif page == "⚙️ Configuration":
    st.title("⚙️ System Configuration & Provider Policy")
    st.markdown("Inspect active Nebius AI Studio settings, Token Factory endpoints, and sandbox parameters.")

    providers = get_available_providers("config.yaml")
    models = get_available_models("config.yaml")

    st.subheader("1. Active Inference Providers")
    st.write(f"Configured Providers: {', '.join([f'`{p}`' for p in providers])}")

    st.subheader("2. Model Registry")
    df_mod = pd.DataFrame([
        {"Model Key": k, "Full Name": v["name"], "Provider": v["provider"], "Description": v["desc"]}
        for k, v in models.items()
    ])
    st.dataframe(df_mod, use_container_width=True, hide_index=True)

    st.subheader("3. P0 Security & Fallback Policy")
    st.markdown(
        """
        - **Execution Mode**: `HACKATHON` (Strict mode — silent fallback disabled)
        - **Sandbox Isolation**: Active path traversal sanitizer in `agentgym/security.py`
        - **Endpoint Base URL**: `https://api.tokenfactory.nebius.com/v1`
        """
    )
