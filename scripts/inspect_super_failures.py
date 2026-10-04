"""Inspect Hard-10 Super failure tasks to re-evaluate failure labels and extract raw replies."""
import json
from pathlib import Path

traj_p = Path("runs/hard_super_v1/trajectories.jsonl")

tasks_to_check = ["h06", "h07", "h08", "h09", "h04", "h10"]
task_data = {t: [] for t in tasks_to_check}

with open(traj_p, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        rec = json.loads(line)
        tid = rec.get("task_id")
        if tid in task_data:
            task_data[tid].append(rec)

print("=== RAW MODEL REPLIES ANALYSIS ===")
for tid in ["h06", "h07", "h08", "h09"]:
    steps = task_data[tid]
    print(f"\n--- Task {tid} ({len(steps)} steps) ---")
    for s in steps:
        step_num = s.get("step")
        action = s.get("action", {})
        output = s.get("output", "")[:120]
        pass_rate = s.get("pass_rate")
        reward = s.get("reward")
        prompt = s.get("prompt", [])

        # Look for assistant message in prompt
        asst_msgs = [m.get("content", "") for m in prompt if m.get("role") == "assistant"]
        last_reply = asst_msgs[-1] if asst_msgs else "(none)"
        print(f"Step {step_num}: Action={action.get('type')}, PassRate={pass_rate}, Rew={reward}")
        if action.get("type") == "run" and "echo 'Invalid JSON action'" in action.get("cmd", ""):
            print(f"  [INVALID JSON] Raw Reply: {repr(last_reply[:140])}")
        elif action.get("type") == "edit":
            print(f"  [EDIT] path={action.get('path')}")
        elif action.get("type") == "run":
            print(f"  [RUN] cmd={action.get('cmd')[:60]}")
