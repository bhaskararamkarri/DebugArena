"""Base generator interface for modular benchmark task creation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseGenerator(ABC):
    """Abstract base class for domain-specific task generators."""

    @abstractmethod
    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        """Generates a complete candidate task dictionary matching TaskSchemaV2.

        Args:
            spec: Specification dictionary detailing category, difficulty, domain, etc.
            seed: Seed ensuring deterministic reproducibility.

        Returns:
            Dictionary with keys: task_id, suite, version, difficulty, bug_type,
            categories, description, spec_notes, repo_files, tests, reference_fix, metadata.
        """
        pass
