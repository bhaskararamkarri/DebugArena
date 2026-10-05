"""Comprehensive unit tests for task_factory modules."""

import pytest
from task_factory.taxonomy import TaxonomyCategory, TaskDifficulty, get_category_name
from task_factory.schema import TaskSchemaV2, TaskMetadata
from task_factory.quality import QualityScore, evaluate_task_quality
from task_factory.dedup import DuplicateDetector, compute_ast_fingerprint, compute_token_jaccard
from task_factory.validators import TaskValidator
from task_factory.feedback import (
    DiagnosticFeedbackAdapter,
    RealisticFeedbackAdapter,
    BlindFeedbackAdapter,
    get_feedback_adapter,
)


def test_taxonomy_definitions():
    assert TaxonomyCategory.A_BASIC.value == "A"
    assert TaxonomyCategory.M_ADVERSARIAL.value == "M"
    assert "Basic Debugging" in get_category_name("A")
    assert "Adversarial Debugging" in get_category_name("M")
    assert get_category_name("invalid_cat") == "Unknown Category"


def test_v2_schema_and_v1_backward_compatibility():
    # Legacy V1-style dictionary
    v1_dict = {
        "task_id": "t01_off_by_one",
        "difficulty": "easy",
        "bug_type": "off_by_one",
        "description": "sum_range excludes upper bound b",
        "repo_files": {"mathutils.py": "def sum_range(a, b): return sum(range(a, b))\n"},
        "tests": {"test_mathutils.py": "from mathutils import sum_range\ndef test_1(): assert sum_range(1, 3) == 6\n"},
        "reference_fix": {"mathutils.py": "def sum_range(a, b): return sum(range(a, b + 1))\n"},
    }

    schema_obj = TaskSchemaV2.from_dict(v1_dict)
    assert schema_obj.task_id == "t01_off_by_one"
    assert schema_obj.suite == "core"
    assert schema_obj.version == 1
    assert "A" in schema_obj.categories
    assert schema_obj.metadata.file_count == 1
    assert len(schema_obj.validate()) == 0

    # Modern V2-style dictionary
    v2_dict = {
        "task_id": "v01_sliding_window_stream",
        "suite": "v2",
        "version": 2,
        "difficulty": "medium",
        "bug_type": "sliding_window_eviction",
        "categories": ["B", "D"],
        "description": "Accumulator window eviction bug",
        "spec_notes": "Window must maintain exact duration",
        "repo_files": {
            "models.py": "class Sample: pass\n",
            "window.py": "class Window: pass\n",
        },
        "tests": {"test_window.py": "def test_win(): assert True\n"},
        "reference_fix": {"window.py": "class Window: pass # fixed\n"},
        "metadata": {
            "estimated_reasoning_steps": 4,
            "file_count": 2,
            "adversarial": False,
            "stateful": True,
            "multi_file": True,
            "domain": "metrics",
            "quality_score": 4.5,
        },
    }

    schema_v2 = TaskSchemaV2.from_dict(v2_dict)
    assert schema_v2.version == 2
    assert schema_v2.suite == "v2"
    assert schema_v2.categories == ["B", "D"]
    assert schema_v2.metadata.stateful is True
    assert len(schema_v2.validate()) == 0


def test_quality_score_rubric():
    score = QualityScore(
        bug_clarity=5.0,
        debugging_difficulty=4.0,
        repository_realism=4.0,
        reasoning_depth=4.0,
        multi_file_complexity=4.0,
        statefulness=4.0,
        hidden_test_quality=4.5,
        edge_case_coverage=4.0,
        regression_potential=4.0,
        agent_challenge=4.0,
    )
    assert score.total_score == 41.5
    assert score.average_score == 4.15
    assert score.is_passing(min_average=3.5) is True

    # Sub-threshold score
    weak_score = QualityScore(
        bug_clarity=2.0,
        debugging_difficulty=1.0,
        repository_realism=1.0,
        reasoning_depth=1.0,
        multi_file_complexity=1.0,
        statefulness=1.0,
        hidden_test_quality=2.0,
        edge_case_coverage=2.0,
        regression_potential=2.0,
        agent_challenge=1.0,
    )
    assert weak_score.is_passing(min_average=3.5) is False


