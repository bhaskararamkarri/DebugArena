"""Generates a structured human review package for Tendem / Toloka expert annotators."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List


def load_task(task_id: str) -> Dict[str, Any]:
    task_file = Path(f"tasks/{task_id}/task.json")
    if task_file.exists():
        with open(task_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_diff(original: str, modified: str, filename: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename} (buggy)",
        tofile=f"b/{filename} (agent fix)",
        n=3,
    )
    return "".join(diff)


def make_review_pack(output_dir: str = "review_pack", max_episodes: int = 10):
    runs_dir = Path("runs")
    episodes_by_task = {}

    # Gather successful episodes from real runs
    for run_folder in runs_dir.iterdir():
        if not run_folder.is_dir():
            continue
        traj_file = run_folder / "trajectories.jsonl"
        if not traj_file.exists():
            continue

        with open(traj_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("done") and rec.get("pass_rate", 0.0) >= 1.0:
                    tid = rec.get("task_id")
                    if tid not in episodes_by_task:
                        episodes_by_task[tid] = rec

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Sort and pick up to max_episodes spanning easy, medium, hard
    selected_tids = sorted(episodes_by_task.keys())[:max_episodes]

    md_lines = [
        "# AgentGym Expert Review Pack (Tendem / Toloka)",
        "",
        "This review package contains AI-generated coding agent bug fixes for human expert quality assessment.",
        "Please review each episode and score it based on correctness, idiomacy, and side effects.",
        "",
        "---",
        "",
    ]

    example_reviews = []

    for i, tid in enumerate(selected_tids, 1):
        task_data = load_task(tid)
        rec = episodes_by_task[tid]
        diff_tier = task_data.get("difficulty", "medium").upper()
        description = task_data.get("description", "(no description)")
        repo_files = task_data.get("repo_files", {})

        action = rec.get("action", {})
        fix_path = action.get("path") or action.get("file") or next(iter(repo_files.keys()))
        original_code = repo_files.get(fix_path, "")
        agent_code = action.get("content") or action.get("code") or ""

        diff_str = generate_diff(original_code, agent_code, fix_path)

        md_lines.extend([
            f"## Episode {i}: `{tid}` [{diff_tier}]",
            f"**Task ID:** `{tid}`  ",
            f"**Model:** `{rec.get('model')}`  ",
            f"**Episode ID:** `{rec.get('episode_id')}`  ",
            f"**Pass Rate:** `100%` (automated tests passed)  ",
            "",
            "### 1. Problem Description",
            f"> {description}",
            "",
            "### 2. Original Buggy File",
            f"```{Path(fix_path).suffix[1:] or 'python'}",
            original_code.strip(),
            "```",
            "",
            "### 3. Agent Fix Diff",
            "```diff",
            diff_str.strip() or "(no textual diff detected)",
            "```",
            "",
            "### 4. Expert Review Questions",
            "- **Q1 - Correctness:** Does this fix address the root cause correctly? `[ ] Yes  [ ] No`",
            "- **Q2 - Idiomatic Style:** Is the fix clean, pythonic, and readable? `[ ] Yes  [ ] No`",
            "- **Q3 - Side Effects:** Does this introduce performance or safety regressions? `[ ] Yes  [ ] No`",
            "- **Q4 - Score (1 to 5):** `[ ]` (1=Broken, 2=Hacky, 3=Suboptimal, 4=Clean, 5=Exemplary)",
            "- **Q5 - Comments / Rationale:** `[                                                ]`",
            "",
            "---",
            "",
        ])

        example_reviews.append({
            "task_id": tid,
            "episode_id": rec.get("episode_id"),
            "human_score": 5,
            "human_comment": "Clean root-cause fix with no regressions.",
        })

    review_md_file = out_path / "review_pack.md"
    with open(review_md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Also emit template reviews.json.example
    example_json_file = out_path / "reviews.json.example"
    with open(example_json_file, "w", encoding="utf-8") as f:
        json.dump(example_reviews, f, indent=2)

    print(f"Generated review pack with {len(selected_tids)} episodes at: {review_md_file}")
    print(f"Template review format saved to: {example_json_file}")


if __name__ == "__main__":
    make_review_pack()
