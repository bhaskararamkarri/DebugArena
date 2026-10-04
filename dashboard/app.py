"""Streamlit Interactive Dashboard for DebugArena (formerly AgentGym).

Features:
1. Leaderboard: Model comparison by success rate, steps, returns, and judge quality.
2. Task Breakdown: Pass rates by difficulty and bug type, model x task heatmap.
3. Episode Replay: Step-by-step interactive inspection of agent observations, actions, rewards, and diffs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="DebugArena | Evaluation Leaderboard & Replay",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished UI
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #334155;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.03);
        padding: 12px;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


import math


def compute_wilson_ci(k: int, n: int, confidence: float = 0.95) -> str:
    """Computes 95% Wilson score interval for binomial proportion."""
    if n == 0:
        return "N/A"
    z = 1.959964
    p_hat = k / n
    denom = 1 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1 - p_hat) / n) + (z ** 2) / (4 * (n ** 2)))
    low = max(0.0, center - margin) * 100
    high = min(1.0, center + margin) * 100
    return f"[{low:.1f}%, {high:.1f}%]"


def format_model_label(run_id: str, model_id: str) -> str:
    if "mock" in run_id.lower() or "mock" in model_id.lower():
        return "Reference solver (upper bound)"
    if "noop" in run_id.lower() or "no_op" in run_id.lower():
        return "No-op submit (lower bound)"
    return model_id.split("/")[-1]


def load_all_runs(runs_dir: str = "runs") -> Dict[str, Dict[str, Any]]:
    runs_path = Path(runs_dir)
    runs_data = {}
    if not runs_path.exists():
        return {}

    for run_folder in runs_path.iterdir():
        if not run_folder.is_dir():
            continue
        run_id = run_folder.name
        summary_file = run_folder / "summary.json"
        traj_file = run_folder / "trajectories.jsonl"

        summary = {}
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            except Exception:
                pass

        trajectories = []
        if traj_file.exists():
            try:
                with open(traj_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            trajectories.append(json.loads(line))
            except Exception:
                pass

        if summary or trajectories:
            runs_data[run_id] = {
                "summary": summary,
                "trajectories": trajectories,
            }
    return runs_data


def load_tasks_metadata(tasks_dir: str = "tasks") -> Dict[str, Dict[str, Any]]:
    meta = {}
    tp = Path(tasks_dir)
    if not tp.exists():
        return {}
    for p in tp.rglob("task.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                tid = d.get("task_id", p.parent.name)
                meta[tid] = d
        except Exception:
            pass
    return meta


# Load data
runs_data = load_all_runs()
tasks_meta = load_tasks_metadata()

# Sidebar Navigation & Suite Selector
st.sidebar.title("⚔️ DebugArena")
st.sidebar.caption("Nebius × NVIDIA AI Hackathon · Agent Gym Track")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏆 Leaderboard", "📊 Task Breakdown", "🎬 Episode Replay"],
    index=0,
)

st.sidebar.markdown("---")
suite_filter = st.sidebar.selectbox(
    "Benchmark Suite",
    ["All Suites", "Core-20", "Hard-10"],
    index=0,
)
show_smoke = st.sidebar.checkbox("Include Smoke/Test Runs", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Loaded Runs:** `{len(runs_data)}`")
st.sidebar.markdown(f"**Available Tasks:** `{len(tasks_meta)}`")


# ==============================================================================
# PAGE 1: LEADERBOARD
# ==============================================================================
if page == "🏆 Leaderboard":
    st.title("🏆 Agent Benchmark Leaderboard")
    st.markdown(
        "Compare autonomous coding agent performance across **Core-20** and **Hard-10** benchmarks "
        "evaluating sandbox pass rate, step efficiency, return, and code quality."
    )

    if not runs_data:
        st.warning("No evaluation runs found in `runs/`. Run an evaluation with `python scripts/run_eval.py` to see results.")
    else:
        rows = []
        for run_id, data in runs_data.items():
            if not show_smoke and ("smoke" in run_id.lower() or "test" in run_id.lower()):
                continue

            summary = data.get("summary", {})
            trajs = data.get("trajectories", [])

            raw_model = summary.get("model", "")
            if not raw_model and trajs:
                raw_model = trajs[0].get("model", "unknown")

            display_model = format_model_label(run_id, raw_model)

            total_tasks = summary.get("total_tasks", 0)
            solved_tasks = summary.get("solved_tasks", 0)
            success_rate = summary.get("success_rate", 0.0)
            avg_steps = summary.get("avg_steps", 0.0)
            avg_return = summary.get("avg_return", 0.0)
            avg_judge = summary.get("avg_judge_score", None)

            # If summary wasn't written, compute from trajectories
            if not summary and trajs:
                episodes = {}
                for t in trajs:
                    episodes[t["episode_id"]] = t
                total_tasks = len(episodes)
                solved_tasks = sum(1 for e in episodes.values() if e.get("pass_rate", 0.0) >= 1.0)
                success_rate = round(solved_tasks / max(1, total_tasks), 4)
                avg_steps = round(len(trajs) / max(1, total_tasks), 2)
                avg_return = round(sum(t.get("reward", 0.0) for t in trajs) / max(1, total_tasks), 2)

            # Infer suite from tasks or run_id
            task_ids_in_run = [ep.get("task_id", "") for ep in summary.get("episodes", [])]
            if not task_ids_in_run and trajs:
                task_ids_in_run = list({t.get("task_id", "") for t in trajs})

            if all(t.startswith("h") for t in task_ids_in_run if t):
                run_suite = "Hard-10"
            elif all(t.startswith("t") for t in task_ids_in_run if t):
                run_suite = "Core-20"
            else:
                run_suite = "Combined / Custom"

            if suite_filter != "All Suites" and run_suite != suite_filter:
                continue

            rows.append({
                "Run ID": run_id,
                "Suite": run_suite,
                "Model": display_model,
                "Full Model": raw_model,
                "Tasks": total_tasks,
                "Solved": solved_tasks,
                "Success Rate (%)": round(success_rate * 100, 1),
                "95% Wilson CI": compute_wilson_ci(solved_tasks, total_tasks),
                "Avg Steps": avg_steps,
                "Avg Return": avg_return,
                "Judge Quality (1-5)": f"{avg_judge:.1f}" if avg_judge else "N/A",
            })

        if not rows:
            st.info(f"No runs matching suite filter: **{suite_filter}**.")
        else:
            df = pd.DataFrame(rows).sort_values(by=["Success Rate (%)", "Avg Return"], ascending=False)

            # KPI Metrics
            best_run = df.iloc[0]
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Top Model", best_run["Model"])
            kpi2.metric("Best Pass Rate", f"{best_run['Success Rate (%)']}%")
            kpi3.metric("Top Avg Return", f"{best_run['Avg Return']}")
            kpi4.metric("Avg Quality Score", best_run["Judge Quality (1-5)"])

            st.markdown("### 📋 Evaluation Runs Standings")
            st.caption("ℹ️ *Statistical Rigor:* Success rates reported with 95% Wilson Score confidence intervals to account for benchmark sample size.")
            st.dataframe(
                df[["Model", "Suite", "Run ID", "Tasks", "Solved", "Success Rate (%)", "95% Wilson CI", "Avg Steps", "Avg Return", "Judge Quality (1-5)"]],
                use_container_width=True,
                hide_index=True,
            )

        # Model Aggregates (Mean and Spread across runs)
        st.markdown("### 📊 Model Aggregate Performance (Mean ± Spread)")
        grouped_records = []
        for model_name, grp in df.groupby("Model"):
            runs_count = len(grp)
            mean_succ = grp["Success Rate (%)"].mean()
            min_succ = grp["Success Rate (%)"].min()
            max_succ = grp["Success Rate (%)"].max()
            spread_succ = (max_succ - min_succ) / 2.0
            mean_ret = grp["Avg Return"].mean()
            mean_steps = grp["Avg Steps"].mean()

            succ_str = f"{mean_succ:.1f}% (±{spread_succ:.1f}%)" if runs_count > 1 else f"{mean_succ:.1f}%"
            grouped_records.append({
                "Model": model_name,
                "Runs": runs_count,
                "Success Rate": succ_str,
                "Avg Return": round(mean_ret, 2),
                "Avg Steps": round(mean_steps, 2),
            })
        agg_df = pd.DataFrame(grouped_records).sort_values(by="Avg Return", ascending=False)
        st.dataframe(agg_df, use_container_width=True, hide_index=True)

        st.markdown("### 📈 Visual Comparison")
        col_c1, col_c2 = st.columns(2)

        with col_c1:
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

        with col_c2:
            chart2 = (
                alt.Chart(df)
                .mark_circle(size=120)
                .encode(
                    x=alt.X("Avg Steps:Q", title="Avg Steps to Complete"),
                    y=alt.Y("Avg Return:Q", title="Avg Return"),
                    color="Model:N",
                    tooltip=["Model", "Success Rate (%)", "Avg Steps", "Avg Return"],
                )
                .properties(height=320, title="Efficiency: Steps vs. Return")
            )
            st.altair_chart(chart2, use_container_width=True)


# ==============================================================================
# PAGE 2: TASK BREAKDOWN
# ==============================================================================
elif page == "📊 Task Breakdown":
    st.title("📊 Task Breakdown & Error Analysis")
    st.markdown("Deep dive into performance across task difficulties, bug categories, and model matrix.")

    if not runs_data:
        st.warning("No runs available to analyze.")
    else:
        # Build task-level dataframe
        task_rows = []
        for run_id, data in runs_data.items():
            summary = data.get("summary", {})
            model = format_model_label(run_id, summary.get("model", run_id))
            episodes = summary.get("episodes", [])

            if not episodes and data.get("trajectories"):
                # derive from trajs
                by_task = {}
                for t in data["trajectories"]:
                    by_task[t["task_id"]] = t
                for tid, last_t in by_task.items():
                    episodes.append({
                        "task_id": tid,
                        "success": last_t.get("pass_rate", 0.0) >= 1.0,
                        "final_pass_rate": last_t.get("pass_rate", 0.0),
                        "steps": last_t.get("step", 1),
                        "return": last_t.get("reward", 0.0),
                        "judge_score": last_t.get("judge_score"),
                    })

            for ep in episodes:
                tid = ep.get("task_id", "")
                t_meta = tasks_meta.get(tid, {})
                task_suite = "Hard-10" if tid.startswith("h") else "Core-20"
                if suite_filter != "All Suites" and task_suite != suite_filter:
                    continue

                task_rows.append({
                    "Run": run_id,
                    "Suite": task_suite,
                    "Model": model,
                    "Task ID": tid,
                    "Difficulty": t_meta.get("difficulty", "unknown"),
                    "Bug Type": t_meta.get("bug_type", "unknown"),
                    "Success": 1 if ep.get("success") else 0,
                    "Final Pass Rate": ep.get("final_pass_rate", 0.0),
                    "Steps": ep.get("steps", 0),
                    "Return": ep.get("return", 0.0),
                })

        tdf = pd.DataFrame(task_rows)

        if not tdf.empty:
            # Heatmap Model x Task
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

            # Failure Category Breakdown
            st.markdown("---")
            st.markdown("### ⚠️ Failure Mode & Error Category Breakdown")
            failed_episodes = []
            for run_id, data in runs_data.items():
                if "baseline" in run_id:
                    continue  # focus error analysis on real evaluated models
                summary = data.get("summary", {})
                disp_model = format_model_label(run_id, summary.get("model", run_id))
                trajs = data.get("trajectories", [])
                trajs_by_ep = {}
                for t in trajs:
                    eid = t.get("episode_id")
                    if eid not in trajs_by_ep:
                        trajs_by_ep[eid] = []
                    trajs_by_ep[eid].append(t)

                for ep in summary.get("episodes", []):
                    if not ep.get("success"):
                        tid = ep.get("task_id", "")
                        task_suite = "Hard-10" if tid.startswith("h") else "Core-20"
                        if suite_filter != "All Suites" and task_suite != suite_filter:
                            continue

                        ep_trajs = trajs_by_ep.get(ep.get("episode_id"), [])
                        category = "Wrong fix"
                        if any("error" in t.get("action", {}) or t.get("action", {}).get("type") not in ("edit", "run", "submit") for t in ep_trajs):
                            category = "Invalid JSON"
                        elif ep.get("regression_occurred") or any(t.get("reward", 0.0) <= -0.20 for t in ep_trajs):
                            category = "Regression"
                        elif ep.get("steps", 0) >= 10:
                            category = "Ran out of steps"

                        failed_episodes.append({
                            "Model": disp_model,
                            "Suite": task_suite,
                            "Run ID": run_id,
                            "Task ID": tid,
                            "Failure Category": category,
                            "Final Pass Rate": f"{ep.get('final_pass_rate', 0.0):.1%}",
                            "Steps": ep.get("steps", 0),
                        })

            if failed_episodes:
                fdf = pd.DataFrame(failed_episodes)
                fc1, fc2 = st.columns([1, 1])
                with fc1:
                    fc_chart = (
                        alt.Chart(fdf)
                        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                        .encode(
                            x=alt.X("Failure Category:N", sort="-y", title="Failure Mode"),
                            y=alt.Y("count():Q", title="Number of Failures"),
                            color=alt.Color("Failure Category:N", legend=None),
                            tooltip=["Failure Category", "count()"],
                        )
                        .properties(height=280, title="Benchmark Failure Categories")
                    )
                    st.altair_chart(fc_chart, use_container_width=True)
                with fc2:
                    st.markdown("#### Failed Episode Details")
                    st.dataframe(fdf[["Model", "Suite", "Task ID", "Failure Category", "Final Pass Rate", "Steps"]], use_container_width=True, hide_index=True)
            else:
                st.success("No failed episodes found in active model runs!")


# ==============================================================================
# PAGE 3: EPISODE REPLAY
# ==============================================================================
elif page == "🎬 Episode Replay":
    st.title("🎬 Episode Step-by-Step Replayer")
    st.markdown("Inspect every interaction: prompt, LLM action, sandbox output, test pass rate, and reward.")

    if not runs_data:
        st.warning("No trajectories available to replay.")
    else:
        # Selectors
        run_ids = list(runs_data.keys())
        sel_run = st.selectbox("Select Evaluation Run", run_ids)

        trajs = runs_data[sel_run].get("trajectories", [])
        if not trajs:
            st.info(f"No trajectory steps recorded for run `{sel_run}`.")
        else:
            # Group by task_id and episode_id
            episodes_dict = {}
            for t in trajs:
                key = f"{t.get('task_id')} ({t.get('episode_id')})"
                if key not in episodes_dict:
                    episodes_dict[key] = []
                episodes_dict[key].append(t)

            sel_ep_key = st.selectbox("Select Task / Episode", list(episodes_dict.keys()))
            ep_steps = sorted(episodes_dict[sel_ep_key], key=lambda x: x["step"])

            # Episode Banner KPIs
            final_step = ep_steps[-1]
            total_return = round(sum(s.get("reward", 0.0) for s in ep_steps), 4)
            is_success = final_step.get("pass_rate", 0.0) >= 1.0

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Task", final_step.get("task_id", ""))
            k2.metric("Outcome", "SOLVED ✅" if is_success else "FAILED ❌")
            k3.metric("Final Pass Rate", f"{final_step.get('pass_rate', 0.0):.1%}")
            k4.metric("Total Return", f"{total_return}")
            k5.metric("Judge Score", f"{final_step.get('judge_score')}/5" if final_step.get("judge_score") else "N/A")

            st.markdown("---")

            # Step Slider
            total_steps = len(ep_steps)
            step_num = st.slider("Step Slider", min_value=1, max_value=total_steps, value=1)
            cur = ep_steps[step_num - 1]

            st.markdown(f"### 📍 Step {cur['step']} of {total_steps}")

            c_info1, c_info2, c_info3, c_info4 = st.columns(4)
            c_info1.metric("Action Type", cur.get("action", {}).get("type", "unknown"))
            c_info2.metric("Step Reward", f"{cur.get('reward', 0.0):+.4f}")
            c_info3.metric("Pass Rate", f"{cur.get('pass_rate', 0.0):.1%}")
            c_info4.metric("LLM Latency", f"{cur.get('latency_ms', 0)} ms")

            # Action inspection
            st.markdown("#### 🤖 Agent Action (JSON)")
            st.json(cur.get("action", {}))

            if cur.get("action", {}).get("type") == "edit":
                st.markdown(f"**Updated File Content (`{cur['action'].get('path')}`):**")
                st.code(cur["action"].get("content", ""), language="python")

            # Execution output
            st.markdown("#### 🖥️ Sandbox Execution Output")
            st.code(cur.get("output", "(no output)"), language="bash")

            # Expandable Full Prompt
            with st.expander("🔍 View Full Conversation History at this Step"):
                st.json(cur.get("prompt", []))
