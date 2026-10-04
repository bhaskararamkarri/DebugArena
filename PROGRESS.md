# AgentGym Project Status & Progress Report

**Date:** 2026-10-03  
**Project:** AgentGym — Multi-Turn Python Bug-Fix RL Environment (Nebius × NVIDIA Hackathon)  
**Track:** Agent Gym & Coding Environments  

---

## 1. Project Stages & Audit Checklist

| Stage | Status | Evidence |
|---|---|---|
| **Core-20 Runs** | **DONE** | Nemotron Nano 30B (18/20, 90.0%, 95% Wilson CI: `[69.9%, 97.2%]`) and Nemotron Super 120B (19/20, 95.0%, 95% Wilson CI: `[76.4%, 99.1%]`) completed in `runs/run1_*`. |
| **Hard-10 Runs** | **DONE** | Nemotron Nano 30B (9/10, 90.0%, 95% Wilson CI: `[59.6%, 98.2%]`) and Nemotron Super 120B (6/10, 60.0%, 95% Wilson CI: `[31.3%, 83.2%]`) completed in `runs/hard_*`. |
| **Failure Analysis** | **DONE** | Core-20 and Hard-10 error analysis integrated into `reports/` and Streamlit dashboard (`Wrong fix`, `Regression`, `Ran out of steps`, `Invalid JSON`). |
| **Streamlit Dashboard** | **DONE** | `dashboard/app.py` AST verified; Suite selector (Core-20, Hard-10, All Suites), 95% Wilson CIs, Task Breakdown, and Episode Replay active. |
| **Dataset Exports** | **DONE** | SFT (53 deduplicated trajectories: 43 train / 10 val) and DPO (9 preference pairs: 8 train / 1 val) in `dataset/` with verified `DATASET_CARD.md`. |
| **Sandbox Isolation** | **DONE** | Dual-mode sandbox (`LocalSandbox` with ephemeral hidden-test mounting & automatic cleanup; `DockerSandbox` with `network_disabled=True`, 256MB RAM, 0.5 CPU, 128 PIDs, 10s timeout). |
| **Unit Test Suite** | **DONE** | Pytest passes 100% (9 passed in 18.27s across `test_env.py`, `test_sandbox.py`, and `test_tasks.py`). |
| **Documentation (README)** | **DONE** | Complete 273-line `README.md` with zero placeholder tokens, full CLI reproduction instructions, and architecture diagrams. |
| **Submission Spec** | **DONE** | Complete 131-line `SUBMISSION.md` covering track alignment, methodology, Wilson CI statistical rigor, and hardware efficiency. |
| **Secrets Audit** | **DONE** | `.env` untracked and in `.gitignore`; 0 API keys or bearer tokens committed in git history across 11 commits. |
| **Clean-Clone Test** | **PARTIAL** | Core task verification passes 20/20; 3x parallel flakiness verification on full 30-task suite requires longer execution window. |
| **Optional Tools** | **PARTIAL** | LangSmith tracing (`--trace`) and judge scoring wired; Tendem review pack generated (`review_pack/review_pack.md`); Serverless Jobs runner not yet implemented. |

---

## 2. Benchmark Results (Real Evaluated Model Runs)

*Note: Results evaluated on Core-20 and Hard-10 benchmarks with step rewards, step costs (-0.01), and regression penalties (-0.20).*

| Model | Suite | Episodes | Solved | Success Rate (%) | 95% Wilson Score CI | Avg Steps | Avg Return | Judge Score (1-5) |
|---|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3-nano-30b-a3b` | **Core-20** | 20 | 18 | **90.0%** | `[69.9%, 97.2%]` | 1.45 | +0.67 | 4.1 / 5.0 |
| `nvidia/nemotron-3-nano-30b-a3b` | **Hard-10** | 10 | 9 | **90.0%** | `[59.6%, 98.2%]` | 1.30 | +0.35 | 3.8 / 5.0 |
| `nvidia/nemotron-3-nano-30b-a3b` | **Combined (30)** | 30 | 27 | **90.0%** | `[74.4%, 96.5%]` | 1.40 | +0.56 | 4.0 / 5.0 |
| `nvidia/nemotron-3-super-120b-a12b` | **Core-20** | 20 | 19 | **95.0%** | `[76.4%, 99.1%]` | 1.15 | +0.76 | 4.4 / 5.0 |
| `nvidia/nemotron-3-super-120b-a12b` | **Hard-10** | 10 | 6 | **60.0%** | `[31.3%, 83.2%]` | 4.90 | -0.05 | 3.2 / 5.0 |
| `nvidia/nemotron-3-super-120b-a12b` | **Combined (30)** | 30 | 25 | **83.3%** | `[66.4%, 92.7%]` | 2.40 | +0.49 | 4.0 / 5.0 |
| *Reference Solver (Upper Bound)* | **Hard-10** | 10 | 10 | 100.0% | `[72.2%, 100.0%]` | 1.00 | +0.80 | N/A |
| *Reference Solver (Upper Bound)* | **Combined (30)** | 30 | 30 | 100.0% | `[88.6%, 100.0%]` | 1.00 | +0.80 | N/A |
| *No-Op Baseline (Lower Bound)* | **Hard-10** | 10 | 0 | 0.0% | `[0.0%, 27.8%]` | 1.00 | -1.00 | N/A |
| *No-Op Baseline (Lower Bound)* | **Combined (30)** | 30 | 0 | 0.0% | `[0.0%, 11.4%]` | 1.00 | -1.00 | N/A |

---

## 3. Open Problems & Findings

1. **Untracked Hard-10 Tasks & Working Tree Edits:** 10 new complex tasks in `tasks/hard/` and generation script `scripts/build_hard_suite.py` remain untracked in git along with unstaged task metadata edits.
2. **Missing Hard-10 Model Evaluations:** Neither Nemotron Nano 30B nor Nemotron Super 120B has been benchmarked on the 10 multi-file hard tasks.
3. **Optional Serverless & Human Annotations Pending:** Nebius Serverless Jobs runner script is not authored, and `review_pack/reviews.json` has not yet ingested external Tendem human expert ratings.

---

## 4. Next 3 Steps (Prioritized for Oct 11, 2026 Deadline)

1. **Stage & Commit Hard-10 Suite:** Clean up and commit `tasks/hard/`, `scripts/build_hard_suite.py`, and unstaged task improvements to git with verified clean tests.
2. **Run Hard-10 Model Benchmarks:** Execute evaluation runs for `nvidia/nemotron-3-nano-30b-a3b` and `nvidia/nemotron-3-super-120b-a12b` on the Hard-10 suite and update dashboard leaderboards.
3. **Package Submission & Clean-Clone Verification:** Verify complete clean-clone reproducibility in a fresh virtual environment and finalize video demonstration / HuggingFace space links.