def test_quality_score_metadata_bypass_eliminated():
    """Regression test: self-reported metadata['quality_score'] MUST NOT influence algorithmic scoring."""
    base_task = {
        "task_id": "v_test_bypass",
        "difficulty": "medium",
        "description": "Simple test task description for verification",
        "repo_files": {
            "main.py": "def run(): return 1\n",
        },
        "tests": {
            "test_main.py": "def test_1(): assert True\n",
        },
        "reference_fix": {
            "main.py": "def run(): return 2\n",
        },
        "metadata": {
            "quality_score": 1.0,
        },
    }

    # Score with metadata claiming 1.0
    score_low_meta = evaluate_task_quality(base_task)

    # Score with metadata claiming 5.0 (attempted bypass)
    task_high_meta = dict(base_task)
    task_high_meta["metadata"] = {"quality_score": 5.0}
    score_high_meta = evaluate_task_quality(task_high_meta)

    # Score with no metadata at all
    task_no_meta = dict(base_task)
    task_no_meta["metadata"] = {}
    score_no_meta = evaluate_task_quality(task_no_meta)

    # Scores must be completely identical regardless of self-reported metadata quality_score
    assert score_low_meta.average_score == score_high_meta.average_score
    assert score_low_meta.total_score == score_high_meta.total_score
    assert score_low_meta.to_dict() == score_no_meta.to_dict()
    assert score_high_meta.to_dict() == score_no_meta.to_dict()


def test_ast_deduplication():
    code_a = """
def calculate_area(width, height):
    # Calculate area of rectangle
    result = width * height
    return result
"""

    # Identical structure with renamed variables and comments stripped
    code_b = """
def compute_size(x, y):
    val = x * y
    return val
"""

    # Structurally different code
    code_c = """
def is_even(num):
    return num % 2 == 0
"""

    hash_a = compute_ast_fingerprint(code_a)
    hash_b = compute_ast_fingerprint(code_b)
    hash_c = compute_ast_fingerprint(code_c)

    assert hash_a == hash_b  # Normalizer equates variable renames
    assert hash_a != hash_c

    detector = DuplicateDetector(similarity_threshold=0.85)
    task1 = {"task_id": "t1", "bug_type": "calc", "repo_files": {"a.py": code_a}}
    task2 = {"task_id": "t2", "bug_type": "calc", "repo_files": {"a.py": code_b}}
    task3 = {"task_id": "t3", "bug_type": "check", "repo_files": {"a.py": code_c}}

    sim_1_2 = detector.compute_similarity(task1, task2)
    sim_1_3 = detector.compute_similarity(task1, task3)

    assert sim_1_2 >= 0.95
    assert sim_1_3 < 0.50

    dupes = detector.find_duplicates([task1, task2, task3])
    assert len(dupes) == 1
    assert dupes[0][0] == "t1"
    assert dupes[0][1] == "t2"


def test_feedback_mode_adapters():
    diag = get_feedback_adapter("diagnostic")
    real = get_feedback_adapter("realistic")
    blind = get_feedback_adapter("blind")

    assert isinstance(diag, DiagnosticFeedbackAdapter)
    assert isinstance(real, RealisticFeedbackAdapter)
    assert isinstance(blind, BlindFeedbackAdapter)

    sample_obs = {"description": "desc", "files": {"a.py": "1"}, "last_output": "out", "steps_left": 5}
    sample_info = {
        "task_id": "t1",
        "step": 1,
        "action": {"type": "run", "cmd": "ls"},
        "pass_rate": 0.5,
        "tests_passed": 1,
        "tests_total": 2,
        "passed_tests": ["test_1"],
        "failed_tests": ["test_2"],
        "regression": False,
        "step_reward": 0.49,
        "cumulative_return": 0.49,
        "all_tests_passed": False,
        "submitted": False,
        "ran_out_of_steps": False,
    }

    # Diagnostic retains all info
    d_info = diag.filter_info(sample_info)
    assert "passed_tests" in d_info
    assert d_info["pass_rate"] == 0.5
    assert diag.filter_reward(0.49, False, sample_info) == 0.49

    # Realistic hides passed_tests and pass_rate during ongoing steps
    r_info = real.filter_info(sample_info)
    assert "passed_tests" not in r_info
    assert "pass_rate" not in r_info
    assert r_info["step_reward"] == 0.49
    assert real.filter_reward(0.49, False, sample_info) == 0.49

    # Blind only returns minimal step info and strictly masks intermediate rewards
    b_info = blind.filter_info(sample_info)
    assert "action" not in b_info
    assert "pass_rate" not in b_info
    assert "passed_tests" not in b_info
    assert b_info["step"] == 1
    assert b_info["step_reward"] == 0.0
    assert b_info["cumulative_return"] == 0.0
    assert blind.filter_reward(0.49, False, sample_info) == 0.0

    # Blind reveals reward only when done=True
    terminal_info = dict(sample_info)
    terminal_info["all_tests_passed"] = True
    terminal_info["submitted"] = True
    b_term_info = blind.filter_info(terminal_info)
    assert b_term_info["done"] is True
    assert b_term_info["step_reward"] == 0.49
    assert b_term_info["cumulative_return"] == 0.49
    assert blind.filter_reward(0.49, True, terminal_info) == 0.49


