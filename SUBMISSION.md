# Hackathon Submission Form Package

This file contains ready-to-paste text for the **Nebius × NVIDIA Global AI Hackathon** submission portal (Track: *Coding & Agentic Engineering*).

---

## 1. Project Title
**AgentGym**

---

## 2. Tagline
**An open RL environment where coding agents get better.**

---

## 3. Short Description (~150 words)
AgentGym gives an AI agent a broken Python repository, lets it edit and execute code inside an isolated Docker sandbox, scores it automatically against hidden pytest test suites, and exports every interaction step as a training-ready dataset. While existing coding benchmarks yield simple binary pass/fail scores, AgentGym provides a reproducible, Gymnasium-style RL environment that pairs continuous rewards with regression penalties. Powered by Nebius Token Factory and NVIDIA Nemotron models, AgentGym measures open models fairly, prevents test leakage, provides LangSmith observability, and exports multi-turn trajectories into Supervised Fine-Tuning (SFT) and Direct Preference Optimization (DPO) datasets. In our empirical evaluations, NVIDIA Nemotron Super achieved a 95.0% pass rate (19/20 tasks) with zero regressions, while Nemotron Nano achieved 90.0% (18/20 tasks). Rather than just testing agents, AgentGym systematically generates the data to improve them.

---

## 4. Long Description

### The Problem
Everyone is building coding agents, but almost nobody is building the environment where coding agents are measured and improved. Frontier labs train their models using proprietary reinforcement learning environments, while open-source developers rely on static benchmarks like SWE-bench or HumanEval. Static benchmarks report a pass rate, but do not provide lightweight, reproducible environments or multi-turn interaction trajectories that can be immediately plugged into Supervised Fine-Tuning (SFT) or RL algorithms (PPO / GRPO).

### The Solution: AgentGym
AgentGym provides an open, lightweight Gymnasium-style environment tailored for code repair and agentic engineering. Agents receive buggy Python repositories, inspect and modify files, execute exploratory commands, and submit solutions inside a contained sandbox. An automated reward calculator compares test progress before and after each action, penalizing regressions when previously passing code breaks. Every step is logged to structured JSONL, allowing instant conversion into high-quality training datasets.

### How It Works
1. **Isolated Sandboxing:** Code executes in an isolated Docker container (or subprocess sandbox) with network access disabled, 256MB memory cap, 0.5 CPU cap, and 128 PID limit. Crucially, hidden pytest test suites are kept unreadable from agent exploratory runs.
2. **Dense RL Reward Function:**
   $$\text{step\_reward} = (\text{pass\_rate}_t - \text{pass\_rate}_{t-1}) - 0.01 - 0.20 \times \text{regression}$$
   Agents earn positive reward for passing new tests, pay a 0.01 step penalty to incentivize minimal edits, and suffer a sharp 0.20 penalty for introducing regressions.
3. **Agent Loop & Schema Normalization:** Powered by NVIDIA Nemotron via Nebius Token Factory with strict JSON schema parsing and synonym normalization, achieving a 0.0% invalid-JSON failure rate.
4. **Trajectory & Dataset Engine:** Successful trajectories are deduplicated and exported into multi-turn SFT datasets (with 80/20 train/val splits) and DPO preference datasets pairing solved versus rejected attempts.
5. **Interactive Dashboard & Replay:** Streamlit interface features a benchmark leaderboard, error mode analysis, and step-by-step episode replay.
6. **Observability & Verification:** Includes hierarchical LangSmith tracing (child spans for LLM reasoning and environment execution) and human review pack generation for Tendem / Toloka expert annotators.

