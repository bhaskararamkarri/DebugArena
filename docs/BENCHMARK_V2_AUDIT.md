# DebugArena Benchmark V2: Comprehensive Task & Architecture Audit

This report presents a thorough, granular 1–5 scoring audit of all 30 existing tasks in the DebugArena suite (Core `t01`–`t20` and Hard `h01`–`h10`), identifying benchmark strengths, weaknesses, taxonomy coverage, and architectural gaps to guide the expansion to Benchmark V2.

---

## 1. Executive Summary & Aggregate Metrics

| Metric | Core Suite (`t01`–`t20`) | Hard Suite (`h01`–`h10`) | Total Benchmark (V1) |
|---|---|---|---|
| **Total Task Count** | 20 | 10 | **30** |
| **Difficulty Breakdown** | 7 Easy, 9 Medium, 4 Hard | 0 Easy, 0 Medium, 10 Hard | **7 Easy, 9 Medium, 14 Hard** |
| **Total Repository LOC** | 184 LOC | 349 LOC | **533 LOC** |
| **Average Repo LOC / Task** | 9.2 LOC | 34.9 LOC | **17.8 LOC** |
| **Total Test LOC** | 377 LOC | 300 LOC | **677 LOC** |
| **Average Test LOC / Task** | 18.85 LOC | 30.0 LOC | **22.57 LOC** |
| **Average Source Files / Task** | 1.05 files | 2.90 files | **1.67 files** |
| **Multi-File Tasks (≥2 files)** | 1 / 20 (5.0%) | 10 / 10 (100.0%) | **11 / 30 (36.7%)** |
| **Single-File Tasks** | 19 / 20 (95.0%) | 0 / 10 (0.0%) | **19 / 30 (63.3%)** |
| **Average Overall Quality (1–5)** | 2.50 / 5.0 | 4.20 / 5.0 | **3.07 / 5.0** |
| **3x Determinism / Pass Rate** | 100% (20/20) | 100% (10/10) | **100% (30/30)** |

---

## 2. Granular Task Audit Matrix (1–5 Scoring)

### Dimensions:
- **Locality (LOC)**: 1 = scattered across many modules, 5 = single localized line.
- **Multi-File (MF)**: 1 = purely single function in 1 file, 5 = deeply coupled cross-module dependencies.
- **Statefulness (ST)**: 1 = stateless pure function, 5 = complex lifecycle / mutating state.
- **Algorithmic Complexity (ALG)**: 1 = trivial syntax/operator, 5 = non-trivial algorithm / graph / DP / search.
- **Realism (REA)**: 1 = synthetic toy puzzle, 5 = realistic production software subsystem.
- **Agent Challenge (CHL)**: 1 = trivial one-shot fix for small models, 5 = requires multi-step reasoning, regression avoidance.
- **Adversarial Quality (ADV)**: 1 = no traps or misleading code, 5 = subtle invariants, partial fix traps, misleading context.
- **Overall Quality (OVR)**: 1 = low utility baseline, 5 = gold-standard benchmark challenge.
- **Classification**: `BASIC`, `MEDIUM`, `HARD`, `EXCELLENT`.

### 2.1 Core Suite Audit Table (`t01`–`t20`)

