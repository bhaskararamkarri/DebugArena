"""Monitor final v2 runs progress."""
import json
from pathlib import Path

runs = ["hard_nano_v2", "hard_super_v2", "core_nano_v2", "core_super_v2"]

for r in runs:
    sp = Path("runs") / r / "summary.json"
    tp = Path("runs") / r / "trajectories.jsonl"
    if sp.exists():
        with open(sp, "r", encoding="utf-8") as f:
            d = json.load(f)
        print(f"[{r}] COMPLETED: Solved {d.get('solved_tasks')}/{d.get('total_tasks')} ({d.get('success_rate'):.1%}), Avg Steps: {d.get('avg_steps')}, Avg Return: {d.get('avg_return')}, Invalid: {d.get('invalid_json_events')}, Extracted: {d.get('extraction_needed_rate'):.1%}")
    elif tp.exists():
        with open(tp, "r", encoding="utf-8") as f:
            steps = len([l for l in f if l.strip()])
        print(f"[{r}] IN PROGRESS: {steps} steps logged")
    else:
        print(f"[{r}] PENDING")
