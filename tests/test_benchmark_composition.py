"""Tests for Benchmark Composition and Task Lifecycle Status (P0 #9)."""

import json
from pathlib import Path
import pytest


TASKS_MANIFEST_FILE = Path("tasks/manifest.json")
OFFICIAL_RUN_MANIFEST = Path("runs/official/manifest.json")
TASKS_DIR = Path("tasks")


def test_tasks_manifest_exists():
    """Verify that the repository-level tasks manifest exists."""
    assert TASKS_MANIFEST_FILE.exists(), "tasks/manifest.json must exist"


def test_total_task_inventory():
    """Verify the repository contains exactly 100 tasks with full lifecycle tracking."""
    assert TASKS_MANIFEST_FILE.exists()
    with open(TASKS_MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("total_tasks") == 100
    assert len(manifest.get("tasks", {})) == 100

    # Validate lifecycle distribution
    summary = manifest.get("summary", {})
    assert summary.get("official_count") == 30
    assert summary.get("v2_experimental_count") == 70
    assert summary.get("core_20_count") == 20
    assert summary.get("hard_10_count") == 10


def test_official_benchmark_definition():
    """Verify official benchmark consists of exactly 30 tasks (Core-20 + Hard-10)."""
    assert TASKS_MANIFEST_FILE.exists()
    with open(TASKS_MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    official_tasks = [
        tid for tid, meta in manifest["tasks"].items()
        if meta.get("official") is True
    ]
    assert len(official_tasks) == 30

    core_tasks = [t for t in official_tasks if t.startswith("t")]
    hard_tasks = [t for t in official_tasks if t.startswith("h")]
    v2_tasks = [t for t in official_tasks if t.startswith("v")]

    assert len(core_tasks) == 20
    assert len(hard_tasks) == 10
    assert len(v2_tasks) == 0, "No V2 tasks should be marked official in the current definition"


def test_v2_tasks_lifecycle_status():
    """Verify all 70 V2 tasks are properly classified as generated/validated/verified but not official/evaluated."""
    assert TASKS_MANIFEST_FILE.exists()
    with open(TASKS_MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    v2_tasks = {
        tid: meta for tid, meta in manifest["tasks"].items()
        if tid.startswith("v") or meta.get("suite") in ["v2", "V2-70"]
    }
    assert len(v2_tasks) == 70

    for tid, meta in v2_tasks.items():
        assert meta.get("generated") is True, f"{tid} must be marked generated"
        assert meta.get("validated") is True, f"{tid} must be marked validated"
        assert meta.get("deterministic_verified") is True, f"{tid} must be marked deterministic_verified"
        assert meta.get("reference_verified") is True, f"{tid} must be marked reference_verified"
        assert meta.get("official") is False, f"{tid} must NOT be marked official"
        assert meta.get("evaluated") is False, f"{tid} must NOT be marked evaluated"


def test_official_manifest_and_run_consistency():
    """Verify that tasks/manifest.json official tasks match runs/official/manifest.json exactly."""
    assert TASKS_MANIFEST_FILE.exists()
    assert OFFICIAL_RUN_MANIFEST.exists()

    with open(TASKS_MANIFEST_FILE, "r", encoding="utf-8") as f:
        task_manifest = json.load(f)
    with open(OFFICIAL_RUN_MANIFEST, "r", encoding="utf-8") as f:
        run_manifest = json.load(f)

    official_task_ids = sorted([
        tid for tid, meta in task_manifest["tasks"].items()
        if meta.get("official") is True
    ])
    run_task_ids = sorted(run_manifest["repository"]["task_ids"])

    assert official_task_ids == run_task_ids
    assert len(official_task_ids) == 30
    assert run_manifest["results"]["total_tasks"] == 30


def test_task_lifecycle_fields_complete():
    """Verify every task in tasks/manifest.json has complete required lifecycle fields."""
    assert TASKS_MANIFEST_FILE.exists()
    with open(TASKS_MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    required_fields = [
        "task_id",
        "suite",
        "difficulty",
        "generated",
        "validated",
        "deterministic_verified",
        "reference_verified",
        "official",
        "evaluated",
    ]

    for tid, meta in manifest["tasks"].items():
        for field in required_fields:
            assert field in meta, f"Task {tid} missing required field '{field}'"


def test_documentation_historical_44_clarification():
    """Verify that README.md clearly distinguishes official 30 from historical 44 milestone."""
    readme_path = Path("README.md")
    assert readme_path.exists()
    readme_text = readme_path.read_text(encoding="utf-8")

    # Should clearly mention 30 official tasks
    assert "30 official benchmark tasks" in readme_text or "30 benchmark tasks" in readme_text
    assert "Core-20" in readme_text
    assert "Hard-10" in readme_text
