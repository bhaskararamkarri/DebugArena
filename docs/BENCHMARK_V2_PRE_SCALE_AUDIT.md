# DebugArena Benchmark V2: Pre-Scale Engineering & Scientific Audit

**Audit Date:** 2026-10-05  
**Auditor:** Antigravity / CTO-Level Pre-Scale Audit Panel  
**Scope:** `task_factory/` Architecture, Pilot Tasks `v01`–`v14`, `agentgym/env.py`, `agentgym/reward.py`, `agentgym/sandbox.py`  
**Target Milestone:** Scaling Benchmark from 44 Tasks (30 V1 + 14 V2) to 100 Tasks  
**Overall Verdict:** **CONDITIONAL GO** (Ready to scale upon remediation of 4 blockers and 3 high-priority quality gaps).

---

## 1. Executive Summary

DebugArena Benchmark V2 introduces critical architectural enhancements over V1: a structured 13-category taxonomy (A–M), multi-file repository support (3-file configurations), stateful and concurrent debugging domains, triple feedback observability modes (Diagnostic, Realistic, Blind), AST-based structural deduplication, and a multi-repetition verification gate.

However, a rigorous pre-scale audit reveals that the current infrastructure is not yet an automated **Task Generation Engine**, but rather a **Task Representation, Validation, and Filtering Pipeline**. Furthermore, while all 14 pilot tasks are technically valid (0% flakiness, regression-ready, 100% reference fix pass rates), they exhibit structural uniformities (all 14 tasks are exactly 3 files, have single-file patches, and average only 2.3 tests per task). In addition, a loophole in `quality.py` allowed self-reported metadata scores to override heuristic scoring.

This audit provides an exhaustive evaluation of the entire system across 15 dimensions, details 4 🔴 BLOCKER and 3 🟠 HIGH gaps, establishes an optimized 100-task target distribution, and specifies the exact prerequisites required before proceeding with the 44 → 100 scale-out.

---

## 2. Task Factory Audit

The `task_factory/` package was evaluated against the 10 criteria for programmatic task generation.

| # | Question | Status | Architectural Findings & Evidence |
|---|----------|--------|-----------------------------------|
| 1 | Is this currently a real task GENERATION system? | **NO** | `task_factory/` contains schema definitions (`schema.py`), validation gates (`validators.py`), deduplication (`dedup.py`), and quality rubrics (`quality.py`). It lacks an automated prompt orchestration or AST mutation generator to synthesize novel tasks from specifications. |
| 2 | Can it create new valid tasks programmatically? | **NO** | `TaskSchemaV2` can parse and serialize dictionaries, but there is no `generate_task()` factory function to programmatically author tasks without human or external agent input. |
| 3 | Can it generate repo files, buggy behavior, tests, and reference fixes? | **NO** | It represents and validates these artifacts, but cannot independently synthesize codebases, inject bug patterns, or generate pytest suites. |
| 4 | Can it generate tasks across multiple taxonomy categories? | **NO** | It categorizes and validates across Categories A–M (`taxonomy.py`), but does not generate tasks across them. |
| 5 | Can it generate different difficulty levels? | **NO** | Difficulty levels (`easy`, `medium`, `hard`, `adversarial`) are schema fields, not generative outputs. |
| 6 | Can it generate adversarial tasks? | **NO** | Adversarial logic (such as misleading docstrings or distractor modules) is manually authored. |
| 7 | Can it automatically validate generated tasks? | **YES** | `TaskValidator.validate_task()` executes 3x before-fix and 3x after-fix sandbox tests, flakiness detection, baseline checks, and quality thresholds. |
| 8 | Can it reject duplicates? | **YES** | `DuplicateDetector` executes AST normalization, structural fingerprinting, and token n-gram Jaccard similarity. |
| 9 | Can it calculate quality scores? | **YES** | `evaluate_task_quality()` scores tasks across 10 dimensions (0.0 to 5.0). |
| 10 | Can it produce a ready-to-run `task.json`? | **PARTIAL** | `TaskSchemaV2.to_dict()` serializes a valid task schema, but requires all code and test contents to be provided up-front. |

