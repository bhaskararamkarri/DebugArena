# Benchmark V2 & Task Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve DebugArena into a rigorous, extensible Benchmark V2 system with a formal taxonomy (Categories A–M), quality scoring rubric, duplicate detection engine, validation gates, feedback mode adapters, comprehensive documentation, and a verified 14-task V2 pilot suite across all target domains without breaking existing V1 tasks or evaluation infrastructure.

**Architecture:** 
- Spec-first documentation suite (`docs/BENCHMARK_V2_AUDIT.md`, `docs/BENCHMARK_V2.md`, `docs/TASK_TAXONOMY.md`, `docs/TASK_AUTHORING_GUIDE.md`).
- Modular Python `task_factory/` package containing taxonomy definitions, backwards-compatible V2 JSON schemas, 10-dimension quality scoring, AST/token deduplication analysis, feedback mode abstractions (`diagnostic`, `realistic`, `blind`), and multi-stage validation gates.
- Non-breaking integration into `agentgym/env.py` and `scripts/verify_tasks.py` supporting V1 and V2 tasks seamlessly.
- 14 high-quality Pilot V2 tasks (`tasks/v2/v01` through `v14`) covering algorithmic, multi-file, stateful, API/backend, parsing, async/concurrency, and adversarial domains.

**Tech Stack:** Python 3.10+, Pydantic/dataclasses, AST parser, pytest, PyYAML, Docker/Local Sandbox, Rich.

**Spec:** `docs/BENCHMARK_V2.md` and user prompt specifications.

## Global Constraints

- **Non-destructive**: All 30 existing tasks (`t01`–`t20`, `h01`–`h10`) must remain untouched and pass all tests and verification.
- **Backwards compatibility**: Default behavior of `BugFixEnv`, `RewardCalculator`, `verify_tasks.py`, `export_dataset.py`, and `dashboard` must be 100% preserved.
- **No external paid dependencies**: AST parsing, structural hashing, and similarity detection must run entirely local without external LLM API dependencies.
- **Strict verification**: All new tasks must pass baseline partial failure (1+ pass, 1+ fail) and 100% reference fix pass across 3x deterministic repetitions.
- **Zero false claims**: Documentation must explicitly clarify RL environment/trajectory generation capability vs. RL policy optimization (no claims of PPO/GRPO training).

## Review Focus

1. **V1 Task Schema Backward Compatibility**: Existing `t01`–`t20` and `h01`–`h10` lack V2 metadata (`categories`, `spec_notes`, `metadata`). The schema validator must accept both V1 and V2 tasks without runtime exceptions.
2. **Hidden Test Isolation**: V2 tasks with multi-file architectures must ensure hidden tests are strictly isolated from agent command inspection.
3. **AST Duplicate Detection Precision**: The deduplication engine must accurately flag structural copies while permitting genuinely different algorithmic implementations of similar concepts.
4. **Feedback Mode Fallbacks**: In `BugFixEnv`, non-diagnostic feedback modes (`realistic`, `blind`) must properly filter test metadata without breaking agent action processing or episode termination logic.
5. **Deterministic Sandbox Concurrency**: Concurrency/async tasks (`v11`, `v12`) must use deterministic thread/event loop synchronization to avoid flakiness across sandbox repetitions.

---

### Task 1: Complete Benchmark V2 Audit & Granular Scoring Report

**Files:**
- Create/Modify: `docs/BENCHMARK_V2_AUDIT.md`

- [ ] **Step 1: Write comprehensive task audit report with granular 1-5 scoring for all 30 existing tasks**
Includes scores for `bug_locality`, `multi_file_complexity`, `statefulness`, `algorithmic_complexity`, `realism`, `agent_challenge`, `adversarial_quality`, and `overall_quality`, categorizing each task into `BASIC`, `MEDIUM`, `HARD`, or `EXCELLENT`.
- [ ] **Step 2: Document gaps, upgrade roadmap, and suite distribution analysis**
Document missing categories (G, H, I, K, L, M), structural bimodality, and diversity recommendations.

---

### Task 2: Author Benchmark V2 Specification & Taxonomy Documentation

**Files:**
- Create: `docs/BENCHMARK_V2.md`
- Create: `docs/TASK_TAXONOMY.md`
- Create: `docs/TASK_AUTHORING_GUIDE.md`

- [ ] **Step 1: Author `docs/TASK_TAXONOMY.md`**
Define categories A through M (Basic, Algorithmic, Data Structure, State Management, Multi-File, Parsing, Concurrency, API/Backend, Database, Config, Performance, Security, Adversarial) with invariants, failure modes, and code examples.
- [ ] **Step 2: Author `docs/BENCHMARK_V2.md`**
Define V2 benchmark philosophy, 100-task distribution targets (20 Basic, 30 Medium, 30 Hard, 20 Adversarial), suite architecture, feedback mode contracts, and clear RL environment vs. RL training distinctions.
- [ ] **Step 3: Author `docs/TASK_AUTHORING_GUIDE.md`**
Provide end-to-end task authoring instructions, 10-dimension quality rubric, test design standards, hidden test isolation requirements, and anti-patterns to avoid.

