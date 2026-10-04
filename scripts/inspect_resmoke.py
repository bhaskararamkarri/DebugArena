"""Inspect re-smoke run results."""
import json
from pathlib import Path

for rid in ["smoke_v2_super_resmoke", "smoke_v2_nano_resmoke"]:
    p = Path("runs") / rid / "summary.json"
    tp = Path("runs") / rid / "trajectories.jsonl"
    with open(p, "r", encoding="utf-8") as f:
        sum_data = json.load(f)
    print(f"=== {rid} ===")
    print(f"Total tasks: {sum_data.get('total_tasks')}, Solved: {sum_data.get('solved_tasks')}")
    print(f"Invalid JSON events: {sum_data.get('invalid_json_events')}, Extraction needed rate: {sum_data.get('extraction_needed_rate')}")
    for ep in sum_data.get("episodes", []):
        print(f"  Task {ep.get('task_id')}: Success={ep.get('success')}, Steps={ep.get('steps')}, PassRate={ep.get('final_pass_rate')}, Return={ep.get('return')}, Extracted={ep.get('extraction_needed')}, InvalidCount={ep.get('invalid_json_count')}")
    print()