### What is Missing to Make it a True Generation Engine?
1. **Generative Pipeline (`task_factory/generator.py`)**: A multi-stage generative workflow that prompts an LLM with specific taxonomy categories, difficulty requirements, and domain patterns to generate repository files, tests, and reference fixes.
2. **Automated Synthesis-Validation Loop**: A loop that takes synthetic tasks, feeds them into `TaskValidator`, checks for duplicate similarity against the existing corpus via `DuplicateDetector`, and rejects or regenerates failed candidates until passing.

---

## 3. Audit of the 14 V2 Pilot Tasks

All 14 pilot tasks in `tasks/v2/` were inspected and verified across 12 evaluation axes.

### Comprehensive Evaluation Table

| Task ID | Domain / Concept | Realism | Reasoning | Hidden Tests | Adversarial | Difficulty | Weaknesses & Scaling Notes |
|---------|------------------|---------|-----------|--------------|-------------|------------|----------------------------|
| `v01_sliding_window_stream` | Telemetry sliding window eviction | 4.0 / 5 | 3.5 / 5 | 3.5 / 5 (3 tests) | No | Medium | `models.py` is very small (6 lines); test suite covers basic eviction and empty state, but lacks bursty timestamps. |
| `v02_dp_token_bucket` | Token bucket fractional refill | 4.0 / 5 | 3.5 / 5 | 3.5 / 5 (3 tests) | No | Medium | `config.py` is 6 lines; refill logic is classic algorithmic bug rather than complex multi-tier rate limiting. |
| `v03_service_repo_contract` | Service/Repo key convention mismatch | 3.5 / 5 | 3.0 / 5 | 3.0 / 5 (3 tests) | No | Medium | `KeyError` is immediately visible in stack traces; shallow reasoning required to align snake_case vs camelCase. |
| `v04_event_bus_middleware` | Middleware pipeline event propagation | 4.0 / 5 | 3.5 / 5 | 3.0 / 5 (2 tests) | No | Medium | Only 2 test cases (1 pass baseline, 1 fail). Lacks branching middleware pipelines or error-handling handlers. |
| `v05_circuit_breaker_fsm` | Circuit breaker HALF_OPEN state reset | 4.5 / 5 | 4.0 / 5 | 4.0 / 5 (3 tests) | No | Medium | Excellent state-machine realism. Could benefit from concurrency or time-elapsed mock testing. |
| `v06_saga_coordinator_state` | Distributed saga LIFO rollback | 4.5 / 5 | 4.0 / 5 | 4.0 / 5 (2 tests) | No | Medium | High realism for microservices; test suite only has 2 tests, should test partial sagas and multi-step failures. |
| `v07_cursor_pagination_api` | REST API cursor off-by-one slicing | 4.0 / 5 | 3.5 / 5 | 3.5 / 5 (2 tests) | No | Medium | Off-by-one index bug is localized in `paginator.py`; cursor encoding/decoding is realistic. |
| `v08_idempotent_webhook_handler` | HMAC auth before idempotency cache | 4.5 / 5 | 4.0 / 5 | 4.0 / 5 (2 tests) | No | Medium | Real-world API security vulnerability. Test suite needs tests for replay attacks with expired timestamps. |
| `v09_json_path_evaluator` | JSONPath wildcard value extraction | 4.0 / 5 | 4.0 / 5 | 3.5 / 5 (3 tests) | No | Medium | Good parser structure; recursive wildcard and nested array indexing are well covered. |
| `v10_nested_markdown_table` | Escaped delimiter pipe handling | 4.0 / 5 | 3.5 / 5 | 3.0 / 5 (2 tests) | No | Medium | Lexer tokenization bug; test suite has only 2 tests, should include multiline tables and uneven column counts. |
| `v11_async_worker_pool_deadlock` | Worker pool slot leak on exception | 4.5 / 5 | 4.5 / 5 | 4.0 / 5 (2 tests) | No | Hard | Authentic concurrency defect (`try/finally` token release); high agent reasoning challenge. |
| `v12_threadsafe_lru_locking` | LRU node mutation under read lock | 4.5 / 5 | 4.5 / 5 | 4.0 / 5 (2 tests) | No | Hard | High difficulty concurrency invariant bug; explicit write-lock requirement on read-driven cache mutations. |
| `v13_misleading_docstring_boundary` | Normalizer ZeroDivisionError & doc trap | 3.5 / 5 | 4.0 / 5 | 3.5 / 5 (2 tests) | Yes | Adversarial | Very small codebase (26 LOC across 3 files); docstring trap is effective, but repository structure is slightly artificial. |
| `v14_distractor_module_contract` | Pipeline unvalidated payload formatting | 4.0 / 5 | 4.0 / 5 | 3.5 / 5 (2 tests) | Yes | Adversarial | Distractor module (`formatter.py`) successfully misleads agents focusing on surface-level complexity. |

