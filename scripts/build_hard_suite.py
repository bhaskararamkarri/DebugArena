"""Builds the 10 Hard Suite tasks (h01..h10) in tasks/hard/."""

import json
from pathlib import Path

HARD_TASKS = [
    {
        "task_id": "h01",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "interval_merging",
        "description": "The scheduling engine fails to combine overlapping and touching time windows, sometimes truncating earlier ranges or leaving adjacent slots unmerged.",
        "spec_notes": "IntervalMerger.merge must sort intervals by (start, end) and merge overlapping ranges into [start, max(end1, end2)]. When allow_adjacent=True, intervals touching at boundaries (end == start) must also be merged.",
        "repo_files": {
            "interval.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class TimeInterval:
    start: int
    end: int

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError("start must be <= end")

    def overlaps(self, other: "TimeInterval", allow_adjacent: bool = True) -> bool:
        if allow_adjacent:
            return self.start <= other.end and other.start <= self.end
        return self.start < other.end and other.start < self.end
""",
            "sorter.py": """from interval import TimeInterval

def sort_intervals(intervals: list[TimeInterval]) -> list[TimeInterval]:
    \"\"\"Sorts intervals primarily by ending boundary for optimal greedy allocation.\"\"\"
    # Misleading docstring and distractor sorting logic:
    return sorted(intervals, key=lambda x: (x.end, x.start))
""",
            "merger.py": """from interval import TimeInterval
from sorter import sort_intervals

class IntervalMerger:
    def __init__(self, allow_adjacent: bool = True):
        self.allow_adjacent = allow_adjacent

    def merge(self, intervals: list[TimeInterval]) -> list[TimeInterval]:
        if not intervals:
            return []
        ordered = sort_intervals(intervals)
        merged = [ordered[0]]
        for current in ordered[1:]:
            prev = merged[-1]
            if prev.end > current.start:
                merged[-1] = TimeInterval(prev.start, current.end)
            else:
                merged.append(current)
        return merged
"""
        },
        "tests": {
            "test_merger.py": """from interval import TimeInterval
from merger import IntervalMerger

def test_empty_and_single():
    merger = IntervalMerger()
    assert merger.merge([]) == []
    single = TimeInterval(1, 5)
    assert merger.merge([single]) == [single]

def test_disjoint_intervals():
    merger = IntervalMerger()
    inp = [TimeInterval(1, 2), TimeInterval(5, 6)]
    assert merger.merge(inp) == [TimeInterval(1, 2), TimeInterval(5, 6)]

def test_overlapping_merge():
    merger = IntervalMerger()
    inp = [TimeInterval(1, 4), TimeInterval(2, 6)]
    assert merger.merge(inp) == [TimeInterval(1, 6)]

def test_contained_interval():
    merger = IntervalMerger()
    inp = [TimeInterval(1, 10), TimeInterval(2, 5)]
    assert merger.merge(inp) == [TimeInterval(1, 10)]

def test_adjacent_boundaries():
    merger = IntervalMerger(allow_adjacent=True)
    inp = [TimeInterval(1, 3), TimeInterval(3, 5)]
    assert merger.merge(inp) == [TimeInterval(1, 5)]
"""
        },
        "reference_fix": {
            "sorter.py": """from interval import TimeInterval

def sort_intervals(intervals: list[TimeInterval]) -> list[TimeInterval]:
    \"\"\"Sorts intervals by starting boundary, then ending boundary.\"\"\"
    return sorted(intervals, key=lambda x: (x.start, x.end))
""",
            "merger.py": """from interval import TimeInterval
from sorter import sort_intervals

class IntervalMerger:
    def __init__(self, allow_adjacent: bool = True):
        self.allow_adjacent = allow_adjacent

    def merge(self, intervals: list[TimeInterval]) -> list[TimeInterval]:
        if not intervals:
            return []
        ordered = sort_intervals(intervals)
        merged = [ordered[0]]
        for current in ordered[1:]:
            prev = merged[-1]
            can_merge = (prev.end >= current.start) if self.allow_adjacent else (prev.end > current.start)
            if can_merge:
                merged[-1] = TimeInterval(prev.start, max(prev.end, current.end))
            else:
                merged.append(current)
        return merged
"""
        }
    },
    {
        "task_id": "h02",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "binary_search_bounds",
        "description": "Search queries for target values in sorted arrays produce incorrect boundary indices or return count 0 when values exist multiple times at array edges.",
        "spec_notes": "find_range returns SearchRange(first_index, last_index, count) where indices are 0-based and count is total occurrences, or (-1, -1, 0) if absent.",
        "repo_files": {
            "models.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class SearchRange:
    first_index: int
    last_index: int
    count: int
""",
            "predicates.py": """# Misleading comment:
def is_monotonic(nums: list[int]) -> bool:
    \"\"\"Assumes strictly ascending numbers with no duplicate values.\"\"\"
    return all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1))
""",
            "searcher.py": """from models import SearchRange
from predicates import is_monotonic

class RangeSearcher:
    def find_range(self, nums: list[int], target: int) -> SearchRange:
        if not nums:
            return SearchRange(-1, -1, 0)

        # Bug: finds single match index without expanding to true first/last boundaries
        low, high = 0, len(nums) - 1
        found_idx = -1
        while low <= high:
            mid = (low + high) // 2
            if nums[mid] == target:
                found_idx = mid
                break
            elif nums[mid] < target:
                low = mid + 1
            else:
                high = mid - 1

        if found_idx == -1:
            return SearchRange(-1, -1, 0)

        return SearchRange(found_idx, found_idx, 1)
"""
        },
        "tests": {
            "test_searcher.py": """from models import SearchRange
from searcher import RangeSearcher

def test_empty_list():
    s = RangeSearcher()
    assert s.find_range([], 5) == SearchRange(-1, -1, 0)

def test_target_absent():
    s = RangeSearcher()
    assert s.find_range([1, 3, 5, 7], 4) == SearchRange(-1, -1, 0)

def test_single_element_found():
    s = RangeSearcher()
    assert s.find_range([4], 4) == SearchRange(0, 0, 1)

def test_multiple_occurrences():
    s = RangeSearcher()
    assert s.find_range([1, 2, 2, 2, 3], 2) == SearchRange(1, 3, 3)

def test_boundary_elements():
    s = RangeSearcher()
    assert s.find_range([5, 5, 5, 8], 5) == SearchRange(0, 2, 3)
"""
        },
        "reference_fix": {
            "searcher.py": """from models import SearchRange
from predicates import is_monotonic

class RangeSearcher:
    def find_range(self, nums: list[int], target: int) -> SearchRange:
        if not nums:
            return SearchRange(-1, -1, 0)

        low, high = 0, len(nums) - 1
        first = -1
        while low <= high:
            mid = (low + high) // 2
            if nums[mid] == target:
                first = mid
                high = mid - 1
            elif nums[mid] < target:
                low = mid + 1
            else:
                high = mid - 1

        low, high = 0, len(nums) - 1
        last = -1
        while low <= high:
            mid = (low + high) // 2
            if nums[mid] == target:
                last = mid
                low = mid + 1
            elif nums[mid] < target:
                low = mid + 1
            else:
                high = mid - 1

        count = (last - first + 1) if (first != -1 and last != -1) else 0
        return SearchRange(first, last, count)
"""
        }
    },
    {
        "task_id": "h03",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "topological_sort_cycle",
        "description": "The build orchestrator executes tasks in an unstable sequence when multiple tasks are ready, and fails to abort with an error when circular references exist between components.",
        "spec_notes": "plan resolves dependency order. Ready nodes (0 in-degree) must be picked in lexicographical order for determinism. If graph has cycles, raise CyclicDependencyError.",
        "repo_files": {
            "errors.py": """class CyclicDependencyError(Exception):
    \"\"\"Raised when a cycle is detected in the dependency graph.\"\"\"
    pass
""",
            "graph.py": """from collections import defaultdict

class DependencyGraph:
    def __init__(self):
        self.adj = defaultdict(set)
        self.in_degree = defaultdict(int)
        self.all_nodes = set()

    def add_dependency(self, prerequisite: str, target: str):
        self.all_nodes.add(prerequisite)
        self.all_nodes.add(target)
        if target not in self.adj[prerequisite]:
            self.adj[prerequisite].add(target)
            self.in_degree[target] += 1
            if prerequisite not in self.in_degree:
                self.in_degree[prerequisite] = 0
""",
            "resolver.py": """from errors import CyclicDependencyError
from graph import DependencyGraph

class ExecutionPlanner:
    def plan(self, graph: DependencyGraph) -> list[str]:
        # Bug 1: iterates in reverse order instead of sorted lexicographical order
        ready = sorted([n for n in graph.all_nodes if graph.in_degree[n] == 0], reverse=True)
        in_degrees = dict(graph.in_degree)
        order = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for neighbor in sorted(graph.adj[node], reverse=True):
                in_degrees[neighbor] -= 1
                if in_degrees[neighbor] == 0:
                    ready.append(neighbor)
        # Bug 2: Does not check for cycles
        return order
"""
        },
        "tests": {
            "test_resolver.py": """import pytest
from errors import CyclicDependencyError
from graph import DependencyGraph
from resolver import ExecutionPlanner

def test_empty_graph():
    g = DependencyGraph()
    p = ExecutionPlanner()
    assert p.plan(g) == []

def test_single_dependency():
    g = DependencyGraph()
    g.add_dependency("build", "test")
    p = ExecutionPlanner()
    assert p.plan(g) == ["build", "test"]

def test_lexicographical_tiebreak():
    g = DependencyGraph()
    g.add_dependency("core", "zebra")
    g.add_dependency("core", "alpha")
    p = ExecutionPlanner()
    assert p.plan(g) == ["core", "alpha", "zebra"]

def test_direct_cycle_raises():
    g = DependencyGraph()
    g.add_dependency("A", "B")
    g.add_dependency("B", "A")
    p = ExecutionPlanner()
    with pytest.raises(CyclicDependencyError):
        p.plan(g)

def test_indirect_cycle_raises():
    g = DependencyGraph()
    g.add_dependency("A", "B")
    g.add_dependency("B", "C")
    g.add_dependency("C", "A")
    p = ExecutionPlanner()
    with pytest.raises(CyclicDependencyError):
        p.plan(g)
"""
        },
        "reference_fix": {
            "resolver.py": """from errors import CyclicDependencyError
from graph import DependencyGraph

class ExecutionPlanner:
    def plan(self, graph: DependencyGraph) -> list[str]:
        in_degrees = {n: graph.in_degree[n] for n in graph.all_nodes}
        ready = sorted([n for n in graph.all_nodes if in_degrees[n] == 0])
        order = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for neighbor in sorted(graph.adj[node]):
                in_degrees[neighbor] -= 1
                if in_degrees[neighbor] == 0:
                    ready.append(neighbor)
                    ready.sort()
        if len(order) < len(graph.all_nodes):
            raise CyclicDependencyError("Cyclic dependency detected in graph.")
        return order
"""
        }
    },
    {
        "task_id": "h04",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "csv_parser_quoting",
        "description": "Exported tabular text is corrupted: records containing commas inside quotation marks or escaped double quotes lose trailing columns or fail to preserve internal quotes.",
        "spec_notes": "parse splits lines into field tokens. Fields wrapped in double quotes can contain commas. Escaped quotes are represented as paired quotes '\"\"' which collapse into a single '\"'.",
        "repo_files": {
            "models.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class CSVDocument:
    total_lines: int
    rows: list[list[str]]
""",
            "lexer.py": """# Misleading helper:
def sanitize_chars(raw: str) -> str:
    \"\"\"Strip non-ascii formatting characters.\"\"\"
    return raw
""",
            "parser.py": """from models import CSVDocument
from lexer import sanitize_chars

class StrictCSVReader:
    def parse(self, content: str) -> list[list[str]]:
        if not content.strip():
            return []
        lines = content.splitlines()
        rows = []
        for line in lines:
            fields = []
            cur = []
            in_quote = False
            i = 0
            while i < len(line):
                ch = line[i]
                if ch == '"':
                    in_quote = not in_quote
                elif ch == ',' and not in_quote:
                    fields.append("".join(cur))
                    cur = []
                else:
                    cur.append(ch)
                i += 1
            fields.append("".join(cur))
            rows.append(fields)
        return rows
"""
        },
        "tests": {
            "test_csv.py": """from parser import StrictCSVReader

def test_empty_content():
    reader = StrictCSVReader()
    assert reader.parse("") == []

def test_unquoted_simple_row():
    reader = StrictCSVReader()
    assert reader.parse("a,b,c") == [["a", "b", "c"]]

def test_commas_inside_quotes():
    reader = StrictCSVReader()
    assert reader.parse('a,"b,c",d') == [["a", "b,c", "d"]]

def test_escaped_double_quotes():
    reader = StrictCSVReader()
    assert reader.parse('a,"b""c",d') == [["a", 'b"c', "d"]]

def test_multiple_lines_mixed():
    reader = StrictCSVReader()
    res = reader.parse('1,2\\n"3,4",5')
    assert res == [["1", "2"], ["3,4", "5"]]
"""
        },
        "reference_fix": {
            "parser.py": """from models import CSVDocument
from lexer import sanitize_chars

class StrictCSVReader:
    def parse(self, content: str) -> list[list[str]]:
        if not content.strip():
            return []
        lines = content.splitlines()
        rows = []
        for line in lines:
            fields = []
            cur = []
            in_quote = False
            i = 0
            while i < len(line):
                ch = line[i]
                if ch == '"':
                    if in_quote and i + 1 < len(line) and line[i + 1] == '"':
                        cur.append('"')
                        i += 1
                    else:
                        in_quote = not in_quote
                elif ch == ',' and not in_quote:
                    fields.append("".join(cur))
                    cur = []
                else:
                    cur.append(ch)
                i += 1
            fields.append("".join(cur))
            rows.append(fields)
        return rows
"""
        }
    },
    {
        "task_id": "h05",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "ttl_rate_limiter",
        "description": "The API rate limiter incorrectly records timestamps for rejected requests, causing clients to remain throttled even after earlier accepted requests have expired from the sliding window.",
        "spec_notes": "SlidingWindowLimiter allows up to max_requests in a rolling window of window_seconds using an injectable clock (a callable now() returning float seconds). Only accepted requests consume capacity; rejected requests must NOT record timestamps or consume quota.",
        "repo_files": {
            "policy.py": """from dataclasses import dataclass

# Misleading comment:
# "Rate limits are fixed bucket counters evaluated on integer second boundaries."
@dataclass(frozen=True)
class RateLimitPolicy:
    max_requests: int
    window_seconds: float
""",
            "limiter.py": """from collections import defaultdict
from typing import Callable, Optional
from policy import RateLimitPolicy

class SlidingWindowLimiter:
    def __init__(self, policy: RateLimitPolicy, clock: Optional[Callable[[], float]] = None):
        self.policy = policy
        self.clock = clock if clock is not None else (lambda: 0.0)
        self.history = defaultdict(list)

    def allow_request(self, client_id: str) -> bool:
        now = float(self.clock())
        cutoff = now - self.policy.window_seconds
        valid_ts = [t for t in self.history[client_id] if t > cutoff]
        self.history[client_id] = valid_ts
        # Bug: records timestamp before verifying quota, consuming capacity on rejection
        self.history[client_id].append(now)
        if len(self.history[client_id]) > self.policy.max_requests:
            return False
        return True
"""
        },
        "tests": {
            "test_limiter.py": """from policy import RateLimitPolicy
from limiter import SlidingWindowLimiter

class MockClock:
    def __init__(self, start: float = 0.0):
        self._time = float(start)
    def __call__(self) -> float:
        return self._time
    def advance(self, seconds: float):
        self._time += float(seconds)

def test_single_request():
    clk = MockClock(100.0)
    lim = SlidingWindowLimiter(RateLimitPolicy(max_requests=2, window_seconds=10.0), clock=clk)
    assert lim.allow_request("client_1") is True

def test_burst_under_limit():
    clk = MockClock(100.0)
    lim = SlidingWindowLimiter(RateLimitPolicy(max_requests=2, window_seconds=10.0), clock=clk)
    assert lim.allow_request("client_1") is True
    assert lim.allow_request("client_1") is True

def test_reject_over_limit():
    clk = MockClock(100.0)
    lim = SlidingWindowLimiter(RateLimitPolicy(max_requests=2, window_seconds=10.0), clock=clk)
    assert lim.allow_request("client_1") is True
    assert lim.allow_request("client_1") is True
    assert lim.allow_request("client_1") is False

def test_interleaved_rejected_requests_do_not_consume_capacity():
    clk = MockClock(0.0)
    lim = SlidingWindowLimiter(RateLimitPolicy(max_requests=2, window_seconds=10.0), clock=clk)
    assert lim.allow_request("c1") is True   # t=0.0 (accepted, 1/2)
    assert lim.allow_request("c1") is True   # t=0.0 (accepted, 2/2)
    clk.advance(5.0)                         # t=5.0
    assert lim.allow_request("c1") is False  # t=5.0 (rejected)
    assert lim.allow_request("c1") is False  # t=5.0 (rejected)
    clk.advance(6.0)                         # t=11.0 (t=0.0 accepted requests expired: 11-10 = 1 > 0)
    # Rejected requests at t=5.0 must not consume quota; client should be allowed again:
    assert lim.allow_request("c1") is True

def test_window_expiry():
    clk = MockClock(100.0)
    lim = SlidingWindowLimiter(RateLimitPolicy(max_requests=1, window_seconds=5.0), clock=clk)
    assert lim.allow_request("client_a") is True
    assert lim.allow_request("client_a") is False
    clk.advance(6.0)
    assert lim.allow_request("client_a") is True
"""
        },
        "reference_fix": {
            "limiter.py": """from collections import defaultdict
from typing import Callable, Optional
from policy import RateLimitPolicy

class SlidingWindowLimiter:
    def __init__(self, policy: RateLimitPolicy, clock: Optional[Callable[[], float]] = None):
        self.policy = policy
        self.clock = clock if clock is not None else (lambda: 0.0)
        self.history = defaultdict(list)

    def allow_request(self, client_id: str) -> bool:
        now = float(self.clock())
        cutoff = now - self.policy.window_seconds
        valid_ts = [t for t in self.history[client_id] if t > cutoff]
        self.history[client_id] = valid_ts
        if len(valid_ts) >= self.policy.max_requests:
            return False
        self.history[client_id].append(now)
        return True
"""
        }
    },
    {
        "task_id": "h06",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "ledger_rounding",
        "description": "Financial allocations among stakeholders frequently lose or gain pennies due to independent rounding, causing the sum of distributed shares to not equal the original ledger amount.",
        "spec_notes": "distribute divides an integer total_cents among beneficiaries by weight using the largest remainder method, guaranteeing sum(allocated) == total_cents exactly.",
        "repo_files": {
            "account.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class Beneficiary:
    name: str
    weight: int
""",
            "rounding.py": """# Misleading comment:
def standard_round(value: float) -> int:
    \"\"\"Standard banker's rounding method.\"\"\"
    return int(round(value))
""",
            "distributor.py": """from account import Beneficiary
from rounding import standard_round

class LedgerDistributor:
    def distribute(self, total_cents: int, beneficiaries: list[Beneficiary]) -> dict[str, int]:
        if not beneficiaries or total_cents <= 0:
            return {b.name: 0 for b in beneficiaries}
        total_weight = sum(b.weight for b in beneficiaries)
        if total_weight == 0:
            return {b.name: 0 for b in beneficiaries}

        res = {}
        for b in beneficiaries:
            exact = (total_cents * b.weight) / total_weight
            res[b.name] = standard_round(exact)
        return res
"""
        },
        "tests": {
            "test_ledger.py": """from account import Beneficiary
from distributor import LedgerDistributor

def test_zero_total():
    dist = LedgerDistributor()
    assert dist.distribute(0, [Beneficiary("A", 1)]) == {"A": 0}

def test_exact_even_split():
    dist = LedgerDistributor()
    assert dist.distribute(100, [Beneficiary("A", 1), Beneficiary("B", 1)]) == {"A": 50, "B": 50}

def test_sum_conservation_three_way():
    dist = LedgerDistributor()
    b = [Beneficiary("A", 1), Beneficiary("B", 1), Beneficiary("C", 1)]
    res = dist.distribute(100, b)
    assert sum(res.values()) == 100

def test_largest_remainder_order():
    dist = LedgerDistributor()
    b = [Beneficiary("A", 70), Beneficiary("B", 20), Beneficiary("C", 10)]
    res = dist.distribute(105, b)
    assert sum(res.values()) == 105
    assert res["A"] == 74 and res["B"] == 21 and res["C"] == 10

def test_many_beneficiaries_sum():
    dist = LedgerDistributor()
    b = [Beneficiary(f"B{i}", 1) for i in range(7)]
    res = dist.distribute(100, b)
    assert sum(res.values()) == 100
"""
        },
        "reference_fix": {
            "distributor.py": """import math
from account import Beneficiary

class LedgerDistributor:
    def distribute(self, total_cents: int, beneficiaries: list[Beneficiary]) -> dict[str, int]:
        if not beneficiaries or total_cents <= 0:
            return {b.name: 0 for b in beneficiaries}
        total_weight = sum(b.weight for b in beneficiaries)
        if total_weight == 0:
            return {b.name: 0 for b in beneficiaries}

        allocated = {}
        remainders = []
        current_sum = 0

        for b in beneficiaries:
            exact = (total_cents * b.weight) / total_weight
            base = math.floor(exact)
            rem = exact - base
            allocated[b.name] = base
            current_sum += base
            remainders.append((rem, b.name))

        leftover = total_cents - current_sum
        remainders.sort(key=lambda x: (-x[0], x[1]))
        for i in range(leftover):
            allocated[remainders[i][1]] += 1

        return allocated
"""
        }
    },
    {
        "task_id": "h07",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "text_wrapping",
        "description": "Formatted document printing hangs or crashes on unusually long identifiers that exceed column limits, and leaves ragged whitespace at line margins.",
        "spec_notes": "LineWrapper.wrap wraps words into lines without exceeding width. Long words exceeding width must be split across multiple chunks.",
        "repo_files": {
            "rules.py": """def is_whitespace(char: str) -> bool:
    return char.isspace()
""",
            "token_stream.py": """def extract_words(text: str) -> list[str]:
    return text.split()
""",
            "wrapper.py": """from token_stream import extract_words

class LineWrapper:
    def wrap(self, text: str, width: int) -> list[str]:
        if not text.strip() or width <= 0:
            return []
        words = extract_words(text)
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_line and (cur_len + 1 + len(w) > width):
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + (1 if len(cur_line) > 1 else 0)
        if cur_line:
            lines.append(" ".join(cur_line))
        return lines
"""
        },
        "tests": {
            "test_wrapper.py": """from wrapper import LineWrapper

def test_empty_text():
    w = LineWrapper()
    assert w.wrap("", 10) == []

def test_short_words_fits_single_line():
    w = LineWrapper()
    assert w.wrap("hi there", 10) == ["hi there"]

def test_exact_line_wrap():
    w = LineWrapper()
    assert w.wrap("alpha beta gamma", 10) == ["alpha beta", "gamma"]

def test_long_word_hard_break():
    w = LineWrapper()
    assert w.wrap("supercalifragilistic", 5) == ["super", "calif", "ragil", "istic"]

def test_mixed_sentence_with_long_word():
    w = LineWrapper()
    assert w.wrap("a 1234567890 b", 5) == ["a", "12345", "67890", "b"]
"""
        },
        "reference_fix": {
            "wrapper.py": """from token_stream import extract_words

class LineWrapper:
    def wrap(self, text: str, width: int) -> list[str]:
        if not text.strip() or width <= 0:
            return []
        words = extract_words(text)
        split_words = []
        for w in words:
            if len(w) > width:
                for i in range(0, len(w), width):
                    split_words.append(w[i:i + width])
            else:
                split_words.append(w)

        lines = []
        cur_line = []
        cur_len = 0
        for w in split_words:
            added = len(w) if not cur_line else len(w) + 1
            if cur_line and cur_len + added > width:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += added
        if cur_line:
            lines.append(" ".join(cur_line))
        return lines
"""
        }
    },
    {
        "task_id": "h08",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "datetime_business_days",
        "description": "Delivery date calculations produce weekend delivery dates when requests originate on Sundays, and miscount deadlines when adjusting backwards before bank holidays.",
        "spec_notes": "add_business_days adds n business days (Monday-Friday excluding holidays). If start date is a weekend/holiday, roll forward to the next business day first. Negative n moves backwards.",
        "repo_files": {
            "date_util.py": """from datetime import date

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5
""",
            "holidays.py": """from datetime import date

class HolidayRegistry:
    def __init__(self, holidays: set[date]):
        self.holidays = holidays

    def is_holiday(self, d: date) -> bool:
        return d in self.holidays
""",
            "business_calendar.py": """from datetime import date, timedelta
from date_util import is_weekend
from holidays import HolidayRegistry

class BusinessCalendar:
    def __init__(self, holiday_registry: HolidayRegistry):
        self.registry = holiday_registry

    def is_business_day(self, d: date) -> bool:
        return not is_weekend(d) and not self.registry.is_holiday(d)

    def add_business_days(self, start: date, n: int) -> date:
        cur = start
        step = 1 if n >= 0 else -1
        remaining = abs(n)
        while remaining > 0:
            cur += timedelta(days=step)
            if step > 0:
                if self.is_business_day(cur):
                    remaining -= 1
            else:
                if not self.registry.is_holiday(cur):
                    remaining -= 1
        return cur
"""
        },
        "tests": {
            "test_calendar.py": """from datetime import date
from holidays import HolidayRegistry
from business_calendar import BusinessCalendar

def test_weekday_add_zero():
    cal = BusinessCalendar(HolidayRegistry(set()))
    d = date(2026, 10, 5)  # Monday
    assert cal.add_business_days(d, 0) == d

def test_weekday_add_one():
    cal = BusinessCalendar(HolidayRegistry(set()))
    d = date(2026, 10, 5)  # Monday
    assert cal.add_business_days(d, 1) == date(2026, 10, 6)

def test_weekend_roll_forward():
    cal = BusinessCalendar(HolidayRegistry(set()))
    d = date(2026, 10, 4)  # Sunday
    assert cal.add_business_days(d, 0) == date(2026, 10, 5)

def test_cross_weekend():
    cal = BusinessCalendar(HolidayRegistry(set()))
    d = date(2026, 10, 9)  # Friday
    assert cal.add_business_days(d, 1) == date(2026, 10, 12)

def test_negative_business_days():
    cal = BusinessCalendar(HolidayRegistry(set()))
    d = date(2026, 10, 12)  # Monday
    assert cal.add_business_days(d, -1) == date(2026, 10, 9)
"""
        },
        "reference_fix": {
            "business_calendar.py": """from datetime import date, timedelta
from date_util import is_weekend
from holidays import HolidayRegistry

class BusinessCalendar:
    def __init__(self, holiday_registry: HolidayRegistry):
        self.registry = holiday_registry

    def is_business_day(self, d: date) -> bool:
        return not is_weekend(d) and not self.registry.is_holiday(d)

    def add_business_days(self, start: date, n: int) -> date:
        cur = start
        while not self.is_business_day(cur):
            cur += timedelta(days=1)
        step = 1 if n >= 0 else -1
        remaining = abs(n)
        while remaining > 0:
            cur += timedelta(days=step)
            if self.is_business_day(cur):
                remaining -= 1
        return cur
"""
        }
    },
    {
        "task_id": "h09",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "graph_tiebreak",
        "description": "The routing optimizer crashes with type comparison errors on alternative paths of equal distance, or outputs non-deterministic routes depending on internal insertion order.",
        "spec_notes": "find_shortest_path returns (cost, path). In case of equal cost, tie-break by fewest edges, then lexicographical order of node sequence.",
        "repo_files": {
            "models.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class Edge:
    u: str
    v: str
    weight: int
""",
            "priority_queue.py": """import heapq

class MinHeap:
    def __init__(self):
        self.elements = []

    def push(self, item):
        heapq.heappush(self.elements, item)

    def pop(self):
        return heapq.heappop(self.elements)

    def __len__(self):
        return len(self.elements)
""",
            "dijkstra.py": """from collections import defaultdict
from models import Edge
from priority_queue import MinHeap

class DijkstraPathFinder:
    def find_shortest_path(self, edges: list[Edge], source: str, target: str) -> tuple[int, list[str]]:
        graph = defaultdict(list)
        for e in edges:
            graph[e.u].append((e.v, e.weight))

        heap = MinHeap()
        heap.push((0, [source]))
        visited = set()

        while len(heap) > 0:
            cost, path = heap.pop()
            curr = path[-1]
            if curr == target:
                return cost, path
            if curr in visited:
                continue
            visited.add(curr)
            for neighbor, weight in graph[curr]:
                if neighbor not in visited:
                    heap.push((cost + weight, path + [neighbor]))
        return -1, []
"""
        },
        "tests": {
            "test_dijkstra.py": """from models import Edge
from dijkstra import DijkstraPathFinder

def test_single_node_start_target():
    finder = DijkstraPathFinder()
    assert finder.find_shortest_path([], "A", "A") == (0, ["A"])

def test_unreachable_node():
    finder = DijkstraPathFinder()
    assert finder.find_shortest_path([Edge("A", "B", 5)], "A", "C") == (-1, [])

def test_simple_direct_path():
    finder = DijkstraPathFinder()
    edges = [Edge("A", "B", 4), Edge("B", "C", 2), Edge("A", "C", 10)]
    assert finder.find_shortest_path(edges, "A", "C") == (6, ["A", "B", "C"])

def test_tie_break_fewer_hops():
    finder = DijkstraPathFinder()
    edges = [
        Edge("A", "D", 10),
        Edge("A", "B", 5),
        Edge("B", "C", 2),
        Edge("C", "D", 3),
    ]
    assert finder.find_shortest_path(edges, "A", "D") == (10, ["A", "D"])

def test_tie_break_lexicographical():
    finder = DijkstraPathFinder()
    edges = [
        Edge("A", "B", 5),
        Edge("B", "D", 5),
        Edge("A", "C", 5),
        Edge("C", "D", 5),
    ]
    assert finder.find_shortest_path(edges, "A", "D") == (10, ["A", "B", "D"])
"""
        },
        "reference_fix": {
            "dijkstra.py": """from collections import defaultdict
from models import Edge
from priority_queue import MinHeap

class DijkstraPathFinder:
    def find_shortest_path(self, edges: list[Edge], source: str, target: str) -> tuple[int, list[str]]:
        graph = defaultdict(list)
        for e in edges:
            graph[e.u].append((e.v, e.weight))

        heap = MinHeap()
        heap.push((0, 1, [source]))
        best_cost = {}

        while len(heap) > 0:
            cost, hops, path = heap.pop()
            curr = path[-1]
            if curr in best_cost and cost > best_cost[curr]:
                continue
            best_cost[curr] = cost
            if curr == target:
                return cost, path
            for neighbor, weight in graph[curr]:
                new_cost = cost + weight
                if neighbor not in best_cost or new_cost <= best_cost[neighbor]:
                    heap.push((new_cost, hops + 1, path + [neighbor]))
        return -1, []
"""
        }
    },
    {
        "task_id": "h10",
        "suite": "hard",
        "difficulty": "hard",
        "bug_type": "config_precedence",
        "description": "Application startup settings ignore command-line flags when environment variables are set, and wipe out sibling configuration keys when overriding nested settings.",
        "spec_notes": "ConfigMerger.merge combines configurations with precedence DEFAULT < FILE < ENV < CLI. Nested dictionaries must be recursively merged without discarding sibling keys.",
        "repo_files": {
            "source_layer.py": """from enum import IntEnum

class Layer(IntEnum):
    DEFAULT = 1
    FILE = 2
    ENV = 3
    CLI = 4
""",
            "validator.py": """# Misleading comment:
def validate_keys(cfg: dict) -> bool:
    \"\"\"Assumes shallow single-level mapping without nested dictionaries.\"\"\"
    return isinstance(cfg, dict)
""",
            "config_merger.py": """from source_layer import Layer

class ConfigMerger:
    def merge(self, default_cfg: dict, file_cfg: dict, env_cfg: dict, cli_cfg: dict) -> dict:
        result = {}
        result.update(default_cfg)
        result.update(file_cfg)
        result.update(cli_cfg)
        result.update(env_cfg)
        return result
"""
        },
        "tests": {
            "test_config.py": """from config_merger import ConfigMerger

def test_default_only():
    cm = ConfigMerger()
    assert cm.merge({"a": 1}, {}, {}, {}) == {"a": 1}

def test_file_overrides_default():
    cm = ConfigMerger()
    assert cm.merge({"a": 1}, {"a": 2}, {}, {}) == {"a": 2}

def test_cli_overrides_env():
    cm = ConfigMerger()
    assert cm.merge({}, {}, {"port": 8000}, {"port": 9000}) == {"port": 9000}

def test_nested_dict_sibling_retention():
    cm = ConfigMerger()
    default_cfg = {"db": {"host": "localhost", "port": 5432}}
    env_cfg = {"db": {"host": "remotehost"}}
    res = cm.merge(default_cfg, {}, env_cfg, {})
    assert res == {"db": {"host": "remotehost", "port": 5432}}

def test_full_four_layer_precedence():
    cm = ConfigMerger()
    d = {"timeout": 10, "nested": {"k1": "d1", "k2": "d2"}}
    f = {"timeout": 20, "nested": {"k1": "f1"}}
    e = {"timeout": 30, "nested": {"k3": "e3"}}
    c = {"timeout": 40}
    res = cm.merge(d, f, e, c)
    assert res["timeout"] == 40
    assert res["nested"] == {"k1": "f1", "k2": "d2", "k3": "e3"}
"""
        },
        "reference_fix": {
            "config_merger.py": """from source_layer import Layer

class ConfigMerger:
    def deep_merge(self, base: dict, override: dict) -> dict:
        out = dict(base)
        for k, v in override.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self.deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    def merge(self, default_cfg: dict, file_cfg: dict, env_cfg: dict, cli_cfg: dict) -> dict:
        layers = [default_cfg, file_cfg, env_cfg, cli_cfg]
        result = {}
        for layer in layers:
            if isinstance(layer, dict):
                result = self.deep_merge(result, layer)
        return result
"""
        }
    }
]

def main():
    base_dir = Path("tasks/hard")
    base_dir.mkdir(parents=True, exist_ok=True)
    for t in HARD_TASKS:
        tid = t["task_id"]
        tdir = base_dir / tid
        tdir.mkdir(parents=True, exist_ok=True)
        tfile = tdir / "task.json"
        with open(tfile, "w", encoding="utf-8") as f:
            json.dump(t, f, indent=2)
        print(f"Created task {tid} in {tfile}")

if __name__ == "__main__":
    main()
