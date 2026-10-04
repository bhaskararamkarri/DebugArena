"""Diagnose smoke_v2_super invalid replies."""
import json
from pathlib import Path

with open("runs/smoke_v2_super/trajectories.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

print(f"Total steps: {len(records)}")
for rec in records:
    step = rec.get("step")
    act = rec.get("action", {})
    prompt = rec.get("prompt", [])
    asst_msgs = [m.get("content", "") for m in prompt if m.get("role") == "assistant"]

    # Check if fallback
    is_fallback = act.get("type") == "run" and "echo 'Invalid JSON action'" in act.get("cmd", "")
    if is_fallback:
        print(f"\n--- STEP {step} (Invalid Fallback) ---")
        for j, raw in enumerate(asst_msgs[-2:]):
            has_balanced = ("{" in raw and "}" in raw)
            is_truncated = raw.endswith('...') or (raw.count('{') > raw.count('}')) or (raw.count('"') % 2 != 0)
            has_reasoning = any(w in raw.lower() for w in ["we need", "we are", "let's", "let us", "think", "because"])
            has_think_tags = ("<think>" in raw.lower() or "</think>" in raw.lower())
            has_triple_quotes = '"""' in raw or "'''" in raw
            print(f"  Attempt {j+1}: len={len(raw)}, has_balanced={has_balanced}, truncated={is_truncated}, reasoning={has_reasoning}, think_tags={has_think_tags}, triple_quotes={has_triple_quotes}")
            print(f"  Preview: {repr(raw[:150])}")
