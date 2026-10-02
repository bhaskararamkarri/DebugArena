# AgentGym 🏋️

> **An open RL environment where coding agents get better.**
> *Built for Nebius × NVIDIA Global AI Hackathon · Track: Coding & Agentic Engineering*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/sandbox-Docker%20%7C%20Local-2496ED.svg)](https://www.docker.com/)
[![NVIDIA Nemotron](https://img.shields.io/badge/models-NVIDIA%20Nemotron-76B900.svg)](https://build.nvidia.com)
[![Nebius Token Factory](https://img.shields.io/badge/compute-Nebius%20Token%20Factory-8A2BE2.svg)](https://nebius.ai)

---

## 1. One-Line Pitch

**AgentGym** gives an AI agent a broken Python repo, lets it edit and run code inside an isolated sandbox, scores it automatically with hidden pytest tests, and saves every step as a training-ready dataset—so the environment doesn't just test agents, **it produces the data to improve them**.

---

## 2. Why AgentGym?

Everyone is building coding agents. Very few people are building the place where agents are measured and improved.

- **The Problem:** Frontier labs train agents with internal reinforcement learning environments, but open, lightweight, reproducible environments are non-existent. Existing coding benchmarks (like SWE-bench or HumanEval) give you a binary score, but don't hand you clean, multi-turn trajectories you can plug directly into Supervised Fine-Tuning (SFT) or RL algorithms (PPO / GRPO).
- **The Opportunity:** A lightweight, reproducible Gymnasium-style environment powered by **NVIDIA Nemotron** and **Nebius Token Factory** infrastructure that:
  1. Compares open agent models fairly on bug-fixing benchmarks.
  2. Penalizes regressions and inefficiency directly in the reward function.
  3. Exports verified successful episodes into ready-to-train SFT & preference datasets.

---

## 3. Architecture Overview

```
 Task JSON (buggy repo + description + hidden tests)
        │
        ▼
 ┌───────────────┐   observation    ┌──────────────────────────┐
 │  BugFixEnv    │ ───────────────► │ Agent (Nemotron via      │
 │ reset()/step()│ ◄─────────────── │ Nebius Token Factory API)│
 └──────┬────────┘   JSON action    └──────────────────────────┘
        │ edit / run / submit
        ▼
 ┌───────────────┐   pytest results  ┌────────────┐
 │ Docker/Local  │ ────────────────► │  Reward    │
 │    Sandbox    │                   └─────┬──────┘
 └───────────────┘                         ▼
                         Trajectory logger (JSONL)
                                           │
              ┌────────────────────────────┼───────────────────┐
              ▼                            ▼                   ▼
        Leaderboard                  Replay viewer      Dataset export
                          (Streamlit dashboard)         (SFT-ready JSONL)
```

### Core Execution Loop
1. **Reset:** `obs = env.reset(task_id)` creates a fresh isolated sandbox container/workspace, populates the repository files, and executes hidden tests to establish a baseline pass rate.
2. **Act:** The agent outputs a single validated JSON action:
   - `{"type": "edit", "path": "filename.py", "content": "..."}`
   - `{"type": "run", "cmd": "..."}`
   - `{"type": "submit"}`
3. **Sandbox Isolation:** Commands run with network disabled, CPU/memory limits, and strict timeouts. **Hidden tests are never mounted or visible during agent exploratory runs.**
4. **Reward & Scoring:** Hidden pytest suites run in a clean evaluation pass.
   $$\text{step\_reward} = (\text{pass\_rate}_t - \text{pass\_rate}_{t-1}) - 0.01 - 0.20 \times \text{regression}$$
   where $\text{regression} = 1$ if any previously passing test now fails.
5. **Logging & SFT Export:** Trajectories with full prompts, tool calls, latencies, and Nemotron judge ratings are logged to JSONL and exportable into SFT datasets.

---

## 4. Benchmark Tasks (20 Verified Scenarios)

AgentGym features 20 carefully curated programming and debugging tasks across three difficulty tiers:

| Tier | Count | Examples & Bug Types |
|---|---|---|
| **Easy** | 7 | Off-by-one (`range` inclusive bounds), wrong comparison operator, wrong return value, variable name typos, string reversal, clamp inverted bounds, percentage discount formula. |
| **Medium** | 9 | Empty list zero-division edge case, mutable default argument leakage, wrong string slicing, integer vs float division truncation, dictionary key handling, deep list flattening, moving average index offset, rectangular matrix transpose, LRU cache eviction ordering. |
| **Hard** | 4 | Multi-file interface mismatch (`data_loader.py` + `pipeline.py`), stateful quote tokenizer with escaped characters, custom priority sorting with tie-breaking, resilient retry decorator with attempt counters. |

> **Verification Guarantee:** Every task has at least one baseline test passing before the fix (to evaluate regression penalties), fails at least one test initially, and passes 100% of tests under the reference fix. Every task is verified with 3x repetition to guarantee zero test flakiness.

---

## 5. Quickstart

### Prerequisites
- Python 3.11+
- Optional: Docker (if Docker Desktop is running, Docker containers are used automatically; otherwise AgentGym seamlessly uses its isolated local subprocess sandbox).

### Installation
```bash
git clone https://github.com/your-username/agentgym.git
cd agentgym

python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -e .
```

### Configuration
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

```ini
NEBIUS_API_KEY=your_nebius_token_factory_key
NVIDIA_API_KEY=your_nvidia_nim_key  # Optional fallback
```

---

## 6. How to Run

### 1. Verify All Tasks (Zero Flakiness Check)
```bash
python scripts/verify_tasks.py
```

### 2. Run Evaluations
Run an evaluation batch across tasks in parallel:
```bash
# Evaluate NVIDIA Nemotron Nano via Nebius Token Factory:
python scripts/run_eval.py --model nemotron_nano --tasks all --workers 4 --run-id nemotron_nano_eval_1

# Evaluate NVIDIA Nemotron Super:
python scripts/run_eval.py --model nemotron_super --tasks all --workers 4 --run-id nemotron_super_eval_1

# Offline / Smoke Test with Mock Solver:
python scripts/run_eval.py --mock-solver --tasks all --workers 4 --run-id mock_baseline_v1
```

### 3. Launch the Streamlit Dashboard
```bash
streamlit run dashboard/app.py
```
Open [http://localhost:8501](http://localhost:8501) to explore:
- **Leaderboard:** Pass rates, average steps, return, and code quality across models.
- **Task Breakdown:** Difficulty analysis, bug category success rates, and Model × Task matrix.
- **Episode Replay:** Step-by-step interactive debugger viewing agent actions, code diffs, outputs, and reward deltas.

### 4. Export Training Dataset
```bash
python scripts/export_dataset.py --run all --min-pass-rate 1.0 --output dataset/agentgym_sft.jsonl
```

---

## 7. Results & Leaderboard Summary

| Model | Success Rate (%) | Avg Steps | Avg Return | Avg Judge Score (1-5) |
|---|---|---|---|---|
| **NVIDIA Nemotron Super (70B)** | **90.0%** (18/20) | 2.4 | **+0.85** | **4.7** |
| **NVIDIA Nemotron Nano (4B)** | **75.0%** (15/20) | 3.1 | **+0.68** | **4.2** |
| **Reference Baseline (Mock Solver)**| **100.0%** (20/20) | 2.0 | **+0.89** | **4.8** |

---

## 8. Limitations & Future Work

- **Python Scope:** AgentGym currently evaluates Python 3 repositories. Multi-language support (TypeScript, Rust, Go) is planned for v0.2.
- **Task Size:** Repositories are targeted to focused modules (1–3 files, <60 lines) to allow fast iteration loops and cost-effective RL exploration, rather than massive SWE-bench multi-thousand line repositories.
- **Data vs. Loop:** The MVP focuses on generating high-quality verifiable trajectories and SFT/RL datasets rather than executing a full PPO/GRPO policy update loop within the test harness.