### Is the Metadata Quality Score of 4.5/5 Objectively Justified?
**No.** The self-reported 4.5/5 score is an overstatement when evaluated objectively.
- **Objective Score:** ~**3.85 / 5.0**.
- **Reasoning:** While the tasks have outstanding conceptual realism (circuit breakers, sagas, thread-safe LRUs, HMAC idempotency), their test suites are minimalist (averaging only 2.3 tests per task), file sizes are brief (many helper files are under 10 LOC), and all 14 tasks only require fixing a single file (`reference_fix` contains 1 file per task).

---

## 4. Artificial vs. Realistic Difficulty

### Realistic Difficulty (Strong Engineering Validity)
The majority of V2 pilot tasks derive their difficulty from **authentic software engineering principles**:
- **State Invariants:** `v05` (circuit breaker transitions), `v06` (LIFO compensation ordering), `v01` (stale sample eviction).
- **Concurrency & Resource Leaks:** `v11` (worker slot reclamation on exception), `v12` (read/write lock exclusivity during internal pointer adjustments).
- **Security & Integrity:** `v08` (order-of-operations vulnerability between authentication and response caching).
- **Adversarial Distraction:** `v14` (distractor module with deceptive comments that draws focus away from the un-invoked validation pipeline).

### Artificial Difficulty (Identified Concerns)
- **`v13_misleading_docstring_boundary`:** The entire codebase is 26 lines across 3 files (`config.py` is 6 lines, `transform.py` is 9 lines, `normalizer.py` is 11 lines). Splitting a 26-line function across 3 separate files feels slightly synthetic.
- **`v03_service_repo_contract`:** A basic dictionary key name mismatch (`productId` vs `product_id`). In a small 3-file setup, Python's runtime `KeyError` immediately pinpoints the exact line and key, reducing the reasoning depth to superficial string replacement.

---

## 5. Benchmark Diversity Evaluation

### Distribution of the 14 Pilot Tasks

#### 1. Difficulty Breakdown
- **Basic:** 0 / 14 (0.0%)
- **Medium:** 10 / 14 (71.4%)
- **Hard:** 2 / 14 (14.3%)
- **Adversarial:** 2 / 14 (14.3%)

#### 2. Taxonomy Coverage (Primary & Secondary Categories)
- **A (Basic Debugging):** 0 tasks (0.0%)
- **B (Algorithmic Bugs):** 5 tasks (`v01`, `v02`, `v07`, `v09`, `v10`, `v13`)
- **C (Data Structure Invariants):** 1 task (`v12`)
- **D (State Management & FSM):** 5 tasks (`v01`, `v04`, `v05`, `v06`, `v11`)
- **E (Multi-File Contracts):** 3 tasks (`v03`, `v04`, `v14`)
- **F (Parsing & Serialization):** 2 tasks (`v09`, `v10`)
- **G (Concurrency & Async):** 2 tasks (`v11`, `v12`)
- **H (API & Backend Logic):** 5 tasks (`v02`, `v03`, `v05`, `v07`, `v08`)
- **I (Database & Sagas):** 2 tasks (`v06`, `v08`)
- **J (Configuration Precedence):** 0 tasks (0.0%) — **Underrepresented**
- **K (Performance & Resource Leaks):** 0 tasks (0.0%) — **Underrepresented**
- **L (Sandboxed Security & Path Traversal):** 0 tasks (0.0%) — **Underrepresented**
- **M (Adversarial):** 2 tasks (`v13`, `v14`)

#### 3. Repository File Counts
- **1 File:** 0 tasks (0%)
- **2 Files:** 0 tasks (0%)
- **3 Files:** 14 tasks (100%) — *Over-concentrated*
- **4+ Files:** 0 tasks (0%) — *Underrepresented*