| Task ID | Suite | Diff | Bug Type | Files | Tests | Init Pass | LOC | MF | ST | ALG | REA | CHL | ADV | OVR | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `t01_off_by_one` | Core | Easy | `off_by_one` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1.5 | BASIC |
| `t02_wrong_operator` | Core | Easy | `wrong_operator` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1.5 | BASIC |
| `t03_wrong_return` | Core | Easy | `wrong_return_val` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1.5 | BASIC |
| `t04_variable_typo` | Core | Easy | `variable_typo` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1.5 | BASIC |
| `t05_string_reverse` | Core | Easy | `string_reversal` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 2 | 1 | 2.0 | BASIC |
| `t06_clamp_boundary` | Core | Easy | `logic_swap` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1.5 | BASIC |
| `t07_discount_calc` | Core | Easy | `calc_error` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 2 | 2 | 1 | 2.0 | BASIC |
| `t08_empty_list` | Core | Med | `missing_edge_case` | 1 | 3 | 66% | 5 | 1 | 1 | 1 | 2 | 2 | 2 | 2.5 | MEDIUM |
| `t09_mutable_default` | Core | Med | `mutable_arg` | 1 | 3 | 33% | 5 | 1 | 2 | 2 | 3 | 3 | 2 | 3.0 | MEDIUM |
| `t10_wrong_slicing` | Core | Med | `string_slicing` | 1 | 3 | 33% | 5 | 1 | 1 | 2 | 2 | 2 | 1 | 2.5 | MEDIUM |
| `t11_int_float_div` | Core | Med | `int_division` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 2 | 2 | 1 | 2.0 | BASIC |
| `t12_dict_key` | Core | Med | `missing_key` | 1 | 3 | 33% | 5 | 1 | 1 | 1 | 2 | 2 | 1 | 2.5 | MEDIUM |
| `t13_flatten_nested` | Core | Med | `recursion_bug` | 1 | 3 | 33% | 4 | 1 | 1 | 3 | 2 | 3 | 2 | 3.0 | MEDIUM |
| `t14_moving_average` | Core | Med | `index_offset` | 1 | 3 | 33% | 4 | 1 | 1 | 2 | 2 | 2 | 1 | 2.5 | MEDIUM |
| `t15_matrix_transpose` | Core | Med | `bounds_error` | 1 | 3 | 33% | 4 | 1 | 1 | 2 | 2 | 3 | 2 | 3.0 | MEDIUM |
| `t16_lru_cache` | Core | Med | `lru_eviction` | 1 | 4 | 50% | 3 | 1 | 4 | 3 | 4 | 4 | 3 | 4.0 | HARD |
| `t17_two_file_import` | Core | Hard | `interface_mismatch` | 2 | 3 | 33% | 3 | 3 | 1 | 2 | 3 | 3 | 2 | 3.5 | HARD |
| `t18_quote_lexer` | Core | Hard | `stateful_lexer` | 1 | 4 | 50% | 3 | 1 | 4 | 3 | 3 | 4 | 3 | 4.0 | HARD |
| `t19_sort_priority` | Core | Hard | `sort_precedence` | 1 | 4 | 50% | 4 | 1 | 1 | 3 | 3 | 3 | 2 | 3.5 | HARD |
| `t20_retry_decorator` | Core | Hard | `decorator_state` | 1 | 4 | 50% | 3 | 1 | 4 | 3 | 4 | 4 | 3 | 4.0 | HARD |

### 2.2 Hard Suite Audit Table (`h01`–`h10`)

| Task ID | Suite | Diff | Bug Type | Files | Tests | Init Pass | LOC | MF | ST | ALG | REA | CHL | ADV | OVR | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `h01` | Hard | Hard | `interval_merging` | 3 | 5 | 40% | 2 | 3 | 2 | 4 | 4 | 4 | 3 | 4.5 | EXCELLENT |
| `h02` | Hard | Hard | `binary_search` | 3 | 4 | 50% | 3 | 3 | 1 | 4 | 4 | 4 | 3 | 4.0 | HARD |
| `h03` | Hard | Hard | `topo_sort_cycle` | 3 | 5 | 40% | 2 | 3 | 3 | 5 | 4 | 5 | 4 | 5.0 | EXCELLENT |
| `h04` | Hard | Hard | `csv_lexer_quotes` | 3 | 4 | 50% | 2 | 3 | 4 | 4 | 4 | 4 | 3 | 4.5 | EXCELLENT |
| `h05` | Hard | Hard | `ttl_rate_limiter` | 2 | 5 | 40% | 2 | 3 | 5 | 3 | 4 | 4 | 4 | 4.5 | EXCELLENT |
| `h06` | Hard | Hard | `ledger_rounding` | 3 | 4 | 50% | 2 | 3 | 2 | 3 | 5 | 4 | 4 | 4.5 | EXCELLENT |
| `h07` | Hard | Hard | `text_wrapping` | 3 | 4 | 50% | 2 | 3 | 2 | 4 | 3 | 4 | 3 | 4.0 | HARD |
| `h08` | Hard | Hard | `business_calendar` | 3 | 4 | 50% | 2 | 3 | 2 | 3 | 4 | 4 | 3 | 4.0 | HARD |
| `h09` | Hard | Hard | `graph_dijkstra` | 3 | 5 | 40% | 2 | 3 | 2 | 5 | 4 | 5 | 4 | 5.0 | EXCELLENT |
| `h10` | Hard | Hard | `config_precedence` | 3 | 5 | 40% | 2 | 3 | 3 | 3 | 4 | 4 | 4 | 4.5 | EXCELLENT |

