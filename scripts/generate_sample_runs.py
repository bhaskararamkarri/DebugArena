"""Generates realistic sample evaluation runs for Nemotron Nano and Nemotron Super."""

import datetime
import json
from pathlib import Path

TASKS_ORDER = [
    # Easy
    ("t01_off_by_one", "easy"),
    ("t02_wrong_operator", "easy"),
    ("t03_wrong_return", "easy"),
    ("t04_variable_typo", "easy"),
    ("t05_string_reverse_words", "easy"),
    ("t06_clamp_boundary", "easy"),
    ("t07_discount_calc", "easy"),
    # Medium
    ("t08_empty_list_edge_case", "medium"),
    ("t09_mutable_default_arg", "medium"),
    ("t10_wrong_slicing", "medium"),
    ("t11_int_vs_float_div", "medium"),
    ("t12_dict_key_handling", "medium"),
    ("t13_flatten_nested", "medium"),
    ("t14_moving_average", "medium"),
    ("t15_matrix_transpose", "medium"),
    ("t16_lru_cache_eviction", "medium"),
    # Hard
    ("t17_two_file_import_bug", "hard"),
    ("t18_stateful_quote_lexer", "hard"),
    ("t19_custom_sort_priority", "hard"),
    ("t20_retry_decorator", "hard"),
]


def load_task_meta():
    tasks = {}
    for tid, _ in TASKS_ORDER:
        p = Path(f"tasks/{tid}/task.json")
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                tasks[tid] = json.load(f)
    return tasks


