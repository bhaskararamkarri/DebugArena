"""Tests for Clean-Clone Reproducibility Audit & Verification Harness (P0 #10)."""

import json
from pathlib import Path
import pytest
from scripts.reproduce_clean import (
    check_git_status,
    check_required_files,
    verify_task_inventory,
    run_offline_baseline,
    check_nebius_credentials,
    check_docker_sandbox,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_required_files_all_present():
    """Verify all mandatory project files exist."""
    files_check = check_required_files(REPO_ROOT)
    for path_str, exists in files_check.items():
        assert exists is True, f"Required file {path_str} is missing"


def test_git_status_check():
    """Verify git status helper extracts commit SHA and working tree state."""
    git_info = check_git_status(REPO_ROOT)
    assert git_info["is_git_repo"] is True
    assert git_info["commit_sha"] is not None
    assert len(git_info["commit_sha"]) == 40


def test_task_inventory_reproducibility():
    """Verify task inventory verification passes with exact 30 official / 70 v2 count and distinct hashes."""
    inv = verify_task_inventory(REPO_ROOT)
    assert inv["status"] == "PASS"
    assert inv["total_tasks"] == 100
    assert inv["official_tasks_count"] == 30
    assert inv["v2_tasks_count"] == 70
    assert len(inv["missing_on_disk"]) == 0
    assert "full_task_corpus_hash" in inv
    assert "official_task_manifest_hash" in inv
    assert inv["official_task_manifest_hash"] == "016fa52aa64aa6875ebf1615663c49eecbd7d4b2616167f02732145f418cad9f"
    assert len(inv["full_task_corpus_hash"]) == 64


def test_offline_baseline_reproducibility():
    """Verify offline mock solver executes cleanly in local sandbox mode."""
    res = run_offline_baseline(REPO_ROOT, suite="core")
    assert res["status"] == "PASS"
    assert res["success_rate"] == 1.0
    assert res["solved_tasks"] == 20


def test_docker_sandbox_reporting():
    """Verify docker sandbox check returns structured status without failing."""
    res = check_docker_sandbox()
    assert "available" in res
    if res["available"]:
        assert "version" in res
    else:
        assert "reason" in res or "note" in res


def test_nebius_credentials_reporting():
    """Verify nebius credential check returns structured status without leaking keys."""
    res = check_nebius_credentials()
    assert "configured" in res
    if res["configured"]:
        assert "masked_key" in res
        assert "..." in res["masked_key"]
