"""DebugArena: An open RL environment where coding agents get better."""

from __future__ import annotations

import sys
from .env import BugFixEnv
from .reward import RewardCalculator
from .sandbox import Sandbox, SandboxResult
from .agent import Agent, MockAgent
from .runner import EpisodeRunner
from .manager import BenchmarkManager, RunConfig, RunStatus, RunState, get_benchmark_manager
from .taxonomy import EvaluationStatus, FailureCategory, classify_episode_outcome
from .security import SecurityError, PathTraversalSecurityError, safe_path
from .provider import (
    ConfigurationError,
    ExecutionMode,
    HACKATHON_TRACK_NAME,
    NEBIUS_CANONICAL_ENDPOINT,
    ProviderPolicyError,
    validate_execution_config,
    resolve_provider_config,
)
from .custom_task import (
    CustomTask,
    ZipSecurityError,
    extract_zip_safely,
    generate_custom_task_id,
    compute_file_diff,
    list_custom_tasks,
)

__version__ = "0.1.0"

__all__ = [
    "BugFixEnv",
    "RewardCalculator",
    "Sandbox",
    "SandboxResult",
    "Agent",
    "MockAgent",
    "EpisodeRunner",
    "BenchmarkManager",
    "RunConfig",
    "RunStatus",
    "RunState",
    "get_benchmark_manager",
    "SecurityError",
    "PathTraversalSecurityError",
    "safe_path",
    "EvaluationStatus",
    "FailureCategory",
    "classify_episode_outcome",
    "ConfigurationError",
    "ExecutionMode",
    "HACKATHON_TRACK_NAME",
    "NEBIUS_CANONICAL_ENDPOINT",
    "ProviderPolicyError",
    "validate_execution_config",
    "resolve_provider_config",
    "CustomTask",
    "ZipSecurityError",
    "extract_zip_safely",
    "generate_custom_task_id",
    "compute_file_diff",
    "list_custom_tasks",
]
