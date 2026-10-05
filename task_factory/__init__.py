"""Task Factory: Core architecture and validation engine for DebugArena Benchmark V2."""

from task_factory.taxonomy import TaxonomyCategory, TaskDifficulty
from task_factory.schema import TaskSchemaV2, TaskMetadata
from task_factory.quality import QualityScore, evaluate_task_quality
from task_factory.dedup import DuplicateDetector
from task_factory.validators import TaskValidator
from task_factory.generator import TaskGenerator
from task_factory.feedback import (
    BaseFeedbackAdapter,
    DiagnosticFeedbackAdapter,
    RealisticFeedbackAdapter,
    BlindFeedbackAdapter,
    get_feedback_adapter,
)

__all__ = [
    "TaxonomyCategory",
    "TaskDifficulty",
    "TaskSchemaV2",
    "TaskMetadata",
    "QualityScore",
    "evaluate_task_quality",
    "DuplicateDetector",
    "TaskValidator",
    "TaskGenerator",
    "BaseFeedbackAdapter",
    "DiagnosticFeedbackAdapter",
    "RealisticFeedbackAdapter",
    "BlindFeedbackAdapter",
    "get_feedback_adapter",
]
