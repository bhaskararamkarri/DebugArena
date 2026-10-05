"""Category M: Adversarial Debugging Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class AdversarialTaskGenerator(BaseGenerator):
    """Generates realistic adversarial reasoning tasks (misleading comments, distractor modules, deceptive contracts)."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v21_misleading_retry_budget")
        sub_type = spec.get("sub_type", "misleading_docstring")

        if sub_type == "distractor_module" or "distractor" in task_id:
            return self._generate_distractor_middleware(task_id, spec, seed)
        elif sub_type == "boundary_invariant" or "invariant" in task_id or "boundary" in task_id:
            return self._generate_boundary_invariant(task_id, spec, seed)
        elif sub_type == "flaky_retry_storm" or "retry_storm" in task_id:
            return self._generate_flaky_retry_storm(task_id, spec, seed)
        return self._generate_misleading_retry_budget(task_id, spec, seed)

    def _generate_misleading_retry_budget(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "policy.py": (
                '"""Retry budget policy definition."""\n\n'
                'class RetryPolicy:\n'
                '    def __init__(self, max_retries: int = 3, min_ratio: float = 0.1, token_cost: float = 1.0):\n'
                '        self.max_retries = max_retries\n'
                '        self.min_ratio = min_ratio\n'
                '        self.token_cost = token_cost\n'
            ),
            "client.py": (
                '"""Resilient RPC client utilizing tokenized retry budgeting."""\n\n'
                'from typing import Callable, Any\n'
                'from policy import RetryPolicy\n'
                'from budget import RetryBudget\n\n\n'
                'class ResilientClient:\n'
                '    def __init__(self, budget: RetryBudget, policy: RetryPolicy):\n'
                '        self.budget = budget\n'
                '        self.policy = policy\n\n'
                '    def execute_with_retry(self, operation: Callable[[], Any]) -> Any:\n'
                '        attempts = 0\n'
                '        while True:\n'
                '            self.budget.record_attempt()\n'
                '            try:\n'
                '                return operation()\n'
                '            except Exception as exc:\n'
                '                attempts += 1\n'
                '                if attempts > self.policy.max_retries or not self.budget.can_retry():\n'
                '                    raise exc\n'
                '                self.budget.spend_retry_token()\n'
            ),
            "budget.py": (
                '"""Client-side token bucket retry budget.\n\n'
                'Note on token replenishment:\n'
                'Per RFC-8999, the retry budget accumulates 0.2 tokens on every successful attempt,\n'
                'and caps total tokens at maximum capacity 10.0.\n'
                'When can_retry() is checked, tokens must strictly exceed 1.0 (>= 1.0 is insufficient).\n'
                '"""\n\n'
                'class RetryBudget:\n'
                '    def __init__(self, capacity: float = 10.0, initial_tokens: float = 5.0, token_cost: float = 1.0):\n'
                '        self.capacity = capacity\n'
                '        self.tokens = initial_tokens\n'
                '        self.token_cost = token_cost\n'
                '        self.total_attempts = 0\n\n'
                '    def record_attempt(self) -> None:\n'
                '        self.total_attempts += 1\n'
                '        # MISLEADING DOCSTRING TRAP:\n'
                '        # Docstring claimed tokens replenish on every attempt by 0.2 unconditionally,\n'
                '        # but replenishing on failed attempts creates an infinite retry storm vulnerability!\n'
                '        # BUG: The code blindly adds tokens on EVERY attempt including failed retries!\n'
                '        self.tokens = min(self.capacity, self.tokens + 0.2)\n\n'
                '    def record_success(self) -> None:\n'
                '        pass  # Omitted because of erroneous record_attempt logic above\n\n'
                '    def can_retry(self) -> bool:\n'
                '        # BUG: Docstring claimed strict > 1.0, but standard token bucket allows can_retry when tokens >= token_cost\n'
                '        return self.tokens > 1.0\n\n'
                '    def spend_retry_token(self) -> bool:\n'
                '        if self.tokens >= self.token_cost:\n'
                '            self.tokens -= self.token_cost\n'
                '            return True\n'
                '        return False\n'
            ),
        }

        reference_fix = {
            "budget.py": (
                '"""Client-side token bucket retry budget."""\n\n'
                'class RetryBudget:\n'
                '    def __init__(self, capacity: float = 10.0, initial_tokens: float = 5.0, token_cost: float = 1.0):\n'
                '        self.capacity = capacity\n'
                '        self.tokens = initial_tokens\n'
                '        self.token_cost = token_cost\n'
                '        self.total_attempts = 0\n\n'
                '    def record_attempt(self) -> None:\n'
                '        self.total_attempts += 1\n\n'
                '    def record_success(self) -> None:\n'
                '        # Tokens only replenish on genuine downstream success\n'
                '        self.tokens = min(self.capacity, self.tokens + 0.2)\n\n'
                '    def can_retry(self) -> bool:\n'
                '        return self.tokens >= self.token_cost\n\n'
                '    def spend_retry_token(self) -> bool:\n'
                '        if self.tokens >= self.token_cost:\n'
                '            self.tokens -= self.token_cost\n'
                '            return True\n'
                '        return False\n'
            ),
            "client.py": (
                '"""Resilient RPC client utilizing tokenized retry budgeting."""\n\n'
                'from typing import Callable, Any\n'
                'from policy import RetryPolicy\n'
                'from budget import RetryBudget\n\n\n'
                'class ResilientClient:\n'
                '    def __init__(self, budget: RetryBudget, policy: RetryPolicy):\n'
                '        self.budget = budget\n'
                '        self.policy = policy\n\n'
                '    def execute_with_retry(self, operation: Callable[[], Any]) -> Any:\n'
                '        attempts = 0\n'
                '        while True:\n'
                '            self.budget.record_attempt()\n'
                '            try:\n'
                '                res = operation()\n'
                '                self.budget.record_success()\n'
                '                return res\n'
                '            except Exception as exc:\n'
                '                attempts += 1\n'
                '                if attempts > self.policy.max_retries or not self.budget.can_retry():\n'
                '                    raise exc\n'
                '                self.budget.spend_retry_token()\n'
            ),
        }

        tests = {
            "test_retry_budget.py": (
                'import pytest\n'
                'from policy import RetryPolicy\n'
                'from budget import RetryBudget\n'
                'from client import ResilientClient\n\n\n'
                'def test_successful_request_replenishes_budget():\n'
                '    budget = RetryBudget(capacity=10.0, initial_tokens=5.0)\n'
                '    policy = RetryPolicy(max_retries=2)\n'
                '    client = ResilientClient(budget, policy)\n'
                '    res = client.execute_with_retry(lambda: "OK")\n'
                '    assert res == "OK"\n'
                '    assert budget.tokens == pytest.approx(5.2)\n\n\n'
                'def test_consecutive_failures_exhaust_tokens():\n'
                '    budget = RetryBudget(capacity=5.0, initial_tokens=2.0, token_cost=1.0)\n'
                '    policy = RetryPolicy(max_retries=5)\n'
                '    client = ResilientClient(budget, policy)\n'
                '    call_count = 0\n'
                '    def always_fails():\n'
                '        nonlocal call_count\n'
                '        call_count += 1\n'
                '        raise ConnectionError("downstream unreachable")\n\n'
                '    with pytest.raises(ConnectionError):\n'
                '        client.execute_with_retry(always_fails)\n\n'
                '    # Initial tokens: 2.0. Attempt 1 fails -> retries (spends 1 token, left 1.0).\n'
                '    # Attempt 2 fails -> retries (spends 1 token, left 0.0).\n'
                '    # Attempt 3 fails -> can_retry is False (0.0 < 1.0) -> halts without infinite replenishment!\n'
                '    assert call_count == 3\n'
                '    assert budget.tokens == pytest.approx(0.0)\n\n\n'
                'def test_can_retry_boundary_at_exact_token_cost():\n'
                '    budget = RetryBudget(capacity=5.0, initial_tokens=1.0, token_cost=1.0)\n'
                '    # Having exactly 1.0 token must allow retry (tokens >= token_cost)\n'
                '    assert budget.can_retry() is True\n'
                '    assert budget.spend_retry_token() is True\n'
                '    assert budget.can_retry() is False\n\n\n'
                'def test_capacity_cap_enforced():\n'
                '    budget = RetryBudget(capacity=3.0, initial_tokens=2.9)\n'
                '    budget.record_success()\n'
                '    assert budget.tokens == pytest.approx(3.0)\n\n\n'
                'def test_transient_failure_then_success_recovers():\n'
                '    budget = RetryBudget(capacity=5.0, initial_tokens=3.0)\n'
                '    policy = RetryPolicy(max_retries=3)\n'
                '    client = ResilientClient(budget, policy)\n'
                '    attempts = 0\n'
                '    def flaky():\n'
                '        nonlocal attempts\n'
                '        attempts += 1\n'
                '        if attempts == 1:\n'
                '            raise TimeoutError("slow")\n'
                '        return "RECOVERED"\n\n'
                '    res = client.execute_with_retry(flaky)\n'
                '    assert res == "RECOVERED"\n'
                '    assert attempts == 2\n'
                '    # Spent 1.0 on retry, gained 0.2 on success -> 3.0 - 1.0 + 0.2 = 2.2\n'
                '    assert budget.tokens == pytest.approx(2.2)\n\n\n'
                'def test_max_retries_policy_bounds_attempts():\n'
                '    budget = RetryBudget(capacity=20.0, initial_tokens=15.0)\n'
                '    policy = RetryPolicy(max_retries=1)\n'
                '    client = ResilientClient(budget, policy)\n'
                '    count = 0\n'
                '    def fail_fn():\n'
                '        nonlocal count\n'
                '        count += 1\n'
                '        raise RuntimeError("boom")\n\n'
                '    with pytest.raises(RuntimeError):\n'
                '        client.execute_with_retry(fail_fn)\n'
                '    # Max retries = 1, so 1 initial attempt + 1 retry = 2 total calls\n'
                '    assert count == 2\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "adversarial",
            "bug_type": "adversarial_misleading_docstring_retry_storm",
            "categories": ["M", "H", "D", "E"],
            "description": "Retry budget contains misleading docstrings asserting tokens replenish on all attempts, masking a retry-storm token leak.",
            "spec_notes": "Ignore misleading docstring comments. Tokens must only replenish on successful downstream calls and can_retry must check tokens >= token_cost.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": True,
                "stateful": True,
                "multi_file": True,
                "domain": "networking",
            },
        }

    def _generate_distractor_middleware(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Request and user models."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class AuthUser:\n'
                '    user_id: str\n'
                '    role: str\n'
                '    is_active: bool = True\n'
            ),
            "distractor_audit.py": (
                '"""Audit logging and telemetry middleware.\n'
                'ATTENTION: This module handles compliance telemetry inspection.\n'
                'Ensure all tokens undergo RFC verification here before routing.\n'
                '"""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class AuditLoggerMiddleware:\n'
                '    def __init__(self):\n'
                '        self.audit_log: list[str] = []\n\n'
                '    def inspect_request(self, headers: Dict[str, str]) -> bool:\n'
                '        # Elaborate distractor checks that do not affect core authorization\n'
                '        auth_hdr = headers.get("Authorization", "")\n'
                '        self.audit_log.append(f"INSPECT:{auth_hdr[:10]}")\n'
                '        return len(auth_hdr) > 0\n'
            ),
            "auth_guard.py": (
                '"""Core authentication and header parsing guard."""\n\n'
                'from typing import Dict, Optional\n'
                'from models import AuthUser\n\n\n'
                'class AuthGuard:\n'
                '    def __init__(self, valid_tokens: Dict[str, AuthUser]):\n'
                '        self.valid_tokens = valid_tokens\n\n'
                '    def authenticate(self, headers: Dict[str, str]) -> Optional[AuthUser]:\n'
                '        # Check Primary Authorization header or Secondary X-API-Token header\n'
                '        auth_header = headers.get("Authorization")\n'
                '        api_token = headers.get("X-API-Token")\n\n'
                '        token = None\n'
                '        if auth_header:\n'
                '            # BUG: Case-sensitive prefix check fails on lowercase "bearer <token>"\n'
                '            if auth_header.startswith("Bearer "):\n'
                '                token = auth_header[7:].strip()\n'
                '            else:\n'
                '                # BUG: If Authorization header exists with non-Bearer format, it returns None\n'
                '                # and completely ignores valid X-API-Token fallback!\n'
                '                return None\n'
                '        elif api_token:\n'
                '            token = api_token.strip()\n\n'
                '        if not token or token not in self.valid_tokens:\n'
                '            return None\n'
                '        user = self.valid_tokens[token]\n'
                '        return user if user.is_active else None\n'
            ),
            "pipeline.py": (
                '"""HTTP request processing pipeline."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from auth_guard import AuthGuard\n'
                'from distractor_audit import AuditLoggerMiddleware\n'
                'from models import AuthUser\n\n\n'
                'class RequestPipeline:\n'
                '    def __init__(self, guard: AuthGuard):\n'
                '        self.guard = guard\n'
                '        self.audit = AuditLoggerMiddleware()\n\n'
                '    def process(self, headers: Dict[str, str], payload: Any) -> Dict[str, Any]:\n'
                '        self.audit.inspect_request(headers)\n'
                '        user = self.guard.authenticate(headers)\n'
                '        if not user:\n'
                '            return {"status": 401, "error": "Unauthorized"}\n'
                '        return {"status": 200, "user_id": user.user_id, "data": payload}\n'
            ),
        }

        reference_fix = {
            "auth_guard.py": (
                '"""Core authentication and header parsing guard."""\n\n'
                'from typing import Dict, Optional\n'
                'from models import AuthUser\n\n\n'
                'class AuthGuard:\n'
                '    def __init__(self, valid_tokens: Dict[str, AuthUser]):\n'
                '        self.valid_tokens = valid_tokens\n\n'
                '    def authenticate(self, headers: Dict[str, str]) -> Optional[AuthUser]:\n'
                '        auth_header = headers.get("Authorization")\n'
                '        api_token = headers.get("X-API-Token")\n\n'
                '        token = None\n'
                '        if auth_header:\n'
                '            parts = auth_header.split(maxsplit=1)\n'
                '            if len(parts) == 2 and parts[0].lower() == "bearer":\n'
                '                token = parts[1].strip()\n'
                '            elif len(parts) == 1:\n'
                '                token = parts[0].strip()\n\n'
                '        # Fallback to secondary header if primary did not yield a valid matched token\n'
                '        if (not token or token not in self.valid_tokens) and api_token:\n'
                '            token = api_token.strip()\n\n'
                '        if not token or token not in self.valid_tokens:\n'
                '            return None\n'
                '        user = self.valid_tokens[token]\n'
                '        return user if user.is_active else None\n'
            )
        }

        tests = {
            "test_pipeline_auth.py": (
                'from models import AuthUser\n'
                'from auth_guard import AuthGuard\n'
                'from pipeline import RequestPipeline\n\n\n'
                'def get_fixture_pipeline():\n'
                '    users = {\n'
                '        "tok_admin": AuthUser("u1", "admin", True),\n'
                '        "tok_guest": AuthUser("u2", "guest", True),\n'
                '        "tok_banned": AuthUser("u3", "member", False),\n'
                '    }\n'
                '    guard = AuthGuard(users)\n'
                '    return RequestPipeline(guard)\n\n\n'
                'def test_standard_bearer_auth():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    res = pipe.process({"Authorization": "Bearer tok_admin"}, {"msg": "hi"})\n'
                '    assert res["status"] == 200\n'
                '    assert res["user_id"] == "u1"\n\n\n'
                'def test_case_insensitive_bearer_token():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    res = pipe.process({"Authorization": "bearer tok_guest"}, {})\n'
                '    assert res["status"] == 200\n'
                '    assert res["user_id"] == "u2"\n\n\n'
                'def test_api_token_fallback_when_auth_header_malformed():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    headers = {\n'
                '        "Authorization": "Basic unhandled",\n'
                '        "X-API-Token": "tok_admin",\n'
                '    }\n'
                '    res = pipe.process(headers, {})\n'
                '    assert res["status"] == 200\n'
                '    assert res["user_id"] == "u1"\n\n\n'
                'def test_inactive_user_rejected():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    res = pipe.process({"Authorization": "Bearer tok_banned"}, {})\n'
                '    assert res["status"] == 401\n'
                '    assert res["error"] == "Unauthorized"\n\n\n'
                'def test_missing_headers_rejected():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    res = pipe.process({}, {})\n'
                '    assert res["status"] == 401\n\n\n'
                'def test_standalone_api_token():\n'
                '    pipe = get_fixture_pipeline()\n'
                '    res = pipe.process({"X-API-Token": "tok_guest"}, {})\n'
                '    assert res["status"] == 200\n'
                '    assert res["user_id"] == "u2"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "adversarial",
            "bug_type": "adversarial_distractor_middleware_auth_mismatch",
            "categories": ["M", "E", "L"],
            "description": "API pipeline contains distractor audit middleware, while the real bug is in AuthGuard lowercase bearer and fallback token handling.",
            "spec_notes": "Do not get sidetracked by distractor_audit.py. Fix AuthGuard to support case-insensitive Bearer prefix and fallback token headers.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": True,
                "stateful": False,
                "multi_file": True,
                "domain": "security",
            },
        }

    def _generate_boundary_invariant(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "metric_types.py": (
                '"""Telemetry sample data definitions."""\n\n'
                'from dataclasses import dataclass\n\n\n'
                '@dataclass\n'
                'class MetricPoint:\n'
                '    timestamp: float\n'
                '    value: float\n'
            ),
            "window.py": (
                '"""Sliding time-window aggregator.\n'
                'Window Invariant:\n'
                'Maintains events within (current_time - duration, current_time].\n'
                '"""\n\n'
                'from collections import deque\n'
                'from typing import List\n'
                'from metric_types import MetricPoint\n\n\n'
                'class SlidingWindowAggregator:\n'
                '    def __init__(self, duration_sec: float = 60.0):\n'
                '        self.duration = duration_sec\n'
                '        self.samples: deque[MetricPoint] = deque()\n\n'
                '    def add_point(self, point: MetricPoint) -> None:\n'
                '        self.samples.append(point)\n'
                '        self._evict_stale(point.timestamp)\n\n'
                '    def _evict_stale(self, now: float) -> None:\n'
                '        # MISLEADING INVARIANT TRAP:\n'
                '        # Comment asserts stale when timestamp < (now - duration),\n'
                '        # but code uses <= which prematurely evicts samples exactly at boundary!\n'
                '        cutoff = now - self.duration\n'
                '        while self.samples and self.samples[0].timestamp <= cutoff:\n'
                '            self.samples.popleft()\n\n'
                '    def get_average(self) -> float:\n'
                '        if not self.samples:\n'
                '            return 0.0\n'
                '        return sum(s.value for s in self.samples) / len(self.samples)\n'
            ),
            "monitor.py": (
                '"""Service health monitor consuming metric points."""\n\n'
                'from window import SlidingWindowAggregator\n'
                'from metric_types import MetricPoint\n\n\n'
                'class ServiceMonitor:\n'
                '    def __init__(self, window_sec: float = 10.0):\n'
                '        self.aggregator = SlidingWindowAggregator(duration_sec=window_sec)\n\n'
                '    def record(self, timestamp: float, latency_ms: float) -> float:\n'
                '        self.aggregator.add_point(MetricPoint(timestamp, latency_ms))\n'
                '        return self.aggregator.get_average()\n'
            ),
        }

        reference_fix = {
            "window.py": (
                '"""Sliding time-window aggregator."""\n\n'
                'from collections import deque\n'
                'from typing import List\n'
                'from metric_types import MetricPoint\n\n\n'
                'class SlidingWindowAggregator:\n'
                '    def __init__(self, duration_sec: float = 60.0):\n'
                '        self.duration = duration_sec\n'
                '        self.samples: deque[MetricPoint] = deque()\n\n'
                '    def add_point(self, point: MetricPoint) -> None:\n'
                '        self.samples.append(point)\n'
                '        self._evict_stale(point.timestamp)\n\n'
                '    def _evict_stale(self, now: float) -> None:\n'
                '        cutoff = now - self.duration\n'
                '        while self.samples and self.samples[0].timestamp < cutoff:\n'
                '            self.samples.popleft()\n\n'
                '    def get_average(self) -> float:\n'
                '        if not self.samples:\n'
                '            return 0.0\n'
                '        return sum(s.value for s in self.samples) / len(self.samples)\n'
            )
        }

        tests = {
            "test_window_invariant.py": (
                'import pytest\n'
                'from metric_types import MetricPoint\n'
                'from monitor import ServiceMonitor\n\n\n'
                'def test_basic_window_aggregation():\n'
                '    mon = ServiceMonitor(window_sec=10.0)\n'
                '    avg1 = mon.record(100.0, 50.0)\n'
                '    assert avg1 == 50.0\n'
                '    avg2 = mon.record(105.0, 70.0)\n'
                '    assert avg2 == 60.0\n\n\n'
                'def test_boundary_exact_timestamp_retention():\n'
                '    mon = ServiceMonitor(window_sec=10.0)\n'
                '    # Point at t=10.0\n'
                '    mon.record(10.0, 100.0)\n'
                '    # Point at t=20.0: cutoff is 20.0 - 10.0 = 10.0.\n'
                '    # A sample at t=10.0 is inside the 10.0s window [10.0, 20.0] and MUST NOT be evicted!\n'
                '    avg = mon.record(20.0, 200.0)\n'
                '    assert len(mon.aggregator.samples) == 2\n'
                '    assert avg == pytest.approx(150.0)\n\n\n'
                'def test_stale_sample_evicted_past_boundary():\n'
                '    mon = ServiceMonitor(window_sec=10.0)\n'
                '    mon.record(10.0, 100.0)\n'
                '    mon.record(20.1, 200.0)  # t=10.0 is strictly < 20.1 - 10.0 (10.1) -> evicted\n'
                '    assert len(mon.aggregator.samples) == 1\n'
                '    assert mon.aggregator.get_average() == 200.0\n\n\n'
                'def test_empty_window_average():\n'
                '    mon = ServiceMonitor(window_sec=5.0)\n'
                '    assert mon.aggregator.get_average() == 0.0\n\n\n'
                'def test_multiple_points_same_timestamp():\n'
                '    mon = ServiceMonitor(window_sec=5.0)\n'
                '    mon.record(10.0, 20.0)\n'
                '    mon.record(10.0, 40.0)\n'
                '    assert mon.aggregator.get_average() == 30.0\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "adversarial",
            "bug_type": "adversarial_boundary_off_by_one_eviction",
            "categories": ["M", "B", "D"],
            "description": "Sliding window aggregator prematurely evicts samples at the exact duration cutoff due to <= operator instead of <.",
            "spec_notes": "Window boundaries must retain samples matching exactly timestamp == (now - duration).",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": True,
                "stateful": True,
                "multi_file": True,
                "domain": "metrics",
            },
        }

    def _generate_flaky_retry_storm(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "telemetry.py": (
                '"""Adversarial telemetry metrics collector."""\n\n'
                'from typing import Dict, List\n\n\n'
                'class TelemetrySink:\n'
                '    def __init__(self):\n'
                '        self.events: List[Dict[str, str]] = []\n\n'
                '    def record(self, metric: str, value: str) -> None:\n'
                '        self.events.append({"metric": metric, "value": value})\n'
            ),
            "jitter.py": (
                '"""Exponential backoff with full jitter calculation."""\n\n'
                'import random\n'
                'from typing import Tuple\n\n\n'
                'class BackoffJitter:\n'
                '    def __init__(self, base_ms: float = 100.0, max_ms: float = 5000.0, factor: float = 2.0):\n'
                '        self.base_ms = base_ms\n'
                '        self.max_ms = max_ms\n'
                '        self.factor = factor\n\n'
                '    def calculate_delay(self, attempt: int, seed: int = 42) -> float:\n'
                '        # ADVERSARIAL TRAP: Misleading comments suggest attempt 0 returns base_ms\n'
                '        # BUG: When seed % 2 == 0, returns 0.0 delay instead of jittered positive delay!\n'
                '        cap = min(self.max_ms, self.base_ms * (self.factor ** attempt))\n'
                '        if seed % 2 == 0:\n'
                '            return 0.0  # Erroneously collapses delay to 0, creating retry storm!\n'
                '        return (seed % int(cap)) + 1.0\n'
            ),
            "policy.py": (
                '"""Retry storm protection policy."""\n\n'
                'from jitter import BackoffJitter\n'
                'from telemetry import TelemetrySink\n\n\n'
                'class RetryPolicy:\n'
                '    def __init__(self, max_retries: int = 3, jitter: BackoffJitter = None, telemetry: TelemetrySink = None):\n'
                '        self.max_retries = max_retries\n'
                '        self.jitter = jitter or BackoffJitter()\n'
                '        self.telemetry = telemetry or TelemetrySink()\n\n'
                '    def get_backoff(self, attempt: int, seed: int) -> float:\n'
                '        delay = self.jitter.calculate_delay(attempt, seed)\n'
                '        self.telemetry.record("backoff_ms", str(delay))\n'
                '        return delay\n'
            ),
            "circuit_breaker.py": (
                '"""Service circuit breaker trip monitor."""\n\n'
                'class CircuitBreaker:\n'
                '    def __init__(self, failure_threshold: int = 5):\n'
                '        self.failure_threshold = failure_threshold\n'
                '        self.consecutive_failures = 0\n'
                '        self.tripped = False\n\n'
                '    def record_failure(self) -> None:\n'
                '        self.consecutive_failures += 1\n'
                '        if self.consecutive_failures >= self.failure_threshold:\n'
                '            self.tripped = True\n\n'
                '    def record_success(self) -> None:\n'
                '        self.consecutive_failures = 0\n'
                '        self.tripped = False\n'
            ),
            "transport.py": (
                '"""Virtual HTTP transport layer."""\n\n'
                'from typing import Callable, Dict\n\n\n'
                'class VirtualTransport:\n'
                '    def __init__(self):\n'
                '        self.request_timestamps: list[float] = []\n\n'
                '    def send(self, ts: float, action: Callable[[], str]) -> str:\n'
                '        self.request_timestamps.append(ts)\n'
                '        return action()\n'
            ),
            "client.py": (
                '"""Resilient RPC client executing retries."""\n\n'
                'from typing import Any, Callable\n'
                'from circuit_breaker import CircuitBreaker\n'
                'from policy import RetryPolicy\n'
                'from transport import VirtualTransport\n\n\n'
                'class StormResistantClient:\n'
                '    def __init__(self, policy: RetryPolicy, cb: CircuitBreaker, transport: VirtualTransport):\n'
                '        self.policy = policy\n'
                '        self.cb = cb\n'
                '        self.transport = transport\n'
                '        self.clock: float = 1000.0\n\n'
                '    def call(self, fn: Callable[[], str], seed: int = 42) -> str:\n'
                '        for attempt in range(self.policy.max_retries + 1):\n'
                '            if self.cb.tripped:\n'
                '                raise RuntimeError("Circuit breaker is open")\n'
                '            try:\n'
                '                res = self.transport.send(self.clock, fn)\n'
                '                self.cb.record_success()\n'
                '                return res\n'
                '            except Exception as e:\n'
                '                self.cb.record_failure()\n'
                '                if attempt == self.policy.max_retries:\n'
                '                    raise e\n'
                '                delay = self.policy.get_backoff(attempt, seed)\n'
                '                self.clock += delay\n'
                '        raise RuntimeError("Retry loop terminated unexpectedly")\n'
            ),
        }

        reference_fix = {
            "jitter.py": (
                '"""Exponential backoff with full jitter calculation."""\n\n'
                'from typing import Tuple\n\n\n'
                'class BackoffJitter:\n'
                '    def __init__(self, base_ms: float = 100.0, max_ms: float = 5000.0, factor: float = 2.0):\n'
                '        self.base_ms = base_ms\n'
                '        self.max_ms = max_ms\n'
                '        self.factor = factor\n\n'
                '    def calculate_delay(self, attempt: int, seed: int = 42) -> float:\n'
                '        cap = min(self.max_ms, self.base_ms * (self.factor ** attempt))\n'
                '        # Ensure positive deterministic jitter non-zero delay across all seeds\n'
                '        jitter_val = (seed % int(cap)) if int(cap) > 0 else 0\n'
                '        return max(self.base_ms / 2.0, float(jitter_val + 1.0))\n'
            )
        }

        tests = {
            "test_retry_storm.py": (
                'import pytest\n'
                'from circuit_breaker import CircuitBreaker\n'
                'from policy import RetryPolicy\n'
                'from transport import VirtualTransport\n'
                'from client import StormResistantClient\n'
                'from jitter import BackoffJitter\n\n\n'
                'def test_even_seed_does_not_collapse_to_zero_delay():\n'
                '    jitter = BackoffJitter(base_ms=100.0, max_ms=1000.0)\n'
                '    # Even seed (42, 100, 200) must NEVER yield 0.0 ms delay\n'
                '    for s in [0, 2, 42, 100, 256]:\n'
                '        d = jitter.calculate_delay(attempt=1, seed=s)\n'
                '        assert d > 0.0\n'
                '        assert d >= 50.0\n\n\n'
                'def test_retry_client_delays_successive_requests():\n'
                '    policy = RetryPolicy(max_retries=3, jitter=BackoffJitter(base_ms=100.0))\n'
                '    cb = CircuitBreaker(failure_threshold=10)\n'
                '    transport = VirtualTransport()\n'
                '    client = StormResistantClient(policy, cb, transport)\n'
                '    attempts = 0\n'
                '    def flaky():\n'
                '        nonlocal attempts\n'
                '        attempts += 1\n'
                '        if attempts < 3:\n'
                '            raise ConnectionResetError("network drop")\n'
                '        return "RECOVERED"\n'
                '    res = client.call(flaky, seed=42)\n'
                '    assert res == "RECOVERED"\n'
                '    assert len(transport.request_timestamps) == 3\n'
                '    # Request timestamps must strictly advance, preventing zero-delay burst\n'
                '    t0, t1, t2 = transport.request_timestamps\n'
                '    assert t1 > t0\n'
                '    assert t2 > t1\n\n\n'
                'def test_circuit_breaker_trips_on_exhaustion():\n'
                '    policy = RetryPolicy(max_retries=2)\n'
                '    cb = CircuitBreaker(failure_threshold=3)\n'
                '    transport = VirtualTransport()\n'
                '    client = StormResistantClient(policy, cb, transport)\n'
                '    with pytest.raises(Exception):\n'
                '        client.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")), seed=10)\n'
                '    assert cb.tripped is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "adversarial",
            "bug_type": "adversarial_retry_backoff_zero_delay_collapse",
            "categories": ["M", "H", "K"],
            "description": "Exponential backoff jitter function erroneously zeroes delays on even seeds, causing zero-interval retry storms.",
            "spec_notes": "BackoffJitter.calculate_delay must guarantee positive non-zero backoff across all seed inputs.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": True,
                "stateful": True,
                "multi_file": True,
                "domain": "networking",
            },
        }

