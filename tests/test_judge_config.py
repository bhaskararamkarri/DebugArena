"""Tests for configuration-driven Judge model resolution and API request tracing."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentgym.judge import CodeJudge
from agentgym.manager import BenchmarkManager, RunConfig
from agentgym.runner import EpisodeRunner


class TestJudgeModelConfiguration:
    """Test suite for P0 #4: Judge model configuration without hard-coded mismatch."""

    def test_judge_resolves_model_from_default_config(self, monkeypatch):
        """Test 1: CodeJudge resolves judge model directly from config.yaml."""
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        judge = CodeJudge(config_path="config.yaml")
        assert judge.model_name == "nvidia/Nemotron-3-Ultra-550b-a55b"

    def test_custom_judge_model_override(self, tmp_path, monkeypatch):
        """Test 2: CodeJudge accepts and preserves a custom judge model."""
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        custom_model = "debugarena/test-judge-model-v1"
        judge = CodeJudge(model_name=custom_model, config_path="config.yaml")
        assert judge.model_name == custom_model

    def test_custom_config_yaml_judge_model(self, tmp_path, monkeypatch):
        """Test 3: CodeJudge reads judge model configured in custom config YAML."""
        custom_yaml = tmp_path / "custom_judge.yaml"
        custom_yaml.write_text(
            """
providers:
  nebius:
    base_url: "https://api.tokenfactory.nebius.com/v1"
    api_key_env: "NEBIUS_API_KEY"
models:
  nemotron_judge:
    name: "debugarena/custom-nemotron-judge-999b"
    provider: "nebius"
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        judge = CodeJudge(config_path=str(custom_yaml))
        assert judge.model_name == "debugarena/custom-nemotron-judge-999b"

    def test_api_request_uses_exact_configured_judge_model(self, monkeypatch):
        """Test 4: Actual API request payload contains the exact configured judge model."""
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        custom_model = "debugarena/test-judge-model-v1"
        judge = CodeJudge(model_name=custom_model, config_path="config.yaml")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"score": 5, "rationale": "Perfect fix"}'))
        ]

        with patch.object(judge.client.chat.completions, "create", return_value=mock_response) as mock_create:
            eval_result = judge.evaluate(
                description="Fix bug",
                original_files={"main.py": "x = 1"},
                final_files={"main.py": "x = 2"},
                pass_rate=1.0,
            )
            assert eval_result["score"] == 5
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            # Verify the exact model passed to API request matches configured model
            assert call_kwargs["model"] == "debugarena/test-judge-model-v1"

    def test_missing_judge_model_in_config_fails_clearly(self, tmp_path, monkeypatch):
        """Test 5: If judge model is missing from configuration, fail explicitly."""
        empty_yaml = tmp_path / "empty_config.yaml"
        empty_yaml.write_text(
            """
providers:
  nebius:
    base_url: "https://api.tokenfactory.nebius.com/v1"
    api_key_env: "NEBIUS_API_KEY"
models:
  nemotron_nano:
    name: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        with pytest.raises(ValueError) as exc_info:
            CodeJudge(config_path=str(empty_yaml))
        assert "Judge model is not configured" in str(exc_info.value)

    def test_run_metadata_records_exact_judge_model(self, tmp_path, monkeypatch):
        """Test 6: Run metadata in summary.json records the exact configured judge model."""
        monkeypatch.setenv("NEBIUS_API_KEY", "fake-key")
        runner = EpisodeRunner(
            tasks_dir="tasks",
            runs_dir=str(tmp_path / "runs"),
            enable_judge=True,
            judge_model="debugarena/test-judge-manifest-v2",
        )

        assert runner.judge is not None
        assert runner.judge.model_name == "debugarena/test-judge-manifest-v2"

        res = runner.run_batch(
            task_ids=["t01_off_by_one"],
            model_name="nemotron_nano",
            run_id="test_judge_meta_run",
            workers=1,
            max_steps=2,
            sandbox_mode="local",
            use_mock_solver=True,
            execution_mode="hackathon",
            provider="nebius",
        )
        assert len(res) == 1

        summary_file = tmp_path / "runs" / "test_judge_meta_run" / "summary.json"
        assert summary_file.exists()
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        assert summary_data["judge_model"] == "debugarena/test-judge-manifest-v2"
        assert summary_data["model"] == "nemotron_nano"