---

### Task 3: Implement Task Factory Core (`taxonomy.py`, `schema.py`, `quality.py`)

**Files:**
- Create: `task_factory/__init__.py`
- Create: `task_factory/taxonomy.py`
- Create: `task_factory/schema.py`
- Create: `task_factory/quality.py`
- Test: `tests/test_task_factory.py`

- [ ] **Step 1: Write failing tests for schema validation, taxonomy enums, and quality rubric calculation**
- [ ] **Step 2: Implement `task_factory/taxonomy.py` and `task_factory/schema.py`**
Define `TaxonomyCategory`, `TaskDifficulty`, `TaskMetadata`, and backwards-compatible `TaskSchemaV2` with Pydantic/dataclass serialization.
- [ ] **Step 3: Implement `task_factory/quality.py`**
Implement 10-dimension scoring rubric calculation and validation functions.
- [ ] **Step 4: Run pytest to verify Task 3 tests pass**

---

### Task 4: Implement Task Deduplication & Validation Gates (`dedup.py`, `validators.py`, `feedback.py`)

**Files:**
- Create: `task_factory/dedup.py`
- Create: `task_factory/validators.py`
- Create: `task_factory/feedback.py`
- Modify: `agentgym/env.py` (add feedback mode adapter support)
- Test: `tests/test_task_factory.py`

- [ ] **Step 1: Write failing tests for AST deduplication, validation gates, and feedback adapters**
- [ ] **Step 2: Implement `task_factory/dedup.py`**
AST normalization, token n-gram similarity, and structural graph hashing to detect renamed duplicates.
- [ ] **Step 3: Implement `task_factory/validators.py`**
Full task validation pipeline: schema check, partial pass before fix, 100% pass after fix, 3x flakiness check, test leakage prevention, and complexity metrics.
- [ ] **Step 4: Implement `task_factory/feedback.py` and connect to `agentgym/env.py`**
Implement `DiagnosticFeedbackAdapter`, `RealisticFeedbackAdapter`, and `BlindFeedbackAdapter`.
- [ ] **Step 5: Run pytest to verify deduplication, validation, and feedback tests pass**

---

### Task 5: Create and Validate 14 Pilot Benchmark V2 Tasks (`v01`–`v14`)

**Files:**
- Create: `tasks/v2/v01_sliding_window_stream/task.json` (Category B: Algorithmic)
- Create: `tasks/v2/v02_dp_token_bucket/task.json` (Category B: Algorithmic)
- Create: `tasks/v2/v03_service_repo_contract/task.json` (Category E: Multi-File)
- Create: `tasks/v2/v04_event_bus_middleware/task.json` (Category E: Multi-File)
- Create: `tasks/v2/v05_circuit_breaker_fsm/task.json` (Category D: State Management)
- Create: `tasks/v2/v06_saga_coordinator_state/task.json` (Category D: State Management)
- Create: `tasks/v2/v07_cursor_pagination_api/task.json` (Category H: API / Backend)
- Create: `tasks/v2/v08_idempotent_webhook_handler/task.json` (Category H: API / Backend)
- Create: `tasks/v2/v09_json_path_evaluator/task.json` (Category F: Parsing)
- Create: `tasks/v2/v10_nested_markdown_table/task.json` (Category F: Parsing)
- Create: `tasks/v2/v11_async_worker_pool_deadlock/task.json` (Category G: Concurrency / Async)
- Create: `tasks/v2/v12_threadsafe_lru_locking/task.json` (Category G: Concurrency / Async)
- Create: `tasks/v2/v13_misleading_docstring_boundary/task.json` (Category M: Adversarial)
- Create: `tasks/v2/v14_distractor_module_contract/task.json` (Category M: Adversarial)

- [ ] **Step 1: Construct tasks v01 through v07 adhering to V2 Schema and Rubric**
- [ ] **Step 2: Construct tasks v08 through v14 adhering to V2 Schema and Rubric**
- [ ] **Step 3: Run `verify_tasks.py` and `task_factory` validators on all 14 pilot tasks**
- [ ] **Step 4: Confirm 100% 3x deterministic verification and zero flakiness**

---

### Task 6: System Integration, Verification & Final Verification Report

**Files:**
- Modify: `scripts/verify_tasks.py` (ensure support for `--suite v2` and `tasks/v2`)
- Modify: `README.md` (document Benchmark V2, Task Factory, and Pilot Suite)
- Test: Full pytest run, task verification run on Core (20), Hard (10), and V2 (14)

- [ ] **Step 1: Update `scripts/verify_tasks.py` to support `v2` suite filtering**
- [ ] **Step 2: Run full test suite (`pytest`) across all tests**
- [ ] **Step 3: Run full benchmark verification (`python scripts/verify_tasks.py --suite all --sandbox local`)**
- [ ] **Step 4: Update `README.md` and document Benchmark V2 architecture**
- [ ] **Step 5: Generate the comprehensive Final Report**
