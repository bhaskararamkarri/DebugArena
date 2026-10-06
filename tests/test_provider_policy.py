"""Tests for provider policy enforcement and zero silent fallback in Hackathon mode."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentgym.agent import Agent, MockAgent
from agentgym.judge import CodeJudge
from agentgym.manager import BenchmarkManager, RunConfig, RunState, RunStatus
from agentgym.provider import (
    ExecutionMode,
    NEBIUS_CANONICAL_ENDPOINT,
    ProviderPolicyError,
    validate_execution_config,
    resolve_provider_config,
)
from agentgym.runner import EpisodeRunner


class TestProviderPolicy:
    """Test suite for P0 #2: Hackathon Nebius-only execution without fallback."""

    def test_hackathon_forces_nebius(self, monkeypatch):
        """Test 1: Hackathon mode with Nebius provider passes validation."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key-12345")
        resolved = validate_execution_config(
            execution_mode="hackathon",
            provider="nebius",
            fallback=None,
        )
        assert resolved["execution_mode"] == "hackathon"
        assert resolved["provider"] == "nebius"
        assert resolved["fallback"] is None

    def test_hackathon_rejects_openrouter(self, monkeypatch):
        """Test 2: Hackathon mode rejects OpenRouter provider."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
        with pytest.raises(ProviderPolicyError) as exc_info:
            validate_execution_config(
                execution_mode="hackathon",
                provider="openrouter",
            )
        assert "Hackathon execution requires Nebius" in str(exc_info.value)
        assert "openrouter" in str(exc_info.value).lower()

    def test_hackathon_rejects_nvidia(self, monkeypatch):
        """Test 3: Hackathon mode rejects NVIDIA provider."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test-nv-key")
        with pytest.raises(ProviderPolicyError) as exc_info:
            validate_execution_config(
                execution_mode="hackathon",
                provider="nvidia",
            )
        assert "Hackathon execution requires Nebius" in str(exc_info.value)
        assert "nvidia" in str(exc_info.value).lower()

    def test_hackathon_rejects_fallback(self, monkeypatch):
        """Test 4: Hackathon mode rejects any fallback provider."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key-12345")
        with pytest.raises(ProviderPolicyError) as exc_info:
            validate_execution_config(
                execution_mode="hackathon",
                provider="nebius",
                fallback="openrouter",
            )
        assert "No provider fallback is enabled in hackathon mode" in str(exc_info.value)

    def test_missing_nebius_credentials_fails_fast(self, monkeypatch):
        """Test 5: Missing Nebius credentials fails fast before run execution."""
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
        with pytest.raises(ProviderPolicyError) as exc_info:
            validate_execution_config(
                execution_mode="hackathon",
                provider="nebius",
                use_mock_solver=False,
                use_noop_solver=False,
            )
        err_msg = str(exc_info.value)
        assert "Hackathon execution requires Nebius" in err_msg
        assert "Nebius API configuration is missing" in err_msg
        assert "No provider fallback is enabled in hackathon mode" in err_msg

    def test_development_mode_allows_other_providers(self, monkeypatch):
        """Test 6: Development mode allows alternative configured providers."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key-dev")
        resolved = validate_execution_config(
            execution_mode="development",
            provider="openrouter",
            fallback="nvidia",
        )
        assert resolved["execution_mode"] == "development"
        assert resolved["provider"] == "openrouter"
        assert resolved["fallback"] == "nvidia"

    def test_no_fallback_after_api_failure(self, monkeypatch):
        """Test 7: When Nebius API fails, agent does NOT fall back to OpenRouter/NVIDIA."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

        agent = Agent(
            model_name="nvidia/nemotron-3-nano-30b-a3b",
            provider="nebius",
            execution_mode="hackathon",
        )
        assert agent.provider == "nebius"

        # Mock the client's chat completions to raise an API error
        with patch.object(agent.client.chat.completions, "create", side_effect=RuntimeError("Nebius connection error")):
            # Fast sleep during test
            with patch("time.sleep", return_value=None):
                action, lat, hist, ext = agent.act({"description": "test", "steps_left": 5, "files": {}})

        # Provider must still be nebius, client must NOT have switched to OpenRouter or NVIDIA
        assert agent.provider == "nebius"
        # The action will reflect invalid/error response, not a silent fallback to OpenRouter
        assert action["type"] == "run"
        assert "echo 'Invalid JSON action'" in action["cmd"]

    def test_run_metadata_records_resolved_provider(self, tmp_path, monkeypatch):
        """Test 8: Run metadata summary.json records execution_mode, provider, and fallback."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key")
        runner = EpisodeRunner(
            tasks_dir="tasks",
            runs_dir=str(tmp_path / "runs"),
            enable_judge=False,
            enable_tracing=False,
        )

        res = runner.run_batch(
            task_ids=["t01_off_by_one"],
            model_name="nemotron_nano",
            run_id="test_meta_run",
            workers=1,
            max_steps=2,
            sandbox_mode="local",
            use_mock_solver=True,
            execution_mode="hackathon",
            provider="nebius",
        )
        assert len(res) == 1

        summary_file = tmp_path / "runs" / "test_meta_run" / "summary.json"
        assert summary_file.exists()
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        assert summary_data["execution_mode"] == "hackathon"
        assert summary_data["provider"] == "nebius"
        assert summary_data["fallback"] is None

    def test_benchmark_manager_validates_before_starting_thread(self, monkeypatch, tmp_path):
        """BenchmarkManager fails immediately on start_run when hackathon config is invalid."""
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
        manager = BenchmarkManager(runs_dir=str(tmp_path / "runs"), tasks_dir="tasks")

        cfg = RunConfig(
            run_id="test_fail_fast",
            model_name="nemotron_nano",
            provider="openrouter",  # Invalid in hackathon mode
            execution_mode="hackathon",
            task_ids=["t01_off_by_one"],
            use_mock_solver=False,
        )

        with pytest.raises(ProviderPolicyError) as exc_info:
            manager.start_run(cfg)

        assert "Hackathon execution requires Nebius" in str(exc_info.value)
        # Verify no active run was created
        assert not manager.is_run_active("test_fail_fast")
        # Verify no run state was saved
        assert not (tmp_path / "runs" / "test_fail_fast" / "run_state.json").exists()

    def test_canonical_endpoint_constant(self):
        """P0 #3 Test 1: Canonical endpoint is https://api.tokenfactory.nebius.com/v1."""
        assert NEBIUS_CANONICAL_ENDPOINT == "https://api.tokenfactory.nebius.com/v1"

    def test_resolve_provider_config_returns_canonical_nebius_endpoint(self, monkeypatch):
        """P0 #3 Test 2: resolve_provider_config returns canonical Token Factory base_url."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key-xyz")
        info = resolve_provider_config("nebius")
        assert info["provider"] == "nebius"
        assert info["base_url"] == "https://api.tokenfactory.nebius.com/v1"
        assert info["api_key_env"] == "NEBIUS_API_KEY"

    def test_agent_client_uses_canonical_endpoint(self, monkeypatch):
        """P0 #3 Test 3: Agent client is initialized with canonical Token Factory endpoint."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key-agent")
        agent = Agent(
            model_name="nvidia/nemotron-3-nano-30b-a3b",
            provider="nebius",
            execution_mode="hackathon",
        )
        assert str(agent.client.base_url).rstrip("/") == "https://api.tokenfactory.nebius.com/v1"

    def test_judge_client_uses_canonical_endpoint(self, monkeypatch):
        """P0 #3 Test 4: Judge client is initialized with canonical Token Factory endpoint."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key-judge")
        judge = CodeJudge(
            provider="nebius",
            execution_mode="hackathon",
        )
        assert judge.client is not None
        assert str(judge.client.base_url).rstrip("/") == "https://api.tokenfactory.nebius.com/v1"

    def test_custom_endpoint_override_honored(self, tmp_path, monkeypatch):
        """P0 #3 Test 5: Custom base_url in config is honored without hardcoded bypass."""
        custom_yaml = tmp_path / "custom_config.yaml"
        custom_yaml.write_text(
            """
providers:
  nebius:
    base_url: "https://custom.proxy.endpoint/v1"
    api_key_env: "NEBIUS_API_KEY"
models:
  nemotron_nano:
    name: "nvidia/nemotron-3-nano-30b-a3b"
    provider: "nebius"
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
        info = resolve_provider_config("nebius", config_path=str(custom_yaml))
        assert info["base_url"] == "https://custom.proxy.endpoint/v1"

        agent = Agent(
            model_name="nvidia/nemotron-3-nano-30b-a3b",
            provider="nebius",
            config_path=str(custom_yaml),
            execution_mode="hackathon",
        )
        assert str(agent.client.base_url).rstrip("/") == "https://custom.proxy.endpoint/v1"

    def test_no_runtime_use_of_old_studio_endpoint(self, monkeypatch):
        """P0 #3 Test 6: Verify default resolution never produces old api.studio.nebius.ai."""
        monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
        info = resolve_provider_config("nebius")
        assert "api.studio.nebius.ai" not in info["base_url"]
        assert info["base_url"] == "https://api.tokenfactory.nebius.com/v1"