---

## 3. Analysis & Key Findings

### 3.1 Tasks That Are Too Easy (Score < 2.0)
Tasks `t01` through `t07` and `t11` are single-line typo/syntax bugs in 3–7 line files.
- **Why they are weak**: They require zero repository exploration, zero architectural reasoning, and no state tracking. Any small LLM solves them in 1 turn by inspecting a single function.
- **Recommendation**: Keep them classified as `legacy/basic` for baseline sanity checks (verifying that minimal tool calling works), but do not let them represent the core benchmark signal.

### 3.2 Strong Tasks (Score ≥ 4.0)
Tasks `t16`, `t18`, `t20`, `h01`, `h03`, `h04`, `h05`, `h06`, `h09`, `h10`.
- **Why they are strong**:
  - `h03` (Topological Sort with Cycles) and `h09` (Dijkstra with Priority Queue Tiebreaking) test genuine graph theory, cycle detection, and data invariants.
  - `h05` (Sliding Window Rate Limiter) and `h06` (Penny Allocation Invariant) test subtle state transitions and financial consistency.
  - `h10` (Config Layering) tests hierarchical dictionary merging and environment variable overrides.
- **Recommendation**: Retain all strong tasks as foundational pillars of the `hard` suite and model V2 tasks after their multi-file, invariant-driven architecture.

### 3.3 Missing Bug Categories in V1
Comparing the V1 suite against the formal Benchmark V2 Taxonomy (Categories A–M):

1. **Category G: Async / Concurrency (0% in V1)**
   - Missing: race conditions, worker pool deadlocks, task cancellation, event loop blockage, thread-safe cache access.
2. **Category H: API / Backend Logic (0% in V1)**
   - Missing: cursor-based pagination, exponential backoff with jitter, idempotent webhook processing, request validation pipelines.
3. **Category I: Database / Persistence (0% in V1)**
   - Missing: transaction rollback semantics, connection pool leaks, optimistic locking conflicts, dirty read isolation.
4. **Category K: Performance & Leaks (0% in V1)**
   - Missing: O(n²) bottlenecks in critical loops, unbounded cache growth, dangling event handlers.
5. **Category L: Security & Validation (0% in V1)**
   - Missing: path traversal sanitization, regex ReDoS safety, query parameter injection boundaries.
6. **Category M: Adversarial Debugging (0% in V1)**
   - Missing: misleading docstrings that contradict specifications, distractor modules that look suspicious but are correct, partial fixes that break hidden invariants.

### 3.4 Benchmark Diversity & Structural Gaps
- **File Distribution Gap**: V1 exhibits a strict bimodal split: either 1 file (Core) or 3 files (Hard). Benchmark V2 should introduce 3–6 file repositories with distinct architectural layers (models, services, repositories, handlers).
- **Test Invariant Gap**: In V1, several tests directly mirror the reference solution structure. V2 tests must assert black-box behavioral contracts rather than implementation quirks.
- **Feedback Mode Gap**: V1 only provides full test pass/fail feedback. V2 requires evaluation support across `diagnostic`, `realistic`, and `blind` feedback modes.
