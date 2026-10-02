# AgentGym Dataset Card

## Dataset Summary
The **AgentGym Dataset** consists of multi-turn interaction trajectories of AI coding agents attempting real-world Python bug fixes inside isolated execution sandboxes.
The environment records full observation-action cycles, terminal outputs, pytest test evaluations, RL reward deltas, and code quality evaluations.

The dataset is exported in two core formats:
1. **Supervised Fine-Tuning (SFT)**: Full multi-turn conversation traces of successful episodes (100% test pass rate).
2. **Direct Preference Optimization (DPO)**: Paired trajectories on the same task comparing chosen (solved / higher return) against rejected (unsolved / lower return / regression) trajectories.

---

## 1. SFT Dataset (`agentgym_sft.jsonl`)

Each row represents an episode where the agent achieved a 100% test pass rate (`pass_rate == 1.0`):

```json
{
  "task_id": "t01_off_by_one",
  "messages": [
    {"role": "system", "content": "You are an autonomous AI coding agent fixing bugs..."},
    {"role": "user", "content": "OBSERVATION:\nDescription: sum_range(a, b) should return..."},
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"mathutils.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nLast execution output: File updated: mathutils.py\nPass rate: 1.0"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "return": 0.74,
  "steps": 1,
  "model": "nvidia/nemotron-3-nano-30b-a3b",
  "judge_score": 4
}
```

### SFT Splits:
- `agentgym_sft.jsonl`: Complete deduplicated set of 53 solved trajectories.
- `agentgym_sft_train.jsonl`: 43 trajectories (80% train split).
- `agentgym_sft_val.jsonl`: 10 trajectories (20% validation split).

---

## 2. DPO Preference Dataset (`agentgym_dpo.jsonl`)

Each row pairs a successful solution (`chosen`) against a failed or suboptimal attempt (`rejected`) for the identical task prompt:

```json
{
  "task_id": "t16_lru_cache_eviction",
  "prompt": "OBSERVATION:\nDescription: LRUCache should evict least recently used items...",
  "chosen": [
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"lru_cache.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nPass rate: 1.0"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "rejected": [
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"lru_cache.py\", \"content\": \"def broken()...\"}"},
    {"role": "user", "content": "OBSERVATION:\nPass rate: 0.25"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "chosen_return": 0.32,
  "rejected_return": -1.09,
  "chosen_pass_rate": 1.0,
  "rejected_pass_rate": 0.25
}
```

### DPO Splits:
- `agentgym_dpo.jsonl`: 9 preference pairs.
- `agentgym_dpo_train.jsonl`: 8 pairs (train split).
- `agentgym_dpo_val.jsonl`: 1 pair (val split).

---

## 3. Data Processing & Validation
- **Deduplication:** SHA-256 fingerprinting on message history eliminates identical trajectories across repeated evaluations.
- **Validation:** Strict verification ensuring non-empty role/content structures and valid assistant JSON actions.
- **Reproducibility:** Train/val splits are generated using fixed seed (`seed=42`).

---

## 4. Human-Verified SFT Subset (`agentgym_sft_human_verified.jsonl`)
- **Status:** Optional partner integration (Tendem / Toloka expert review), not yet run pending reviewer submission.
- **Review Package:** Solved episodes are compiled via `python scripts/make_review_pack.py` into `review_pack/review_pack.md` with problem descriptions, original buggy code, unified fix diffs, and 5 quality questions.
- **Ingestion Pipeline:** Annotated evaluations in `review_pack/reviews.json` are filtered (rating $\ge 4$) via `python scripts/import_review.py` to produce `dataset/agentgym_sft_human_verified.jsonl`.