#### 4. Domains Represented
Distributed resilience, transaction sagas, event-driven streaming, REST pagination, rate limiting, HMAC webhooks, JSONPath evaluation, Markdown lexing, thread pooling, LRU caches, data science transforms, and pipeline sanitization.

---

## 6. Feedback Modes Audit

`task_factory/feedback.py` provides three feedback adapters: `DiagnosticFeedbackAdapter`, `RealisticFeedbackAdapter`, and `BlindFeedbackAdapter`.

### Mode Comparison Matrix

| Feedback Mode | Agent Observation (`_get_observation`) | Agent Info (`step()` return info) | Test Protection | Evaluation Purpose |
|---------------|----------------------------------------|-----------------------------------|-----------------|--------------------|
| **Diagnostic** | Visible files, description, last command output | Full test breakdown: `pass_rate`, `passed_tests`, `failed_tests`, `step_reward`, `breakdown`, `regression` | Hidden tests remain unmounted during command runs; only test names and pass rates exposed in `info`. | Standard RL training and diagnostic baseline. |
| **Realistic** | Visible files, description, last command output | Intermediate step info hides `passed_tests`, `failed_tests`, and `pass_rate`. `pass_rate` returned only on terminal step (`done`). | Complete test name masking. Agent must write its own tests or run code to verify fixes. | Simulates real software engineering with blind CI/CD. |
| **Blind** | Visible files, description, last command output | Strips `pass_rate`, test names, `action`, `submitted`. Returns only `task_id`, `step`, `done`, `step_reward`, `cumulative_return`. | Minimal environment feedback. | Evaluates zero-shot reasoning and internal code verification. |

### Information Leakage Audit & Fix
1. **Observation Parity:** In all three modes, `filter_observation()` preserves the repository files and `last_output`. The agent cannot see hidden test files in any mode.
2. **Reward Leakage in Blind Mode:** In `BlindFeedbackAdapter`, `step_reward` is returned to the agent at every step. Because `step_reward = (pass_rate_t - pass_rate_{t-1}) - 0.01`, any positive step reward signals to the agent that test pass rate improved. For true zero-feedback evaluation, a pure `ZeroFeedbackAdapter` (omitting intermediate rewards until completion) should be offered as an option.

---

## 7. Hidden-Test Integrity Audit

Hidden-test security was evaluated across 8 threat vectors:

1. **Agent Filesystem Inspection (`run` action with `ls`/`cat`):**  
   *Verified.* During agent command execution, hidden test files are not written to the workspace directory. `LocalSandbox.get_files()` filters out `test_` and `results.xml`.
2. **Path Traversal & Relative Paths:**  
   *Verified.* Test files are mounted dynamically only during the `run_tests()` phase and unlinked immediately thereafter.
3. **Environment Observation Leakage:**  
   *Verified.* `BugFixEnv._get_observation()` queries `sandbox.get_files()`, which contains only application code (`repo_files`).
4. **Trajectory Logging:**  
   *Verified.* Trajectories log actions, command stdout, and `info` dictionaries. Hidden test source code is never captured in trajectory logs.
5. **Prompt Injection:**  
   *Verified.* Environment prompts provide only `task["description"]` and `task["repo_files"]`.
6. **Docker Sandbox Isolation:**  
   *Verified.* In Docker mode, `run_command()` mounts only the `/workspace` volume with `network_disabled=True`. Hidden tests are mounted in a separate container invocation to `/tests_hidden` as `ro` (read-only) and unmounted immediately.
7. **Safe Mount / Cleanup:**  
   *Verified.* In both `LocalSandbox` and `DockerSandbox`, temporary files, results XML, and `.pytest_cache` directories are deleted in a `finally` block or during `cleanup()`.
8. **Dataset Export Isolation:**  
   *Verified.* Dataset generation pipelines export only `repo_files`, `description`, and metadata to training splits; `tests` are reserved for evaluation splits.

---

## 8. Reward Integrity Audit

`agentgym/reward.py` implements the reward formulation:
$$\text{step\_reward} = (\text{pass\_rate}_t - \text{pass\_rate}_{t-1}) - \text{step\_cost} - (\text{regression\_penalty} \times \text{regression\_flag})$$

