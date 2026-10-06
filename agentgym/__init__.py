"""DebugArena: An open RL environment where coding agents get better."""

from __future__ import annotations

import sys
from .env import BugFixEnv
from .reward import RewardCalculator
from .sandbox import Sandbox, SandboxResult
from .agent import Agent, MockAgent
from .runner import EpisodeRunner
from .manager import BenchmarkManager, RunConfig, RunStatus, RunState, get_benchmark_manager
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
    "CustomTask",
    "ZipSecurityError",
    "extract_zip_safely",
    "generate_custom_task_id",
    "compute_file_diff",
    "list_custom_tasks",
]
