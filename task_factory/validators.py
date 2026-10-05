"""Validation pipeline and quality gates for DebugArena Benchmark V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentgym.sandbox import Sandbox
from task_factory.quality import QualityScore, evaluate_task_quality
from task_factory.schema import TaskSchemaV2


@dataclass
class TaskValidationReport:
    """Structured report generated from comprehensive task verification gates."""
    task_id: str
    is_valid: bool
    schema_valid: bool
    before_fix_passed: int
    before_fix_failed: int
    after_fix_passed: int
    after_fix_failed: int
    is_flaky: bool
    quality: QualityScore
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "is_valid": self.is_valid,
            "schema_valid": self.schema_valid,
            "before_fix_passed": self.before_fix_passed,
            "before_fix_failed": self.before_fix_failed,
            "after_fix_passed": self.after_fix_passed,
            "after_fix_failed": self.after_fix_failed,
            "is_flaky": self.is_flaky,
            "quality": self.quality.to_dict(),
            "errors": self.errors,
        }


class TaskValidator:
    """Executes multi-stage validation gates on benchmark tasks."""

    def __init__(self, sandbox_mode: str = "local", repetitions: int = 3, min_quality: float = 3.0):
        self.sandbox_mode = sandbox_mode
        self.repetitions = repetitions
        self.min_quality = min_quality

    def validate_schema(self, task_data: Dict[str, Any]) -> List[str]:
        """Validates task against TaskSchemaV2."""
        try:
            task_obj = TaskSchemaV2.from_dict(task_data)
            return task_obj.validate()
        except Exception as e:
            return [f"Schema parsing error: {str(e)}"]

    def validate_task(self, task_data: Dict[str, Any]) -> TaskValidationReport:
        """Runs the complete verification gate: schema, 3x before/after sandbox execution, and quality check."""
        errors: List[str] = []
        tid = task_data.get("task_id", "unknown_task")

        # 1. Schema Validation
        schema_errors = self.validate_schema(task_data)
        errors.extend(schema_errors)
        schema_valid = len(schema_errors) == 0

        repo_files = task_data.get("repo_files", {})
        tests = task_data.get("tests", {})
        ref_fix = task_data.get("reference_fix", {})

        # 2. Quality Evaluation
        quality = evaluate_task_quality(task_data)
        if not quality.is_passing(min_average=self.min_quality):
            errors.append(f"Quality score {quality.average_score} is below threshold {self.min_quality}")

        if not schema_valid or not repo_files or not tests or not ref_fix:
            return TaskValidationReport(
                task_id=tid,
                is_valid=False,
                schema_valid=schema_valid,
                before_fix_passed=0,
                before_fix_failed=0,
                after_fix_passed=0,
                after_fix_failed=0,
                is_flaky=False,
                quality=quality,
                errors=errors,
            )

        # 3. Before-Fix Execution (3x repetitions)
        before_passes = []
        before_fails = []
        for _ in range(self.repetitions):
            sb = Sandbox.create(mode=self.sandbox_mode)
            sb.write_files(repo_files)
            res = sb.run_tests(tests)
            sb.cleanup()
            before_passes.append(res.passed_tests)
            before_fails.append(res.failed_tests)

        flaky_before = not all(p == before_passes[0] for p in before_passes)
        init_pass = len(before_passes[0])
        init_fail = len(before_fails[0])
        total_tests = init_pass + init_fail

        if init_pass == 0:
            errors.append("Before-fix state has 0 passing tests (must have at least 1 passing test for regression baseline).")
        if init_fail == 0:
            errors.append("Before-fix state has 0 failing tests (bug is not active or tests do not trigger bug).")
        if flaky_before:
            errors.append("Flakiness detected in before-fix test runs across repetitions.")

        # 4. After-Fix Execution (3x repetitions)
        after_passes = []
        after_fails = []
        merged_files = dict(repo_files)
        merged_files.update(ref_fix)

        for _ in range(self.repetitions):
            sb = Sandbox.create(mode=self.sandbox_mode)
            sb.write_files(merged_files)
            res = sb.run_tests(tests)
            sb.cleanup()
            after_passes.append(res.passed_tests)
            after_fails.append(res.failed_tests)

        flaky_after = not all(p == after_passes[0] for p in after_passes)
        after_pass = len(after_passes[0])
        after_fail = len(after_fails[0])

        if after_fail > 0 or after_pass != total_tests:
            errors.append(f"Reference fix failed to achieve 100% pass rate ({after_pass}/{total_tests} passed).")
        if flaky_after:
            errors.append("Flakiness detected in after-fix test runs across repetitions.")

        is_flaky = flaky_before or flaky_after
        is_valid = len(errors) == 0

        return TaskValidationReport(
            task_id=tid,
            is_valid=is_valid,
            schema_valid=schema_valid,
            before_fix_passed=init_pass,
            before_fix_failed=init_fail,
            after_fix_passed=after_pass,
            after_fix_failed=after_fail,
            is_flaky=is_flaky,
            quality=quality,
            errors=errors,
        )
