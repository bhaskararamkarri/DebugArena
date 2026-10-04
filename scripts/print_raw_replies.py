"""Print raw assistant replies from smoke test."""
import json

with open("runs/smoke_v2_super/trajectories.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        rec = json.loads(line)
        prompt = rec.get("prompt", [])
        asst = [m.get("content", "") for m in prompt if m.get("role") == "assistant"]
        print(f"=== Step {rec.get('step')} raw replies (total {len(asst)}) ===")
        for j, a in enumerate(asst[-2:]):
            print(f"  [{j}] {repr(a[:140])}")
