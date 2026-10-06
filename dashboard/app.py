"""Streamlit Real-Time Benchmark Control Center for DebugArena.

Features:
1. 🚀 New Evaluation: Configure and launch official benchmark runs or Custom Coding Tasks.
2. 🔴 Live Monitor: Real-time telemetry, auto-refresh streaming, and cooperative cancellation.
3. 🏆 Leaderboard: Model rankings with 95% Wilson Score confidence intervals & Altair visual analytics.
4. 📊 Task Breakdown: 100-task taxonomy explorer, Model × Task matrix, and error mode analytics.
5. 🎬 Episode Replay: Interactive step-by-step inspector with prompts, actions, outputs, and diffs.
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

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
    compute_wilson_ci,
    format_model_label,
    get_available_models,
    get_available_providers,
    get_suite_task_ids,
    is_custom_run,
    load_all_runs,
    load_custom_tasks_metadata,
    load_single_run_trajectories,
    load_tasks_metadata,
)

st.set_page_config(
    page_title="DebugArena | Real-Time Benchmark Control Center",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for production feel
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
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Initialize BenchmarkManager singleton
@st.cache_resource
def get_manager() -> BenchmarkManager:
    return get_benchmark_manager(runs_dir="runs", tasks_dir="tasks")


manager = get_manager()

# Load tasks and runs metadata
tasks_meta = load_tasks_metadata("tasks")
suite_task_map = get_suite_task_ids(tasks_meta)
runs_data = load_all_runs("runs")

# Session state initialization for Custom Task builder
if "custom_repo_files" not in st.session_state:
    st.session_state.custom_repo_files = {}
if "custom_test_files" not in st.session_state:
    st.session_state.custom_test_files = {}
if "custom_ref_files" not in st.session_state:
    st.session_state.custom_ref_files = {}

# Sidebar Navigation
st.sidebar.title("⚔️ DebugArena")
st.sidebar.caption("Real-Time Benchmark Control Center · 100 Verified Tasks + Custom Eval")
st.sidebar.markdown("---")

active_run_id = manager.get_active_run_id()
if active_run_id:
    st.sidebar.markdown(f'<span class="live-badge-running">🔴 LIVE RUN ACTIVE: {active_run_id}</span>', unsafe_allow_html=True)
    st.sidebar.markdown("")

page = st.sidebar.radio(
    "Control Center Navigation",
    [
        "🚀 New Evaluation",
        "🔴 Live Monitor",
        "🏆 Leaderboard",
        "📊 Task Breakdown",
        "🎬 Episode Replay",
    ],
    index=1 if active_run_id else 0,
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Official Tasks:** `{len(tasks_meta)}` (Core: 20 | Hard: 10 | V2: 70)")
custom_runs_count = sum(1 for r in runs_data.values() if r.get("is_custom"))
official_runs_count = len(runs_data) - custom_runs_count
st.sidebar.markdown(f"**Recorded Runs:** `{len(runs_data)}` (Official: {official_runs_count} | Custom: {custom_runs_count})")


# ==============================================================================
# PAGE 1: NEW EVALUATION
# ==============================================================================
if page == "🚀 New Evaluation":
    st.title("🚀 Configure & Launch Evaluation")

    eval_mode = st.radio(
        "Evaluation Mode",
        ["● Official Benchmark", "🧪 Custom Task"],
        horizontal=True,
        help="Select whether to evaluate against the 100 official benchmark tasks or run a custom coding task.",
    )

    available_models = get_available_models("config.yaml")
    available_providers = get_available_providers("config.yaml")

    if eval_mode == "● Official Benchmark":
        st.markdown(
            "Launch an evaluation of autonomous coding agents against the authoritative 100-task DebugArena benchmark suite. "
            "Execution runs asynchronously in the background."
        )

        with st.form("new_eval_form"):
            st.subheader("1. Run & Model Configuration")
            c1, c2 = st.columns(2)
            with c1:
                default_run_id = f"eval_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                run_id_input = st.text_input("Run Identifier", value=default_run_id, help="Unique directory name under runs/")
                model_keys = list(available_models.keys())
                sel_model_key = st.selectbox("Select Model", model_keys, index=0, format_func=lambda k: available_models[k].get("desc", k))
                selected_model_name = available_models[sel_model_key]["name"]

            with c2:
                default_prov = available_models[sel_model_key].get("provider", "nebius")
                prov_index = available_providers.index(default_prov) if default_prov in available_providers else 0
                provider_input = st.selectbox("API Provider", available_providers, index=prov_index)
                feedback_mode = st.selectbox("Feedback Mode", ["diagnostic", "realistic", "blind"], index=0, help="Diagnostic (transparent), Realistic (hidden tests masked), Blind (zero-shot, reward masked)")

            st.subheader("2. Benchmark Suite & Task Selection")
            s1, s2 = st.columns([1, 2])
            with s1:
                suite_choice = st.selectbox("Suite Preset", ["All (100 Tasks)", "Benchmark V2 (70 Tasks)", "Core-20 (20 Tasks)", "Hard-10 (10 Tasks)", "Custom Selection"], index=0)
            with s2:
                preset_tasks = suite_task_map.get(suite_choice, suite_task_map["All (100 Tasks)"])
                if suite_choice == "Custom Selection":
                    selected_tasks = st.multiselect("Select Task IDs", sorted(list(tasks_meta.keys())), default=preset_tasks[:5])
                else:
                    st.info(f"Preset **{suite_choice}** includes **{len(preset_tasks)}** benchmark tasks.")
                    selected_tasks = preset_tasks

            st.subheader("3. Execution & Environment Parameters")
            e1, e2, e3 = st.columns(3)
            with e1:
                workers_input = st.number_input("Concurrent Workers", min_value=1, max_value=16, value=4, step=1)
                sandbox_mode = st.selectbox("Sandbox Environment", ["docker", "local"], index=0, help="Docker isolation is recommended. Local is for offline baselines.")
            with e2:
                max_steps_input = st.number_input("Max Steps per Episode", min_value=1, max_value=30, value=10, step=1)
                enable_judge = st.checkbox("Enable Nemotron Code Judge", value=True)
            with e3:
                use_mock_solver = st.checkbox("Run Reference Solver (Mock Upper Bound)", value=("mock_solver" in sel_model_key))
                use_noop_solver = st.checkbox("Run No-Op Submit (Mock Lower Bound)", value=("mock_noop" in sel_model_key))
                enable_tracing = st.checkbox("Enable LangSmith Tracing", value=False)

            submit_launch = st.form_submit_button("⚔️ Launch Benchmark Run", type="primary", use_container_width=True)

        if submit_launch:
            if not run_id_input.strip():
                st.error("Run identifier cannot be empty.")
            elif not selected_tasks:
                st.error("Please select at least one task to evaluate.")
            elif manager.is_run_active(run_id_input):
                st.error(f"A run with ID `{run_id_input}` is already executing.")
            else:
                if sandbox_mode == "local" and not (use_mock_solver or use_noop_solver):
                    st.warning("⚠️ Local sandbox selected for live model. If execution fails, switch to Docker sandbox.")

                cfg = RunConfig(
                    run_id=run_id_input.strip(),
                    model_name=selected_model_name,
                    provider=provider_input,
                    suite=suite_choice.lower().split()[0],
                    task_ids=selected_tasks,
                    workers=int(workers_input),
                    max_steps=int(max_steps_input),
                    sandbox_mode=sandbox_mode,
                    feedback_mode=feedback_mode,
                    use_mock_solver=use_mock_solver,
                    use_noop_solver=use_noop_solver,
                    enable_judge=enable_judge,
                    enable_tracing=enable_tracing,
                )

                try:
                    launched_id = manager.start_run(cfg)
                    st.success(f"✅ Benchmark run `{launched_id}` successfully started in background!")
                    st.info("Switching to 🔴 **Live Monitor** to track real-time execution...")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start benchmark run: {e}")

    else:
        # ======================================================================
        # CUSTOM CODING TASK MODE
        # ======================================================================
        st.markdown(
            "Give DebugArena your own coding problem and let an autonomous coding agent inspect, edit, "
            "and run tests inside an isolated sandbox using the authoritative execution engine."
        )

        st.markdown("### 📝 1. Problem Description & Instructions")
        problem_desc = st.text_area(
            "Describe the task/bug for the coding agent",
            value="",
            height=140,
            placeholder="e.g. Fix the off-by-one bug in buggy.py where sum_to_n excludes n. Ensure sum_to_n(5) returns 15.",
            help="This instruction becomes the task description provided to the agent in its observation.",
        )

        st.markdown("### 📦 2. Project Files (Source Workspace)")
        proj_tab1, proj_tab2 = st.tabs(["📦 Upload ZIP Archive", "📝 Add / Edit Files Manually"])

        with proj_tab1:
            uploaded_zip = st.file_uploader(
                "Upload Project ZIP (.zip)",
                type=["zip"],
                key="custom_project_zip_uploader",
                help="Securely extracts code and configuration files. Path traversal and archive bombs are automatically rejected.",
            )
            if uploaded_zip is not None:
                try:
                    extracted = extract_zip_safely(uploaded_zip)
                    st.session_state.custom_repo_files = extracted
                    st.success(f"✅ Extracted {len(extracted)} project file(s) safely into workspace memory.")
                except ZipSecurityError as e:
                    st.error(f"🚨 ZIP Security Error: {e}")
                except Exception as e:
                    st.error(f"Failed to extract ZIP: {e}")

        with proj_tab2:
            st.caption("Add or modify project files individually:")
            new_file_path = st.text_input("Relative File Path", value="app.py", placeholder="e.g. utils/math.py", key="manual_file_path")
            new_file_content = st.text_area(
                "File Content",
                value="def sum_to_n(n):\n    return sum(range(n))\n",
                height=150,
                key="manual_file_content",
            )
            col_add1, col_add2 = st.columns([1, 4])
            with col_add1:
                if st.button("➕ Add / Update File", use_container_width=True):
                    if new_file_path.strip():
                        clean_p = new_file_path.strip().replace("\\", "/")
                        st.session_state.custom_repo_files[clean_p] = new_file_content
                        st.success(f"Saved `{clean_p}`")
                    else:
                        st.error("File path cannot be empty.")
            with col_add2:
                if st.session_state.custom_repo_files and st.button("🗑️ Clear All Project Files"):
                    st.session_state.custom_repo_files = {}
                    st.rerun()

        # Project Preview Card
        if st.session_state.custom_repo_files:
            total_bytes = sum(len(c.encode("utf-8")) for c in st.session_state.custom_repo_files.values())
            st.info(f"📁 **Workspace Preview:** `{len(st.session_state.custom_repo_files)}` files | `{total_bytes}` bytes")
            with st.expander("🔍 View Project Files", expanded=False):
                for fpath, fcont in sorted(st.session_state.custom_repo_files.items()):
                    st.markdown(f"**`{fpath}`** ({len(fcont.splitlines())} lines)")
                    st.code(fcont, language="python" if fpath.endswith(".py") else "text")
        else:
            st.warning("⚠️ No project files loaded yet. Upload a ZIP or add files manually above.")

        st.markdown("### 🧪 3. Evaluation Oracle (Correctness Verification)")
        oracle_choice = st.radio(
            "Evaluation Oracle Type",
            [
                "Hidden Tests (Automated Test Oracle)",
                "Reference Solution / Patch",
                "Solve Only (No Oracle — Exploration Only)",
            ],
            index=0,
            help="An evaluation oracle is required to compute verified pass rates and rewards.",
        )

        if oracle_choice == "Hidden Tests (Automated Test Oracle)":
            st.markdown(
                "🔒 *Evaluator Isolation Guarantee:* Hidden tests are mounted strictly in the evaluator sandbox during "
                "evaluation steps. The agent **NEVER** sees or accesses these tests."
            )
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                test_zip_upload = st.file_uploader("Upload Hidden Tests ZIP", type=["zip"], key="custom_tests_zip_uploader")
                if test_zip_upload is not None:
                    try:
                        extracted_tests = extract_zip_safely(test_zip_upload)
                        st.session_state.custom_test_files = extracted_tests
                        st.success(f"✅ Loaded {len(extracted_tests)} hidden test file(s).")
                    except Exception as e:
                        st.error(f"Failed to extract test ZIP: {e}")
            with t_col2:
                test_manual_path = st.text_input("Test File Name", value="test_solution.py", key="manual_test_path")
                test_manual_code = st.text_area(
                    "Test Code (pytest)",
                    value="from app import sum_to_n\n\ndef test_sum():\n    assert sum_to_n(5) == 15\n",
                    height=120,
                    key="manual_test_content",
                )
                if st.button("➕ Set / Update Single Hidden Test File"):
                    if test_manual_path.strip() and test_manual_code.strip():
                        st.session_state.custom_test_files = {test_manual_path.strip(): test_manual_code}
                        st.success(f"Configured test `{test_manual_path.strip()}`")

            if st.session_state.custom_test_files:
                st.caption(f"Configured Hidden Tests: {list(st.session_state.custom_test_files.keys())}")

        elif oracle_choice == "Reference Solution / Patch":
            st.markdown("Provide reference fixed code for mock validation and upper-bound solvers.")
            ref_path = st.text_input("Reference Fixed File Path", value="app.py", key="ref_fix_path")
            ref_code = st.text_area(
                "Reference Fixed Content",
                value="def sum_to_n(n):\n    return sum(range(n + 1))\n",
                height=120,
                key="ref_fix_content",
            )
            if st.button("➕ Set Reference Fix"):
                st.session_state.custom_ref_files = {ref_path.strip(): ref_code}
                st.success(f"Reference fix set for `{ref_path}`")

        else:
            st.warning(
                "⚠️ **Evaluation Oracle Notice:** Without hidden tests or an automated evaluation oracle, "
                "DebugArena cannot calculate an objective pass rate. The agent will attempt to solve the task, "
                "and results will be recorded with status **SOLVE ONLY** without fabricated scores."
            )
            st.session_state.custom_test_files = {}

        st.markdown("### ⚙️ 4. Model & Execution Parameters")
        with st.form("custom_task_launch_form"):
            cm1, cm2 = st.columns(2)
            with cm1:
                auto_task_id = generate_custom_task_id()
                custom_run_id_input = st.text_input("Custom Run Identifier", value=auto_task_id, help="Unique identifier for this custom evaluation.")
                model_keys = list(available_models.keys())
                sel_m_key = st.selectbox("Select Model", model_keys, index=0, format_func=lambda k: available_models[k].get("desc", k), key="custom_model_select")
                sel_model_name = available_models[sel_m_key]["name"]

            with cm2:
                def_prov = available_models[sel_m_key].get("provider", "nebius")
                p_idx = available_providers.index(def_prov) if def_prov in available_providers else 0
                custom_provider = st.selectbox("API Provider", available_providers, index=p_idx, key="custom_prov_select")
                custom_feedback = st.selectbox("Feedback Mode", ["diagnostic", "realistic", "blind"], index=0, help="Diagnostic (detailed), Realistic (hidden tests masked), Blind (zero-shot)")

            ce1, ce2, ce3 = st.columns(3)
            with ce1:
                custom_sandbox = st.selectbox("Sandbox Environment", ["docker", "local"], index=0, help="Docker sandbox enforces container isolation.")
            with ce2:
                custom_max_steps = st.number_input("Max Steps", min_value=1, max_value=30, value=10, step=1)
            with ce3:
                custom_use_mock = st.checkbox("Run Mock Reference Solver", value=("mock_solver" in sel_m_key))
                custom_use_noop = st.checkbox("Run No-Op Submit", value=("mock_noop" in sel_m_key))

            submit_custom = st.form_submit_button("🚀 RUN CUSTOM TASK", type="primary", use_container_width=True)

        if submit_custom:
            if not problem_desc.strip():
                st.error("Problem description cannot be empty.")
            elif not st.session_state.custom_repo_files:
                st.error("Please provide at least one project file via ZIP upload or manual entry.")
            elif manager.is_run_active(custom_run_id_input):
                st.error(f"A run with ID `{custom_run_id_input}` is already executing.")
            else:
                has_oracle = bool(st.session_state.custom_test_files)
                task_obj = CustomTask(
                    task_id=custom_run_id_input.strip(),
                    description=problem_desc.strip(),
                    repo_files=dict(st.session_state.custom_repo_files),
                    tests=dict(st.session_state.custom_test_files),
                    reference_fix=dict(st.session_state.custom_ref_files),
                    suite="custom",
                    difficulty="custom",
                    has_oracle=has_oracle,
                    created_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                task_obj.save("custom_tasks")

                cfg = RunConfig(
                    run_id=custom_run_id_input.strip(),
                    model_name=sel_model_name,
                    provider=custom_provider,
                    suite="custom",
                    task_ids=[custom_run_id_input.strip()],
                    workers=1,
                    max_steps=int(custom_max_steps),
                    sandbox_mode=custom_sandbox,
                    feedback_mode=custom_feedback,
                    use_mock_solver=custom_use_mock,
                    use_noop_solver=custom_use_noop,
                    enable_judge=False,
                )

                try:
                    launched_id = manager.start_run(cfg)
                    st.success(f"✅ Custom task evaluation `{launched_id}` started successfully!")
                    st.info("Switching to 🔴 **Live Monitor** to observe agent actions in real time...")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start custom evaluation: {e}")


# ==============================================================================
# PAGE 2: LIVE MONITOR
# ==============================================================================
elif page == "🔴 Live Monitor":
    st.title("🔴 Real-Time Benchmark & Custom Control Center")
    st.markdown("Live observability, sub-second telemetry streaming, and active execution control.")

    # Select run to monitor
    active_id = manager.get_active_run_id()
    all_known_runs = list(load_all_runs("runs").keys())
    if active_id and active_id not in all_known_runs:
        all_known_runs.insert(0, active_id)

    if not all_known_runs and not active_id:
        st.info("No evaluation runs currently executing or found in `runs/`. Launch one from **🚀 New Evaluation**!")
    else:
        sel_run_id = st.selectbox("Active / Inspect Run", all_known_runs, index=0 if active_id else 0)

        telemetry = manager.get_live_telemetry(sel_run_id)
        is_active = telemetry["is_active"]
        state_dict = telemetry.get("state") or {}
        latest_step = telemetry.get("latest_step_record") or {}
        events = telemetry.get("recent_events") or []

        # Autorefresh trigger when active
        if is_active:
            time.sleep(1.5)
            st.rerun()

        # Status Header Card
        status_val = state_dict.get("status", "completed" if not is_active else "running")
        status_badge = f'<span class="live-badge-{status_val}">{status_val.upper()}</span>'

        cfg = state_dict.get("config", {})
        is_custom_eval = cfg.get("suite") == "custom" or sel_run_id.startswith("custom_")

        head_c1, head_c2 = st.columns([3, 1])
        with head_c1:
            title_prefix = "🧪 Custom Task Run:" if is_custom_eval else "⚔️ Benchmark Run:"
            st.markdown(f"### {title_prefix} `{sel_run_id}` &nbsp; {status_badge}", unsafe_allow_html=True)
            st.caption(f"**Model:** `{cfg.get('model_name', 'N/A')}` &nbsp;|&nbsp; **Sandbox:** `{cfg.get('sandbox_mode', 'N/A')}` &nbsp;|&nbsp; **Feedback:** `{cfg.get('feedback_mode', 'diagnostic')}` &nbsp;|&nbsp; **Workers:** `{cfg.get('workers', '1')}`")

        with head_c2:
            if is_active:
                if st.button("🛑 STOP / CANCEL RUN", type="primary", use_container_width=True):
                    canceled = manager.cancel_run(sel_run_id)
                    if canceled:
                        st.warning(f"Cancellation signal sent to run `{sel_run_id}`. Awaiting graceful worker shutdown...")
                        time.sleep(1.0)
                        st.rerun()
            else:
                st.markdown(f"**Finished State:** `{status_val}`")

        st.markdown("---")

        # Custom Task Description banner if custom
        if is_custom_eval:
            custom_obj = CustomTask.load(sel_run_id)
            if custom_obj:
                with st.expander("📋 View Problem Instructions & Initial Files", expanded=False):
                    st.markdown(f"**Problem Description:**\n{custom_obj.description}")
                    st.caption(f"Initial files: {list(custom_obj.repo_files.keys())}")

        # Progress Section
        total_tasks = state_dict.get("total_tasks", 1)
        completed_tasks = state_dict.get("completed_tasks", 0)
        solved_tasks = state_dict.get("solved_tasks", 0)
        progress_pct = min(1.0, max(0.0, completed_tasks / max(1, total_tasks)))

        st.progress(progress_pct, text=f"Progress: {completed_tasks}/{total_tasks} Tasks Completed ({progress_pct*100:.1f}%)")

        # Key Metrics Row
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Tasks Completed", f"{completed_tasks} / {total_tasks}")
        m2.metric("Tasks Solved", f"{solved_tasks} ({state_dict.get('success_rate', 0.0)*100:.1f}%)")
        m3.metric("Current Task", state_dict.get("current_task_id", "N/A"))
        m4.metric("Current Step", f"Step {state_dict.get('current_step', 0)}")
        m5.metric("Avg Return", f"{state_dict.get('avg_return', 0.0):.2f}")

        # Active Task Spotlight & Step Telemetry
        st.markdown("### 📍 Active Task Spotlight")
        if latest_step:
            spot1, spot2 = st.columns([1, 1])
            with spot1:
                st.markdown(f"**Current Action (`{latest_step.get('action', {}).get('type', 'N/A')}`):**")
                st.json(latest_step.get("action", {}))
                if latest_step.get("action", {}).get("type") == "edit":
                    st.markdown(f"**Modified Code (`{latest_step['action'].get('path')}`):**")
                    st.code(latest_step["action"].get("content", ""), language="python")

            with spot2:
                st.markdown(f"**Sandbox Execution Output:** (Pass rate: `{latest_step.get('pass_rate', 0.0):.1%}` | Reward: `{latest_step.get('reward', 0.0):+.2f}`)")
                st.code(latest_step.get("output", "(no output recorded)"), language="bash")
        else:
            st.info("Awaiting first step telemetry from environment...")

        # Live Event Feed
        st.markdown("### 📜 Real-Time Event Stream")
        if events:
            event_df = pd.DataFrame(list(reversed(events)))
            st.dataframe(event_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No events in current buffer.")


# ==============================================================================
# PAGE 3: LEADERBOARD (OFFICIAL BENCHMARK ONLY)
# ==============================================================================
elif page == "🏆 Leaderboard":
    st.title("🏆 Benchmark Leaderboard & Comparative Standings")
    st.markdown(
        "Compare autonomous coding agent performance across **Core-20**, **Hard-10**, and **Benchmark V2-70** "
        "evaluating sandbox pass rates with 95% Wilson confidence intervals, step efficiency, return, and code quality. "
        "*(Note: Custom evaluations are kept strictly separate from official benchmark standings.)*"
    )

    protocol_filter = st.selectbox("Protocol Version", ["All Protocols", "Protocol v2 (Docker)", "Protocol v1 (Local)"], index=0)
    suite_filter = st.selectbox("Benchmark Suite", ["All Suites", "All (100 Tasks)", "Benchmark V2 (70 Tasks)", "Core-20 (20 Tasks)", "Hard-10 (10 Tasks)"], index=0)
    show_smoke = st.checkbox("Include Smoke/Test Runs", value=False)

    if not runs_data:
        st.warning("No evaluation runs found in `runs/`. Run a benchmark to view results.")
    else:
        rows = []
        for run_id, data in runs_data.items():
            # Exclude custom runs from official leaderboard
            if data.get("is_custom"):
                continue

            if not show_smoke and ("smoke" in run_id.lower() or "test" in run_id.lower()):
                continue

            summary = data.get("summary", {})
            state = data.get("state", {})
            trajs = load_single_run_trajectories(run_id, "runs") if data.get("has_trajectories") else []

            raw_model = summary.get("model") or state.get("config", {}).get("model_name", "")
            if not raw_model and trajs:
                raw_model = trajs[0].get("model", "unknown")

            display_model = format_model_label(run_id, raw_model)
            run_protocol = summary.get("protocol", "v2")
            run_sandbox = summary.get("sandbox_type") or state.get("config", {}).get("sandbox_mode", "docker")

            if protocol_filter == "Protocol v2 (Docker)" and run_protocol != "v2":
                continue
            if protocol_filter == "Protocol v1 (Local)" and run_protocol != "v1":
                continue

            total_tasks = summary.get("total_tasks", state.get("total_tasks", len(trajs)))
            solved_tasks = summary.get("solved_tasks", state.get("solved_tasks", 0))
            success_rate = summary.get("success_rate", state.get("success_rate", 0.0))
            avg_steps = summary.get("avg_steps", state.get("avg_steps", 0.0))
            avg_return = summary.get("avg_return", state.get("avg_return", 0.0))
            avg_judge = summary.get("avg_judge_score", None)
            ext_rate = summary.get("extraction_needed_rate", 0.0)
            inv_events = summary.get("invalid_json_events", 0)

            # Reconstruct from trajectories if summary is empty
            if not summary and trajs:
                episodes = {}
                for t in trajs:
                    episodes[t["episode_id"]] = t
                total_tasks = len(episodes)
                solved_tasks = sum(1 for e in episodes.values() if e.get("pass_rate", 0.0) >= 1.0)
                success_rate = round(solved_tasks / max(1, total_tasks), 4)
                avg_steps = round(len(trajs) / max(1, total_tasks), 2)
                avg_return = round(sum(t.get("reward", 0.0) for t in trajs) / max(1, total_tasks), 2)

            task_ids_in_run = [ep.get("task_id", "") for ep in summary.get("episodes", [])]
            if not task_ids_in_run and trajs:
                task_ids_in_run = list({t.get("task_id", "") for t in trajs})

            if len(task_ids_in_run) == 100:
                run_suite = "All (100 Tasks)"
            elif all(t.startswith("v") for t in task_ids_in_run if t):
                run_suite = "Benchmark V2 (70 Tasks)"
            elif all(t.startswith("h") for t in task_ids_in_run if t):
                run_suite = "Hard-10 (10 Tasks)"
            elif all(t.startswith("t") for t in task_ids_in_run if t):
                run_suite = "Core-20 (20 Tasks)"
            else:
                run_suite = "Custom / Subset"

            if suite_filter != "All Suites" and run_suite != suite_filter:
                continue

            rows.append({
                "Run ID": run_id,
                "Model": display_model,
                "Suite": run_suite,
                "Protocol": f"v{str(run_protocol).replace('v', '')}",
                "Sandbox": str(run_sandbox).capitalize(),
                "Tasks": total_tasks,
                "Solved": solved_tasks,
                "Success Rate (%)": round(success_rate * 100, 1),
                "95% Wilson CI": compute_wilson_ci(solved_tasks, total_tasks),
                "Avg Steps": avg_steps,
                "Avg Return": avg_return,
                "Extraction Needed (%)": f"{ext_rate * 100:.1f}%",
                "Invalid JSON": inv_events,
                "Judge Quality (1-5)": f"{avg_judge:.1f}" if avg_judge else "N/A",
            })

        if not rows:
            st.info("No official benchmark runs matching current filters.")
        else:
            df = pd.DataFrame(rows).sort_values(by=["Success Rate (%)", "Avg Return"], ascending=False)

            best_run = df.iloc[0]
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Top Model", best_run["Model"])
            kpi2.metric("Best Pass Rate", f"{best_run['Success Rate (%)']}%")
            kpi3.metric("Top Avg Return", f"{best_run['Avg Return']}")
            kpi4.metric("Avg Quality Score", best_run["Judge Quality (1-5)"])

            st.markdown("### 📋 Standings Table")
            st.caption("ℹ️ *Statistical Rigor:* Wilson score intervals compute exact binomial confidence bounds accounting for sample size.")
            st.dataframe(
                df[["Model", "Suite", "Protocol", "Sandbox", "Run ID", "Tasks", "Solved", "Success Rate (%)", "95% Wilson CI", "Avg Steps", "Avg Return", "Extraction Needed (%)", "Invalid JSON", "Judge Quality (1-5)"]],
                use_container_width=True,
                hide_index=True,
            )

            # Visualizations
            st.markdown("### 📈 Visual Comparative Analytics")
            vcol1, vcol2 = st.columns(2)
            with vcol1:
                chart1 = (
                    alt.Chart(df)
                    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                    .encode(
                        x=alt.X("Model:N", sort="-y", title="Model"),
                        y=alt.Y("Success Rate (%):Q", title="Task Success Rate (%)", scale=alt.Scale(domain=[0, 100])),
                        color=alt.Color("Model:N", legend=None),
                        tooltip=["Model", "Run ID", "Success Rate (%)", "Avg Steps", "Avg Return"],
                    )
                    .properties(height=320, title="Task Success Rate by Model")
                )
                st.altair_chart(chart1, use_container_width=True)

            with vcol2:
                chart2 = (
                    alt.Chart(df)
                    .mark_circle(size=120)
                    .encode(
                        x=alt.X("Avg Steps:Q", title="Avg Steps per Task"),
                        y=alt.Y("Avg Return:Q", title="Average Return"),
                        color="Model:N",
                        tooltip=["Model", "Success Rate (%)", "Avg Steps", "Avg Return"],
                    )
                    .properties(height=320, title="Step Efficiency vs. Return")
                )
                st.altair_chart(chart2, use_container_width=True)


# ==============================================================================
# PAGE 4: TASK BREAKDOWN & TAXONOMY EXPLORER
# ==============================================================================
elif page == "📊 Task Breakdown":
    st.title("📊 Task Breakdown & Error Diagnostics")
    st.markdown("Deep dive into performance across task difficulties, bug categories, and the 100-task matrix.")

    tab1, tab2 = st.tabs(["🔥 Model × Task Matrix & Failures", "📚 100-Task Benchmark Taxonomy Explorer"])

    with tab1:
        if not runs_data:
            st.warning("No runs available to analyze.")
        else:
            task_rows = []
            for run_id, data in runs_data.items():
                if data.get("is_custom"):
                    continue
                summary = data.get("summary", {})
                model = format_model_label(run_id, summary.get("model", run_id))
                episodes = summary.get("episodes", [])
                for ep in episodes:
                    tid = ep.get("task_id", "")
                    t_meta = tasks_meta.get(tid, {})
                    task_rows.append({
                        "Run": run_id,
                        "Model": model,
                        "Task ID": tid,
                        "Difficulty": t_meta.get("difficulty", "unknown"),
                        "Bug Type": t_meta.get("bug_type", "unknown"),
                        "Success": 1 if ep.get("success") else 0,
                        "Steps": ep.get("steps", 0),
                        "Return": ep.get("return", 0.0),
                    })

            tdf = pd.DataFrame(task_rows)
            if not tdf.empty:
                st.markdown("### 🔥 Model × Task Matrix (1 = Solved, 0 = Failed)")
                pivot = tdf.pivot_table(index="Task ID", columns="Model", values="Success", aggfunc="max").fillna(0)
                st.dataframe(pivot.style.background_gradient(cmap="Greens", vmin=0, vmax=1), use_container_width=True)

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("### 🎯 Success Rate by Difficulty")
                    diff_df = tdf.groupby(["Difficulty", "Model"])["Success"].mean().reset_index()
                    diff_df["Success Rate (%)"] = (diff_df["Success"] * 100).round(1)
                    diff_chart = (
                        alt.Chart(diff_df)
                        .mark_bar()
                        .encode(
                            x="Difficulty:N",
                            y="Success Rate (%):Q",
                            color="Model:N",
                            xOffset="Model:N",
                            tooltip=["Difficulty", "Model", "Success Rate (%)"],
                        )
                        .properties(height=300)
                    )
                    st.altair_chart(diff_chart, use_container_width=True)

                with col_b2:
                    st.markdown("### 🐞 Success Rate by Bug Category")
                    bug_df = tdf.groupby("Bug Type")["Success"].mean().reset_index()
                    bug_df["Success Rate (%)"] = (bug_df["Success"] * 100).round(1)
                    bug_chart = (
                        alt.Chart(bug_df)
                        .mark_bar(color="#3b82f6")
                        .encode(
                            x=alt.X("Bug Type:N", sort="-y"),
                            y="Success Rate (%):Q",
                            tooltip=["Bug Type", "Success Rate (%)"],
                        )
                        .properties(height=300)
                    )
                    st.altair_chart(bug_chart, use_container_width=True)

    with tab2:
        st.markdown("### 📚 100 Verified Tasks in DebugArena Benchmark")
        taxonomy_records = []
        for tid, d in sorted(tasks_meta.items()):
            taxonomy_records.append({
                "Task ID": tid,
                "Suite": d.get("suite", "N/A"),
                "Category": d.get("category", "N/A"),
                "Difficulty": d.get("difficulty", "N/A"),
                "Bug Type": d.get("bug_type", "N/A"),
                "Files": d.get("file_count", 1),
                "Tests": d.get("test_count", 1),
                "Description": d.get("description", "")[:90] + "...",
            })
        tax_df = pd.DataFrame(taxonomy_records)
        st.dataframe(tax_df, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE 5: EPISODE REPLAY
# ==============================================================================
elif page == "🎬 Episode Replay":
    st.title("🎬 Episode Step-by-Step Replay & Inspection")
    st.markdown("Inspect every interaction: system prompt, agent JSON actions, sandbox execution outputs, rewards, and diffs.")

    if not runs_data:
        st.warning("No trajectories available to replay.")
    else:
        filter_c1, filter_c2 = st.columns([1, 2])
        with filter_c1:
            run_filter_type = st.radio("Filter Run Type", ["All Runs", "Official Benchmark", "Custom Evaluations"], horizontal=True)

        candidate_runs = []
        for rid, d in runs_data.items():
            is_cust = d.get("is_custom", False)
            if run_filter_type == "Official Benchmark" and is_cust:
                continue
            if run_filter_type == "Custom Evaluations" and not is_cust:
                continue
            candidate_runs.append(rid)

        if not candidate_runs:
            st.info(f"No runs matching type '{run_filter_type}'.")
        else:
            sel_run = st.selectbox("Select Evaluation Run", candidate_runs)

            trajs = load_single_run_trajectories(sel_run, "runs")
            if not trajs:
                st.info(f"No trajectory steps recorded for run `{sel_run}`.")
            else:
                episodes_dict: Dict[str, List[Dict[str, Any]]] = {}
                for t in trajs:
                    key = f"{t.get('task_id')} ({t.get('episode_id')})"
                    if key not in episodes_dict:
                        episodes_dict[key] = []
                    episodes_dict[key].append(t)

                sel_ep_key = st.selectbox("Select Task / Episode", list(episodes_dict.keys()))
                ep_steps = sorted(episodes_dict[sel_ep_key], key=lambda x: x.get("step", 0))

                final_step = ep_steps[-1]
                total_return = round(sum(s.get("reward", 0.0) for s in ep_steps), 4)
                has_oracle = final_step.get("has_oracle", True)
                is_success = (final_step.get("pass_rate", 0.0) >= 1.0) if has_oracle else None

                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("Task", final_step.get("task_id", ""))
                if not has_oracle:
                    k2.metric("Outcome", "SOLVE ONLY 🔍")
                else:
                    k2.metric("Outcome", "SOLVED ✅" if is_success else "FAILED ❌")
                k3.metric("Final Pass Rate", f"{final_step.get('pass_rate', 0.0):.1%}" if has_oracle else "N/A (No oracle)")
                k4.metric("Total Return", f"{total_return}")
                k5.metric("Judge Score", f"{final_step.get('judge_score')}/5" if final_step.get("judge_score") else "N/A")

                st.markdown("---")

                # Step navigation slider
                total_steps = len(ep_steps)
                step_num = st.slider("Step Navigation Slider", min_value=1, max_value=total_steps, value=1)
                cur = ep_steps[step_num - 1]

                st.markdown(f"### 📍 Step {cur.get('step', 1)} of {total_steps}")
                c_info1, c_info2, c_info3, c_info4 = st.columns(4)
                c_info1.metric("Action Type", cur.get("action", {}).get("type", "unknown"))
                c_info2.metric("Step Reward", f"{cur.get('reward', 0.0):+.4f}")
                c_info3.metric("Pass Rate", f"{cur.get('pass_rate', 0.0):.1%}" if has_oracle else "N/A")
                c_info4.metric("LLM Latency", f"{cur.get('latency_ms', 0)} ms")

                st.markdown("#### 🤖 Agent Action (JSON)")
                st.json(cur.get("action", {}))

                if cur.get("action", {}).get("type") == "edit":
                    st.markdown(f"**Updated File Content (`{cur['action'].get('path')}`):**")
                    st.code(cur["action"].get("content", ""), language="python")

                st.markdown("#### 🖥️ Sandbox Execution Output")
                st.code(cur.get("output", "(no output)"), language="bash")

                # Final Diff Viewer for Custom Tasks or any task with edits
                edited_files: Dict[str, str] = {}
                for s in ep_steps:
                    act = s.get("action", {})
                    if act.get("type") == "edit" and act.get("path") and act.get("content"):
                        edited_files[act["path"]] = act["content"]

                if edited_files:
                    st.markdown("#### 🔍 Modified Files & Unified Diffs")
                    # Check if custom task object has original files
                    custom_task_meta = CustomTask.load(final_step.get("task_id", ""))
                    orig_files = custom_task_meta.repo_files if custom_task_meta else {}
                    diffs = compute_file_diff(orig_files, edited_files)

                    for fpath, diff_content in diffs.items():
                        with st.expander(f"Diff: `{fpath}`", expanded=True):
                            st.code(diff_content, language="diff")

                with st.expander("🔍 View Full Conversation History at this Step"):
                    st.json(cur.get("prompt", []))
