"""Category A: Basic Debugging & Calibration Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class BasicCalibrationTaskGenerator(BaseGenerator):
    """Generates realistic basic calibration tasks (timezone parsing, semver precedence, rotated search)."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v29_datetime_timezone_normalization")
        sub_type = spec.get("sub_type", "timezone")

        if sub_type == "semver" or "semver" in task_id:
            return self._generate_semver_comparator(task_id, spec, seed)
        elif sub_type == "rotated_search" or "rotated" in task_id:
            return self._generate_rotated_search(task_id, spec, seed)
        elif sub_type == "jit_optimizer" or "jit" in task_id or "bytecode" in task_id:
            return self._generate_jit_optimizer(task_id, spec, seed)
        elif sub_type == "ast_rewriter" or "ast" in task_id or "shadowing" in task_id:
            return self._generate_ast_pattern_rewriter(task_id, spec, seed)
        return self._generate_timezone_normalization(task_id, spec, seed)

    def _generate_timezone_normalization(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "tz_parser.py": (
                '"""ISO-8601 timestamp and timezone offset parser."""\n\n'
                'import re\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class ParsedTimestamp:\n'
                '    year: int\n'
                '    month: int\n'
                '    day: int\n'
                '    hour: int\n'
                '    minute: int\n'
                '    second: int\n'
                '    offset_minutes: int\n\n\n'
                'ISO_REGEX = re.compile(\n'
                '    r"^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2}):(\\d{2})(?:Z|([+-])(\\d{2}):(\\d{2}))?$"\n'
                ')\n\n\n'
                'def parse_iso_timestamp(ts_str: str) -> Optional[ParsedTimestamp]:\n'
                '    match = ISO_REGEX.match(ts_str.strip())\n'
                '    if not match:\n'
                '        return None\n'
                '    y, m, d, hh, mm, ss = map(int, match.groups()[:6])\n'
                '    sign = match.group(7)\n'
                '    if sign:\n'
                '        off_h = int(match.group(8))\n'
                '        off_m = int(match.group(9))\n'
                '        # BUG: Fails to invert offset for negative sign properly\n'
                '        offset = (off_h * 60 + off_m) if sign == "+" else (off_h * 60 - off_m)\n'
                '    else:\n'
                '        offset = 0\n'
                '    return ParsedTimestamp(y, m, d, hh, mm, ss, offset)\n'
            ),
            "formatter.py": (
                '"""Timestamp UTC normalizer and epoch converter."""\n\n'
                'from tz_parser import ParsedTimestamp, parse_iso_timestamp\n\n\n'
                'class TimestampNormalizer:\n'
                '    @staticmethod\n'
                '    def to_utc_minutes_of_day(ts_str: str) -> int:\n'
                '        pt = parse_iso_timestamp(ts_str)\n'
                '        if not pt:\n'
                '            raise ValueError(f"Invalid timestamp: {ts_str}")\n'
                '        local_minutes = pt.hour * 60 + pt.minute\n'
                '        # Normalizing to UTC: utc = local - offset_minutes\n'
                '        # BUG: Modulo 1440 does not handle negative hour wrap-around correctly without +1440\n'
                '        utc_minutes = (local_minutes - pt.offset_minutes) % 1440\n'
                '        return utc_minutes\n'
            ),
        }

        reference_fix = {
            "tz_parser.py": (
                '"""ISO-8601 timestamp and timezone offset parser."""\n\n'
                'import re\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class ParsedTimestamp:\n'
                '    year: int\n'
                '    month: int\n'
                '    day: int\n'
                '    hour: int\n'
                '    minute: int\n'
                '    second: int\n'
                '    offset_minutes: int\n\n\n'
                'ISO_REGEX = re.compile(\n'
                '    r"^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2}):(\\d{2})(?:Z|([+-])(\\d{2}):(\\d{2}))?$"\n'
                ')\n\n\n'
                'def parse_iso_timestamp(ts_str: str) -> Optional[ParsedTimestamp]:\n'
                '    match = ISO_REGEX.match(ts_str.strip())\n'
                '    if not match:\n'
                '        return None\n'
                '    y, m, d, hh, mm, ss = map(int, match.groups()[:6])\n'
                '    sign = match.group(7)\n'
                '    if sign:\n'
                '        off_h = int(match.group(8))\n'
                '        off_m = int(match.group(9))\n'
                '        total_m = off_h * 60 + off_m\n'
                '        offset = total_m if sign == "+" else -total_m\n'
                '    else:\n'
                '        offset = 0\n'
                '    return ParsedTimestamp(y, m, d, hh, mm, ss, offset)\n'
            )
        }

        tests = {
            "test_timezone_norm.py": (
                'import pytest\n'
                'from tz_parser import parse_iso_timestamp\n'
                'from formatter import TimestampNormalizer\n\n\n'
                'def test_utc_zulu_timestamp():\n'
                '    pt = parse_iso_timestamp("2026-05-10T14:30:00Z")\n'
                '    assert pt is not None\n'
                '    assert pt.offset_minutes == 0\n'
                '    assert TimestampNormalizer.to_utc_minutes_of_day("2026-05-10T14:30:00Z") == 14 * 60 + 30\n\n\n'
                'def test_positive_offset_normalization():\n'
                '    # UTC+05:30 -> 10:30 local is 05:00 UTC (300 minutes)\n'
                '    pt = parse_iso_timestamp("2026-05-10T10:30:00+05:30")\n'
                '    assert pt is not None\n'
                '    assert pt.offset_minutes == 330\n'
                '    assert TimestampNormalizer.to_utc_minutes_of_day("2026-05-10T10:30:00+05:30") == 300\n\n\n'
                'def test_negative_offset_normalization():\n'
                '    # UTC-08:00 (PST) -> 12:00 local is 20:00 UTC (1200 minutes)\n'
                '    pt = parse_iso_timestamp("2026-05-10T12:00:00-08:00")\n'
                '    assert pt is not None\n'
                '    assert pt.offset_minutes == -480\n'
                '    assert TimestampNormalizer.to_utc_minutes_of_day("2026-05-10T12:00:00-08:00") == 1200\n\n\n'
                'def test_negative_offset_with_minutes():\n'
                '    # UTC-03:30 (Newfoundland) -> offset must be -210, not -150!\n'
                '    pt = parse_iso_timestamp("2026-05-10T12:00:00-03:30")\n'
                '    assert pt is not None\n'
                '    assert pt.offset_minutes == -210\n\n\n'
                'def test_invalid_string_raises_value_error():\n'
                '    with pytest.raises(ValueError):\n'
                '        TimestampNormalizer.to_utc_minutes_of_day("not-a-date")\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "easy",
            "bug_type": "timezone_offset_sign_subtraction_error",
            "categories": ["A", "F"],
            "description": "ISO timestamp parser subtracts minutes incorrectly when parsing negative timezone offsets.",
            "spec_notes": "parse_iso_timestamp must calculate negative offset as -(hours * 60 + minutes).",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 2,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "datetime",
            },
        }

    def _generate_semver_comparator(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "semver.py": (
                '"""Semantic version representation."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional, Tuple\n\n\n'
                '@dataclass\n'
                'class SemVer:\n'
                '    major: int\n'
                '    minor: int\n'
                '    patch: int\n'
                '    prerelease: Optional[str] = None\n\n'
                '    @classmethod\n'
                '    def parse(cls, version_str: str) -> "SemVer":\n'
                '        clean = version_str.strip().lstrip("v")\n'
                '        pre = None\n'
                '        if "-" in clean:\n'
                '            clean, pre = clean.split("-", 1)\n'
                '        parts = list(map(int, clean.split(".")))\n'
                '        while len(parts) < 3:\n'
                '            parts.append(0)\n'
                '        return cls(parts[0], parts[1], parts[2], pre)\n'
            ),
            "matcher.py": (
                '"""SemVer comparison and ordering engine."""\n\n'
                'from semver import SemVer\n\n\n'
                'class SemVerComparator:\n'
                '    @staticmethod\n'
                '    def compare(v1: SemVer, v2: SemVer) -> int:\n'
                '        """Returns -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2."""\n'
                '        if (v1.major, v1.minor, v1.patch) != (v2.major, v2.minor, v2.patch):\n'
                '            t1 = (v1.major, v1.minor, v1.patch)\n'
                '            t2 = (v2.major, v2.minor, v2.patch)\n'
                '            return 1 if t1 > t2 else -1\n\n'
                '        # Handle Prerelease precedence: standard release has HIGHER precedence than pre-release\n'
                '        # e.g., 1.0.0 > 1.0.0-alpha\n'
                '        # BUG: Inverted logic treats prerelease as greater than release\n'
                '        if v1.prerelease is None and v2.prerelease is not None:\n'
                '            return -1  # BUG: Should be +1\n'
                '        if v1.prerelease is not None and v2.prerelease is None:\n'
                '            return 1   # BUG: Should be -1\n\n'
                '        if v1.prerelease == v2.prerelease:\n'
                '            return 0\n'
                '        return 1 if str(v1.prerelease) > str(v2.prerelease) else -1\n'
            ),
        }

        reference_fix = {
            "matcher.py": (
                '"""SemVer comparison and ordering engine."""\n\n'
                'from semver import SemVer\n\n\n'
                'class SemVerComparator:\n'
                '    @staticmethod\n'
                '    def compare(v1: SemVer, v2: SemVer) -> int:\n'
                '        """Returns -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2."""\n'
                '        if (v1.major, v1.minor, v1.patch) != (v2.major, v2.minor, v2.patch):\n'
                '            t1 = (v1.major, v1.minor, v1.patch)\n'
                '            t2 = (v2.major, v2.minor, v2.patch)\n'
                '            return 1 if t1 > t2 else -1\n\n'
                '        # Standard release has HIGHER precedence than pre-release\n'
                '        if v1.prerelease is None and v2.prerelease is not None:\n'
                '            return 1\n'
                '        if v1.prerelease is not None and v2.prerelease is None:\n'
                '            return -1\n'
                '        if v1.prerelease == v2.prerelease:\n'
                '            return 0\n'
                '        return 1 if str(v1.prerelease) > str(v2.prerelease) else -1\n'
            )
        }

        tests = {
            "test_semver_comparator.py": (
                'from semver import SemVer\n'
                'from matcher import SemVerComparator\n\n\n'
                'def test_major_minor_patch_comparison():\n'
                '    v1 = SemVer.parse("1.2.3")\n'
                '    v2 = SemVer.parse("1.2.4")\n'
                '    v3 = SemVer.parse("2.0.0")\n'
                '    assert SemVerComparator.compare(v1, v2) == -1\n'
                '    assert SemVerComparator.compare(v2, v1) == 1\n'
                '    assert SemVerComparator.compare(v3, v2) == 1\n'
                '    assert SemVerComparator.compare(v1, v1) == 0\n\n\n'
                'def test_prerelease_lower_than_normal_release():\n'
                '    # 1.0.0 is strictly GREATER than 1.0.0-alpha\n'
                '    release = SemVer.parse("1.0.0")\n'
                '    prerelease = SemVer.parse("1.0.0-alpha")\n'
                '    assert SemVerComparator.compare(release, prerelease) == 1\n'
                '    assert SemVerComparator.compare(prerelease, release) == -1\n\n\n'
                'def test_prerelease_lexicographical_comparison():\n'
                '    v_alpha = SemVer.parse("1.0.0-alpha")\n'
                '    v_beta = SemVer.parse("1.0.0-beta")\n'
                '    assert SemVerComparator.compare(v_alpha, v_beta) == -1\n'
                '    assert SemVerComparator.compare(v_beta, v_alpha) == 1\n\n\n'
                'def test_v_prefix_parsing():\n'
                '    v = SemVer.parse("v2.1.0")\n'
                '    assert v.major == 2 and v.minor == 1 and v.patch == 0\n\n\n'
                'def test_equal_prereleases():\n'
                '    v1 = SemVer.parse("1.0.0-rc.1")\n'
                '    v2 = SemVer.parse("1.0.0-rc.1")\n'
                '    assert SemVerComparator.compare(v1, v2) == 0\n\n\n'
                'def test_sorting_version_list():\n'
                '    raw = ["1.0.0", "1.0.0-beta", "1.0.0-alpha", "0.9.0", "2.0.0"]\n'
                '    versions = [SemVer.parse(r) for r in raw]\n'
                '    # Bubble sort using comparator\n'
                '    for i in range(len(versions)):\n'
                '        for j in range(len(versions) - 1):\n'
                '            if SemVerComparator.compare(versions[j], versions[j + 1]) == 1:\n'
                '                versions[j], versions[j + 1] = versions[j + 1], versions[j]\n'
                '    assert [f"{v.major}.{v.minor}.{v.patch}" + (f"-{v.prerelease}" if v.prerelease else "") for v in versions] == [\n'
                '        "0.9.0", "1.0.0-alpha", "1.0.0-beta", "1.0.0", "2.0.0"\n'
                '    ]\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "easy",
            "bug_type": "semver_prerelease_precedence_inversion",
            "categories": ["A", "B"],
            "description": "SemVer comparator inverts pre-release precedence rule, rating pre-releases higher than normal releases.",
            "spec_notes": "SemVer standard stipulates 1.0.0 > 1.0.0-alpha.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 2,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "packaging",
            },
        }

    def _generate_rotated_search(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "indexer.py": (
                '"""Rotated sorted array minimum pivot indexer."""\n\n'
                'from typing import List\n\n\n'
                'class RotatedIndexer:\n'
                '    def __init__(self, nums: List[int]):\n'
                '        self.nums = nums\n\n'
                '    def find_pivot_index(self) -> int:\n'
                '        """Returns the index of the minimum element in rotated sorted array."""\n'
                '        if not self.nums:\n'
                '            return -1\n'
                '        left, right = 0, len(self.nums) - 1\n'
                '        while left < right:\n'
                '            mid = (left + right) // 2\n'
                '            # BUG: Compares mid against left element instead of right boundary element,\n'
                '            # failing to converge on the minimum pivot in unrotated and multi-element arrays!\n'
                '            if self.nums[mid] < self.nums[left]:\n'
                '                right = mid\n'
                '            else:\n'
                '                left = mid + 1\n'
                '        return left\n'
            ),
            "search.py": (
                '"""Search service utilizing rotated pivot index."""\n\n'
                'from typing import List\n'
                'from indexer import RotatedIndexer\n\n\n'
                'class SearchService:\n'
                '    @staticmethod\n'
                '    def find_minimum_value(dataset: List[int]) -> int:\n'
                '        if not dataset:\n'
                '            return -1\n'
                '        idx = RotatedIndexer(dataset)\n'
                '        pivot_pos = idx.find_pivot_index()\n'
                '        return dataset[pivot_pos]\n'
            ),
        }

        reference_fix = {
            "indexer.py": (
                '"""Rotated sorted array minimum pivot indexer."""\n\n'
                'from typing import List\n\n\n'
                'class RotatedIndexer:\n'
                '    def __init__(self, nums: List[int]):\n'
                '        self.nums = nums\n\n'
                '    def find_pivot_index(self) -> int:\n'
                '        """Returns the index of the minimum element in rotated sorted array."""\n'
                '        if not self.nums:\n'
                '            return -1\n'
                '        left, right = 0, len(self.nums) - 1\n'
                '        while left < right:\n'
                '            mid = (left + right) // 2\n'
                '            if self.nums[mid] > self.nums[right]:\n'
                '                left = mid + 1\n'
                '            else:\n'
                '                right = mid\n'
                '        return left\n'
            )
        }

        tests = {
            "test_rotated_search.py": (
                'from search import SearchService\n'
                'from indexer import RotatedIndexer\n\n\n'
                'def test_standard_rotated_array():\n'
                '    nums = [4, 5, 6, 7, 1, 2, 3]\n'
                '    idx = RotatedIndexer(nums)\n'
                '    assert idx.find_pivot_index() == 4\n'
                '    assert SearchService.find_minimum_value(nums) == 1\n\n\n'
                'def test_unrotated_sorted_array():\n'
                '    nums = [1, 2, 3, 4, 5]\n'
                '    idx = RotatedIndexer(nums)\n'
                '    assert idx.find_pivot_index() == 0\n'
                '    assert SearchService.find_minimum_value(nums) == 1\n\n\n'
                'def test_two_element_rotation():\n'
                '    nums = [3, 1]\n'
                '    idx = RotatedIndexer(nums)\n'
                '    assert idx.find_pivot_index() == 1\n'
                '    assert SearchService.find_minimum_value(nums) == 1\n\n\n'
                'def test_pivot_at_last_element():\n'
                '    nums = [2, 3, 4, 5, 1]\n'
                '    idx = RotatedIndexer(nums)\n'
                '    assert idx.find_pivot_index() == 4\n'
                '    assert SearchService.find_minimum_value(nums) == 1\n\n\n'
                'def test_single_element_array():\n'
                '    nums = [42]\n'
                '    idx = RotatedIndexer(nums)\n'
                '    assert idx.find_pivot_index() == 0\n'
                '    assert SearchService.find_minimum_value(nums) == 42\n\n\n'
                'def test_empty_array():\n'
                '    idx = RotatedIndexer([])\n'
                '    assert idx.find_pivot_index() == -1\n'
                '    assert SearchService.find_minimum_value([]) == -1\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "easy",
            "bug_type": "binary_search_rotated_pivot_boundary_inversion",
            "categories": ["A", "B"],
            "description": "Rotated binary search indexer compares mid against left element instead of right boundary, failing on unrotated and rotated arrays.",
            "spec_notes": "RotatedIndexer.find_pivot_index must compare nums[mid] > nums[right] to find pivot.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 2,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "algorithms",
            },
        }

    def _generate_jit_optimizer(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "opcodes.py": (
                '"""Bytecode opcode and instruction definitions."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Optional\n\n\n'
                '@dataclass\n'
                'class Instruction:\n'
                '    op: str  # "CONST", "LOAD", "STORE", "ADD", "CALL", "RETURN"\n'
                '    arg: Optional[Any] = None\n'
                '    target_var: Optional[str] = None\n'
                '    has_side_effect: bool = False\n'
            ),
            "basic_block.py": (
                '"""CFG basic block node."""\n\n'
                'from typing import List\n'
                'from opcodes import Instruction\n\n\n'
                'class BasicBlock:\n'
                '    def __init__(self, block_id: str):\n'
                '        self.block_id = block_id\n'
                '        self.instructions: List[Instruction] = []\n'
                '        self.predecessors: List["BasicBlock"] = []\n'
                '        self.successors: List["BasicBlock"] = []\n'
            ),
            "dce_pass.py": (
                '"""Dead code elimination optimization pass."""\n\n'
                'from typing import List, Set\n'
                'from basic_block import BasicBlock\n'
                'from opcodes import Instruction\n\n\n'
                'class DeadCodeEliminationPass:\n'
                '    @staticmethod\n'
                '    def optimize_block(block: BasicBlock) -> List[Instruction]:\n'
                '        # Collect variables read by instructions\n'
                '        used_vars: Set[str] = set()\n'
                '        for instr in reversed(block.instructions):\n'
                '            if instr.op == "RETURN" and instr.arg:\n'
                '                used_vars.add(str(instr.arg))\n'
                '            elif instr.op == "ADD" and isinstance(instr.arg, tuple):\n'
                '                used_vars.add(str(instr.arg[0]))\n'
                '                used_vars.add(str(instr.arg[1]))\n\n'
                '        # Backward dead store elimination\n'
                '        surviving: List[Instruction] = []\n'
                '        for instr in reversed(block.instructions):\n'
                '            # BUG: Strips CALL / side-effect instructions if target_var is not in used_vars!\n'
                '            # Fails to treat instr.has_side_effect or op in ("CALL", "RETURN") as unconditional roots!\n'
                '            if instr.target_var and instr.target_var not in used_vars and not instr.has_side_effect:\n'
                '                continue  # Dead store removed\n'
                '            elif instr.op == "CALL" and instr.target_var and instr.target_var not in used_vars:\n'
                '                continue  # BUG: Erroneously prunes external function calls!\n\n'
                '            surviving.append(instr)\n'
                '            if instr.target_var and instr.target_var in used_vars:\n'
                '                used_vars.discard(instr.target_var)\n'
                '            if instr.op in ("LOAD", "CONST") and instr.arg:\n'
                '                used_vars.add(str(instr.arg))\n'
                '        return list(reversed(surviving))\n'
            ),
            "optimizer.py": (
                '"""JIT compiler optimization pipeline."""\n\n'
                'from basic_block import BasicBlock\n'
                'from dce_pass import DeadCodeEliminationPass\n'
                'from opcodes import Instruction\n\n\n'
                'class JITOptimizer:\n'
                '    def __init__(self):\n'
                '        self.dce = DeadCodeEliminationPass()\n\n'
                '    def run(self, block: BasicBlock) -> None:\n'
                '        block.instructions = self.dce.optimize_block(block)\n'
            ),
        }

        reference_fix = {
            "dce_pass.py": (
                '"""Dead code elimination optimization pass."""\n\n'
                'from typing import List, Set\n'
                'from basic_block import BasicBlock\n'
                'from opcodes import Instruction\n\n\n'
                'class DeadCodeEliminationPass:\n'
                '    @staticmethod\n'
                '    def optimize_block(block: BasicBlock) -> List[Instruction]:\n'
                '        used_vars: Set[str] = set()\n'
                '        for instr in reversed(block.instructions):\n'
                '            if instr.op == "RETURN" and instr.arg:\n'
                '                used_vars.add(str(instr.arg))\n'
                '            elif instr.op == "ADD" and isinstance(instr.arg, tuple):\n'
                '                used_vars.add(str(instr.arg[0]))\n'
                '                used_vars.add(str(instr.arg[1]))\n\n'
                '        surviving: List[Instruction] = []\n'
                '        for instr in reversed(block.instructions):\n'
                '            is_side_effect = instr.has_side_effect or instr.op in ("CALL", "RETURN")\n'
                '            if instr.target_var and instr.target_var not in used_vars and not is_side_effect:\n'
                '                continue\n\n'
                '            surviving.append(instr)\n'
                '            if instr.target_var and instr.target_var in used_vars:\n'
                '                used_vars.discard(instr.target_var)\n'
                '            if instr.op in ("LOAD", "CONST") and instr.arg:\n'
                '                used_vars.add(str(instr.arg))\n'
                '        return list(reversed(surviving))\n'
            )
        }

        tests = {
            "test_jit_dce.py": (
                'from basic_block import BasicBlock\n'
                'from opcodes import Instruction\n'
                'from optimizer import JITOptimizer\n\n\n'
                'def test_pure_dead_stores_eliminated():\n'
                '    bb = BasicBlock("b1")\n'
                '    bb.instructions = [\n'
                '        Instruction("CONST", 10, target_var="unused_x"),\n'
                '        Instruction("CONST", 20, target_var="y"),\n'
                '        Instruction("RETURN", arg="y"),\n'
                '    ]\n'
                '    opt = JITOptimizer()\n'
                '    opt.run(bb)\n'
                '    ops = [(i.op, i.target_var) for i in bb.instructions]\n'
                '    assert ops == [("CONST", "y"), ("RETURN", None)]\n\n\n'
                'def test_function_calls_with_side_effects_preserved():\n'
                '    bb = BasicBlock("b2")\n'
                '    bb.instructions = [\n'
                '        Instruction("CALL", "send_email_webhook", target_var="unused_resp", has_side_effect=True),\n'
                '        Instruction("CONST", 100, target_var="ret_val"),\n'
                '        Instruction("RETURN", arg="ret_val"),\n'
                '    ]\n'
                '    opt = JITOptimizer()\n'
                '    opt.run(bb)\n'
                '    # Function call MUST be preserved despite unused return target_var\n'
                '    assert any(i.op == "CALL" for i in bb.instructions)\n'
                '    assert len(bb.instructions) == 3\n\n\n'
                'def test_dependency_chain_kept():\n'
                '    bb = BasicBlock("b3")\n'
                '    bb.instructions = [\n'
                '        Instruction("CONST", 5, target_var="a"),\n'
                '        Instruction("CONST", 10, target_var="b"),\n'
                '        Instruction("ADD", ("a", "b"), target_var="c"),\n'
                '        Instruction("RETURN", arg="c"),\n'
                '    ]\n'
                '    opt = JITOptimizer()\n'
                '    opt.run(bb)\n'
                '    assert len(bb.instructions) == 4\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "compiler_dce_side_effect_call_pruning",
            "categories": ["B", "K"],
            "description": "JIT dead code elimination pass drops function calls with unused return values, deleting required external side-effects.",
            "spec_notes": "DeadCodeEliminationPass must preserve instructions with has_side_effect=True or op=='CALL'.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "compilers",
            },
        }

    def _generate_ast_pattern_rewriter(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "ast_nodes.py": (
                '"""AST node representations."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Any, List, Optional\n\n\n'
                '@dataclass\n'
                'class ASTNode:\n'
                '    pass\n\n\n'
                '@dataclass\n'
                'class VarNode(ASTNode):\n'
                '    name: str\n\n\n'
                '@dataclass\n'
                'class AssignNode(ASTNode):\n'
                '    target: str\n'
                '    value: Any\n\n\n'
                '@dataclass\n'
                'class FunctionDefNode(ASTNode):\n'
                '    fn_name: str\n'
                '    params: List[str]\n'
                '    body: List[ASTNode] = field(default_factory=list)\n'
            ),
            "symbol_table.py": (
                '"""Hierarchical lexical scope symbol table."""\n\n'
                'from typing import Dict, Optional\n\n\n'
                'class Scope:\n'
                '    def __init__(self, parent: Optional["Scope"] = None):\n'
                '        self.parent = parent\n'
                '        self.bindings: Dict[str, str] = {}\n\n'
                '    def define(self, name: str, alias: str) -> None:\n'
                '        self.bindings[name] = alias\n\n'
                '    def lookup(self, name: str) -> Optional[str]:\n'
                '        if name in self.bindings:\n'
                '            return self.bindings[name]\n'
                '        if self.parent:\n'
                '            return self.parent.lookup(name)\n'
                '        return None\n'
            ),
            "rewriter.py": (
                '"""AST alpha-renaming rewriter."""\n\n'
                'from typing import List\n'
                'from ast_nodes import ASTNode, AssignNode, FunctionDefNode, VarNode\n'
                'from symbol_table import Scope\n\n\n'
                'class ASTAlphaRewriter:\n'
                '    def rewrite(self, node: ASTNode, current_scope: Scope) -> ASTNode:\n'
                '        if isinstance(node, VarNode):\n'
                '            mapped = current_scope.lookup(node.name)\n'
                '            return VarNode(mapped if mapped else node.name)\n\n'
                '        elif isinstance(node, AssignNode):\n'
                '            mapped = current_scope.lookup(node.target)\n'
                '            val = node.value\n'
                '            if isinstance(val, ASTNode):\n'
                '                val = self.rewrite(val, current_scope)\n'
                '            return AssignNode(mapped if mapped else node.target, val)\n\n'
                '        elif isinstance(node, FunctionDefNode):\n'
                '            # BUG: Reuses current_scope directly instead of creating a child Scope(parent=current_scope)\n'
                '            # Shadowed parameters overwrite parent bindings in current_scope!\n'
                '            for p in node.params:\n'
                '                current_scope.define(p, f"{node.fn_name}_{p}")\n'
                '            new_body = [self.rewrite(stmt, current_scope) for stmt in node.body]\n'
                '            return FunctionDefNode(node.fn_name, [f"{node.fn_name}_{p}" for p in node.params], new_body)\n\n'
                '        return node\n'
            ),
        }

        reference_fix = {
            "rewriter.py": (
                '"""AST alpha-renaming rewriter."""\n\n'
                'from typing import List\n'
                'from ast_nodes import ASTNode, AssignNode, FunctionDefNode, VarNode\n'
                'from symbol_table import Scope\n\n\n'
                'class ASTAlphaRewriter:\n'
                '    def rewrite(self, node: ASTNode, current_scope: Scope) -> ASTNode:\n'
                '        if isinstance(node, VarNode):\n'
                '            mapped = current_scope.lookup(node.name)\n'
                '            return VarNode(mapped if mapped else node.name)\n\n'
                '        elif isinstance(node, AssignNode):\n'
                '            mapped = current_scope.lookup(node.target)\n'
                '            val = node.value\n'
                '            if isinstance(val, ASTNode):\n'
                '                val = self.rewrite(val, current_scope)\n'
                '            return AssignNode(mapped if mapped else node.target, val)\n\n'
                '        elif isinstance(node, FunctionDefNode):\n'
                '            inner_scope = Scope(parent=current_scope)\n'
                '            for p in node.params:\n'
                '                inner_scope.define(p, f"{node.fn_name}_{p}")\n'
                '            new_body = [self.rewrite(stmt, inner_scope) for stmt in node.body]\n'
                '            return FunctionDefNode(node.fn_name, [f"{node.fn_name}_{p}" for p in node.params], new_body)\n\n'
                '        return node\n'
            )
        }

        tests = {
            "test_ast_rewriter.py": (
                'from ast_nodes import AssignNode, FunctionDefNode, VarNode\n'
                'from rewriter import ASTAlphaRewriter\n'
                'from symbol_table import Scope\n\n\n'
                'def test_global_scope_renaming():\n'
                '    s = Scope()\n'
                '    s.define("x", "g_x")\n'
                '    rewriter = ASTAlphaRewriter()\n'
                '    res = rewriter.rewrite(VarNode("x"), s)\n'
                '    assert isinstance(res, VarNode)\n'
                '    assert res.name == "g_x"\n\n\n'
                'def test_nested_shadowed_parameters_isolated():\n'
                '    outer = Scope()\n'
                '    outer.define("x", "outer_x")\n'
                '    # Function with parameter x shadows outer x\n'
                '    fn = FunctionDefNode("inner", ["x"], [AssignNode("x", VarNode("x"))])\n'
                '    rewriter = ASTAlphaRewriter()\n'
                '    rewritten_fn = rewriter.rewrite(fn, outer)\n'
                '    assert isinstance(rewritten_fn, FunctionDefNode)\n'
                '    assert rewritten_fn.params == ["inner_x"]\n'
                '    body_assign = rewritten_fn.body[0]\n'
                '    assert body_assign.target == "inner_x"\n'
                '    assert body_assign.value.name == "inner_x"\n'
                '    # Outer scope MUST NOT have its binding overwritten!\n'
                '    assert outer.lookup("x") == "outer_x"\n\n\n'
                'def test_unshadowed_outer_access_in_nested_fn():\n'
                '    outer = Scope()\n'
                '    outer.define("y", "global_y")\n'
                '    fn = FunctionDefNode("compute", ["z"], [VarNode("y")])\n'
                '    rewriter = ASTAlphaRewriter()\n'
                '    res = rewriter.rewrite(fn, outer)\n'
                '    assert res.body[0].name == "global_y"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "ast_rewriter_scope_shadowing_corruption",
            "categories": ["B", "E"],
            "description": "AST alpha-renamer mutates parent scope directly instead of creating nested child scopes, corrupting outer variable bindings.",
            "spec_notes": "ASTAlphaRewriter.rewrite must instantiate a child Scope for FunctionDefNode.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "compilers",
            },
        }

