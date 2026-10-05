"""Category E: Multi-File Repository & Contract Propagation Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class RepositoryTaskGenerator(BaseGenerator):
    """Generates cross-module contract and serialization propagation multi-file tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v25_service_data_contract_propagation")
        sub_type = spec.get("sub_type", "contract")

        if sub_type == "trace_correlation" or "trace" in task_id or "distributed" in task_id:
            return self._generate_trace_correlation(task_id, spec, seed)
        return self._generate_contract_propagation(task_id, spec, seed)

    def _generate_contract_propagation(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Entity data models."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class CustomerProfile:\n'
                '    customer_id: str\n'
                '    name: str\n'
                '    email: str\n'
                '    tier: str\n'
                '    created_at_ts: int\n'
            ),
            "repository.py": (
                '"""Customer data persistence repository."""\n\n'
                'from typing import Dict, Optional\n'
                'from models import CustomerProfile\n\n\n'
                'class CustomerRepository:\n'
                '    def __init__(self):\n'
                '        self._storage: Dict[str, dict] = {}\n\n'
                '    def save(self, profile: CustomerProfile) -> None:\n'
                '        # BUG: Persists with dictionary key "timestamp" instead of model attribute "created_at_ts"\n'
                '        self._storage[profile.customer_id] = {\n'
                '            "customer_id": profile.customer_id,\n'
                '            "name": profile.name,\n'
                '            "email": profile.email,\n'
                '            "tier": profile.tier,\n'
                '            "timestamp": profile.created_at_ts,\n'
                '        }\n\n'
                '    def find_by_id(self, customer_id: str) -> Optional[CustomerProfile]:\n'
                '        data = self._storage.get(customer_id)\n'
                '        if not data:\n'
                '            return None\n'
                '        # BUG: Expects "created_at_ts" but saved as "timestamp", resulting in KeyError or 0\n'
                '        ts = data.get("created_at_ts", 0)\n'
                '        return CustomerProfile(\n'
                '            customer_id=data["customer_id"],\n'
                '            name=data["name"],\n'
                '            email=data["email"],\n'
                '            tier=data["tier"],\n'
                '            created_at_ts=ts,\n'
                '        )\n'
            ),
            "serializer.py": (
                '"""API serialization and wire transformation."""\n\n'
                'from typing import Any, Dict\n'
                'from models import CustomerProfile\n\n\n'
                'class CustomerSerializer:\n'
                '    @staticmethod\n'
                '    def to_wire(profile: CustomerProfile) -> Dict[str, Any]:\n'
                '        # BUG: Wire schema contract specifies "created_at_ts" integer and uppercase tier,\n'
                '        # but serializer outputs "created_at" string\n'
                '        return {\n'
                '            "id": profile.customer_id,\n'
                '            "full_name": profile.name,\n'
                '            "email_address": profile.email,\n'
                '            "account_tier": profile.tier.upper(),\n'
                '            "created_at": str(profile.created_at_ts),\n'
                '        }\n'
            ),
            "service.py": (
                '"""Customer domain management service."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from models import CustomerProfile\n'
                'from repository import CustomerRepository\n'
                'from serializer import CustomerSerializer\n\n\n'
                'class CustomerService:\n'
                '    def __init__(self, repo: CustomerRepository):\n'
                '        self.repo = repo\n\n'
                '    def register_customer(self, customer_id: str, name: str, email: str, tier: str, ts: int) -> CustomerProfile:\n'
                '        profile = CustomerProfile(customer_id, name, email, tier, ts)\n'
                '        self.repo.save(profile)\n'
                '        return profile\n\n'
                '    def get_wire_payload(self, customer_id: str) -> Optional[Dict[str, Any]]:\n'
                '        profile = self.repo.find_by_id(customer_id)\n'
                '        if not profile:\n'
                '            return None\n'
                '        return CustomerSerializer.to_wire(profile)\n'
            ),
        }

        reference_fix = {
            "repository.py": (
                '"""Customer data persistence repository."""\n\n'
                'from typing import Dict, Optional\n'
                'from models import CustomerProfile\n\n\n'
                'class CustomerRepository:\n'
                '    def __init__(self):\n'
                '        self._storage: Dict[str, dict] = {}\n\n'
                '    def save(self, profile: CustomerProfile) -> None:\n'
                '        self._storage[profile.customer_id] = {\n'
                '            "customer_id": profile.customer_id,\n'
                '            "name": profile.name,\n'
                '            "email": profile.email,\n'
                '            "tier": profile.tier,\n'
                '            "created_at_ts": profile.created_at_ts,\n'
                '        }\n\n'
                '    def find_by_id(self, customer_id: str) -> Optional[CustomerProfile]:\n'
                '        data = self._storage.get(customer_id)\n'
                '        if not data:\n'
                '            return None\n'
                '        return CustomerProfile(\n'
                '            customer_id=data["customer_id"],\n'
                '            name=data["name"],\n'
                '            email=data["email"],\n'
                '            tier=data["tier"],\n'
                '            created_at_ts=data["created_at_ts"],\n'
                '        )\n'
            ),
            "serializer.py": (
                '"""API serialization and wire transformation."""\n\n'
                'from typing import Any, Dict\n'
                'from models import CustomerProfile\n\n\n'
                'class CustomerSerializer:\n'
                '    @staticmethod\n'
                '    def to_wire(profile: CustomerProfile) -> Dict[str, Any]:\n'
                '        return {\n'
                '            "id": profile.customer_id,\n'
                '            "full_name": profile.name,\n'
                '            "email_address": profile.email,\n'
                '            "account_tier": profile.tier.upper(),\n'
                '            "created_at_ts": profile.created_at_ts,\n'
                '        }\n'
            ),
        }

        tests = {
            "test_customer_contract.py": (
                'from repository import CustomerRepository\n'
                'from service import CustomerService\n'
                'from models import CustomerProfile\n\n\n'
                'def test_save_and_retrieve_preserves_timestamp():\n'
                '    repo = CustomerRepository()\n'
                '    service = CustomerService(repo)\n'
                '    service.register_customer("c1", "Alice", "alice@example.com", "gold", 1700000000)\n'
                '    retrieved = repo.find_by_id("c1")\n'
                '    assert retrieved is not None\n'
                '    assert retrieved.created_at_ts == 1700000000\n'
                '    assert retrieved.name == "Alice"\n\n\n'
                'def test_wire_payload_serialization_contract():\n'
                '    repo = CustomerRepository()\n'
                '    service = CustomerService(repo)\n'
                '    service.register_customer("c2", "Bob Smith", "bob@example.com", "platinum", 1700000500)\n'
                '    wire = service.get_wire_payload("c2")\n'
                '    assert wire is not None\n'
                '    assert wire["id"] == "c2"\n'
                '    assert wire["full_name"] == "Bob Smith"\n'
                '    assert wire["email_address"] == "bob@example.com"\n'
                '    assert wire["account_tier"] == "PLATINUM"\n'
                '    assert wire["created_at_ts"] == 1700000500\n'
                '    assert isinstance(wire["created_at_ts"], int)\n\n\n'
                'def test_nonexistent_customer_returns_none():\n'
                '    repo = CustomerRepository()\n'
                '    service = CustomerService(repo)\n'
                '    assert service.get_wire_payload("c_missing") is None\n'
                '    assert repo.find_by_id("c_missing") is None\n\n\n'
                'def test_multiple_customers_isolated_state():\n'
                '    repo = CustomerRepository()\n'
                '    service = CustomerService(repo)\n'
                '    service.register_customer("u1", "User 1", "u1@test.com", "silver", 100)\n'
                '    service.register_customer("u2", "User 2", "u2@test.com", "bronze", 200)\n'
                '    w1 = service.get_wire_payload("u1")\n'
                '    w2 = service.get_wire_payload("u2")\n'
                '    assert w1["created_at_ts"] == 100\n'
                '    assert w2["created_at_ts"] == 200\n\n\n'
                'def test_update_profile_overwrites_cleanly():\n'
                '    repo = CustomerRepository()\n'
                '    service = CustomerService(repo)\n'
                '    service.register_customer("u1", "Old Name", "old@test.com", "silver", 100)\n'
                '    service.register_customer("u1", "New Name", "new@test.com", "gold", 300)\n'
                '    w = service.get_wire_payload("u1")\n'
                '    assert w["full_name"] == "New Name"\n'
                '    assert w["account_tier"] == "GOLD"\n'
                '    assert w["created_at_ts"] == 300\n\n\n'
                'def test_empty_repository_lookup():\n'
                '    repo = CustomerRepository()\n'
                '    assert repo.find_by_id("any") is None\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "cross_module_contract_serialization_mismatch",
            "categories": ["E", "H"],
            "description": "Cross-module schema mismatch between repository persistence key and wire serializer drops timestamp field.",
            "spec_notes": "CustomerRepository and CustomerSerializer must uniformly use created_at_ts integer attribute.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "service-architecture",
            },
        }

    def _generate_trace_correlation(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "context.py": (
                '"""Distributed trace context model."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class TraceContext:\n'
                '    trace_id: str\n'
                '    span_id: str\n'
                '    parent_span_id: Optional[str] = None\n'
                '    sampled: bool = True\n'
            ),
            "propagator.py": (
                '"""W3C traceparent header serializer and parser."""\n\n'
                'import re\n'
                'from typing import Dict, Optional\n'
                'from context import TraceContext\n\n'
                'TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")\n\n\n'
                'class W3CTracePropagator:\n'
                '    @staticmethod\n'
                '    def extract(headers: Dict[str, str]) -> Optional[TraceContext]:\n'
                '        header_val = headers.get("traceparent") or headers.get("Traceparent")\n'
                '        if not header_val:\n'
                '            return None\n'
                '        match = TRACEPARENT_REGEX.match(header_val.strip())\n'
                '        if not match:\n'
                '            return None\n'
                '        trace_id, span_id, flags = match.groups()\n'
                '        sampled = flags == "01"\n'
                '        return TraceContext(trace_id=trace_id, span_id=span_id, sampled=sampled)\n\n'
                '    @staticmethod\n'
                '    def inject(ctx: TraceContext, headers: Dict[str, str]) -> None:\n'
                '        flags = "01" if ctx.sampled else "00"\n'
                '        headers["traceparent"] = f"00-{ctx.trace_id}-{ctx.span_id}-{flags}"\n'
            ),
            "span.py": (
                '"""Span execution record."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Any, Dict, Optional\n'
                'from context import TraceContext\n\n\n'
                '@dataclass\n'
                'class Span:\n'
                '    name: str\n'
                '    context: TraceContext\n'
                '    tags: Dict[str, Any] = field(default_factory=dict)\n'
                '    finished: bool = False\n'
            ),
            "tracer.py": (
                '"""Tracer generating spans and maintaining active scopes."""\n\n'
                'import uuid\n'
                'from typing import Optional\n'
                'from context import TraceContext\n'
                'from span import Span\n\n\n'
                'def generate_id(length: int) -> str:\n'
                '    return uuid.uuid4().hex[:length]\n\n\n'
                'class Tracer:\n'
                '    def start_span(self, name: str, parent_ctx: Optional[TraceContext] = None) -> Span:\n'
                '        new_span_id = generate_id(16)\n'
                '        if parent_ctx:\n'
                '            # Inherit trace_id and set parent_span_id\n'
                '            ctx = TraceContext(\n'
                '                trace_id=parent_ctx.trace_id,\n'
                '                span_id=new_span_id,\n'
                '                parent_span_id=parent_ctx.span_id,\n'
                '                sampled=parent_ctx.sampled,\n'
                '            )\n'
                '        else:\n'
                '            ctx = TraceContext(\n'
                '                trace_id=generate_id(32),\n'
                '                span_id=new_span_id,\n'
                '                parent_span_id=None,\n'
                '                sampled=True,\n'
                '            )\n'
                '        return Span(name=name, context=ctx)\n'
            ),
            "middleware.py": (
                '"""HTTP tracing middleware."""\n\n'
                'from typing import Any, Callable, Dict, Tuple\n'
                'from propagator import W3CTracePropagator\n'
                'from tracer import Tracer\n\n\n'
                'class TracingMiddleware:\n'
                '    def __init__(self, tracer: Tracer):\n'
                '        self.tracer = tracer\n\n'
                '    def handle_request(self, headers: Dict[str, str], handler: Callable[[], Any]) -> Tuple[Any, Dict[str, str]]:\n'
                '        extracted_ctx = W3CTracePropagator.extract(headers)\n'
                '        # BUG: Ignores extracted_ctx and passes None to start_span,\n'
                '        # creating a disconnected root trace instead of continuing the distributed trace!\n'
                '        span = self.tracer.start_span("http_request", parent_ctx=None)\n'
                '        try:\n'
                '            result = handler()\n'
                '        finally:\n'
                '            span.finished = True\n'
                '        out_headers: Dict[str, str] = {}\n'
                '        W3CTracePropagator.inject(span.context, out_headers)\n'
                '        return result, out_headers\n'
            ),
        }

        reference_fix = {
            "middleware.py": (
                '"""HTTP tracing middleware."""\n\n'
                'from typing import Any, Callable, Dict, Tuple\n'
                'from propagator import W3CTracePropagator\n'
                'from tracer import Tracer\n\n\n'
                'class TracingMiddleware:\n'
                '    def __init__(self, tracer: Tracer):\n'
                '        self.tracer = tracer\n\n'
                '    def handle_request(self, headers: Dict[str, str], handler: Callable[[], Any]) -> Tuple[Any, Dict[str, str]]:\n'
                '        extracted_ctx = W3CTracePropagator.extract(headers)\n'
                '        span = self.tracer.start_span("http_request", parent_ctx=extracted_ctx)\n'
                '        try:\n'
                '            result = handler()\n'
                '        finally:\n'
                '            span.finished = True\n'
                '        out_headers: Dict[str, str] = {}\n'
                '        W3CTracePropagator.inject(span.context, out_headers)\n'
                '        return result, out_headers\n'
            )
        }

        tests = {
            "test_trace_propagation.py": (
                'from tracer import Tracer\n'
                'from middleware import TracingMiddleware\n'
                'from propagator import W3CTracePropagator\n\n\n'
                'def test_root_trace_creation():\n'
                '    tracer = Tracer()\n'
                '    mw = TracingMiddleware(tracer)\n'
                '    res, out_headers = mw.handle_request({}, lambda: "OK")\n'
                '    assert res == "OK"\n'
                '    assert "traceparent" in out_headers\n'
                '    ctx = W3CTracePropagator.extract(out_headers)\n'
                '    assert ctx is not None\n'
                '    assert len(ctx.trace_id) == 32\n'
                '    assert len(ctx.span_id) == 16\n'
                '    assert ctx.sampled is True\n\n\n'
                'def test_distributed_trace_context_correlation_inheritance():\n'
                '    tracer = Tracer()\n'
                '    mw = TracingMiddleware(tracer)\n'
                '    upstream_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"\n'
                '    upstream_span_id = "00f067aa0ba902b7"\n'
                '    in_headers = {"traceparent": f"00-{upstream_trace_id}-{upstream_span_id}-01"}\n'
                '    res, out_headers = mw.handle_request(in_headers, lambda: "DOWNSTREAM_RES")\n'
                '    assert res == "DOWNSTREAM_RES"\n'
                '    ctx = W3CTracePropagator.extract(out_headers)\n'
                '    assert ctx is not None\n'
                '    # CRITICAL: Trace ID must be preserved exactly across service hops!\n'
                '    assert ctx.trace_id == upstream_trace_id\n'
                '    # Span ID must be newly generated\n'
                '    assert ctx.span_id != upstream_span_id\n\n\n'
                'def test_invalid_traceparent_fallback_to_root():\n'
                '    tracer = Tracer()\n'
                '    mw = TracingMiddleware(tracer)\n'
                '    in_headers = {"traceparent": "malformed-header-format"}\n'
                '    res, out_headers = mw.handle_request(in_headers, lambda: "RECOVERED")\n'
                '    ctx = W3CTracePropagator.extract(out_headers)\n'
                '    assert ctx is not None\n'
                '    assert len(ctx.trace_id) == 32\n\n\n'
                'def test_multi_hop_chain_propagation():\n'
                '    tracer = Tracer()\n'
                '    service_a = TracingMiddleware(tracer)\n'
                '    service_b = TracingMiddleware(tracer)\n'
                '    service_c = TracingMiddleware(tracer)\n'
                '    _, h_a = service_a.handle_request({}, lambda: "A")\n'
                '    _, h_b = service_b.handle_request(h_a, lambda: "B")\n'
                '    _, h_c = service_c.handle_request(h_b, lambda: "C")\n'
                '    ctx_a = W3CTracePropagator.extract(h_a)\n'
                '    ctx_b = W3CTracePropagator.extract(h_b)\n'
                '    ctx_c = W3CTracePropagator.extract(h_c)\n'
                '    assert ctx_a.trace_id == ctx_b.trace_id == ctx_c.trace_id\n'
                '    assert ctx_a.span_id != ctx_b.span_id != ctx_c.span_id\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "distributed_trace_context_parent_propagation_omission",
            "categories": ["F", "E", "H"],
            "description": "Tracing middleware ignores incoming W3C traceparent headers and starts new root traces, breaking distributed trace correlation.",
            "spec_notes": "TracingMiddleware.handle_request must pass extracted_ctx as parent_ctx to tracer.start_span.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "distributed-tracing",
            },
        }

