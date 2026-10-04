# DebugArena

> **DebugArena — an arena where coding agents compete on real bugs, scored by hidden tests in a Docker sandbox, and every attempt becomes training data.**  
> *Formerly named AgentGym; the Python package keeps the name `agentgym` for compatibility.*  
> *Built for Nebius × NVIDIA Global AI Hackathon · Track: Agent Gym & Coding Environments*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/sandbox-Docker%20Mandatory-2496ED.svg)](https://www.docker.com/)
[![NVIDIA Nemotron](https://img.shields.io/badge/models-NVIDIA%20Nemotron-76B900.svg)](https://build.nvidia.com)
[![Nebius Token Factory](https://img.shields.io/badge/compute-Nebius%20Token%20Factory-8A2BE2.svg)](https://nebius.ai)

---

## 1. Overview

**DebugArena** provides a Gymnasium-style reinforcement learning environment for coding agents. An agent receives a broken Python repository, interacts exclusively by outputting JSON actions (`edit`, `run`, `submit`), executes inside an isolated Docker sandbox, is scored by hidden pytest tests, and exports every verified trajectory directly into SFT and DPO preference datasets.

---

## 2. Architecture

```mermaid
flowchart TD
    subgraph Input ["Task Benchmark Definition"]
        TaskJSON["Task JSON\n(Buggy Code + Hidden Pytests + Metadata)"]
    end

    subgraph CoreLoop ["DebugArena RL Execution Loop"]
        Env["BugFixEnv\nreset() / step()"]
        Agent["Autonomous Agent\n(NVIDIA Nemotron via Nebius Token Factory)"]
        Sandbox["Docker Sandbox\n(network: none, 256MB, 0.5 CPU, 128 PIDs)"]
        RewardCalc["Reward Calculator\n(Pass Rate Delta - Step Cost - Regression Penalty)"]
    end

    subgraph Outputs ["Evaluation & Training Artifacts"]
        Trajectories["Trajectories Log\n(JSONL Multi-turn Traces)"]
        Leaderboard["Streamlit Dashboard\n(Leaderboard, Replay Viewer, Failure Analysis)"]
        SFT["SFT Dataset Export\n(Train / Val splits)"]
        DPO["DPO Preference Dataset\n(Chosen vs Rejected pairs)"]
    end

    TaskJSON -->|Load repository| Env
    Env -->|Observation: files, output, steps_left| Agent
    Agent -->|JSON Action: edit / run / submit| Env
    Env -->|Run command / edit files| Sandbox
    Sandbox -->|Isolated pytest scoring| RewardCalc
    RewardCalc -->|Step reward & pass rate| Env
    Env -->|Log step record| Trajectories

    Trajectories --> Leaderboard
    Trajectories --> SFT
    Trajectories --> DPO
```

### Execution Loop & Sandbox Isolation
1. **Reset:** `obs = env.reset(task_id)` creates an ephemeral workspace in the Docker container, writes repository files, and executes hidden tests to establish baseline pass rates.
2. **Action Execution:** The agent emits a single JSON action (`edit`, `run`, `submit`). Commands execute in the container with `--network none`, `256MB RAM`, `0.5 CPU`, `128 PIDs`, and a 10s timeout.
3. **Hidden Test Protection:** Hidden tests are mounted read-only at `/tests_hidden` only during environment scoring passes; agent `run` commands cannot see `/tests_hidden` or host files.
4. **Step Reward Formula:**
   $$\text{step\_reward} = (\text{pass\_rate}_t - \text{pass\_rate}_{t-1}) - 0.01 - 0.20 \times \mathbb{I}(\text{regression})$$
   where regression occurs if any previously passing test now fails.
5. **Data Export:** Complete multi-turn trajectories are saved to `runs/<run_id>/trajectories.jsonl`.

---

## 3. Benchmark Tasks (30 Verified Scenarios)

DebugArena includes 30 verified tasks across two suites:
- **Core-20:** 20 fundamental debugging tasks (7 easy, 9 medium, 4 hard) covering off-by-one errors, mutable default arguments, division truncations, custom sorting, and multi-file interfaces.
- **Hard-10:** 10 multi-step engineering bugs (e.g., date arithmetic, interval merging, tokenizer states, transaction rollbacks).

Every task is verified across 3x repetitions with zero flakiness:
```bash
python scripts/verify_tasks.py --suite all --sandbox docker
```

---

## 4. Setup & Quickstart

### Prerequisites
- Python 3.10+
- Docker (Docker Desktop or Linux Docker daemon running)

### Installation
```bash
git clone <REPO_URL>
cd debugarena

python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -e .
```

### Build Docker Sandbox Image
```bash
docker build -t agentgym-sandbox:python3.11 -f - . <<EOF
FROM python:3.11-slim
RUN pip install --no-cache-dir pytest
WORKDIR /workspace
EOF
```

### Configuration
Copy `.env.example` to `.env` and insert your Nebius API key:
```ini
NEBIUS_API_KEY=your_nebius_api_key
```

---

## 5. How to Run

### 1. Offline Baselines (Quick-Start)
Run the built-in reference solver (upper bound) and no-op submit (lower bound) through the Docker sandbox:
```bash
# Reference Solver:
python scripts/run_eval.py --mock-solver --suite core --run-id baseline_reference_core_v2 --sandbox docker --no-judge
python scripts/run_eval.py --mock-solver --suite hard --run-id baseline_reference_hard_v2 --sandbox docker --no-judge

# No-Op Submit:
python scripts/run_eval.py --noop-solver --suite core --run-id baseline_noop_core_v2 --sandbox docker --no-judge
python scripts/run_eval.py --noop-solver --suite hard --run-id baseline_noop_hard_v2 --sandbox docker --no-judge
```

### 2. Live Model Evaluations
```bash
# Evaluate NVIDIA Nemotron Nano (30B):
python scripts/run_eval.py --model nemotron_nano --suite core --workers 4 --run-id core_nano_v2 --sandbox docker

# Evaluate NVIDIA Nemotron Super (120B):
python scripts/run_eval.py --model nemotron_super --suite core --workers 4 --run-id core_super_v2 --sandbox docker
```

### 3. Launch the Streamlit Dashboard
```bash
streamlit run dashboard/app.py
```

### 4. Export Training Datasets (SFT & DPO)
```bash
python scripts/export_dataset.py --format sft --split
python scripts/export_dataset.py --format dpo --split
```

---

## 6. Empirical Results: Protocol v1 vs Protocol v2

### Empirical Findings:
- In **Protocol v1** (executed on local host with rigid JSON parsing), Nemotron Super (120B) was heavily penalized when emitting conversational chain-of-thought analysis alongside code, triggering invalid JSON fallback loops on Hard-10.
- In **Protocol v2** (mandatory Docker sandbox with robust JSON parsing, think tag stripping, and factual system prompts), action extraction handles conversational formatting cleanly, while true bug-solving capability is rigorously measured.

| Model / Baseline | Suite | Protocol | Sandbox | Solved | Success Rate (%) | 95% Wilson CI | Avg Steps | Avg Return |
|---|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3-nano-30b-a3b` | Core-20 | v1 | Local | 18 / 20 | **90.0%** | `[69.9%, 97.2%]` | 1.45 | +0.67 |
| `nvidia/nemotron-3-nano-30b-a3b` | Hard-10 | v1 | Local | 9 / 10 | **90.0%** | `[59.6%, 98.2%]` | 1.30 | +0.35 |
| `nvidia/nemotron-3-super-120b-a12b` | Core-20 | v1 | Local | 19 / 20 | **95.0%** | `[76.4%, 99.1%]` | 1.15 | +0.76 |
| `nvidia/nemotron-3-super-120b-a12b` | Hard-10 | v1 | Local | 6 / 10 | **60.0%** | `[31.3%, 83.2%]` | 4.90 | -0.05 |
| `baseline_reference` (Upper Bound) | Core-20 | v2 | Docker | 20 / 20 | **100.0%** | `[83.9%, 100.0%]` | 1.00 | +0.54 |
| `baseline_reference` (Upper Bound) | Hard-10 | v2 | Docker | 10 / 10 | **100.0%** | `[72.2%, 100.0%]` | 1.10 | +0.37 |
| `baseline_noop` (Lower Bound) | Core-20 | v2 | Docker | 0 / 20 | **0.0%** | `[0.0%, 16.1%]` | 1.00 | -0.01 |
| `baseline_noop` (Lower Bound) | Hard-10 | v2 | Docker | 0 / 10 | **0.0%** | `[0.0%, 27.8%]` | 1.00 | -0.01 |

---

## 7. Limitations

1. **Benchmark Suite Size:** With $N=30$ total tasks ($N=20$ core, $N=10$ hard), binomial confidence intervals are broad.
2. **Single Evaluation Runs:** Results represent single-run rollouts per configuration.
3. **Language Scope:** Focused on Python 3 repositories.
4. **RL Training Loop:** DebugArena produces SFT and DPO training data; policy training (PPO/GRPO) is performed using the exported datasets.

---

## 8. Products & Technologies Used

- **[Nebius Token Factory](https://nebius.ai):** High-throughput, low-latency LLM API inference compute powering agent rollouts.
- **[NVIDIA Nemotron Models](https://build.nvidia.com):** State-of-the-art open reasoning and coding models (`nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`, `nvidia/nemotron-3-ultra-550b-a55b`).
- **[Docker](https://www.docker.com):** Mandatory isolated container sandbox with zero network access and strict CPU/RAM/PID resource limits.
- **[Streamlit](https://streamlit.io):** Interactive benchmark leaderboard and trajectory replay UI.

---

## 9. License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
