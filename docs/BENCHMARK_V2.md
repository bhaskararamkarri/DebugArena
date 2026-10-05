# DebugArena Benchmark V2 Specification

DebugArena Benchmark V2 is a rigorous evaluation suite and training trajectory generator for autonomous AI coding agents.

---

## 1. Core Benchmark Philosophy

Benchmark V2 is built on six foundational principles:

1. **Quality > Quantity**: A suite of 100 deep, verified, multi-file tasks provides far stronger evaluation signal than 500 shallow single-line bugs.
2. **Realism > Synthetic Puzzles**: Tasks model real repository structures with multiple interacting modules, realistic domain models, and genuine architectural patterns.
3. **Behavioral Correctness > Reference Matching**: Hidden tests assert black-box behavioural contracts. Any correct implementation that preserves system invariants is accepted.
4. **Adversarial Rigor**: High-difficulty tasks include misleading comments, partial fix traps, and distractors to test whether agents truly reason or merely pattern-match.
5. **Deterministic Execution**: Every task undergoes 3x repetition checks to guarantee zero flakiness in both buggy and repaired states.
6. **Provenance & Safety**: Complete offline sandbox containment with zero host leakage and zero paid external dependencies.

---

## 2. Target 100-Task Distribution

| Suite / Tier | Target Count | Share | Primary Focus | Taxonomy Coverage |
|---|---|---|---|---|
| **Basic (Sanity)** | 20 tasks | 20% | Localized syntax, operators, basic edge cases | Category A, localized B/C |
| **Medium (Core)** | 30 tasks | 30% | Multi-file interfaces, parsing, state machines, API logic | Categories D, E, F, H, J |
| **Hard (Advanced)** | 30 tasks | 30% | Deep graph/DP algorithms, concurrency, transactions, leaks | Categories B, C, G, I, K, L |
| **Adversarial** | 20 tasks | 20% | Misleading comments, distractor files, partial-fix traps | Category M (across all domains) |
| **Total Benchmark** | **100 tasks** | **100%** | Comprehensive SWE & Debugging Capability | Categories A through M |

---

## 3. Feedback Mode Abstraction

Benchmark V2 supports three evaluation feedback modes to test agents under varying degrees of observability:

```
+-------------------------------------------------------------------------+
|                           Agent Action Execution                        |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  Sandbox Runs Hidden Tests In Isolation                 |
+-------------------------------------------------------------------------+
                                     |
                                     v
                        +-------------------------+
                        | Feedback Adapter Router |
                        +-------------------------+
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
+--------------------+      +--------------------+      +--------------------+
|  Diagnostic Mode   |      |   Realistic Mode   |      |     Blind Mode     |
| (Full test counts, |      | (Command output &  |      |  (Action exit code |
|  pass rates, test  |      |  stderr only; no   |      |  only; zero test   |
|   names exposed)   |      |  test metadata)    |      |     metadata)      |
+--------------------+      +--------------------+      +--------------------+
```

1. **`diagnostic` (Default)**: Full step-by-step visibility into pass rate, passed tests, and failed tests. Ideal for dense reward RL rollouts and diagnostic evaluation.
2. **`realistic`**: Simulates realistic developer workflows. The agent only observes command outputs, stdout, and stderr from manual test executions; hidden benchmark test names and pass rates remain completely concealed until episode completion.
3. **`blind`**: Zero intermediate feedback; the agent is only notified of command exit codes. Evaluates true zero-shot reasoning and internal validation.

---

## 4. Backwards-Compatible Task Schema V2

Benchmark V2 tasks adhere to the following schema:

```json
{
  "task_id": "v01_sliding_window_stream",
  "suite": "v2",
  "version": 2,
  "difficulty": "medium",
  "bug_type": "sliding_window_eviction",
  "categories": ["B", "D"],
  "description": "The real-time metric accumulator fails to evict stale samples on window slides...",
  "spec_notes": "Invariant: Window duration must be maintained exactly. In-order arrival guaranteed.",
  "repo_files": {
    "models.py": "...",
    "window.py": "...",
    "accumulator.py": "..."
  },
  "tests": {
    "test_accumulator.py": "..."
  },
  "reference_fix": {
    "window.py": "..."
  },
  "metadata": {
    "estimated_reasoning_steps": 4,
    "file_count": 3,
    "adversarial": false,
    "stateful": true,
    "multi_file": true,
    "domain": "telemetry_metrics",
    "quality_score": 4.5
  }
}
```

---

## 5. RL Environment vs. RL Training Clarification

DebugArena provides:
- **Gymnasium-style RL Environment (`BugFixEnv`)**
- **Step-level Reward Calculator (`RewardCalculator`)** with progress credit, step costs, and regression penalties
- **Rollout Runner (`AgentRunner`)** for trajectory collection across LLM agents
- **Dataset Exporters (`export_dataset.py`)** for SFT and DPO preference pair generation

**Note on RL Training**: DebugArena is an **RL-compatible evaluation and rollout environment**. It does **not** include built-in PPO, GRPO, or policy gradient optimizer training loops. Downstream researchers use DebugArena trajectories to train policy models in external training frameworks.
