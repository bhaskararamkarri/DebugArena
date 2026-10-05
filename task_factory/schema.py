"""Backwards-compatible schema definitions for DebugArena Benchmark V1 and V2 tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from task_factory.taxonomy import TaskDifficulty, TaxonomyCategory


@dataclass
class TaskMetadata:
    """Metadata describing architectural and evaluation attributes of a task."""
    estimated_reasoning_steps: int = 1
    file_count: int = 1
    adversarial: bool = False
    stateful: bool = False
    multi_file: bool = False
    domain: str = "general"
    quality_score: float = 3.0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> TaskMetadata:
        if not data:
            return cls()
        return cls(
            estimated_reasoning_steps=int(data.get("estimated_reasoning_steps", 1)),
            file_count=int(data.get("file_count", 1)),
            adversarial=bool(data.get("adversarial", False)),
            stateful=bool(data.get("stateful", False)),
            multi_file=bool(data.get("multi_file", False)),
            domain=str(data.get("domain", "general")),
            quality_score=float(data.get("quality_score", 3.0)),
        )


@dataclass
class TaskSchemaV2:
    """Benchmark V2 task definition schema with full V1 backward compatibility."""
    task_id: str
    suite: str = "v2"
    version: int = 2
    difficulty: str = TaskDifficulty.MEDIUM.value
    bug_type: str = "unknown"
    categories: List[str] = field(default_factory=list)
    description: str = ""
    spec_notes: str = ""
    repo_files: Dict[str, str] = field(default_factory=dict)
    tests: Dict[str, str] = field(default_factory=dict)
    reference_fix: Dict[str, str] = field(default_factory=dict)
    metadata: TaskMetadata = field(default_factory=TaskMetadata)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskSchemaV2:
        """Parses a task dictionary, inferring V2 fields if loading a legacy V1 task."""
        if not isinstance(data, dict):
            raise ValueError("Task data must be a dictionary")

        tid = data.get("task_id", "")
        if not tid:
            raise ValueError("Task is missing required field: 'task_id'")

        repo_files = data.get("repo_files", {})
        tests = data.get("tests", {})
        ref_fix = data.get("reference_fix", {})

        # Backward compatibility inference for V1 tasks
        suite = data.get("suite")
        if not suite:
            suite = "core" if tid.startswith("t") else ("hard" if tid.startswith("h") else "v2")

        version = int(data.get("version", 1 if ("t" in tid[:2] or "h" in tid[:2]) else 2))
        difficulty = data.get("difficulty", "medium").lower()
        bug_type = data.get("bug_type", "general")
        categories = data.get("categories", [])
        if not categories:
            # Infer default category
            categories = ["A"] if difficulty == "easy" else (["E", "B"] if len(repo_files) > 1 else ["B"])

        desc = data.get("description", "")
        spec_notes = data.get("spec_notes", "")

        raw_meta = data.get("metadata")
        if raw_meta:
            meta = TaskMetadata.from_dict(raw_meta)
        else:
            meta = TaskMetadata(
                estimated_reasoning_steps=2 if len(repo_files) == 1 else 4,
                file_count=len(repo_files),
                adversarial=difficulty == "adversarial",
                stateful=any("state" in f or "cache" in f or "limiter" in f for f in repo_files),
                multi_file=len(repo_files) > 1,
                domain="general",
                quality_score=4.0 if len(repo_files) > 1 else 2.5,
            )

        return cls(
            task_id=tid,
            suite=suite,
            version=version,
            difficulty=difficulty,
            bug_type=bug_type,
            categories=categories,
            description=desc,
            spec_notes=spec_notes,
            repo_files=repo_files,
            tests=tests,
            reference_fix=ref_fix,
            metadata=meta,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the task to a clean JSON-serializable dictionary."""
        d = asdict(self)
        return d

    def validate(self) -> List[str]:
        """Performs static structural validation on the task definition."""
        errors: List[str] = []
        if not self.task_id:
            errors.append("Missing required field: task_id")
        if not self.description:
            errors.append("Missing required field: description")
        if not self.repo_files:
            errors.append("Task must have at least 1 repository file in repo_files")
        if not self.tests:
            errors.append("Task must have at least 1 test file in tests")
        if not self.reference_fix:
            errors.append("Task must have at least 1 file in reference_fix")

        # Check reference fix files exist in repo_files
        for fix_file in self.reference_fix:
            if fix_file not in self.repo_files:
                errors.append(f"reference_fix file '{fix_file}' is not present in repo_files")

        return errors
