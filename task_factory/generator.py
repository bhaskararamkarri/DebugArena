"""Central Task Generator with automated multi-stage validation and quality gates for Benchmark V2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from task_factory.dedup import DuplicateDetector
from task_factory.generators.base import BaseGenerator
from task_factory.generators.basic import BasicCalibrationTaskGenerator
from task_factory.generators.datastructure import DataStructureTaskGenerator
from task_factory.generators.database import DatabaseTaskGenerator
from task_factory.generators.configuration import ConfigurationTaskGenerator
from task_factory.generators.performance import PerformanceTaskGenerator
from task_factory.generators.security import SecurityTaskGenerator
from task_factory.generators.adversarial import AdversarialTaskGenerator
from task_factory.generators.stateful import StatefulTaskGenerator
from task_factory.generators.repository import RepositoryTaskGenerator
from task_factory.generators.concurrency import ConcurrencyTaskGenerator
from task_factory.generators.api import ApiTaskGenerator
from task_factory.generators.parsing import ParsingTaskGenerator
from task_factory.quality import QualityScore, evaluate_task_quality
from task_factory.schema import TaskSchemaV2
from task_factory.validators import TaskValidationReport, TaskValidator


class TaskGenerator:
    """Orchestrates deterministic task synthesis, validation gates, quality checks, and deduplication."""

    def __init__(
        self,
        sandbox_mode: str = "local",
        repetitions: int = 3,
        min_quality: float = 3.5,
        duplicate_threshold: float = 0.85,
    ):
        self.sandbox_mode = sandbox_mode
        self.repetitions = repetitions
        self.min_quality = min_quality
        self.duplicate_threshold = duplicate_threshold
        self.validator = TaskValidator(
            sandbox_mode=sandbox_mode,
            repetitions=repetitions,
            min_quality=min_quality,
        )
        self.dedup_detector = DuplicateDetector(similarity_threshold=duplicate_threshold)
        self.generators: Dict[str, BaseGenerator] = {
            "A": BasicCalibrationTaskGenerator(),
            "basic": BasicCalibrationTaskGenerator(),
            "calibration": BasicCalibrationTaskGenerator(),
            "C": DataStructureTaskGenerator(),
            "datastructure": DataStructureTaskGenerator(),
            "tree": DataStructureTaskGenerator(),
            "heap": DataStructureTaskGenerator(),
            "dsu": DataStructureTaskGenerator(),
            "trie": DataStructureTaskGenerator(),
            "I": DatabaseTaskGenerator(),
            "database": DatabaseTaskGenerator(),
            "transaction": DatabaseTaskGenerator(),
            "wal": DatabaseTaskGenerator(),
            "savepoint": DatabaseTaskGenerator(),
            "J": ConfigurationTaskGenerator(),
            "config": ConfigurationTaskGenerator(),
            "configuration": ConfigurationTaskGenerator(),
            "K": PerformanceTaskGenerator(),
            "performance": PerformanceTaskGenerator(),
            "leaks": PerformanceTaskGenerator(),
            "L": SecurityTaskGenerator(),
            "security": SecurityTaskGenerator(),
            "validation": SecurityTaskGenerator(),
            "M": AdversarialTaskGenerator(),
            "adversarial": AdversarialTaskGenerator(),
            "D": StatefulTaskGenerator(),
            "stateful": StatefulTaskGenerator(),
            "E": RepositoryTaskGenerator(),
            "repository": RepositoryTaskGenerator(),
            "multi_file": RepositoryTaskGenerator(),
            "G": ConcurrencyTaskGenerator(),
            "concurrency": ConcurrencyTaskGenerator(),
            "H": ApiTaskGenerator(),
            "api": ApiTaskGenerator(),
            "F": ParsingTaskGenerator(),
            "parsing": ParsingTaskGenerator(),
        }

    def register_generator(self, key: str, generator: BaseGenerator) -> None:
        """Registers a custom domain generator."""
        self.generators[key.upper()] = generator
        self.generators[key.lower()] = generator

    def resolve_generator(self, spec: Dict[str, Any]) -> BaseGenerator:
        """Finds appropriate generator matching task specification."""
        sub_type = spec.get("sub_type", "")
        task_id = spec.get("task_id", "")
        cat = spec.get("category", "")
        domain = spec.get("domain", "")

        # Specific sub_type mappings
        if sub_type in ("event_sourcing", "websocket_fsm", "compensating_tx", "saga", "state_machine", "two_phase_commit", "crdt"):
            return self.generators["D"]
        if sub_type in ("trace_correlation", "contract"):
            return self.generators["repository"]
        if sub_type in ("dataloader", "versioning_router", "federation_planner", "circuit_breaker"):
            return self.generators["H"]
        if sub_type in ("cache_coherence", "channel_backpressure", "sliding_window_dedup", "leader_lease", "raft_consensus", "byzantine_quorum", "actor_mailbox"):
            return self.generators["G"]
        if sub_type in ("schema_evolution", "hierarchical_rate_limiter"):
            return self.generators["J"]
        if sub_type in ("migration_rollback", "lsm_compaction"):
            return self.generators["I"]
        if sub_type in ("jit_optimizer", "ast_rewriter"):
            return self.generators["A"]
        if sub_type in ("bplus_tree",):
            return self.generators["C"]
        if sub_type in ("oauth_pkce", "merkle_proof"):
            return self.generators["L"]
        if sub_type in ("flaky_retry_storm",):
            return self.generators["M"]

        for key in [sub_type, domain, cat]:
            if key and key in self.generators:
                return self.generators[key]
            if key and key.upper() in self.generators:
                return self.generators[key.upper()]
            if key and key.lower() in self.generators:
                return self.generators[key.lower()]

        # Keyword heuristics
        if "timezone" in task_id or "semver" in task_id or "rotated" in task_id:
            return self.generators["A"]
        if "tree" in task_id or "heap" in task_id or "trie" in task_id or "dsu" in task_id or "rank" in task_id:
            return self.generators["C"]
        if "savepoint" in task_id or "pool" in task_id or "locking" in task_id or "wal" in task_id or "checkpoint" in task_id or "migration" in task_id:
            return self.generators["I"]
        if "config" in task_id or "merge" in task_id or "precedence" in task_id or "flag" in task_id or "schema_evolution" in task_id or "rate_limiter" in task_id:
            return self.generators["J"]
        if "leak" in task_id or "quadratic" in task_id or "performance" in task_id or "buffer" in task_id:
            return self.generators["K"]
        if "traversal" in task_id or "sanitiz" in task_id or "boundary" in task_id or "ssrf" in task_id or "whitelist" in task_id:
            return self.generators["L"]
        if "misleading" in task_id or "distractor" in task_id or "adversarial" in task_id or "deceptive" in task_id:
            return self.generators["M"]
        if "saga" in task_id or "event_sourcing" in task_id or "websocket" in task_id or "compensating" in task_id or "fsm" in task_id:
            return self.generators["D"]
        if "trace" in task_id or "contract" in task_id or "propagation" in task_id or "serializer" in task_id:
            return self.generators["repository"]
        if "queue" in task_id or "executor" in task_id or "concurrency" in task_id or "cache_coherence" in task_id or "backpressure" in task_id or "leader" in task_id or "dedup" in task_id:
            return self.generators["G"]
        if "dataloader" in task_id or "versioning" in task_id or "pagination" in task_id or "webhook" in task_id or "api" in task_id:
            return self.generators["H"]
        if "csv" in task_id or "parse" in task_id:
            return self.generators["F"]

        # Default to Configuration
        return self.generators["J"]

    def generate_candidate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        """Generates a raw task candidate dictionary deterministically."""
        gen = self.resolve_generator(spec)
        candidate = gen.generate(spec, seed=seed)
        return candidate

    def generate_and_validate(
        self,
        spec: Dict[str, Any],
        seed: int = 42,
        existing_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[TaskSchemaV2], TaskValidationReport, Dict[str, Any]]:
        """Executes full generation + validation gate pipeline.

        Returns:
            (approved_task_schema_or_None, validation_report, candidate_dict)
        """
        candidate = self.generate_candidate(spec, seed=seed)
        tid = candidate.get("task_id", "candidate_task")

        # 1. Run TaskValidator sandbox execution and quality gates
        report = self.validator.validate_task(candidate)

        # 2. Check for duplicates against existing corpus
        if existing_tasks and report.is_valid:
            for existing in existing_tasks:
                if existing.get("task_id") == tid:
                    continue
                sim = self.dedup_detector.compute_similarity(candidate, existing)
                if sim >= self.duplicate_threshold:
                    report.is_valid = False
                    report.errors.append(
                        f"Task rejected by DuplicateDetector: {sim:.2f} similarity with '{existing.get('task_id')}' exceeds threshold {self.duplicate_threshold}"
                    )
                    break

        if not report.is_valid:
            return None, report, candidate

        schema_obj = TaskSchemaV2.from_dict(candidate)
        return schema_obj, report, candidate

    def save_task(self, task_data: Dict[str, Any], target_base_dir: str = "tasks/v2") -> Path:
        """Persists approved task definition to disk."""
        tid = task_data["task_id"]
        out_dir = Path(target_base_dir) / tid
        out_dir.mkdir(parents=True, exist_ok=True)
        task_json_path = out_dir / "task.json"

        with open(task_json_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2)

        return task_json_path