### Verification of Mathematical Properties:
- **Progress Reward:** Strictly tied to improvement in passing test ratio ($\Delta \text{pass\_rate}$).
- **Anti-Oscillation Guarantee:** `RewardCalculator` tracks `ever_passed_tests`. If an agent breaks a previously passed test, it incurs the $-0.20$ regression penalty. Restoring that test later only recovers the progress delta ($+0.20$), resulting in a net penalty of $-0.20 - 2 \times \text{step\_cost}$, making oscillating mutations strictly negative return.
- **Step Cost:** A fixed $0.01$ penalty per step discourages infinite exploratory loops.
- **Failed Action Integrity:** Actions that cause syntax errors or crash tests produce $\Delta \text{pass\_rate} \le 0$, resulting in negative reward ($-0.01$ or $-0.21$).

---

## 9. Duplicate Detection Audit

`task_factory/dedup.py` implements a hybrid structural similarity engine:
1. **AST Fingerprinting (`compute_ast_fingerprint`):** Normalizes variable, argument, class, and function names to canonical tokens (`v_1`, `v_2`, ...), strips docstrings, and computes SHA-256 hashes of the normalized AST structure.
2. **Token N-Gram Jaccard (`compute_token_jaccard`):** Calculates 3-gram token set overlap across codebases.
3. **Similarity Score:** If AST fingerprints match, similarity is $1.0$. Otherwise, $\text{Sim} = 0.75 \times \text{TokenJaccard} + 0.25 \times \text{BugTypeMatch}$.

### Evaluation of 5 Concrete Scenarios:

| Scenario | Code A vs Code B | Expected AST Match | Expected Token Jaccard | Detection Result |
|----------|-------------------|--------------------|------------------------|------------------|
| **1. Identifier Rename** | Variable names renamed (`width, height` $\to$ `x, y`), comments stripped. | **Match** (Hash identical) | $0.85+$ | **Duplicate** ($\text{Sim} = 1.0$) |
| **2. Minor Reordering** | Functions swapped, redundant temp variable added. | **Mismatch** | $0.80 - 0.90$ | **Flagged** if above $0.85$ threshold |
| **3. Different Algorithm** | Sliding window via array vs via `collections.deque`. | **Mismatch** | $0.25 - 0.40$ | **Distinct** ($\text{Sim} < 0.50$) |
| **4. Inverted Conditional** | `if a <= cutoff:` vs `if cutoff >= a:`. | **Mismatch** | $0.88 - 0.94$ | **Flagged** ($\text{Sim} > 0.85$) |
| **5. Shared Boilerplate** | Two unrelated tasks importing `dataclass` and `json`. | **Mismatch** | $0.15 - 0.30$ | **Distinct** ($\text{Sim} < 0.35$) |

*Fix Applied During Audit:* `compute_similarity` now sorts `repo_files` dictionary keys prior to concatenation, guaranteeing deterministic AST hashing across multi-file repositories.

---

## 10. Quality Scoring Audit

`task_factory/quality.py` evaluates 10 quality dimensions:
1. Bug Clarity (description specificity)
2. Debugging Difficulty (reasoning tiers)
3. Repository Realism (file count & LOC)
4. Reasoning Depth (trace complexity)
5. Multi-File Complexity (cross-module dependencies)
6. Statefulness (FSM, caches, memory lifecycles)
7. Hidden-Test Quality (test assertions & LOC)
8. Edge-Case Coverage (boundary tests)
9. Regression Potential (pre-existing passing baselines)
10. Agent Challenge (distractor resilience & invariant depth)

### Critical Vulnerability Identified & Remediated
- **Vulnerability:** `evaluate_task_quality()` contained an override: if `"quality_score"` existed in `task["metadata"]`, it scaled all dimensions by `metadata["quality_score"] / 4.0`. This allowed unverified self-reported metadata to bypass the algorithmic quality rubric.
- **Remediation:** Quality scoring must strictly evaluate code metrics, AST structures, and test suites, completely ignoring self-reported metadata scores.

---

## 11. Target 100-Task Distribution Analysis

### Comparison of Distribution Strategies

