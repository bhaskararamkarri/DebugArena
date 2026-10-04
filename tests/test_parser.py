"""Unit tests for DebugArena v2 robust action parser."""

import pytest
from agentgym.agent import extract_action_json, validate_action_schema


def test_clean_direct_json():
    text = '{"type": "submit"}'
    action, needed = extract_action_json(text)
    assert action == {"type": "submit"}
    assert needed is False


def test_markdown_code_fence():
    text = """Here is the command to run:
```json
{"type": "run", "cmd": "python -m pytest"}
```
"""
    action, needed = extract_action_json(text)
    assert action == {"type": "run", "cmd": "python -m pytest"}
    assert needed is True


def test_think_tags_with_json():
    text = """<think>
We noticed an off-by-one error in range calculation.
We should edit mathutils.py to add +1 to the upper bound.
</think>
{"type": "edit", "path": "mathutils.py", "content": "def sum_range(a, b): return sum(range(a, b + 1))"}
"""
    action, needed = extract_action_json(text)
    assert action["type"] == "edit"
    assert action["path"] == "mathutils.py"
    assert "range(a, b + 1)" in action["content"]
    assert needed is True


def test_commentary_before_and_after_json():
    text = """We need to output a valid JSON action. The previous responses were error messages.

{"type": "run", "cmd": "python3 -c 'from account import Beneficiary'"}

Hope this command works.
"""
    action, needed = extract_action_json(text)
    assert action == {"type": "run", "cmd": "python3 -c 'from account import Beneficiary'"}
    assert needed is True


def test_multiple_json_objects_picks_last_valid_action():
    text = """{"metadata": {"status": "analyzing"}}
{"type": "edit", "path": "old.py", "content": "pass"}
{"type": "submit"}"""
    action, needed = extract_action_json(text)
    assert action == {"type": "submit"}
    assert needed is True


def test_pure_conversational_no_json():
    text = "We are in a debugging session. We have identified a potential issue in wrapper.py."
    action, needed = extract_action_json(text)
    assert action is None
    assert needed is True


def test_invalid_schema_json():
    text = '{"status": "success", "result": 42}'
    action, needed = extract_action_json(text)
    assert action is None
    assert needed is True
