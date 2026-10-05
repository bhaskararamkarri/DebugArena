"""Category H: API & Backend Logic Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class ApiTaskGenerator(BaseGenerator):
    """Generates realistic cursor pagination and webhook API backend debugging tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v27_cursor_time_pagination_drift")
        sub_type = spec.get("sub_type", "pagination")

        if sub_type == "graphql_nplus1" or "dataloader" in task_id:
            return self._generate_dataloader_batching(task_id, spec, seed)
        elif sub_type == "api_versioning" or "versioning" in task_id or "routing" in task_id:
            return self._generate_versioning_router(task_id, spec, seed)
        elif sub_type == "federation_planner" or "federation" in task_id or "planner" in task_id:
            return self._generate_federation_planner(task_id, spec, seed)
        elif sub_type == "circuit_breaker" or "circuit_breaker" in task_id or "mesh" in task_id:
            return self._generate_circuit_breaker_oscillation(task_id, spec, seed)
        return self._generate_cursor_pagination(task_id, spec, seed)

    def _generate_cursor_pagination(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Log record data models."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict, List, Optional\n\n\n'
                '@dataclass\n'
                'class AuditLog:\n'
                '    log_id: str\n'
                '    created_at: int\n'
                '    action: str\n\n\n'
                '@dataclass\n'
                'class PageResult:\n'
                '    items: List[AuditLog]\n'
                '    next_cursor: Optional[str]\n'
                '    has_more: bool\n'
            ),
            "database.py": (
                '"""Database mock with indexed query capabilities."""\n\n'
                'from typing import List\n'
                'from models import AuditLog\n\n\n'
                'class AuditLogDB:\n'
                '    def __init__(self):\n'
                '        self.records: List[AuditLog] = []\n\n'
                '    def insert_batch(self, logs: List[AuditLog]) -> None:\n'
                '        self.records.extend(logs)\n'
                '        # Records naturally indexed by (created_at, log_id)\n'
                '        self.records.sort(key=lambda r: (r.created_at, r.log_id))\n\n'
                '    def get_all(self) -> List[AuditLog]:\n'
                '        return list(self.records)\n'
            ),
            "pagination.py": (
                '"""Cursor pagination evaluator."""\n\n'
                'import base64\n'
                'from typing import List, Optional\n'
                'from database import AuditLogDB\n'
                'from models import AuditLog, PageResult\n\n\n'
                'class CursorPaginator:\n'
                '    def __init__(self, db: AuditLogDB):\n'
                '        self.db = db\n\n'
                '    def encode_cursor(self, ts: int, log_id: str) -> str:\n'
                '        raw = f"{ts}:{log_id}"\n'
                '        return base64.b64encode(raw.encode("utf-8")).decode("utf-8")\n\n'
                '    def decode_cursor(self, cursor: str) -> tuple[int, str]:\n'
                '        raw = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")\n'
                '        parts = raw.split(":")\n'
                '        return int(parts[0]), parts[1]\n\n'
                '    def fetch_page(self, cursor: Optional[str], limit: int = 2) -> PageResult:\n'
                '        all_logs = self.db.get_all()\n'
                '        filtered: List[AuditLog] = []\n\n'
                '        if cursor:\n'
                '            after_ts, after_id = self.decode_cursor(cursor)\n'
                '            # BUG: Only checks r.created_at > after_ts without secondary tie-breaker ID r.log_id > after_id,\n'
                '            # skipping all subsequent sibling records sharing the exact same created_at timestamp!\n'
                '            filtered = [r for r in all_logs if r.created_at > after_ts]\n'
                '        else:\n'
                '            filtered = all_logs\n\n'
                '        page_items = filtered[:limit]\n'
                '        has_more = len(filtered) > limit\n'
                '        next_cur = None\n'
                '        if page_items and has_more:\n'
                '            last = page_items[-1]\n'
                '            next_cur = self.encode_cursor(last.created_at, last.log_id)\n\n'
                '        return PageResult(items=page_items, next_cursor=next_cur, has_more=has_more)\n'
            ),
        }

        reference_fix = {
            "pagination.py": (
                '"""Cursor pagination evaluator."""\n\n'
                'import base64\n'
                'from typing import List, Optional\n'
                'from database import AuditLogDB\n'
                'from models import AuditLog, PageResult\n\n\n'
                'class CursorPaginator:\n'
                '    def __init__(self, db: AuditLogDB):\n'
                '        self.db = db\n\n'
                '    def encode_cursor(self, ts: int, log_id: str) -> str:\n'
                '        raw = f"{ts}:{log_id}"\n'
                '        return base64.b64encode(raw.encode("utf-8")).decode("utf-8")\n\n'
                '    def decode_cursor(self, cursor: str) -> tuple[int, str]:\n'
                '        raw = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")\n'
                '        parts = raw.split(":")\n'
                '        return int(parts[0]), parts[1]\n\n'
                '    def fetch_page(self, cursor: Optional[str], limit: int = 2) -> PageResult:\n'
                '        all_logs = self.db.get_all()\n'
                '        filtered: List[AuditLog] = []\n\n'
                '        if cursor:\n'
                '            after_ts, after_id = self.decode_cursor(cursor)\n'
                '            # Filter with composite condition: created_at > after_ts OR (created_at == after_ts AND log_id > after_id)\n'
                '            filtered = [\n'
                '                r for r in all_logs\n'
                '                if (r.created_at > after_ts) or (r.created_at == after_ts and r.log_id > after_id)\n'
                '            ]\n'
                '        else:\n'
                '            filtered = all_logs\n\n'
                '        page_items = filtered[:limit]\n'
                '        has_more = len(filtered) > limit\n'
                '        next_cur = None\n'
                '        if page_items and has_more:\n'
                '            last = page_items[-1]\n'
                '            next_cur = self.encode_cursor(last.created_at, last.log_id)\n\n'
                '        return PageResult(items=page_items, next_cursor=next_cur, has_more=has_more)\n'
            )
        }

        tests = {
            "test_cursor_pagination.py": (
                'from models import AuditLog\n'
                'from database import AuditLogDB\n'
                'from pagination import CursorPaginator\n\n\n'
                'def test_pagination_distinct_timestamps():\n'
                '    db = AuditLogDB()\n'
                '    db.insert_batch([\n'
                '        AuditLog("log_1", 100, "login"),\n'
                '        AuditLog("log_2", 200, "edit"),\n'
                '        AuditLog("log_3", 300, "logout"),\n'
                '    ])\n'
                '    p = CursorPaginator(db)\n'
                '    page1 = p.fetch_page(None, limit=2)\n'
                '    assert [r.log_id for r in page1.items] == ["log_1", "log_2"]\n'
                '    assert page1.has_more is True\n'
                '    assert page1.next_cursor is not None\n\n'
                '    page2 = p.fetch_page(page1.next_cursor, limit=2)\n'
                '    assert [r.log_id for r in page2.items] == ["log_3"]\n'
                '    assert page2.has_more is False\n'
                '    assert page2.next_cursor is None\n\n\n'
                'def test_identical_timestamp_secondary_key_pagination():\n'
                '    db = AuditLogDB()\n'
                '    # 4 records sharing the EXACT same timestamp 1000\n'
                '    db.insert_batch([\n'
                '        AuditLog("a", 1000, "op_a"),\n'
                '        AuditLog("b", 1000, "op_b"),\n'
                '        AuditLog("c", 1000, "op_c"),\n'
                '        AuditLog("d", 1000, "op_d"),\n'
                '    ])\n'
                '    p = CursorPaginator(db)\n'
                '    # Page 1: limit 2 -> [a, b]\n'
                '    p1 = p.fetch_page(None, limit=2)\n'
                '    assert [r.log_id for r in p1.items] == ["a", "b"]\n'
                '    assert p1.has_more is True\n\n'
                '    # Page 2: with cursor from b -> MUST return [c, d], NOT empty list!\n'
                '    p2 = p.fetch_page(p1.next_cursor, limit=2)\n'
                '    assert [r.log_id for r in p2.items] == ["c", "d"]\n'
                '    assert p2.has_more is False\n\n\n'
                'def test_empty_db_page():\n'
                '    db = AuditLogDB()\n'
                '    p = CursorPaginator(db)\n'
                '    page = p.fetch_page(None, limit=10)\n'
                '    assert len(page.items) == 0\n'
                '    assert page.has_more is False\n'
                '    assert page.next_cursor is None\n\n\n'
                'def test_single_item_fits_in_page():\n'
                '    db = AuditLogDB()\n'
                '    db.insert_batch([AuditLog("x", 50, "action")])\n'
                '    p = CursorPaginator(db)\n'
                '    page = p.fetch_page(None, limit=5)\n'
                '    assert len(page.items) == 1\n'
                '    assert page.has_more is False\n'
                '    assert page.next_cursor is None\n\n\n'
                'def test_cursor_roundtrip_codec():\n'
                '    p = CursorPaginator(AuditLogDB())\n'
                '    cur = p.encode_cursor(123456, "log_alpha")\n'
                '    ts, lid = p.decode_cursor(cur)\n'
                '    assert ts == 123456\n'
                '    assert lid == "log_alpha"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "cursor_pagination_timestamp_tiebreaker_omission",
            "categories": ["H", "I", "B"],
            "description": "Cursor paginator only checks timestamp > cursor_timestamp, dropping sibling records with identical timestamps.",
            "spec_notes": "CursorPaginator must apply secondary tie-breaker comparison (created_at > after_ts) or (created_at == after_ts and log_id > after_id).",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "api-backend",
            },
        }

    def _generate_dataloader_batching(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Entity models for GraphQL resolution."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class Author:\n'
                '    author_id: str\n'
                '    name: str\n\n\n'
                '@dataclass\n'
                'class Book:\n'
                '    book_id: str\n'
                '    title: str\n'
                '    author_id: str\n'
            ),
            "dataloader.py": (
                '"""Batch DataLoader collecting IDs for single bulk query resolution."""\n\n'
                'from typing import Any, Callable, Dict, List, Optional\n\n\n'
                'class BatchDataLoader:\n'
                '    def __init__(self, batch_fn: Callable[[List[str]], Dict[str, Any]]):\n'
                '        self.batch_fn = batch_fn\n'
                '        self._queue: list[str] = []\n'
                '        self._cache: Dict[str, Any] = {}\n\n'
                '    def load(self, key: str) -> None:\n'
                '        if key not in self._cache and key not in self._queue:\n'
                '            self._queue.append(key)\n\n'
                '    def dispatch(self) -> None:\n'
                '        if not self._queue:\n'
                '            return\n'
                '        results = self.batch_fn(self._queue)\n'
                '        self._cache.update(results)\n'
                '        # BUG: Clears _queue but fails to populate missing keys with None,\n'
                '        # causing infinite re-fetching or KeyErrors on nonexistent keys!\n'
                '        self._queue = []\n\n'
                '    def get_result(self, key: str) -> Optional[Any]:\n'
                '        return self._cache.get(key)\n'
            ),
            "resolver.py": (
                '"""GraphQL schema field resolvers."""\n\n'
                'from typing import Any, Dict, List, Optional\n'
                'from dataloader import BatchDataLoader\n'
                'from models import Author, Book\n\n\n'
                'class BookResolver:\n'
                '    def __init__(self, authors_db: Dict[str, Author]):\n'
                '        self.db_query_count = 0\n'
                '        def bulk_fetch_authors(keys: List[str]) -> Dict[str, Author]:\n'
                '            self.db_query_count += 1\n'
                '            return {k: authors_db[k] for k in keys if k in authors_db}\n'
                '        self.loader = BatchDataLoader(bulk_fetch_authors)\n\n'
                '    def resolve_author_for_book(self, book: Book) -> Optional[Author]:\n'
                '        self.loader.load(book.author_id)\n'
                '        return None  # Pending batch dispatch\n'
            ),
            "executor.py": (
                '"""GraphQL query plan batch execution coordinator."""\n\n'
                'from typing import Any, Dict, List\n'
                'from models import Author, Book\n'
                'from resolver import BookResolver\n\n\n'
                'class QueryExecutor:\n'
                '    def __init__(self, resolver: BookResolver):\n'
                '        self.resolver = resolver\n\n'
                '    def execute_books_query(self, books: List[Book]) -> List[Dict[str, Any]]:\n'
                '        # Stage 1: Enqueue all author IDs\n'
                '        for b in books:\n'
                '            self.resolver.resolve_author_for_book(b)\n'
                '        # Stage 2: Single batch dispatch\n'
                '        self.resolver.loader.dispatch()\n'
                '        # Stage 3: Assemble results\n'
                '        out = []\n'
                '        for b in books:\n'
                '            author = self.resolver.loader.get_result(b.author_id)\n'
                '            out.append({\n'
                '                "title": b.title,\n'
                '                "author_name": author.name if author else "Unknown",\n'
                '            })\n'
                '        return out\n'
            ),
        }

        reference_fix = {
            "dataloader.py": (
                '"""Batch DataLoader collecting IDs for single bulk query resolution."""\n\n'
                'from typing import Any, Callable, Dict, List, Optional\n\n\n'
                'class BatchDataLoader:\n'
                '    def __init__(self, batch_fn: Callable[[List[str]], Dict[str, Any]]):\n'
                '        self.batch_fn = batch_fn\n'
                '        self._queue: list[str] = []\n'
                '        self._cache: Dict[str, Any] = {}\n\n'
                '    def load(self, key: str) -> None:\n'
                '        if key not in self._cache and key not in self._queue:\n'
                '            self._queue.append(key)\n\n'
                '    def dispatch(self) -> None:\n'
                '        if not self._queue:\n'
                '            return\n'
                '        keys_to_fetch = list(self._queue)\n'
                '        self._queue = []\n'
                '        results = self.batch_fn(keys_to_fetch)\n'
                '        for k in keys_to_fetch:\n'
                '            self._cache[k] = results.get(k, None)\n\n'
                '    def get_result(self, key: str) -> Optional[Any]:\n'
                '        return self._cache.get(key)\n'
            )
        }

        tests = {
            "test_dataloader.py": (
                'from models import Author, Book\n'
                'from resolver import BookResolver\n'
                'from executor import QueryExecutor\n\n\n'
                'def test_n_plus_one_batching_single_db_query():\n'
                '    authors_db = {\n'
                '        "a1": Author("a1", "Tolkien"),\n'
                '        "a2": Author("a2", "Martin"),\n'
                '    }\n'
                '    resolver = BookResolver(authors_db)\n'
                '    executor = QueryExecutor(resolver)\n'
                '    books = [\n'
                '        Book("b1", "The Hobbit", "a1"),\n'
                '        Book("b2", "The Fellowship", "a1"),\n'
                '        Book("b3", "A Game of Thrones", "a2"),\n'
                '        Book("b4", "The Two Towers", "a1"),\n'
                '    ]\n'
                '    res = executor.execute_books_query(books)\n'
                '    assert len(res) == 4\n'
                '    assert res[0]["author_name"] == "Tolkien"\n'
                '    assert res[2]["author_name"] == "Martin"\n'
                '    # CRITICAL: 4 books resolved in EXACTLY 1 batch DB query (not N=4 queries!)\n'
                '    assert resolver.db_query_count == 1\n\n\n'
                'def test_missing_author_cached_as_none_without_refetch():\n'
                '    resolver = BookResolver({"a1": Author("a1", "Rowling")})\n'
                '    executor = QueryExecutor(resolver)\n'
                '    books = [Book("b1", "Ghost Story", "nonexistent_author")]\n'
                '    res = executor.execute_books_query(books)\n'
                '    assert res[0]["author_name"] == "Unknown"\n'
                '    assert resolver.db_query_count == 1\n'
                '    # Dispatch again: cached None must prevent re-querying\n'
                '    resolver.loader.load("nonexistent_author")\n'
                '    resolver.loader.dispatch()\n'
                '    assert resolver.db_query_count == 1\n\n\n'
                'def test_empty_books_query():\n'
                '    resolver = BookResolver({})\n'
                '    executor = QueryExecutor(resolver)\n'
                '    assert executor.execute_books_query([]) == []\n'
                '    assert resolver.db_query_count == 0\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "graphql_dataloader_missing_key_null_cache_omission",
            "categories": ["H", "K", "E"],
            "description": "GraphQL DataLoader fails to cache null/missing entity keys, triggering repeated round-trips and corrupting batch resolution.",
            "spec_notes": "BatchDataLoader.dispatch must store None for requested keys not returned by batch_fn.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "api-backend",
            },
        }

    def _generate_versioning_router(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "version.py": (
                '"""API version header extractor."""\n\n'
                'from typing import Dict\n\n\n'
                'class APIVersionExtractor:\n'
                '    @staticmethod\n'
                '    def extract_version(headers: Dict[str, str]) -> str:\n'
                '        # Header: X-API-Version: 2026-01 or Accept: application/vnd.app.v2+json\n'
                '        v_hdr = headers.get("X-API-Version")\n'
                '        if v_hdr:\n'
                '            return v_hdr.strip()\n'
                '        accept = headers.get("Accept", "")\n'
                '        if "vnd.app.v2" in accept:\n'
                '            return "v2"\n'
                '        return "v1"\n'
            ),
            "adapter_v1.py": (
                '"""V1 API payload adapter."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class V1Adapter:\n'
                '    @staticmethod\n'
                '    def format_response(user_id: str, name: str) -> Dict[str, Any]:\n'
                '        return {"id": user_id, "name": name, "version": "v1"}\n'
            ),
            "adapter_v2.py": (
                '"""V2 API payload adapter."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class V2Adapter:\n'
                '    @staticmethod\n'
                '    def format_response(user_id: str, name: str) -> Dict[str, Any]:\n'
                '        return {"data": {"userId": user_id, "displayName": name}, "version": "v2"}\n'
            ),
            "router.py": (
                '"""Versioned route dispatcher."""\n\n'
                'from typing import Any, Dict\n'
                'from adapter_v1 import V1Adapter\n'
                'from adapter_v2 import V2Adapter\n'
                'from version import APIVersionExtractor\n\n\n'
                'class VersionedAPIRouter:\n'
                '    def route_request(self, headers: Dict[str, str], user_id: str, name: str) -> Dict[str, Any]:\n'
                '        ver = APIVersionExtractor.extract_version(headers)\n'
                '        # BUG: Case-sensitive version equality check fails on "V2" or date strings like "2026-01"!\n'
                '        if ver == "v2":\n'
                '            return V2Adapter.format_response(user_id, name)\n'
                '        return V1Adapter.format_response(user_id, name)\n'
            ),
        }

        reference_fix = {
            "router.py": (
                '"""Versioned route dispatcher."""\n\n'
                'from typing import Any, Dict\n'
                'from adapter_v1 import V1Adapter\n'
                'from adapter_v2 import V2Adapter\n'
                'from version import APIVersionExtractor\n\n\n'
                'class VersionedAPIRouter:\n'
                '    def route_request(self, headers: Dict[str, str], user_id: str, name: str) -> Dict[str, Any]:\n'
                '        ver = APIVersionExtractor.extract_version(headers).lower()\n'
                '        if ver in ("v2", "2026-01", "2"):\n'
                '            return V2Adapter.format_response(user_id, name)\n'
                '        return V1Adapter.format_response(user_id, name)\n'
            )
        }

        tests = {
            "test_version_routing.py": (
                'from router import VersionedAPIRouter\n\n\n'
                'def test_default_v1_routing():\n'
                '    r = VersionedAPIRouter()\n'
                '    res = r.route_request({}, "u1", "Alice")\n'
                '    assert res["version"] == "v1"\n'
                '    assert res["name"] == "Alice"\n\n\n'
                'def test_header_version_v2_routing():\n'
                '    r = VersionedAPIRouter()\n'
                '    res = r.route_request({"X-API-Version": "v2"}, "u2", "Bob")\n'
                '    assert res["version"] == "v2"\n'
                '    assert res["data"]["displayName"] == "Bob"\n\n\n'
                'def test_date_based_version_routing():\n'
                '    r = VersionedAPIRouter()\n'
                '    res = r.route_request({"X-API-Version": "2026-01"}, "u3", "Charlie")\n'
                '    assert res["version"] == "v2"\n'
                '    assert res["data"]["userId"] == "u3"\n\n\n'
                'def test_accept_header_content_negotiation():\n'
                '    r = VersionedAPIRouter()\n'
                '    res = r.route_request({"Accept": "application/vnd.app.v2+json"}, "u4", "Dave")\n'
                '    assert res["version"] == "v2"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "api_versioning_header_case_and_date_dispatch_mismatch",
            "categories": ["H", "E"],
            "description": "Versioned router fails to match date-based and case-variant API version headers, routing v2 clients to legacy v1 formats.",
            "spec_notes": "VersionedAPIRouter must route '2026-01' and case-insensitive 'V2' headers to V2Adapter.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "api-backend",
            },
        }

    def _generate_federation_planner(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "schema.py": (
                '"""GraphQL federation subgraph schema definitions."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Dict, List\n\n\n'
                '@dataclass\n'
                'class SubgraphField:\n'
                '    name: str\n'
                '    service_name: str\n'
                '    required_fields: List[str] = field(default_factory=list)\n'
            ),
            "service_registry.py": (
                '"""Subgraph service registry."""\n\n'
                'from typing import Dict, List\n'
                'from schema import SubgraphField\n\n\n'
                'class FederationRegistry:\n'
                '    def __init__(self):\n'
                '        # Maps field_name -> SubgraphField\n'
                '        self.fields: Dict[str, SubgraphField] = {}\n\n'
                '    def register_field(self, field: SubgraphField) -> None:\n'
                '        self.fields[field.name] = field\n'
            ),
            "planner.py": (
                '"""Federated query planner assembling cross-service execution steps."""\n\n'
                'from typing import Dict, List, Set\n'
                'from schema import SubgraphField\n'
                'from service_registry import FederationRegistry\n\n\n'
                'class QueryPlanStep:\n'
                '    def __init__(self, service: str, requested_fields: List[str]):\n'
                '        self.service = service\n'
                '        self.requested_fields = list(requested_fields)\n\n\n'
                'class FederationQueryPlanner:\n'
                '    def __init__(self, registry: FederationRegistry):\n'
                '        self.registry = registry\n\n'
                '    def plan_query(self, target_fields: List[str]) -> List[QueryPlanStep]:\n'
                '        service_map: Dict[str, Set[str]] = {}\n'
                '        # BUG: Only schedules requested target_fields into service buckets,\n'
                '        # failing to inspect field.required_fields dependencies (like author_id for reviews)!\n'
                '        for f_name in target_fields:\n'
                '            field_def = self.registry.fields.get(f_name)\n'
                '            if not field_def:\n'
                '                continue\n'
                '            svc = field_def.service_name\n'
                '            if svc not in service_map:\n'
                '                service_map[svc] = set()\n'
                '            service_map[svc].add(f_name)\n'
                '        return [QueryPlanStep(svc, sorted(fields)) for svc, fields in service_map.items()]\n'
            ),
        }

        reference_fix = {
            "planner.py": (
                '"""Federated query planner assembling cross-service execution steps."""\n\n'
                'from typing import Dict, List, Set\n'
                'from schema import SubgraphField\n'
                'from service_registry import FederationRegistry\n\n\n'
                'class QueryPlanStep:\n'
                '    def __init__(self, service: str, requested_fields: List[str]):\n'
                '        self.service = service\n'
                '        self.requested_fields = list(requested_fields)\n\n\n'
                'class FederationQueryPlanner:\n'
                '    def __init__(self, registry: FederationRegistry):\n'
                '        self.registry = registry\n\n'
                '    def plan_query(self, target_fields: List[str]) -> List[QueryPlanStep]:\n'
                '        service_map: Dict[str, Set[str]] = {}\n'
                '        for f_name in target_fields:\n'
                '            field_def = self.registry.fields.get(f_name)\n'
                '            if not field_def:\n'
                '                continue\n'
                '            svc = field_def.service_name\n'
                '            if svc not in service_map:\n'
                '                service_map[svc] = set()\n'
                '            service_map[svc].add(f_name)\n'
                '            # Inject required prerequisite dependency fields\n'
                '            for req in field_def.required_fields:\n'
                '                req_def = self.registry.fields.get(req)\n'
                '                if req_def:\n'
                '                    req_svc = req_def.service_name\n'
                '                    if req_svc not in service_map:\n'
                '                        service_map[req_svc] = set()\n'
                '                    service_map[req_svc].add(req)\n'
                '        return [QueryPlanStep(svc, sorted(fields)) for svc, fields in sorted(service_map.items())]\n'
            )
        }

        tests = {
            "test_federation_planner.py": (
                'from schema import SubgraphField\n'
                'from service_registry import FederationRegistry\n'
                'from planner import FederationQueryPlanner\n\n\n'
                'def test_federated_dependency_injection():\n'
                '    reg = FederationRegistry()\n'
                '    # User service provides id, username\n'
                '    reg.register_field(SubgraphField("id", "users_service"))\n'
                '    reg.register_field(SubgraphField("username", "users_service"))\n'
                '    # Reviews service provides rating, but requires id\n'
                '    reg.register_field(SubgraphField("rating", "reviews_service", required_fields=["id"]))\n'
                '    planner = FederationQueryPlanner(reg)\n'
                '    # Querying rating on reviews service must inject id fetch in users_service!\n'
                '    plan = planner.plan_query(["rating"])\n'
                '    svc_map = {step.service: step.requested_fields for step in plan}\n'
                '    assert "reviews_service" in svc_map\n'
                '    assert svc_map["reviews_service"] == ["rating"]\n'
                '    assert "users_service" in svc_map\n'
                '    assert "id" in svc_map["users_service"]\n\n\n'
                'def test_simple_single_service_query():\n'
                '    reg = FederationRegistry()\n'
                '    reg.register_field(SubgraphField("title", "products_service"))\n'
                '    planner = FederationQueryPlanner(reg)\n'
                '    plan = planner.plan_query(["title"])\n'
                '    assert len(plan) == 1\n'
                '    assert plan[0].service == "products_service"\n'
                '    assert plan[0].requested_fields == ["title"]\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "graphql_federation_requires_directive_dependency_omission",
            "categories": ["H", "E"],
            "description": "GraphQL federation query planner fails to inject required prerequisite fields across subgraphs, causing resolution failures.",
            "spec_notes": "FederationQueryPlanner.plan_query must inject field.required_fields into upstream service sub-queries.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "api-gateways",
            },
        }

    def _generate_circuit_breaker_oscillation(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "circuit_state.py": (
                '"""Circuit breaker state enumeration."""\n\n'
                'class CircuitState:\n'
                '    CLOSED = "CLOSED"\n'
                '    OPEN = "OPEN"\n'
                '    HALF_OPEN = "HALF_OPEN"\n'
            ),
            "circuit_breaker.py": (
                '"""Service mesh circuit breaker with half-open trial progression."""\n\n'
                'from circuit_state import CircuitState\n\n\n'
                'class MeshCircuitBreaker:\n'
                '    def __init__(self, failure_threshold: int = 3, success_threshold: int = 3, cooldown_sec: float = 5.0):\n'
                '        self.failure_threshold = failure_threshold\n'
                '        self.success_threshold = success_threshold\n'
                '        self.cooldown_sec = cooldown_sec\n'
                '        self.state = CircuitState.CLOSED\n'
                '        self.consecutive_failures = 0\n'
                '        self.consecutive_successes = 0\n'
                '        self.tripped_at: float = 0.0\n\n'
                '    def allow_request(self, now: float) -> bool:\n'
                '        if self.state == CircuitState.CLOSED:\n'
                '            return True\n'
                '        if self.state == CircuitState.OPEN:\n'
                '            if now - self.tripped_at >= self.cooldown_sec:\n'
                '                self.state = CircuitState.HALF_OPEN\n'
                '                self.consecutive_successes = 0\n'
                '                return True\n'
                '            return False\n'
                '        return True  # HALF_OPEN allows probe requests\n\n'
                '    def record_result(self, success: bool, now: float) -> None:\n'
                '        if not success:\n'
                '            self.consecutive_failures += 1\n'
                '            self.consecutive_successes = 0\n'
                '            self.state = CircuitState.OPEN\n'
                '            self.tripped_at = now\n'
                '        else:\n'
                '            if self.state == CircuitState.HALF_OPEN:\n'
                '                # BUG: Resets consecutive_successes to 0 instead of incrementing toward success_threshold!\n'
                '                # Circuit remains stuck in HALF_OPEN oscillating forever.\n'
                '                self.consecutive_successes = 0\n'
                '                if self.consecutive_successes >= self.success_threshold:\n'
                '                    self.state = CircuitState.CLOSED\n'
                '            elif self.state == CircuitState.CLOSED:\n'
                '                self.consecutive_failures = 0\n'
            ),
            "mesh_proxy.py": (
                '"""Mesh proxy wrapping upstream calls with circuit breaker."""\n\n'
                'from typing import Callable\n'
                'from circuit_breaker import MeshCircuitBreaker\n\n\n'
                'class MeshProxy:\n'
                '    def __init__(self, breaker: MeshCircuitBreaker):\n'
                '        self.breaker = breaker\n\n'
                '    def send(self, now: float, fn: Callable[[], bool]) -> bool:\n'
                '        if not self.breaker.allow_request(now):\n'
                '            return False\n'
                '        res = fn()\n'
                '        self.breaker.record_result(res, now)\n'
                '        return res\n'
            ),
        }

        reference_fix = {
            "circuit_breaker.py": (
                '"""Service mesh circuit breaker with half-open trial progression."""\n\n'
                'from circuit_state import CircuitState\n\n\n'
                'class MeshCircuitBreaker:\n'
                '    def __init__(self, failure_threshold: int = 3, success_threshold: int = 3, cooldown_sec: float = 5.0):\n'
                '        self.failure_threshold = failure_threshold\n'
                '        self.success_threshold = success_threshold\n'
                '        self.cooldown_sec = cooldown_sec\n'
                '        self.state = CircuitState.CLOSED\n'
                '        self.consecutive_failures = 0\n'
                '        self.consecutive_successes = 0\n'
                '        self.tripped_at: float = 0.0\n\n'
                '    def allow_request(self, now: float) -> bool:\n'
                '        if self.state == CircuitState.CLOSED:\n'
                '            return True\n'
                '        if self.state == CircuitState.OPEN:\n'
                '            if now - self.tripped_at >= self.cooldown_sec:\n'
                '                self.state = CircuitState.HALF_OPEN\n'
                '                self.consecutive_successes = 0\n'
                '                return True\n'
                '            return False\n'
                '        return True\n\n'
                '    def record_result(self, success: bool, now: float) -> None:\n'
                '        if not success:\n'
                '            self.consecutive_failures += 1\n'
                '            self.consecutive_successes = 0\n'
                '            self.state = CircuitState.OPEN\n'
                '            self.tripped_at = now\n'
                '        else:\n'
                '            if self.state == CircuitState.HALF_OPEN:\n'
                '                self.consecutive_successes += 1\n'
                '                if self.consecutive_successes >= self.success_threshold:\n'
                '                    self.state = CircuitState.CLOSED\n'
                '                    self.consecutive_failures = 0\n'
                '                    self.consecutive_successes = 0\n'
                '            elif self.state == CircuitState.CLOSED:\n'
                '                self.consecutive_failures = 0\n'
            )
        }

        tests = {
            "test_circuit_oscillation.py": (
                'from circuit_breaker import MeshCircuitBreaker\n'
                'from circuit_state import CircuitState\n'
                'from mesh_proxy import MeshProxy\n\n\n'
                'def test_half_open_recovers_to_closed_after_success_threshold():\n'
                '    cb = MeshCircuitBreaker(failure_threshold=2, success_threshold=3, cooldown_sec=5.0)\n'
                '    proxy = MeshProxy(cb)\n'
                '    # Trip to OPEN\n'
                '    proxy.send(100.0, lambda: False)\n'
                '    proxy.send(100.0, lambda: False)\n'
                '    assert cb.state == CircuitState.OPEN\n\n'
                '    # Probe at t=106 (cooldown elapsed) enters HALF_OPEN\n'
                '    assert proxy.send(106.0, lambda: True) is True\n'
                '    assert cb.state == CircuitState.HALF_OPEN\n'
                '    assert cb.consecutive_successes == 1\n\n'
                '    # 2nd and 3rd successes reach success_threshold=3 and CLOSE circuit\n'
                '    proxy.send(107.0, lambda: True)\n'
                '    proxy.send(108.0, lambda: True)\n'
                '    assert cb.state == CircuitState.CLOSED\n'
                '    assert cb.consecutive_failures == 0\n\n\n'
                'def test_single_failure_in_half_open_reopens_immediately():\n'
                '    cb = MeshCircuitBreaker(failure_threshold=2, success_threshold=3, cooldown_sec=5.0)\n'
                '    proxy = MeshProxy(cb)\n'
                '    proxy.send(100.0, lambda: False)\n'
                '    proxy.send(100.0, lambda: False)\n'
                '    # Probe succeeds\n'
                '    proxy.send(106.0, lambda: True)\n'
                '    # Subsequent probe fails -> re-trips to OPEN\n'
                '    proxy.send(107.0, lambda: False)\n'
                '    assert cb.state == CircuitState.OPEN\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "circuit_breaker_half_open_success_counter_zeroing",
            "categories": ["H", "E", "G"],
            "description": "Circuit breaker zeroes consecutive successes during HALF_OPEN probe requests, preventing transition back to CLOSED state.",
            "spec_notes": "MeshCircuitBreaker.record_result must increment consecutive_successes and close circuit once threshold is reached.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "service-mesh",
            },
        }


