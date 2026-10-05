"""Task generator module registry for DebugArena Benchmark V2."""

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

__all__ = [
    "BaseGenerator",
    "BasicCalibrationTaskGenerator",
    "DataStructureTaskGenerator",
    "DatabaseTaskGenerator",
    "ConfigurationTaskGenerator",
    "PerformanceTaskGenerator",
    "SecurityTaskGenerator",
    "AdversarialTaskGenerator",
    "StatefulTaskGenerator",
    "RepositoryTaskGenerator",
    "ConcurrencyTaskGenerator",
    "ApiTaskGenerator",
    "ParsingTaskGenerator",
]
