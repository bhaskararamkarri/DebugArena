"""Analyze v1 trajectory logs for invalid JSON events, failure diagnosis, and token statistics."""
import json
from pathlib import Path

runs = [
    ("Core-20 Nano", "runs/run1_nemotron_nano"),
    ("Core-20 Super", "runs/run1_nemotron_super"),
    ("Hard-10 Nano", "runs/hard_nano_v1"),
    ("Hard-10 Super", "runs/hard_super_v1"),
]

for name, run_dir in runs:
    traj_p = Path(run_dir) / "trajectories.jsonl"
    sum_p = Path(run_dir) / "summary.json"
    if not traj_p.exists():
        continue

    with open(sum_p, "r", encoding="utf-8") as f:
        summary = json.load(f)

    total_steps = 0
    invalid_json_events = 0
    episodes_invalid = set()
    failed_raw_replies = []
    task_steps = {}

    with open(traj_p, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            total_steps += 1
            tid = rec.get("task_id")
            action = rec.get("action", {})
            prompt_msgs = rec.get("prompt", [])

            task_steps[tid] = task_steps.get(tid, 0) + 1

            # Check if action was a fallback or invalid action
            is_fallback = False
            if action.get("type") == "run" and "echo 'Invalid JSON action'" in action.get("cmd", ""):
                is_fallback = True
            elif not action.get("type") or action.get("type") not in ["edit", "run", "submit"]:
                is_fallback = True

            if is_fallback:
                invalid_json_events += 1
                episodes_invalid.add(tid)
                if prompt_msgs and len(prompt_msgs) > 1:
                    last_asst = [m["content"] for m in prompt_msgs if m.get("role") == "assistant"]
                    if last_asst:
                        failed_raw_replies.append((tid, last_asst[-1]))

    print(f"=== {name} ({run_dir}) ===")
    print(f"Total tasks: {summary.get('total_tasks')}, Solved: {summary.get('solved_tasks')}")
    print(f"Total steps: {total_steps}, Invalid JSON events: {invalid_json_events} across {len(episodes_invalid)} tasks")
    if episodes_invalid:
        print(f"Tasks with invalid JSON: {sorted(list(episodes_invalid))}")
    print()
