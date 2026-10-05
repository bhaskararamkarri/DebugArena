"""Taxonomy definitions and category classifications for Benchmark V2."""

from enum import Enum
from typing import Dict, List, Optional


class TaxonomyCategory(str, Enum):
    """Formal 13-category benchmark taxonomy for AI coding agent evaluation."""
    A_BASIC = "A"               # Basic Debugging (typos, off-by-one, basic conditionals)
    B_ALGORITHMIC = "B"         # Algorithmic Bugs (graph, DP, sorting, search, intervals)
    C_DATA_STRUCTURE = "C"      # Data Structure Invariants (trees, heaps, caches, lists)
    D_STATE_MANAGEMENT = "D"    # State Management & Lifecycle (FSM, stale cache, transitions)
    E_MULTI_FILE = "E"          # Multi-File Repository (cross-module contract, imports, schema)
    F_PARSING = "F"             # Parsing & Serialization (grammars, escaping, tokenizers)
    G_CONCURRENCY = "G"         # Async & Concurrency (deadlocks, race conditions, workers)
    H_API_BACKEND = "H"         # API & Backend Logic (pagination, backoff, idempotency)
    I_DATABASE = "I"            # Database & Persistence (transactions, rollback, lifecycle)
    J_CONFIG = "J"              # Configuration & Layering (precedence, env overrides, merges)
    K_PERFORMANCE = "K"         # Performance & Leaks (O(n²) bottlenecks, memory growth)
    L_SECURITY = "L"            # Sandboxed Security & Validation (path traversal, boundaries)
    M_ADVERSARIAL = "M"         # Adversarial Debugging (misleading docstrings, distractors)


class TaskDifficulty(str, Enum):
    """Task difficulty rating."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


CATEGORY_METADATA: Dict[TaxonomyCategory, Dict[str, str]] = {
    TaxonomyCategory.A_BASIC: {
        "name": "Basic Debugging",
        "description": "Syntax, typos, off-by-one, basic conditionals, and operator bugs.",
    },
    TaxonomyCategory.B_ALGORITHMIC: {
        "name": "Algorithmic Bugs",
        "description": "Graph algorithms, interval merging, sorting, binary search, and dynamic programming.",
    },
    TaxonomyCategory.C_DATA_STRUCTURE: {
        "name": "Data Structure Bugs",
        "description": "Invariants in trees, heaps, caches, linked lists, and hash tables.",
    },
    TaxonomyCategory.D_STATE_MANAGEMENT: {
        "name": "State Management",
        "description": "Lifecycle transitions, state machines, and accumulating or stale cache state.",
    },
    TaxonomyCategory.E_MULTI_FILE: {
        "name": "Multi-File Repository",
        "description": "Cross-module interfaces, data contracts, and serialization schema boundaries.",
    },
    TaxonomyCategory.F_PARSING: {
        "name": "Parsing & Language Processing",
        "description": "Grammars, tokenizers, nested structured formats, escaping, and quoting.",
    },
    TaxonomyCategory.G_CONCURRENCY: {
        "name": "Async & Concurrency",
        "description": "Deadlocks, race conditions, cancellation tokens, and worker pools.",
    },
    TaxonomyCategory.H_API_BACKEND: {
        "name": "API & Backend Logic",
        "description": "Cursor pagination, exponential backoff, rate limiting, and idempotent webhooks.",
    },
    TaxonomyCategory.I_DATABASE: {
        "name": "Database & Persistence",
        "description": "Transaction rollback semantics, connection pool lifecycle, and optimistic locking.",
    },
    TaxonomyCategory.J_CONFIG: {
        "name": "Configuration & Layering",
        "description": "Multi-tier configuration precedence, environment variable overrides, and dict merging.",
    },
    TaxonomyCategory.K_PERFORMANCE: {
        "name": "Performance & Resource Leaks",
        "description": "Algorithmic bottlenecks O(n²), memory growth, and dangling resource handles.",
    },
    TaxonomyCategory.L_SECURITY: {
        "name": "Sandboxed Security & Validation",
        "description": "Path traversal sanitization, input boundary checks, and ReDoS defense.",
    },
    TaxonomyCategory.M_ADVERSARIAL: {
        "name": "Adversarial Debugging",
        "description": "Misleading docstrings, distractor modules, partial-fix traps, and hidden invariants.",
    },
}


def get_category_name(category: str) -> str:
    """Returns human-readable category name."""
    try:
        cat_enum = TaxonomyCategory(category.upper())
        return CATEGORY_METADATA.get(cat_enum, {}).get("name", "Unknown Category")
    except ValueError:
        return "Unknown Category"
