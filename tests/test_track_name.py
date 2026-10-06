"""Tests for authoritative hackathon track name verification."""

from pathlib import Path

import yaml

from agentgym.provider import HACKATHON_TRACK_NAME, load_config


class TestHackathonTrackName:
    """Test suite for P0 #5: Hackathon track name correctness."""

    def test_canonical_track_name_constant(self):
        """Test 1: Constant HACKATHON_TRACK_NAME is exactly 'Coding and Agentic Engineering'."""
        assert HACKATHON_TRACK_NAME == "Coding and Agentic Engineering"

    def test_config_yaml_track_name(self):
        """Test 2: config.yaml contains the canonical hackathon_track field."""
        cfg = load_config("config.yaml")
        assert cfg.get("hackathon_track") == "Coding and Agentic Engineering"

    def test_readme_track_name(self):
        """Test 3: README.md references the canonical track name and no obsolete track names."""
        content = Path("README.md").read_text(encoding="utf-8")
        assert "Track: Coding and Agentic Engineering" in content
        assert "Agent Gym & Coding Environments" not in content

    def test_submission_doc_track_name(self):
        """Test 4: SUBMISSION.md references the canonical track name and no obsolete track names."""
        content = Path("SUBMISSION.md").read_text(encoding="utf-8")
        assert "Track: *Coding and Agentic Engineering*" in content
        assert "Agent Gym & Coding Environments" not in content