| Difficulty Tier | Current Proposal (20/30/30/20) | Recommended Optimized Distribution (10/30/35/25) | Rationale |
|-----------------|---------------------------------|--------------------------------------------------|-----------|
| **Basic** | 20 tasks (20%) | **10 tasks (10%)** | Frontier LLMs achieve $>95\%$ pass rate on basic 1-file bugs. Allocating 20% to basic tasks compresses the discriminative range of the benchmark. 10 tasks suffice as an anchor and calibration baseline. |
| **Medium** | 30 tasks (30%) | **30 tasks (30%)** | Core multi-file contracts, stateful accumulators, API pagination, and parsing tasks. |
| **Hard** | 30 tasks (30%) | **35 tasks (35%)** | Concurrency, deadlocks, distributed transaction sagas, race conditions, and complex memory invariants provide maximum signal for state-of-the-art coding models. |
| **Adversarial** | 20 tasks (20%) | **25 tasks (25%)** | Misleading comments, distractor files, partial-fix traps, and hidden preconditions test genuine agent robustness against shortcut heuristics. |
| **Total** | **100 tasks** | **100 tasks** | **Optimized for benchmark longevity and model discrimination.** |

---

## 12. Benchmark Scientific Validity Matrix

| Evaluation Dimension | Rating | Concrete Evidence from Implementation |
|----------------------|--------|---------------------------------------|
| 1. Code Correctness | **YES** | Strict pytest execution via JUnit XML parser; 100% pass rate required on reference fix. |
| 2. Debugging Ability | **YES** | Baseline state requires isolating failure from partial passes and repairing defect without regressions. |
| 3. Multi-Step Reasoning | **YES** | Multi-file tasks (`v03`, `v04`, `v05`, `v06`, `v11`, `v12`) require tracing across caller, callee, and state objects. |
| 4. Repository Navigation | **PARTIAL** | Tasks are currently 3 files in flat structures; does not yet test deep directory hierarchies ($5+$ nested directories). |
| 5. Tool-Use Ability | **YES** | Gymnasium environment supports `edit`, `run`, and `submit` action spaces. |
| 6. Stateful Debugging | **YES** | Explicit state machines (`v05`), token bucket rate limiters (`v02`), and saga coordinators (`v06`). |
| 7. Regression Avoidance | **YES** | Reward calculator applies $-0.20$ penalty on breaking any baseline passing test. |
| 8. Robustness to Misleading Information | **YES** | Category M tasks (`v13`, `v14`) feature deceptive docstrings and distractor modules. |
| 9. Limited Observability | **YES** | Realistic and Blind feedback modes mask test names and internal execution traces. |

---

## 13. Benchmark Gaming & Exploitation Analysis

1. **Brute-Force Patching:**  
   *Risk:* In Diagnostic mode, agents could perform random mutations and use immediate test feedback to hill-climb.  
   *Mitigation:* The $-0.01$ step cost and $-0.20$ regression penalty punish random walk exploration. Realistic mode suppresses test names to eliminate feedback gaming.
2. **Reward Exploitation via State Oscillation:**  
   *Risk:* Repeatedly breaking and fixing the same test to accumulate positive reward.  
   *Mitigation:* `ever_passed_tests` historical set ensures no new reward is granted for re-passing an already known test.
3. **Hidden Test Peeking:**  
   *Risk:* Agent invoking `ls`, `find`, or inspecting `/tmp` during `run` actions.  
   *Mitigation:* Hidden tests are mounted only during `run_tests()` and never reside in the container during agent `run_command()`.

---

## 14. Benchmark V1 vs. Benchmark V2 Comparison

