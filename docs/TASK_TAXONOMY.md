# DebugArena Benchmark V2: Formal Task Taxonomy

The Benchmark V2 taxonomy establishes a formal 13-category classification system (Categories **A** through **M**) for AI coding-agent debugging benchmarks.

---

## Taxonomy Overview

| Category | Category Name | Primary Focus | Target Difficulty |
|---|---|---|---|
| **A** | Basic Debugging | Syntax, typos, off-by-one, basic conditionals | Easy |
| **B** | Algorithmic Bugs | Graph algorithms, intervals, sorting, search, DP | Medium – Hard |
| **C** | Data Structure Bugs | Invariants in trees, heaps, caches, linked lists | Medium – Hard |
| **D** | State Management | Lifecycle transitions, state machines, stale cache | Medium – Hard |
| **E** | Multi-File Repository | Cross-module contracts, schema mismatch, imports | Medium – Hard |
| **F** | Parsing & Serialization | Grammars, tokenizers, nested formats, escaping | Medium – Hard |
| **G** | Async & Concurrency | Deadlocks, race conditions, cancellation, worker pools | Hard – Adversarial |
| **H** | API & Backend Logic | Pagination, backoff retries, rate limiting, idempotency | Medium – Hard |
| **I** | Database & Persistence | Transaction rollback, dirty reads, connection lifecycle | Hard |
| **J** | Configuration & Layering | Precedence, env overrides, deep dict merging | Medium – Hard |
| **K** | Performance & Leaks | Algorithmic bottlenecks O(n²), memory growth | Hard |
| **L** | Sandboxed Security | Path traversal, sanitization, boundary checks | Medium – Hard |
| **M** | Adversarial Debugging | Misleading docstrings, distractors, hidden invariants | Adversarial |

---

## Category Specifications

### Category A: Basic Debugging
- **Description**: Fundamental programmer errors in localized code blocks.
- **Sub-types**: Off-by-one (`<` vs `<=`), inverted boolean logic, incorrect return values, unhandled empty collections, wrong arithmetic operator (`//` vs `/`).
- **Benchmark Role**: Serves as a baseline sanity check. Should represent ≤20% of the benchmark.

### Category B: Algorithmic Bugs
- **Description**: Logic errors in standard algorithmic procedures and data processing pipelines.
- **Sub-types**: Binary search duplicate edge boundaries, interval merging overlap logic, topological sort cycle handling, Dijkstra tiebreaking, sliding window deques.
- **Invariant**: Algorithms must adhere to strict mathematical invariants across edge cases (empty collections, single-element, all duplicates, negative numbers).

### Category C: Data Structure Bugs
- **Description**: Structural invariant violations in custom or wrapped data structures.
- **Sub-types**: LRU cache eviction ordering on `get()`, binary heap sift-down comparator errors, doubly-linked list sentinel pointer corruption, Trie prefix termination flags.

### Category D: State Management & Lifecycle
- **Description**: Defects in state machines, lifecycle hooks, and accumulating or stale context.
- **Sub-types**: Circuit breaker state transition failures (`CLOSED` -> `OPEN` -> `HALF-OPEN`), mutable default arguments across invocations, saga compensation ordering, missing state reset on error.

### Category E: Multi-File Repository Bugs
- **Description**: Bugs spanning architectural boundaries where no single file contains the complete defect.
- **Sub-types**: Service-Repository data contract mismatch, event bus parameter mismatches, serialization schema drift across API layers.
- **Invariant**: The agent must inspect at least 2 distinct files to diagnose and fix the root cause.

### Category F: Parsing & Language Processing
- **Description**: Handling structured or nested textual formats with escaped tokens and edge syntax.
- **Sub-types**: CSV quotes containing commas and escaped quotes `\"`, JSONPath evaluator with recursive descent `..`, Markdown nested table tokenization.

### Category G: Async / Concurrency
- **Description**: Non-deterministic execution bugs, synchronization failures, and shared mutable state.
- **Sub-types**: Async worker pool deadlock on exception handling, thread-safe cache locking invariants, event loop blocking operations, cancellation token handling.
- **Safety Note**: All concurrency tests in DebugArena must be 100% deterministic (using synchronization primitives, mocked timers, or deterministic barrier joins).

### Category H: API / Backend Logic
- **Description**: Distributed systems and backend service patterns.
- **Sub-types**: Opaque cursor-based pagination boundary slicing, exponential backoff with full jitter calculation, idempotent webhook replay protection, request signature verification.

### Category I: Database & Persistence
- **Description**: Transactional semantics and data store lifecycle management.
- **Sub-types**: Nested transaction rollback on partial failure, optimistic concurrency version mismatch handling, connection pool exhaustion handling.
- **Safety Note**: Use lightweight in-memory SQL/mock engines without external database daemon dependencies.

### Category J: Configuration & Environment Layering
- **Description**: Multi-tiered configuration merging and override precedence.
- **Sub-types**: CLI args vs Environment variables vs Default config merging, deep nested dictionary overwrites without preserving sibling keys.

### Category K: Performance & Resource Leaks
- **Description**: High-complexity performance pitfalls and resource management.
- **Sub-types**: Unintentional O(n²) string concatenations or lookups in loops, unclosed file handles in generators, unbounded cache growth.

### Category L: Sandboxed Security & Validation
- **Description**: Defensive programming and boundary validation errors.
- **Sub-types**: Path traversal via un-sanitized relative paths (`../../etc/passwd`), regex ReDoS catastrophic backtracking, input schema bypass.
- **Safety Note**: Tasks must be completely safe and contained within the local/Docker sandbox environment.

### Category M: Adversarial Debugging
- **Description**: Debugging challenges specifically designed to expose common AI agent failure modes (syndromes).
- **Sub-types**:
  1. *Misleading Docstring*: Docstring claims one behavior, but the system specification and hidden test assert the opposite.
  2. *Distractor File*: A suspicious-looking helper module exists with misleading comments, but the true bug is in the caller or repository layer.
  3. *Partial Fix Trap*: A superficial patch fixes 60% of tests but regresses an unstated critical invariant.
  4. *Multiple Plausible Fixes*: Several syntactic fixes appear viable, but only one respects the cross-module contract.
  5. *Hidden Invariant*: Public behavior works for basic inputs, but edge cases expose structural invariant violations.
