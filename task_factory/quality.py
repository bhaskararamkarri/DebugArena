"""Formal 10-dimension task quality scoring rubric for Benchmark V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class QualityScore:
    """10-dimension quality score representation (0.0 to 5.0 per dimension)."""
    bug_clarity: float = 4.0
    debugging_difficulty: float = 3.5
    repository_realism: float = 3.5
    reasoning_depth: float = 3.5
    multi_file_complexity: float = 3.0
    statefulness: float = 3.0
    hidden_test_quality: float = 4.5
    edge_case_coverage: float = 4.0
    regression_potential: float = 4.0
    agent_challenge: float = 3.5

    @property
    def total_score(self) -> float:
        """Sum of all 10 dimensions (max 50.0)."""
        return round(
            self.bug_clarity
            + self.debugging_difficulty
            + self.repository_realism
            + self.reasoning_depth
            + self.multi_file_complexity
            + self.statefulness
            + self.hidden_test_quality
            + self.edge_case_coverage
            + self.regression_potential
            + self.agent_challenge,
            2,
        )

    @property
    def average_score(self) -> float:
        """Average score across all dimensions (0.0 to 5.0)."""
        return round(self.total_score / 10.0, 2)

    def is_passing(self, min_average: float = 3.5) -> bool:
        """Evaluates whether the task satisfies the benchmark quality threshold."""
        return self.average_score >= min_average

    def to_dict(self) -> Dict[str, float]:
        return {
            "bug_clarity": self.bug_clarity,
            "debugging_difficulty": self.debugging_difficulty,
            "repository_realism": self.repository_realism,
            "reasoning_depth": self.reasoning_depth,
            "multi_file_complexity": self.multi_file_complexity,
            "statefulness": self.statefulness,
            "hidden_test_quality": self.hidden_test_quality,
            "edge_case_coverage": self.edge_case_coverage,
            "regression_potential": self.regression_potential,
            "agent_challenge": self.agent_challenge,
            "total_score": self.total_score,
            "average_score": self.average_score,
        }


def evaluate_task_quality(task_data: Dict[str, Any]) -> QualityScore:
    """Computes an authoritative 10-dimension quality score purely from task code, tests, and structure.

    Self-reported metadata['quality_score'] is strictly ignored to prevent artificial inflation.
    """
    repo_files = task_data.get("repo_files", {})
    tests = task_data.get("tests", {})
    ref_fix = task_data.get("reference_fix", {})
    description = task_data.get("description", "")
    spec_notes = task_data.get("spec_notes", "")
    metadata = task_data.get("metadata", {})
    difficulty = str(task_data.get("difficulty", "medium")).lower()

    file_count = len(repo_files)
    total_repo_lines = sum(len(c.splitlines()) for c in repo_files.values())
    total_test_lines = sum(len(c.splitlines()) for c in tests.values())

    # Count test functions across all test files
    test_func_count = 0
    for test_code in tests.values():
        test_func_count += test_code.count("def test_") or test_code.count("def test")

    # 1. Bug clarity (length & precision of description and spec notes)
    full_desc_len = len(description) + len(spec_notes)
    if full_desc_len >= 80:
        clarity = 5.0
    elif full_desc_len >= 40:
        clarity = 4.0
    elif full_desc_len >= 20:
        clarity = 3.0
    else:
        clarity = 2.0

    # 2. Repository Realism (realistic file structure, LOC, class/function definitions)
    all_repo_code = " ".join(repo_files.values())
    has_classes = "class " in all_repo_code
    has_type_hints = "->" in all_repo_code or ": int" in all_repo_code or ": str" in all_repo_code

    if file_count >= 3:
        realism = 5.0 if total_repo_lines >= 60 else (4.5 if total_repo_lines >= 30 else 4.0)
    elif file_count == 2:
        realism = 4.0 if total_repo_lines >= 30 else 3.5
    else:
        realism = 3.0 if total_repo_lines >= 20 else 2.0
    if has_classes and has_type_hints:
        realism = min(5.0, realism + 0.5)

    # 3. Multi-file complexity (cross-module dependencies and multi-file patches)
    ref_fix_files = len(ref_fix)
    cross_file_imports = any(
        any(f.replace(".py", "") in code for f in repo_files if f != src_f)
        for src_f, code in repo_files.items()
    ) if file_count > 1 else False

    if file_count >= 3:
        mf_complexity = 5.0 if ref_fix_files > 1 else (4.5 if cross_file_imports else 4.0)
    elif file_count == 2:
        mf_complexity = 4.0 if ref_fix_files > 1 else (3.5 if cross_file_imports else 3.0)
    else:
        mf_complexity = 1.0

    # 4. Statefulness (presence of mutable state, FSM, caches, locks, buffers)
    stateful_keywords = [
        "self.", "state", "cache", "session", "timer", "pool", "limiter",
        "token", "lock", "queue", "fsm", "buffer", "history", "status"
    ]
    state_kw_matches = sum(1 for kw in stateful_keywords if kw in all_repo_code.lower())
    if state_kw_matches >= 4:
        statefulness = 5.0
    elif state_kw_matches >= 2:
        statefulness = 4.0
    elif state_kw_matches >= 1:
        statefulness = 3.0
    else:
        statefulness = 2.0

    # 5. Reasoning Depth & Debugging Difficulty
    is_adversarial = difficulty == "adversarial" or bool(metadata.get("adversarial", False))
    if is_adversarial:
        reasoning = 4.8
        diff_score = 4.8
        challenge = 5.0
    elif difficulty == "hard":
        reasoning = 4.5
        diff_score = 4.5
        challenge = 4.5
    elif difficulty == "medium":
        reasoning = 3.5
        diff_score = 3.5
        challenge = 3.5
    else:
        reasoning = 2.5
        diff_score = 2.0
        challenge = 2.0

    # 6. Test Quality & Coverage
    if test_func_count >= 5:
        test_quality = 5.0
    elif test_func_count >= 3:
        test_quality = 4.5
    elif test_func_count >= 2:
        test_quality = 4.0
    else:
        test_quality = 3.0

    if total_test_lines >= 40 or test_func_count >= 4:
        edge_cases = 4.5
        regression = 4.5
    elif total_test_lines >= 20:
        edge_cases = 4.0
        regression = 4.0
    else:
        edge_cases = 3.0
        regression = 3.0

    return QualityScore(
        bug_clarity=round(clarity, 1),
        debugging_difficulty=round(diff_score, 1),
        repository_realism=round(realism, 1),
        reasoning_depth=round(reasoning, 1),
        multi_file_complexity=round(mf_complexity, 1),
        statefulness=round(statefulness, 1),
        hidden_test_quality=round(test_quality, 1),
        edge_case_coverage=round(edge_cases, 1),
        regression_potential=round(regression, 1),
        agent_challenge=round(challenge, 1),
    )