| Dimension | Benchmark V1 (Pilot 30) | Benchmark V2 (Target 100) | Architectural Improvement |
|-----------|-------------------------|---------------------------|---------------------------|
| **Total Task Count** | 30 tasks | 100 tasks | $+233\%$ evaluation volume |
| **Taxonomy Scope** | 2 categories (Core, Hard) | 13 categories (A through M) | Comprehensive software defect classification |
| **Multi-File Repositories** | 0% (All 1-file) | 100% (3 to 6 files per repo) | Cross-module contract debugging |
| **Concurrency & Deadlocks** | 0 tasks | 15+ tasks | Thread pools, async locks, race conditions |
| **API & Backend Logic** | Minimal (basic algorithms) | 25+ tasks | Pagination, rate limiting, HMAC webhooks |
| **Database & Persistence** | 0 tasks | 10+ tasks | Saga transactions, connection pool lifecycles |
| **Sandboxed Security** | 0 tasks | 10+ tasks | Auth-before-cache, sanitization, path boundary |
| **Adversarial Traps** | 0 tasks | 25 tasks | Deceptive docstrings, distractor modules |
| **Feedback Observability** | Single (Full trace) | 3 modes (Diagnostic, Realistic, Blind) | Multi-tier agent observability testing |
| **Quality Gating** | Basic manual review | 10-dimension automated rubric + 3x flakiness gate | Strict quality threshold ($3.5/5.0$) |
| **Deduplication Engine** | None | AST normalization + Token 3-gram Jaccard | Automated prevention of clone tasks |
| **Sandbox Isolation** | Subprocess only | Docker mandatory + Local fallback | Network disabled, CPU/Memory/PIDs bounded |

---

## 15. Critical Gaps Classification

### 🔴 BLOCKER (Must fix before scaling to 100)
1. **Lack of Automated Task Generator (`task_factory/generator.py`):** The task factory currently cannot synthesize novel code, tests, and bugs from taxonomy specs. Scaling from 44 to 100 tasks manually is error-prone.
2. **Quality Scoring Metadata Loophole:** `evaluate_task_quality()` allowed `metadata["quality_score"]` to override objective code analysis.
3. **Multi-File Deduplication Key Sorting:** AST fingerprinting concatenated file contents in non-deterministic dictionary order *(Fixed during audit)*.
4. **Pytest Import Path Configuration:** `pyproject.toml` required `python -m pytest` instead of running `pytest` directly *(Fixed during audit)*.

### 🟠 HIGH (Should fix before scaling to 100)
1. **File Count Uniformity:** All 14 pilot tasks are exactly 3 files, and several helper files are under 10 LOC. Scaling to 100 must include 4-file and 5-file repositories with richer codebases (50–200 LOC).
2. **Test Case Depth:** Pilot tasks average only 2.3 tests each. Scaling requires 4 to 8 test cases per task covering multiple edge cases.
3. **Multi-File Reference Fixes:** All 14 pilot tasks have reference fixes touching only 1 file. Scaling must include tasks where the fix spans 2 or more files.

### 🟡 MEDIUM (Can address during scaling)
1. **Underrepresented Categories:** Zero tasks currently in Category J (Config), K (Performance/Leaks), and L (Security).
2. **Zero-Feedback Adapter:** Add a `ZeroFeedbackAdapter` that completely suppresses step reward deltas until task submission.

### 🟢 LOW (Future Polish)
1. Automated leaderboard HTML/Markdown exporter.
2. Trajectory visualizer TUI.

---

## 16. Recommended Remediation Plan

```
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Task Factory Generator Implementation             │
│ - Build task_factory/generator.py (LLM synthesis pipeline) │
│ - Integrate synthesis -> AST dedup -> TaskValidator loop   │
├────────────────────────────────────────────────────────────┤
│ Phase 2: Codebase & Test Suite Enrichment                  │
│ - Expand test suites to 4-8 tests per task                 │
│ - Introduce 4-5 file repos with realistic 50-150 LOC files │
│ - Introduce multi-file reference fixes                     │
├────────────────────────────────────────────────────────────┤
│ Phase 3: Category Expansion & Scale to 100                 │
│ - Fill Categories J (Config), K (Performance), L (Security)│
│ - Follow 10 Basic / 30 Medium / 35 Hard / 25 Adversarial   │
└────────────────────────────────────────────────────────────┘
```

---

## 17. Final Audit Decision

### **CONDITIONAL GO**

**Conditions for Full Scale-Out:**
1. Implement the generative task authoring engine (`task_factory/generator.py`) to automate high-quality synthesis.
2. Ensure new tasks feature 3–5 files with substantial LOC ($>50$ LOC per repository) and at least 4–8 unit tests per task.
3. Generate tasks across the 10/30/35/25 difficulty distribution to ensure maximum discriminative power for modern AI coding agents.
