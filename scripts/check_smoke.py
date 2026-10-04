"""Inspect smoke test results."""
import json
from pathlib import Path

for r_id in ["smoke_v2_super", "smoke_v2_nano"]:
    p = Path("runs") / r_id / "summary.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        print(f"=== {r_id} ===")
        print(f"Success: {d.get('success_rate')}, Solved: {d.get('solved_tasks')}/{d.get('total_tasks')}")
        print(f"Avg steps: {d.get('avg_steps')}, Avg return: {d.get('avg_return')}")
        print(f"Extraction needed rate: {d.get('extraction_needed_rate')}, Invalid JSON events: {d.get('invalid_json_events')}")
        print(f"Prompt hash: {d.get('prompt_hash')}")
        print()
    else:
        # Check trajectories line count
        tp = Path("runs") / r_id / "trajectories.jsonl"
        if tp.exists():
            with open(tp, "r", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            print(f"=== {r_id} in progress: {len(lines)} steps recorded ===")
