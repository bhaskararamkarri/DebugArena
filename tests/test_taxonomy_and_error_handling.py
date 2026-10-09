"""Unit tests for failure taxonomy, evaluation status, judge error handling, and config fail-fast."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentgym.agent import validate_action_schema
from agentgym.judge import CodeJudge
from agentgym.provider import ConfigurationError, load_config
from agentgym.taxonomy import EvaluationStatus, FailureCategory, classify_episode_outcome


class TestTaxonomyClassification:
    """Test suite for evaluation status and failure taxonomy classification."""

    def test_correct_fix_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=1.0)
        assert status == EvaluationStatus.PASS
        assert cat == FailureCategory.CORRECT_FIX

    def test_partial_fix_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=0.5)
        assert status == EvaluationStatus.PARTIAL
        assert cat == FailureCategory.PARTIAL_FIX

    def test_wrong_fix_submitted(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, submitted=True)
        assert status == EvaluationStatus.FAIL
        assert cat == FailureCategory.WRONG_FIX

    def test_regression_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, regression=True)
        assert status == EvaluationStatus.FAIL
        assert cat == FailureCategory.REGRESSION

    def test_timeout_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, timed_out=True)
        assert status == EvaluationStatus.TIMEOUT
        assert cat == FailureCategory.TIMEOUT

    def test_out_of_steps_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, ran_out_of_steps=True)
        assert status == EvaluationStatus.FAIL
        assert cat == FailureCategory.OUT_OF_STEPS

    def test_malformed_action_outcome(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, invalid_json_count=2)
        assert status == EvaluationStatus.INVALID_AGENT_OUTPUT
        assert cat == FailureCategory.MALFORMED_ACTION

    def test_security_violation_error(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, error="PathTraversalSecurityError: Path escapes sandbox")
        assert status == EvaluationStatus.SECURITY_VIOLATION
        assert cat == FailureCategory.SECURITY_VIOLATION

    def test_provider_failure_error(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, error="ProviderPolicyError: Nebius API key not set")
        assert status == EvaluationStatus.ENVIRONMENT_ERROR
        assert cat == FailureCategory.PROVIDER_FAILURE

    def test_docker_sandbox_failure_error(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, error="Docker daemon unavailable")
        assert status == EvaluationStatus.ENVIRONMENT_ERROR
        assert cat == FailureCategory.SANDBOX_FAILURE

    def test_solve_only_mode_without_oracle(self):
        status, cat = classify_episode_outcome(pass_rate=0.0, has_oracle=False)
        assert status == EvaluationStatus.SOLVE_ONLY
        assert cat == FailureCategory.NONE


class TestJudgeNoScoreFabrication:
    """Test suite ensuring Judge never fabricates score 4 when offline or on error."""

    def test_judge_offline_returns_none_score_and_judge_unavailable_status(self, monkeypatch):
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
        judge = CodeJudge(config_path="config.yaml")
        # Ensure client is None when no API key
        judge.client = None

        result = judge.evaluate(
            description="Fix calculation bug",
            original_files={"math.py": "def add(a, b): return a - b"},
            final_files={"math.py": "def add(a, b): return a + b"},
            pass_rate=1.0,
        )
        assert result["score"] is None
        assert result["status"] == EvaluationStatus.JUDGE_UNAVAILABLE.value
        assert "offline" in result["rationale"].lower()

    def test_judge_api_exception_returns_none_score_and_error(self, monkeypatch):
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
        judge = CodeJudge(config_path="config.yaml")

        with patch.object(judge.client.chat.completions, "create", side_effect=Exception("API Connection Refused")):
            result = judge.evaluate(
                description="Fix calculation bug",
                original_files={"math.py": "def add(a, b): return a - b"},
                final_files={"math.py": "def add(a, b): return a + b"},
                pass_rate=1.0,
            )
            assert result["score"] is None
            assert result["status"] == EvaluationStatus.JUDGE_UNAVAILABLE.value
            assert "API Connection Refused" in result["error"]

    def test_judge_failed_tests_returns_bounded_score(self):
        judge = CodeJudge(config_path="config.yaml")
        result = judge.evaluate(
            description="Fix calculation bug",
            original_files={"math.py": "def add(a, b): return a - b"},
            final_files={"math.py": "def add(a, b): return a - b"},
            pass_rate=0.0,
        )
        assert result["score"] == 1
        assert result["status"] == EvaluationStatus.FAIL.value

        partial_result = judge.evaluate(
            description="Fix calculation bug",
            original_files={"math.py": "def add(a, b): return a - b"},
            final_files={"math.py": "def add(a, b): return a - b"},
            pass_rate=0.5,
        )
        assert partial_result["score"] == 2
        assert partial_result["status"] == EvaluationStatus.PARTIAL.value


class TestConfigurationFailFast:
    """Test suite for failing fast on malformed config YAML."""

    def test_malformed_yaml_raises_configuration_error(self, tmp_path):
        bad_yaml = tmp_path / "corrupt.yaml"
        bad_yaml.write_text("invalid: [unclosed list", encoding="utf-8")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(str(bad_yaml))
        assert "Failed to parse configuration YAML" in str(exc_info.value)


class TestActionSchemaValidation:
    """Test suite for hardened action schema validation."""

    def test_reject_null_bytes_in_edit_path(self):
        valid, err, _ = validate_action_schema({"type": "edit", "path": "test\x00.py", "content": "print(1)"})
        assert not valid
        assert "null byte" in err.lower()

    def test_reject_null_bytes_in_run_cmd(self):
        valid, err, _ = validate_action_schema({"type": "run", "cmd": "ls\x00 -la"})
        assert not valid
        assert "null byte" in err.lower()

    def test_reject_oversized_edit_payload(self):
        huge_content = "x" * (6 * 1024 * 1024)
        valid, err, _ = validate_action_schema({"type": "edit", "path": "big.py", "content": huge_content})
        assert not valid
        assert "exceeds maximum size" in err.lower()

    def test_reject_oversized_run_command(self):
        huge_cmd = "echo " + ("a" * 12000)
        valid, err, _ = validate_action_schema({"type": "run", "cmd": huge_cmd})
        assert not valid
        assert "exceeds maximum length" in err.lower()
