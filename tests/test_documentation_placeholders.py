"""Tests for detecting unresolved placeholders and template artifacts in project documentation."""

import re
from pathlib import Path

import pytest


class TestDocumentationPlaceholders:
    """Test suite for P0 #6: Documentation placeholder removal and integrity."""

    def test_readme_has_no_unresolved_placeholders(self):
        """Verify README.md contains no unresolved placeholder tokens."""
        content = Path("README.md").read_text(encoding="utf-8")
        assert "<REPO_URL>" not in content
        assert "your_nebius_api_key" in content or "NEBIUS_API_KEY" in content  # Legitimate config example

        # Assert no unfinished template tags
        forbidden_patterns = [
            r"\[TODO\]",
            r"\[TBD\]",
            r"\[TBA\]",
            r"\[YOUR_[A-Z_]+\]",
            r"\[INSERT_[A-Z_]+\]",
            r"<INSERT_[A-Z_]+>",
            r"<YOUR_[A-Z_]+>",
            r"lorem ipsum",
        ]
        for pat in forbidden_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            assert not matches, f"Found unresolved placeholder pattern '{pat}' in README.md: {matches}"

    def test_submission_has_no_unresolved_placeholders(self):
        """Verify SUBMISSION.md contains no unresolved repository URL or placeholder tokens."""
        content = Path("SUBMISSION.md").read_text(encoding="utf-8")
        assert "<REPO_URL>" not in content

        forbidden_patterns = [
            r"\[TODO\]",
            r"\[TBD\]",
            r"\[TBA\]",
            r"\[YOUR_[A-Z_]+\]",
            r"\[INSERT_[A-Z_]+\]",
            r"<INSERT_[A-Z_]+>",
            r"<YOUR_[A-Z_]+>",
            r"lorem ipsum",
        ]
        for pat in forbidden_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            assert not matches, f"Found unresolved placeholder pattern '{pat}' in SUBMISSION.md: {matches}"

    def test_canonical_repo_url_in_docs(self):
        """Verify README and SUBMISSION reference the canonical repo URL."""
        readme = Path("README.md").read_text(encoding="utf-8")
        submission = Path("SUBMISSION.md").read_text(encoding="utf-8")
        canonical_url = "https://github.com/bhaskararamkarri/DebugArena.git"

        assert canonical_url in readme
        assert canonical_url in submission

    def test_documented_scripts_and_paths_exist(self):
        """Verify all scripts and entrypoints documented in README actually exist on disk."""
        documented_paths = [
            "dashboard/app.py",
            "scripts/run_eval.py",
            "scripts/verify_tasks.py",
            "scripts/export_dataset.py",
            "config.yaml",
            ".env.example",
            "pyproject.toml",
        ]
        for p in documented_paths:
            assert Path(p).exists(), f"Path '{p}' documented in README does not exist on disk."

