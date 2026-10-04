# DebugArena Dataset Card

## Dataset Summary
The **DebugArena Dataset** consists of multi-turn interaction trajectories of AI coding agents attempting real-world Python bug fixes inside isolated execution sandboxes.
Evaluations were conducted on **Nebius Token Factory** using **NVIDIA Nemotron** models (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` and `nvidia/nemotron-3-super-120b-a12b`) running inside isolated **Docker** containers (Protocol v2).
The environment records full observation-action cycles, terminal outputs, pytest test evaluations, RL reward deltas, and code quality evaluations.

The dataset is exported in two core formats:
1. **Supervised Fine-Tuning (SFT)**: Full multi-turn conversation traces of successful episodes (100% test pass rate).
2. **Direct Preference Optimization (DPO)**: Paired trajectories on the same task comparing chosen (solved / higher return) against rejected (unsolved / lower return / regression) trajectories.

---

## 1. Primary SFT Dataset (`debugarena_sft.jsonl`)

Each row represents an episode where a real model achieved a 100% test pass rate (`pass_rate == 1.0`) under **Protocol v2 in Docker** (no baselines, no smoke tests, no duplicates):

```json
{
  "task_id": "c01_off_by_one",
  "messages": [
    {"role": "system", "content": "You are an autonomous AI coding agent fixing bugs..."},
    {"role": "user", "content": "OBSERVATION:\nDescription: sum_range(a, b) should return..."},
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"mathutils.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nLast execution output: File updated: mathutils.py\nPass rate: 1.0"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "return": 0.74,
  "steps": 1,
  "model": "nvidia/nemotron-3-super-120b-a12b",
  "judge_score": 4
}
```

### Primary SFT Splits (Protocol v2 in Docker — Task-Disjoint):
- `debugarena_sft.jsonl`: Complete deduplicated set of **49** solved real-model trajectories across 29 unique tasks.
- `debugarena_sft_train.jsonl`: **39** trajectories across 24 unique tasks (task-level train split).
- `debugarena_sft_val.jsonl`: **10** trajectories across 5 unique tasks (task-level validation split).
*No task appears in both the train and validation splits.*

---

## 2. DPO Preference Datasets

Each row pairs a successful solution (`chosen`) against a failed attempt (`rejected`) for the identical task prompt:

```json
{
  "task_id": "h01_merge_intervals",
  "prompt": "OBSERVATION:\nDescription: Merge overlapping intervals...",
  "chosen": [
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"merger.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nPass rate: 1.0"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "rejected": [
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"merger.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nPass rate: 0.6"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "chosen_return": 0.38,
  "rejected_return": -0.06,
  "chosen_pass_rate": 1.0,
  "rejected_pass_rate": 0.6,
  "chosen_model": "nvidia/nemotron-3-super-120b-a12b",
  "rejected_model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
}
```

### DPO Pairing Strategy & Splits:
- `debugarena_dpo.jsonl`: **0** pairs (strictly same-task and same-model; in v2 each model is evaluated once per task, so a single model does not produce both a success and failure for the same task in the v2 run).
- `debugarena_dpo_cross_model.jsonl`: **9** cross-model preference pairs (same task, comparing successful Super-120B vs failed Nano-30B under Protocol v2 in Docker).
  - `debugarena_dpo_cross_model_train.jsonl`: **8** pairs across 8 distinct tasks.
  - `debugarena_dpo_cross_model_val.jsonl`: **1** pair across 1 distinct task (*tiny split due to small total pool of 9 contrasting tasks; preserved strictly task-disjoint*).

---

## 3. Protocol v1 Local Sandbox Datasets
Legacy Protocol v1 episodes executed in `LocalSandbox` with the v1 parser are exported separately:
- `debugarena_sft_v1_local.jsonl`: **48** unique solved trajectories from Protocol v1 in local sandbox.
  - *Provenance Note on 48 vs 52 Solved Episodes:* While raw runs produced 52 solved episodes (Nano: 27, Super: 25), Nano and Super generated identical single-step solutions on 4 tasks (`t06_clamp_boundary`, `t08_empty_list_edge_case`, `t09_mutable_default_arg`, `t13_flatten_nested`). SHA-256 fingerprint deduplication collapsed these duplicate trajectories, leaving 48 unique training traces.
- `debugarena_dpo_v1_local.jsonl`: **0** pairs (same-model).
- Legacy files are archived in `dataset/v1_archive/`.

---

## 4. Data Processing & Validation
- **Task-Disjoint Partitioning:** All train/val splits are grouped strictly by `task_id` (zero task leakage between train and val).
- **Deduplication:** SHA-256 fingerprinting on message history eliminates identical trajectories across repeated evaluations.
- **Validation:** Strict verification ensuring non-empty role/content structures and valid assistant JSON actions.
- **Reproducibility:** Train/val splits are generated using fixed seed (`seed=42`).
- **Provenance:** All baseline episodes (`baseline_reference`, `baseline_noop`, mock solver) and smoke tests are excluded from training datasets.
