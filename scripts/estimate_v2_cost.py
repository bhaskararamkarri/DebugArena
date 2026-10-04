"""Compute token statistics from v1 logs and project v2 re-run costs."""
import json
from pathlib import Path

def analyze_model_tokens(traj_paths):
    prompt_chars = []
    completion_chars = []
    steps_count = 0
    for tp in traj_paths:
        if not Path(tp).exists():
            continue
        with open(tp, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                steps_count += 1
                p_text = "".join(m.get("content", "") for m in rec.get("prompt", []))
                prompt_chars.append(len(p_text))
                a_text = json.dumps(rec.get("action", {}))
                completion_chars.append(len(a_text))

    avg_p_tokens = (sum(prompt_chars) / len(prompt_chars)) / 4.0 if prompt_chars else 0
    avg_c_tokens = (sum(completion_chars) / len(completion_chars)) / 4.0 if completion_chars else 0
    return avg_p_tokens, avg_c_tokens

# Nano v1
nano_p_tokens, nano_c_tokens = analyze_model_tokens(["runs/run1_nemotron_nano/trajectories.jsonl", "runs/hard_nano_v1/trajectories.jsonl"])
# Super v1
super_p_tokens, super_c_tokens = analyze_model_tokens(["runs/run1_nemotron_super/trajectories.jsonl", "runs/hard_super_v1/trajectories.jsonl"])

nano_core_steps = 22
nano_hard_steps = 13
super_core_steps = int(24 * 1.5)  # 36
super_hard_steps = int(49 * 1.5)  # 74

print(f"Nano: Avg prompt tokens/step={nano_p_tokens:.1f}, Avg completion tokens/step={nano_c_tokens:.1f}")
print(f"Super: Avg prompt tokens/step={super_p_tokens:.1f}, Avg completion tokens/step={super_c_tokens:.1f}")

nano_core_total_tokens = nano_core_steps * (nano_p_tokens + nano_c_tokens)
nano_hard_total_tokens = nano_hard_steps * (nano_p_tokens + nano_c_tokens)
super_core_total_tokens = super_core_steps * (super_p_tokens + super_c_tokens)
super_hard_total_tokens = super_hard_steps * (super_p_tokens + super_c_tokens)

print(f"\nEstimated Tokens:")
print(f"hard_nano_v2 (10 tasks, ~13 steps): {nano_hard_total_tokens:,.0f} tokens")
print(f"hard_super_v2 (10 tasks, ~74 steps): {super_hard_total_tokens:,.0f} tokens")
print(f"core_nano_v2 (20 tasks, ~22 steps): {nano_core_total_tokens:,.0f} tokens")
print(f"core_super_v2 (20 tasks, ~36 steps): {super_core_total_tokens:,.0f} tokens")
total_tokens = nano_core_total_tokens + nano_hard_total_tokens + super_core_total_tokens + super_hard_total_tokens
print(f"Total estimated tokens across all 4 runs: {total_tokens:,.0f} tokens")