### Empirical Results Across 20 Verified Tasks
All 20 benchmark tasks were verified 3x sequentially to guarantee zero test flakiness:
- **`nvidia/nemotron-3-super-120b-a12b`**: **95.0% Pass Rate** (19/20 solved), Avg Steps: 1.20, Avg Return: **+0.53**, Avg Judge Score: 3.85 / 5.0.
- **`nvidia/nemotron-3-nano-30b-a3b`**: **90.0% Pass Rate** (18/20 solved), Avg Steps: 1.25, Avg Return: **+0.40**, Avg Judge Score: 3.80 / 5.0.
- **Reference Solver (Upper Bound Baseline)**: **100.0% Pass Rate** (20/20 solved), Avg Steps: 2.00, Avg Return: +0.53.
- **No-op Submit (Lower Bound Baseline)**: **0.0% Pass Rate** (0/20 solved), Avg Steps: 1.00, Avg Return: -0.01.

### Challenges Overcome
1. **Test Isolation:** Ensuring agent shell commands (`ls`, `cat`) cannot discover or cheat using hidden test files while still enabling the environment to run pytest dynamically.
2. **Prompt & Schema Robustness:** Managing reasoning model outputs and raw text formatting to guarantee 100% reliable JSON action execution across models.
3. **Flakiness Elimination:** Designing regression tests and environment teardown to ensure reproducible scores across multiple runs.

### What's Next
- Multi-language expansion to TypeScript, Go, and Rust.
- Continuous online RL training loops (in-process GRPO / PPO policy updates using exported trajectories).
- Community benchmark contribution pipeline for submitting new broken repositories.

---

## 5. Built With
- **Nebius Token Factory:** High-performance OpenAI-compatible inference API.
- **NVIDIA Nemotron Models:** `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`.
- **LangSmith:** Episode-level and tool-level multi-span tracing.
- **Tendem / Toloka Workflow:** Expert human review generation and verified dataset ingestion.
- **Streamlit:** Interactive web dashboard, leaderboard, and visual replay viewer.
- **Docker & Pytest:** Isolated execution sandbox and automated deterministic evaluation.

---

## 6. How Judges Can Try It

Judges can test AgentGym in under 2 minutes without needing API keys using the built-in reference baselines, or test live with Nebius / NVIDIA API keys.

### Option A: Quickstart Smoke Test (No API Keys Needed)
```bash
# 1. Clone the repository
git clone https://github.com/your-username/agentgym.git
cd agentgym

# 2. Set up virtual environment and install dependencies
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -e .

# 3. Run sandbox security self-tests (verifies hidden test isolation & timeout enforcement)
pytest tests/ -v

# 4. Verify benchmark tasks (zero flakiness guarantee)
python scripts/verify_tasks.py

# 5. Run offline reference solver evaluation
python scripts/run_eval.py --mock-solver --tasks t01_off_by_one,t02_wrong_operator --workers 2 --run-id demo_eval

# 6. Launch the interactive leaderboard & replay dashboard
streamlit run dashboard/app.py
```

### Option B: Live Evaluation with Nebius Token Factory
```bash
# 1. Provide your API key in .env
echo "NEBIUS_API_KEY=your_key_here" > .env

# 2. Run evaluation with NVIDIA Nemotron Nano or Super
python scripts/run_eval.py --model nemotron_nano --tasks all --workers 4 --run-id nemotron_nano_test

# 3. (Optional) Run with LangSmith observability tracing
python scripts/run_eval.py --model nemotron_nano --tasks t01_off_by_one --trace --run-id trace_test

# 4. Export the resulting SFT and DPO training datasets
python scripts/export_dataset.py --format sft --split
python scripts/export_dataset.py --format dpo --split
```

### Observability Trace URL Format
When running with `--trace`, hierarchical traces are visible in the LangSmith dashboard at:  
`https://smith.langchain.com/o/<org>/projects/p/<project-id>?peek=<run-id>`

---

## 7. Submission Checklist for Hackathon Submitter
- [ ] Push repository to public GitHub.
- [ ] Add public GitHub repository URL to form.
- [ ] Record 2-3 minute demo video showing:
  - Running `scripts/verify_tasks.py` and `scripts/run_eval.py`
  - Exploring Streamlit leaderboard and episode replayer
  - Inspecting exported `dataset/agentgym_sft.jsonl` and `dataset/agentgym_dpo.jsonl`
- [ ] Paste Demo Video URL into form.
- [ ] Submit form on Hackathon platform before deadline.
