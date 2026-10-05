# DebugArena: Task Authoring & Quality Rubric Guide

This guide details the end-to-end authoring, review, and quality validation process for Benchmark V2 tasks.

---

## 1. Formal 10-Dimension Quality Rubric (0–5 Scale)

Every Benchmark V2 task is evaluated across 10 scoring dimensions:

| Dimension | Description | Target Standard |
|---|---|---|
| **1. Bug Clarity (0–5)** | The bug symptoms and observed failure mode are unambiguous in the issue description. | Score ≥ 4.0 |
| **2. Debugging Difficulty (0–5)** | Difficulty stems from genuine reasoning and state tracking, not artificial code obfuscation. | Score ≥ 3.5 (Med/Hard) |
| **3. Repository Realism (0–5)** | Clean multi-file modular architecture (e.g. models, services, repositories). | Score ≥ 4.0 |
| **4. Reasoning Depth (0–5)** | Requires tracing dataflow across at least 2–3 functions or classes. | Score ≥ 3.5 |
| **5. Multi-File Complexity (0–5)** | Cross-module interface contracts or serialization boundaries. | Score ≥ 3.0 |
| **6. Statefulness (0–5)** | Mutating state, lifecycle transitions, caching, or event dispatching. | Score ≥ 3.0 |
| **7. Hidden-Test Quality (0–5)** | Asserts black-box behavioral correctness, not specific variable names or internal styles. | Score ≥ 4.5 |
| **8. Edge-Case Coverage (0–5)** | Comprehensive coverage: empty inputs, single elements, boundary values, invalid types. | Score ≥ 4.0 |
| **9. Regression Potential (0–5)** | Includes tests that pass initially and catch naive/incomplete patches. | Score ≥ 4.0 |
| **10. Agent Challenge (0–5)** | Poses a genuine challenge to frontier reasoning models while remaining deterministic. | Score ≥ 3.5 |

**Composite Quality Threshold**: To qualify for the official Benchmark V2 suite, a candidate task must achieve a **total composite score ≥ 35 / 50 (Average ≥ 3.5/5.0)**.

---

## 2. Test Design Standards

### 2.1 Behavioral Verification (Black-Box Assertions)
- Tests must verify observable behavior, contract conformance, and return values.
- **Anti-Pattern**: Testing for specific private helper functions (e.g., `assert task._my_private_helper() == 1`).
- **Good Pattern**: Testing the public interface and contract invariance (e.g., `assert accumulator.get_window_total() == expected_sum`).

### 2.2 Baseline Partial Failure Contract
- **Before Fix**: At least **1 test must PASS** (establishing the baseline contract) and at least **1 test must FAIL** (detecting the active defect).
- **After Reference Fix**: **100% of tests must PASS**.

### 2.3 3x Determinism & Isolation
- Concurrency or async tasks must use deterministic coordination (locks, condition variables, latches, or mocked clock ticks) rather than arbitrary `time.sleep()` race windows.
- Hidden tests must never write to visible repository files or leak test fixtures into agent workspace commands.

---

## 3. Adversarial Task Construction

Adversarial tasks (Category M) evaluate whether an agent blindly follows comments or truly verifies code logic:

1. **Misleading Docstring**: An internal function docstring suggests an outdated algorithm, while the top-level specification and behavioral test require the correct standard.
2. **Distractor Module**: A realistic repository contains multiple helper files (e.g. `logger.py`, `formatter.py`). An agent must locate the real source of failure in `pipeline.py` without breaking other modules.
3. **Partial-Fix Trap**: A naive fix solves the basic test case but causes a regression on an edge-case test that previously passed.
