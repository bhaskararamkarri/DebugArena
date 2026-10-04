from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import tempfile
import pytest

from scripts.make_review_pack import make_review_pack, generate_diff
from scripts.import_review import import_reviews


def test_generate_diff():
    orig = "def foo():\n    return False\n"
    mod = "def foo():\n    return True\n"
    diff = generate_diff(orig, mod, "foo.py")
    assert "--- a/foo.py (buggy)" in diff
    assert "+++ b/foo.py (agent fix)" in diff
    assert "-    return False" in diff
    assert "+    return True" in diff


def test_make_review_pack_and_import(tmp_path):
    out_dir = tmp_path / "review_pack"
    make_review_pack(output_dir=str(out_dir), max_episodes=3)

    md_file = out_dir / "review_pack.md"
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert "# DebugArena Expert Review Pack" in content

    example_json = out_dir / "reviews.json.example"
    assert example_json.exists()
    reviews_data = json.loads(example_json.read_text(encoding="utf-8"))
    assert len(reviews_data) > 0

    # Test importing with mock reviews
    mock_reviews = tmp_path / "reviews.json"
    mock_reviews.write_text(json.dumps([
        {
            "task_id": reviews_data[0]["task_id"],
            "human_score": 5,
            "human_comment": "Perfect fix",
        },
        {
            "task_id": "nonexistent_task",
            "human_score": 2,
            "human_comment": "Poor quality",
        }
    ]), encoding="utf-8")

    out_sft = tmp_path / "verified_sft.jsonl"
    count = import_reviews(
        reviews_path=str(mock_reviews),
        sft_path="dataset/debugarena_sft.jsonl",
        output_path=str(out_sft),
        min_score=4,
    )
    assert count >= 1
    assert out_sft.exists()
    with open(out_sft, "r", encoding="utf-8") as f:
        first_line = json.loads(f.readline())
        assert first_line["human_score"] == 5
        assert first_line["human_comment"] == "Perfect fix"
