"""Data access and abstraction layer for the DebugArena Dashboard Control Center."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


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
    """Formats raw model identifier or baseline run id into a readable label."""
    r_lower = run_id.lower()
    m_lower = model_id.lower()
    if "noop" in r_lower or "no_op" in r_lower or "no-op" in r_lower or "noop" in m_lower:
        return "No-op submit (lower bound)"
    if "mock" in r_lower or "mock" in m_lower or "reference" in r_lower or "solver" in r_lower:
        return "Reference solver (upper bound)"
    clean = model_id.split("/")[-1]
    return clean


def load_tasks_metadata(tasks_dir: str = "tasks") -> Dict[str, Dict[str, Any]]:
    """Loads metadata for all 100 tasks across Core-20, Hard-10, and V2-70."""
    meta: Dict[str, Dict[str, Any]] = {}
    tp = Path(tasks_dir)
    if not tp.exists():
        return meta

    for p in tp.rglob("task.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                tid = d.get("task_id", p.parent.name)

                # Classify suite accurately
                if tid.startswith("t") or "t0" in tid or "t1" in tid or "t2" in tid:
                    suite = "Core-20"
                elif tid.startswith("h") or "hard" in str(p).lower():
                    suite = "Hard-10"
                elif tid.startswith("v") or "v2" in str(p).lower():
                    suite = "V2-70"
                else:
                    suite = d.get("suite", "Core-20")

                d["suite"] = suite
                d["task_path"] = str(p.parent)
                d["file_count"] = len(d.get("repo_files", {}))
                d["test_count"] = len(d.get("tests", {}))
                meta[tid] = d
        except Exception:
            pass
    return meta


def get_suite_task_ids(tasks_meta: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Returns sorted task IDs grouped by standard benchmark suites."""
    all_tids = sorted(list(tasks_meta.keys()))
    core_tids = sorted([t for t, d in tasks_meta.items() if d.get("suite") == "Core-20" or t.startswith("t")])
    hard_tids = sorted([t for t, d in tasks_meta.items() if d.get("suite") == "Hard-10" or t.startswith("h")])
    v2_tids = sorted([t for t, d in tasks_meta.items() if d.get("suite") == "V2-70" or t.startswith("v")])

    return {
        "All (100 Tasks)": all_tids,
        "Benchmark V2 (70 Tasks)": v2_tids,
        "Core-20 (20 Tasks)": core_tids,
        "Hard-10 (10 Tasks)": hard_tids,
    }


def load_custom_tasks_metadata(custom_tasks_dir: str = "custom_tasks") -> Dict[str, Dict[str, Any]]:
    """Loads metadata for custom user-created tasks."""
    meta: Dict[str, Dict[str, Any]] = {}
    tp = Path(custom_tasks_dir)
    if not tp.exists():
        return meta

    for sub in tp.iterdir():
        if sub.is_dir():
            p = sub / "task.json"
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        tid = d.get("task_id", sub.name)
                        d["suite"] = "Custom"
                        d["task_path"] = str(sub)
                        d["file_count"] = len(d.get("repo_files", {}))
                        d["test_count"] = len(d.get("tests", {}))
                        meta[tid] = d
                except Exception:
                    pass
    return meta


def is_custom_run(run_item: Dict[str, Any]) -> bool:
    """Returns True if the run corresponds to a Custom Task evaluation."""
    run_id = run_item.get("run_id", "")
    if run_id.startswith("custom_"):
        return True

    state = run_item.get("state", {})
    cfg = state.get("config", {})
    if cfg.get("suite") == "custom":
        return True

    task_ids = cfg.get("task_ids", [])
    if any(str(t).startswith("custom_") for t in task_ids):
        return True

    summary = run_item.get("summary", {})
    if summary.get("suite") == "custom":
        return True

    episodes = summary.get("episodes", [])
    if any(str(e.get("task_id", "")).startswith("custom_") for e in episodes):
        return True

    return False


def load_all_runs(runs_dir: str = "runs") -> Dict[str, Dict[str, Any]]:
    """Scans and loads all runs, their summary, run_state, and trajectory count."""
    runs_path = Path(runs_dir)
    runs_data: Dict[str, Dict[str, Any]] = {}
    if not runs_path.exists():
        return runs_data

    for run_folder in runs_path.iterdir():
        if not run_folder.is_dir():
            continue
        run_id = run_folder.name
        summary_file = run_folder / "summary.json"
        state_file = run_folder / "run_state.json"
        traj_file = run_folder / "trajectories.jsonl"

        summary: Dict[str, Any] = {}
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            except Exception:
                pass

        state: Dict[str, Any] = {}
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                pass

        has_traj = traj_file.exists()
        traj_count = 0
        if has_traj:
            try:
                with open(traj_file, "r", encoding="utf-8") as f:
                    traj_count = sum(1 for line in f if line.strip())
            except Exception:
                pass

        if summary or state or has_traj:
            item = {
                "run_id": run_id,
                "summary": summary,
                "state": state,
                "trajectory_count": traj_count,
                "has_trajectories": has_traj,
            }
            item["is_custom"] = is_custom_run(item)
            runs_data[run_id] = item

    return runs_data


def load_single_run_trajectories(run_id: str, runs_dir: str = "runs") -> List[Dict[str, Any]]:
    """Loads all step records from a run's trajectories.jsonl file."""
    traj_path = Path(runs_dir) / run_id / "trajectories.jsonl"
    records: List[Dict[str, Any]] = []
    if not traj_path.exists():
        return records

    try:
        with open(traj_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        records.append(json.loads(line_str))
                    except Exception:
                        pass
    except Exception:
        pass
    return records


def get_available_models(config_path: str = "config.yaml") -> Dict[str, Dict[str, Any]]:
    """Returns available models configured in config.yaml."""
    p = Path(config_path)
    models: Dict[str, Dict[str, Any]] = {
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": {
            "name": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
            "provider": "nebius",
            "alias": "nemotron_nano",
            "desc": "Nemotron 3 Nano (Fast, 30B)",
        },
        "nvidia/nemotron-3-super-120b-a12b": {
            "name": "nvidia/nemotron-3-super-120b-a12b",
            "provider": "nebius",
            "alias": "nemotron_super",
            "desc": "Nemotron 3 Super (Advanced, 120B)",
        },
        "nvidia/Nemotron-3-Ultra-550b-a55b": {
            "name": "nvidia/Nemotron-3-Ultra-550b-a55b",
            "provider": "nebius",
            "alias": "nemotron_judge",
            "desc": "Nemotron 3 Ultra / Judge (550B)",
        },
        "mock_solver": {
            "name": "mock_solver",
            "provider": "mock",
            "alias": "mock_solver",
            "desc": "Reference Solver (Offline Upper Bound)",
        },
        "mock_noop": {
            "name": "mock_noop",
            "provider": "mock",
            "alias": "mock_noop",
            "desc": "No-Op Submit (Offline Lower Bound)",
        },
    }

    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                for k, m_info in cfg.get("models", {}).items():
                    m_name = m_info.get("name", k)
                    models[m_name] = {
                        "name": m_name,
                        "provider": m_info.get("provider", "nebius"),
                        "alias": k,
                        "desc": f"{k} ({m_name})",
                    }
        except Exception:
            pass

    return models


def get_available_providers(config_path: str = "config.yaml") -> List[str]:
    """Returns list of active providers."""
    p = Path(config_path)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                return list(cfg.get("providers", {}).keys())
        except Exception:
            pass
    return ["nebius", "nvidia", "openrouter", "mock"]
