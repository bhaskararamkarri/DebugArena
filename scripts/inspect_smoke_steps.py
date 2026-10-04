"""Inspect smoke_v2_super step actions and extraction flags."""
import json
from pathlib import Path

tp = Path("runs/smoke_v2_super/trajectories.jsonl")
if tp.exists():
    with open(tp, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            rec = json.loads(line)
            act = rec.get("action", {})
            ext = rec.get("extraction_needed")
            pr = rec.get("pass_rate")
            rew = rec.get("reward")
            print(f"Step {rec.get('step')}: Action={act.get('type')}, Path={act.get('path')}, Cmd={act.get('cmd')}, Extracted={ext}, PassRate={pr}, Reward={rew}")
