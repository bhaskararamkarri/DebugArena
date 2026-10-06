# Hackathon Submission Form Package

This file contains ready-to-paste text for the **Nebius × NVIDIA Global AI Hackathon** submission portal (Track: *Coding and Agentic Engineering*).

---

## 1. Project Title
**DebugArena**

*Formerly named AgentGym; the Python package keeps the name `agentgym` for compatibility. Shown as 'AgentGym' in the demo video, its earlier working name.*

---

## 2. Tagline
**DebugArena — an arena where coding agents compete on real bugs, scored by hidden tests in a Docker sandbox, and every attempt becomes training data.**

---

## 3. Short Description (~150 words)
DebugArena gives an AI coding agent a broken Python repository, lets it inspect, edit, and execute code inside an isolated Docker sandbox, scores it automatically against hidden pytest test suites, and exports every multi-turn interaction as a training-ready dataset. While traditional coding benchmarks yield static binary pass/fail scores without trajectory traces, DebugArena provides a reproducible, Gymnasium-style RL environment that pairs continuous progress rewards with regression penalties. Powered by Nebius Token Factory and NVIDIA Nemotron models, DebugArena measures open models fairly, enforces strict container isolation (network disabled, 256MB RAM, 0.5 CPU, 128 PIDs), and exports multi-turn trajectories into Supervised Fine-Tuning (SFT) and Direct Preference Optimization (DPO) datasets. In our evaluations across 30 benchmark tasks, NVIDIA Nemotron models demonstrate high multi-turn repair capabilities. Rather than just evaluating agents, DebugArena systematically generates the training data to improve them.

---

## 4. Long Description

### The Problem
Everyone is building coding agents, but almost nobody is building the environment where coding agents are measured, debugged, and improved. Frontier research labs train coding models using internal reinforcement learning environments, while the open-source community relies on static benchmarks like SWE-bench or HumanEval. Static benchmarks report a single pass rate, but do not provide lightweight, reproducible environments or multi-turn interaction trajectories that can be immediately plugged into Supervised Fine-Tuning (SFT) or RL algorithms (PPO / GRPO).

### The Solution: DebugArena
DebugArena provides an open, lightweight Gymnasium-style environment tailored for code repair and agentic engineering. Agents receive buggy Python repositories, inspect and modify files, execute exploratory commands, and submit solutions inside a contained sandbox. An automated reward calculator compares test progress before and after each action, penalizing regressions when previously passing code breaks. Every step is logged to structured JSONL, allowing instant conversion into high-quality training datasets.

### How It Works
1. **Isolated Docker Sandboxing:** Code executes in an isolated Docker container with network access disabled, 256MB memory cap, 0.5 CPU cap, 128 PID limit, and a 10s timeout. Hidden pytest test suites are mounted read-only at `/tests_hidden` only during environment scoring passes and are completely invisible during agent exploratory commands.
2. **Dense RL Reward Function:**
   $$\text{step\_reward} = (\text{pass\_rate}_t - \text{pass\_rate}_{t-1}) - 0.01 - 0.20 \times \mathbb{I}(\text{regression})$$
   Agents earn positive reward for passing new tests, pay a 0.01 step penalty to incentivize minimal edits, and suffer a sharp 0.20 penalty for introducing regressions.
3. **Agent Loop & Schema Normalization:** Powered by NVIDIA Nemotron via Nebius Token Factory with robust JSON action extraction (handling think tags, markdown fences, and balanced JSON objects) and factual environment prompts.
4. **Trajectory & Dataset Engine:** Verified trajectories are deduplicated and exported into a 49-episode SFT dataset (partitioned by task into train/val splits) and 9 cross-model DPO preference pairs (chosen from Super-120B, rejected from Nano-30B; 0 same-model pairs), with Protocol v1 local sandbox data kept strictly separate.
5. **Interactive Dashboard & Replay:** Streamlit interface features a benchmark leaderboard, error mode analysis, and step-by-step episode replay.

### Challenges Overcome
1. **Docker Sandbox Isolation:** Ensuring agent shell commands (`ls`, `cat`, python commands) cannot discover or cheat using hidden test files while still enabling the environment to run pytest dynamically.
2. **Parsing & Formatting Robustness:** Larger models like Nemotron Super frequently generated conversational reasoning or markdown blocks; our v2 balanced JSON parser strips think tags and fences reliably.
3. **Flakiness Elimination:** Designing regression tests and environment teardown to ensure reproducible scores across multiple runs.

### What's Next
- Multi-language expansion to TypeScript, Go, and Rust.
- Continuous online RL training loops (in-process GRPO / PPO policy updates using exported trajectories).
- Community benchmark contribution pipeline for submitting new broken repositories.

---

## 5. Built With
- **Nebius Token Factory:** High-performance OpenAI-compatible inference API.
- **NVIDIA Nemotron Models:** `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`, `nvidia/nemotron-3-ultra-550b-a55b`.
- **Docker & Pytest:** Mandatory isolated execution sandbox with resource and network constraints.
- **Streamlit:** Interactive web dashboard, leaderboard, and visual replay viewer.

---

## 6. How Judges Can Try It

Judges can test DebugArena in under 2 minutes without needing API keys using the built-in reference baselines in Docker, or test live with Nebius / NVIDIA API keys.

### Quickstart Smoke Test (No API Keys Needed)
```bash
# 1. Clone the repository
git clone https://github.com/bhaskararamkarri/DebugArena.git
cd DebugArena

# 2. Set up virtual environment and install dependencies
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -e .

# 3. Build the Docker sandbox image
docker build -t agentgym-sandbox:python3.11 -f - . <<EOF
FROM python:3.11-slim
RUN pip install --no-cache-dir pytest
WORKDIR /workspace
EOF

# 4. Run sandbox security self-tests (verifies hidden test isolation & timeout enforcement)
pytest tests/ -v

# 5. Verify benchmark tasks (zero flakiness guarantee)
python scripts/verify_tasks.py --suite all --sandbox docker

# 6. Run offline reference solver baseline in Docker
python scripts/run_eval.py --mock-solver --suite core --run-id baseline_reference_core_v2 --sandbox docker --no-judge

# 7. Launch the interactive leaderboard & replay dashboard
streamlit run dashboard/app.py
```

---

## 7. Demo Video
**Demo video:** <PASTE LINK>