def generate_run(run_id: str, model_name: str, solved_task_ids: set, base_latency: int):
    tasks_meta = load_task_meta()
    out_dir = Path("runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    traj_path = out_dir / "trajectories.jsonl"
    summary_path = out_dir / "summary.json"

    episodes = []
    traj_records = []

    now_base = datetime.datetime.now(datetime.timezone.utc)

    for i, (tid, diff) in enumerate(TASKS_ORDER):
        ep_id = f"ep_{i+1:04d}"
        tdata = tasks_meta.get(tid, {})
        is_solved = tid in solved_task_ids
        ref_fix = tdata.get("reference_fix", {})
        repo_files = tdata.get("repo_files", {})
        fix_path, fix_content = next(iter(ref_fix.items())) if ref_fix else ("solution.py", "")

        t_stamp1 = (now_base + datetime.timedelta(seconds=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t_stamp2 = (now_base + datetime.timedelta(seconds=i * 10 + 2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t_stamp3 = (now_base + datetime.timedelta(seconds=i * 10 + 4)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Step 1: Run inspection
        step1 = {
            "run_id": run_id,
            "model": model_name,
            "episode_id": ep_id,
            "task_id": tid,
            "step": 1,
            "prompt": [
                {"role": "system", "content": "You are an autonomous AI coding agent fixing bugs in a Python repo."},
                {"role": "user", "content": f"OBSERVATION:\nDescription: {tdata.get('description')}\nFiles: {list(repo_files.keys())}"},
            ],
            "action": {"type": "run", "cmd": f"python -c 'print(\"Inspecting {fix_path}...\")'"},
            "output": f"Inspecting {fix_path}...",
            "pass_rate": 0.25,
            "reward": -0.01,
            "done": False,
            "judge_score": None,
            "latency_ms": base_latency + 150,
            "timestamp": t_stamp1,
        }
        traj_records.append(step1)

        if is_solved:
            # Step 2: Edit with valid fix
            step2 = {
                "run_id": run_id,
                "model": model_name,
                "episode_id": ep_id,
                "task_id": tid,
                "step": 2,
                "prompt": [
                    {"role": "user", "content": f"OBSERVATION:\nLast output: Inspecting {fix_path}...\nSteps left: 9"}
                ],
                "action": {"type": "edit", "path": fix_path, "content": fix_content},
                "output": f"File updated: {fix_path}",
                "pass_rate": 1.0,
                "reward": 0.74,
                "done": False,
                "judge_score": None,
                "latency_ms": base_latency + 300,
                "timestamp": t_stamp2,
            }
            traj_records.append(step2)

            # Step 3: Submit
            judge_val = 5 if diff == "hard" or "70b" in model_name else 4
            step3 = {
                "run_id": run_id,
                "model": model_name,
                "episode_id": ep_id,
                "task_id": tid,
                "step": 3,
                "prompt": [
                    {"role": "user", "content": f"OBSERVATION:\nLast output: File updated: {fix_path}\nPass rate: 1.0\nSteps left: 8"}
                ],
                "action": {"type": "submit"},
                "output": "Solution submitted.",
                "pass_rate": 1.0,
                "reward": -0.01,
                "done": True,
                "judge_score": judge_val,
                "latency_ms": base_latency + 50,
                "timestamp": t_stamp3,
            }
            traj_records.append(step3)

            episodes.append({
                "episode_id": ep_id,
                "task_id": tid,
                "model": model_name,
                "success": True,
                "final_pass_rate": 1.0,
                "steps": 3,
                "return": round(-0.01 + 0.74 - 0.01, 2),
                "judge_score": judge_val,
                "regression_occurred": False,
            })
        else:
            # Step 2: Incomplete or broken fix
            step2 = {
                "run_id": run_id,
                "model": model_name,
                "episode_id": ep_id,
                "task_id": tid,
                "step": 2,
                "prompt": [
                    {"role": "user", "content": f"OBSERVATION:\nLast output: Inspecting {fix_path}...\nSteps left: 9"}
                ],
                "action": {"type": "edit", "path": fix_path, "content": "# Partial attempt\n" + next(iter(repo_files.values()))},
                "output": f"File updated: {fix_path}",
                "pass_rate": 0.25,
                "reward": -0.21,
                "done": True,
                "judge_score": 2,
                "latency_ms": base_latency + 280,
                "timestamp": t_stamp2,
            }
            traj_records.append(step2)

            episodes.append({
                "episode_id": ep_id,
                "task_id": tid,
                "model": model_name,
                "success": False,
                "final_pass_rate": 0.25,
                "steps": 2,
                "return": -0.22,
                "judge_score": 2,
                "regression_occurred": True,
            })

    # Write trajectories
    with open(traj_path, "w", encoding="utf-8") as f:
        for r in traj_records:
            f.write(json.dumps(r) + "\n")

    # Write summary
    total = len(episodes)
    solved = sum(1 for e in episodes if e["success"])
    avg_steps = round(sum(e["steps"] for e in episodes) / total, 2)
    avg_return = round(sum(e["return"] for e in episodes) / total, 2)
    scores = [e["judge_score"] for e in episodes if e["judge_score"] is not None]
    avg_judge = round(sum(scores) / len(scores), 2)

    summary_data = {
        "run_id": run_id,
        "model": model_name,
        "total_tasks": total,
        "solved_tasks": solved,
        "success_rate": round(solved / total, 4),
        "avg_steps": avg_steps,
        "avg_return": avg_return,
        "avg_judge_score": avg_judge,
        "episodes": episodes,
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Generated {run_id}: {solved}/{total} solved ({summary_data['success_rate']:.1%}), Avg Return: {avg_return}")


def main():
    # Nemotron Nano: Solves 15 / 20 (75%)
    # Solves all 7 easy, 6 medium, 2 hard
    nano_solved = {
        "t01_off_by_one", "t02_wrong_operator", "t03_wrong_return", "t04_variable_typo",
        "t05_string_reverse_words", "t06_clamp_boundary", "t07_discount_calc",
        "t08_empty_list_edge_case", "t09_mutable_default_arg", "t10_wrong_slicing",
        "t11_int_vs_float_div", "t12_dict_key_handling", "t13_flatten_nested",
        "t17_two_file_import_bug", "t19_custom_sort_priority"
    }
    generate_run(
        run_id="2026-10-02_nemotron_nano",
        model_name="nvidia/llama-3.1-nemotron-nano-4b-instruct",
        solved_task_ids=nano_solved,
        base_latency=420,
    )

    # Nemotron Super: Solves 18 / 20 (90%)
    # Solves all 7 easy, 8 medium, 3 hard
    super_solved = {
        "t01_off_by_one", "t02_wrong_operator", "t03_wrong_return", "t04_variable_typo",
        "t05_string_reverse_words", "t06_clamp_boundary", "t07_discount_calc",
        "t08_empty_list_edge_case", "t09_mutable_default_arg", "t10_wrong_slicing",
        "t11_int_vs_float_div", "t12_dict_key_handling", "t13_flatten_nested",
        "t14_moving_average", "t15_matrix_transpose",
        "t17_two_file_import_bug", "t18_stateful_quote_lexer", "t19_custom_sort_priority"
    }
    generate_run(
        run_id="2026-10-02_nemotron_super",
        model_name="nvidia/llama-3.1-nemotron-70b-instruct",
        solved_task_ids=super_solved,
        base_latency=1250,
    )


if __name__ == "__main__":
    main()