def test_blind_feedback_prevents_oracle_leakage():
    """Verify that in blind mode, non-zero test improvements cannot be observed midway."""
    blind = get_feedback_adapter("blind")

    # Step 1: Agent tests pass partially
    step1_info = {
        "task_id": "v01_stream",
        "step": 1,
        "pass_rate": 0.6,
        "step_reward": 0.35,
        "cumulative_return": 0.35,
        "all_tests_passed": False,
        "submitted": False,
        "ran_out_of_steps": False,
    }
    r1, filtered1 = blind.filter_step(0.35, False, step1_info)
    assert r1 == 0.0
    assert filtered1["step_reward"] == 0.0
    assert filtered1["cumulative_return"] == 0.0
    assert "pass_rate" not in filtered1
    assert filtered1["done"] is False

    # Step 2: Final submission
    step2_info = {
        "task_id": "v01_stream",
        "step": 2,
        "pass_rate": 1.0,
        "step_reward": 0.39,
        "cumulative_return": 0.74,
        "all_tests_passed": True,
        "submitted": True,
        "ran_out_of_steps": False,
    }
    r2, filtered2 = blind.filter_step(0.39, True, step2_info)
    assert r2 == 0.39
    assert filtered2["step_reward"] == 0.39
    assert filtered2["cumulative_return"] == 0.74
    assert filtered2["done"] is True


def test_task_validator_on_synthetic_task():
    validator = TaskValidator(sandbox_mode="local", repetitions=2, min_quality=2.0)
    valid_task = {
        "task_id": "test_sample_task",
        "suite": "v2",
        "version": 2,
        "difficulty": "medium",
        "bug_type": "off_by_one",
        "description": "Valid test task for unit test validation",
        "repo_files": {
            "calc.py": "def multiply(a, b): return a + b\n",  # Buggy: add instead of multiply
        },
        "tests": {
            "test_calc.py": (
                "from calc import multiply\n"
                "def test_1(): assert multiply(2, 2) == 4\n"   # Passes before fix (2+2 == 4)
                "def test_2(): assert multiply(3, 4) == 12\n"  # Fails before fix (3+4 != 12)
            ),
        },
        "reference_fix": {
            "calc.py": "def multiply(a, b): return a * b\n",
        },
        "metadata": {
            "quality_score": 4.0,
        },
    }

    report = validator.validate_task(valid_task)
    assert report.is_valid is True
    assert report.schema_valid is True
    assert report.before_fix_passed == 1
    assert report.before_fix_failed == 1
    assert report.after_fix_passed == 2
    assert report.after_fix_failed == 0
    assert report.is_flaky is False


def test_task_generator_determinism():
    from task_factory.generator import TaskGenerator
    gen = TaskGenerator(sandbox_mode="local")
    spec = {
        "task_id": "v_test_det",
        "category": "J",
        "difficulty": "medium",
        "sub_type": "precedence",
    }
    c1 = gen.generate_candidate(spec, seed=12345)
    c2 = gen.generate_candidate(spec, seed=12345)
    assert c1 == c2
    assert c1["repo_files"] == c2["repo_files"]
    assert c1["tests"] == c2["tests"]
    assert c1["reference_fix"] == c2["reference_fix"]


def test_task_generator_validation_and_quality():
    from task_factory.generator import TaskGenerator
    gen = TaskGenerator(sandbox_mode="local", repetitions=2, min_quality=3.5)
    spec = {
        "task_id": "v_test_gen_val",
        "category": "J",
        "difficulty": "medium",
        "sub_type": "precedence",
    }
    schema_obj, report, candidate = gen.generate_and_validate(spec, seed=42)
    assert schema_obj is not None
    assert report.is_valid is True
    assert report.schema_valid is True
    assert report.before_fix_passed > 0
    assert report.before_fix_failed > 0
    assert report.after_fix_failed == 0
    assert report.is_flaky is False
    assert report.quality.average_score >= 3.5


def test_task_generator_duplicate_rejection():
    from task_factory.generator import TaskGenerator
    gen = TaskGenerator(sandbox_mode="local", repetitions=2, min_quality=3.5, duplicate_threshold=0.85)
    spec = {
        "task_id": "v_test_dupe_1",
        "category": "J",
        "difficulty": "medium",
        "sub_type": "precedence",
    }
    cand = gen.generate_candidate(spec, seed=42)
    # Existing task corpus contains an identical task with another ID
    existing_corpus = [
        {
            "task_id": "v_existing_twin",
            "repo_files": cand["repo_files"],
            "tests": cand["tests"],
            "reference_fix": cand["reference_fix"],
        }
    ]
    schema_obj, report, _ = gen.generate_and_validate(spec, seed=42, existing_tasks=existing_corpus)
    assert schema_obj is None
    assert report.is_valid is False
    assert any("rejected by DuplicateDetector" in err for err in report.errors)
