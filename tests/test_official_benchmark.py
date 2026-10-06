"""Tests for the Canonical Official Benchmark Result (P0 #8)."""

import json
import re
from pathlib import Path
import pytest


OFFICIAL_DIR = Path("runs/official")
MANIFEST_FILE = OFFICIAL_DIR / "manifest.json"
RESULTS_FILE = OFFICIAL_DIR / "results.json"
ENV_FILE = OFFICIAL_DIR / "environment.json"
SUMMARY_FILE = OFFICIAL_DIR / "summary.json"
TRAJECTORIES_FILE = OFFICIAL_DIR / "trajectories.jsonl"
README_FILE = OFFICIAL_DIR / "README.md"


def test_official_directory_exists():
    """Verify that runs/official exists and is a directory."""
    assert OFFICIAL_DIR.exists(), "runs/official directory does not exist"
    assert OFFICIAL_DIR.is_dir(), "runs/official must be a directory"


def test_official_required_files_exist():
    """Verify that all mandatory official benchmark files exist."""
    assert MANIFEST_FILE.exists(), "manifest.json must exist under runs/official"
    assert RESULTS_FILE.exists(), "results.json must exist under runs/official"
    assert ENV_FILE.exists(), "environment.json must exist under runs/official"
    assert SUMMARY_FILE.exists(), "summary.json must exist under runs/official"
    assert TRAJECTORIES_FILE.exists(), "trajectories.jsonl must exist under runs/official"
    assert README_FILE.exists(), "README.md must exist under runs/official"


def test_manifest_structure_and_provenance():
    """Verify that manifest.json contains all required metadata and valid provenance."""
    assert MANIFEST_FILE.exists()
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Repository & Git Provenance
    repo_meta = manifest.get("repository", {})
    assert "git_repository" in repo_meta
    assert "commit_sha" in repo_meta
    assert re.match(r"^[0-9a-fA-F]{40}$", repo_meta["commit_sha"]), "commit_sha must be a 40-char git SHA"
    assert "working_tree_cleanliness" in repo_meta
    assert "task_manifest_hash" in repo_meta
    assert re.match(r"^[0-9a-fA-F]{64}$", repo_meta["task_manifest_hash"]), "task_manifest_hash must be SHA-256"
    assert "task_ids" in repo_meta
    assert isinstance(repo_meta["task_ids"], list)
    assert len(repo_meta["task_ids"]) == repo_meta.get("task_count", 0)
    assert repo_meta["task_count"] > 0

    # Model & Provider Policy
    model_meta = manifest.get("model", {})
    assert model_meta.get("agent_model") == "nvidia/nemotron-3-super-120b-a12b"
    assert model_meta.get("provider") == "nebius"
    assert "https://api.tokenfactory.nebius.com/v1" in model_meta.get("endpoint_base_url", "")
    assert model_meta.get("execution_mode") == "hackathon"
    assert model_meta.get("fallback_policy") == "strict_error_no_fallback"
    assert "judge_model" in model_meta

    # Configuration Hashes & Sandbox
    config_meta = manifest.get("configuration", {})
    assert "config_hash" in config_meta
    assert re.match(r"^[0-9a-fA-F]{64}$", config_meta["config_hash"]), "config_hash must be SHA-256"
    assert config_meta.get("sandbox_type") == "docker"
    assert "prompt_hash" in config_meta
    assert config_meta.get("max_steps") == 10
    assert config_meta.get("temperature") == 0.2
    assert config_meta.get("response_format") == "json_object"

    # Execution & Environment Metadata
    exec_meta = manifest.get("execution", {})
    assert "run_id" in exec_meta
    assert "timestamp" in exec_meta
    assert "docker_image_digest" in exec_meta
    assert exec_meta.get("docker_image_digest", "").startswith("sha256:")

    # Results & Metrics
    res_meta = manifest.get("results", {})
    assert "total_tasks" in res_meta
    assert "solved_tasks" in res_meta
    assert "success_rate" in res_meta
    assert "avg_steps" in res_meta
    assert "avg_return" in res_meta
    assert "wilson_95_ci" in res_meta
    assert res_meta["total_tasks"] == len(repo_meta["task_ids"])
    assert res_meta["solved_tasks"] <= res_meta["total_tasks"]
    assert 0.0 <= res_meta["success_rate"] <= 1.0


def test_results_consistency():
    """Verify results.json matches summary and manifest metrics."""
    assert RESULTS_FILE.exists()
    assert SUMMARY_FILE.exists()
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results_data = json.load(f)
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert results_data["total_tasks"] == summary_data["total_tasks"] == manifest_data["results"]["total_tasks"]
    assert results_data["solved_tasks"] == summary_data["solved_tasks"] == manifest_data["results"]["solved_tasks"]
    assert len(results_data["episodes"]) == results_data["total_tasks"]
    assert len(summary_data["episodes"]) == summary_data["total_tasks"]


def test_trajectories_file_integrity():
    """Verify trajectories.jsonl contains non-empty valid JSON records matching total tasks."""
    assert TRAJECTORIES_FILE.exists()
    episodes_seen = set()
    with open(TRAJECTORIES_FILE, "r", encoding="utf-8") as f:
        line_count = 0
        for line in f:
            if line.strip():
                line_count += 1
                rec = json.loads(line)
                assert "run_id" in rec
                assert "episode_id" in rec
                assert "task_id" in rec
                assert "step" in rec
                assert "action" in rec
                episodes_seen.add(rec["episode_id"])

    assert line_count > 0
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert len(episodes_seen) == summary["total_tasks"]


def test_environment_snapshot_contents():
    """Verify environment.json captures container sandbox, platform, and python details."""
    assert ENV_FILE.exists()
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        env = json.load(f)

    assert "os" in env
    assert "python_version" in env
    assert "docker" in env
    assert env["docker"].get("sandbox_type") == "docker"
    assert env["docker"].get("image_digest", "").startswith("sha256:")
    assert "sandbox_constraints" in env["docker"]
    assert env["docker"]["sandbox_constraints"].get("network_disabled") is True
    assert "packages" in env


def test_official_readme_exists_and_detailed():
    """Verify runs/official/README.md covers all required documentation items."""
    assert README_FILE.exists()
    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Canonical Official Benchmark Result" in content
    assert "nvidia/nemotron-3-super-120b-a12b" in content
    assert "Nebius Token Factory" in content
    assert "Docker Sandbox" in content
    assert "task_manifest_hash" in content or "Manifest Hash" in content
    assert "commit_sha" in content or "Commit SHA" in content


def test_no_secrets_in_official_artifacts():
    """Verify no API keys, bearer tokens, or sensitive credentials are leak in runs/official."""
    secret_patterns = [
        re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}", re.IGNORECASE),  # JWT
        re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
        re.compile(r"nvapi-[A-Za-z0-9]{20,}", re.IGNORECASE),
    ]

    for p in OFFICIAL_DIR.glob("*"):
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pattern in secret_patterns:
                assert not pattern.search(text), f"Potential secret leak found in {p.name}"


def test_canonical_directory_uniqueness():
    """Verify that only ONE canonical official directory exists (no competing official-* dirs)."""
    runs_dir = Path("runs")
    competing = [
        p.name for p in runs_dir.iterdir()
        if p.is_dir() and p.name.startswith("official") and p.name != "official"
    ]
    assert not competing, f"Found competing official directories: {competing}"
