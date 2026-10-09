"""Evaluation status codes and failure taxonomy for DebugArena."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple


class EvaluationStatus(str, Enum):
    """Authoritative evaluation status codes for benchmark episodes."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    INVALID_AGENT_OUTPUT = "INVALID_AGENT_OUTPUT"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    ABSTAIN = "ABSTAIN"
    NOT_EVALUATED = "NOT_EVALUATED"
    SOLVE_ONLY = "SOLVE_ONLY"


class FailureCategory(str, Enum):
    """Fine-grained machine-readable failure taxonomy."""
    CORRECT_FIX = "correct_fix"
    WRONG_DIAGNOSIS = "wrong_diagnosis"
    WRONG_FIX = "wrong_fix"
    PARTIAL_FIX = "partial_fix"
    REGRESSION = "regression"
    NO_OP = "no_op"
    INVALID_ACTION = "invalid_action"
    MALFORMED_ACTION = "malformed_action"
    TEST_MANIPULATION = "test_manipulation"
    TIMEOUT = "timeout"
    ENVIRONMENT_ERROR = "environment_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    SANDBOX_FAILURE = "sandbox_failure"
    JUDGE_UNAVAILABLE = "judge_unavailable"
    PROVIDER_FAILURE = "provider_failure"
    SECURITY_VIOLATION = "security_violation"
    CORRECT_ABSTENTION = "correct_abstention"
    INCORRECT_ABSTENTION = "incorrect_abstention"
    OUT_OF_STEPS = "out_of_steps"
    NONE = "none"


def classify_episode_outcome(
    pass_rate: float,
    regression: bool = False,
    timed_out: bool = False,
    ran_out_of_steps: bool = False,
    invalid_json_count: int = 0,
    error: Optional[str] = None,
    has_oracle: bool = True,
    submitted: bool = False,
) -> Tuple[EvaluationStatus, FailureCategory]:
    """Classifies an episode outcome into standard status and failure category.

    Args:
        pass_rate: Final test pass rate [0.0, 1.0].
        regression: Whether regression occurred during episode.
        timed_out: Whether execution timed out.
        ran_out_of_steps: Whether agent exhausted step budget without solving.
        invalid_json_count: Number of invalid JSON actions encountered.
        error: Optional error string if exception was raised.
        has_oracle: Whether automated test oracle exists for the task.
        submitted: Whether agent explicitly submitted solution.

    Returns:
        (EvaluationStatus, FailureCategory)
    """
    if error:
        err_lower = error.lower()
        if "security" in err_lower or "traversal" in err_lower:
            return EvaluationStatus.SECURITY_VIOLATION, FailureCategory.SECURITY_VIOLATION
        if "provider" in err_lower or "nebius" in err_lower or "api_key" in err_lower:
            return EvaluationStatus.ENVIRONMENT_ERROR, FailureCategory.PROVIDER_FAILURE
        if "docker" in err_lower or "sandbox" in err_lower:
            return EvaluationStatus.ENVIRONMENT_ERROR, FailureCategory.SANDBOX_FAILURE
        return EvaluationStatus.ENVIRONMENT_ERROR, FailureCategory.ENVIRONMENT_ERROR

    if not has_oracle:
        return EvaluationStatus.SOLVE_ONLY, FailureCategory.NONE

    if timed_out:
        return EvaluationStatus.TIMEOUT, FailureCategory.TIMEOUT

    if pass_rate >= 1.0:
        return EvaluationStatus.PASS, FailureCategory.CORRECT_FIX

    if regression:
        return EvaluationStatus.FAIL, FailureCategory.REGRESSION

    if invalid_json_count > 0 and pass_rate == 0.0:
        return EvaluationStatus.INVALID_AGENT_OUTPUT, FailureCategory.MALFORMED_ACTION

    if 0.0 < pass_rate < 1.0:
        return EvaluationStatus.PARTIAL, FailureCategory.PARTIAL_FIX

    if ran_out_of_steps:
        return EvaluationStatus.FAIL, FailureCategory.OUT_OF_STEPS

    if submitted and pass_rate == 0.0:
        return EvaluationStatus.FAIL, FailureCategory.WRONG_FIX

    return EvaluationStatus.FAIL, FailureCategory.WRONG_FIX
