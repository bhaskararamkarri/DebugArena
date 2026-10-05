"""Category I: Database & Persistence Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class DatabaseTaskGenerator(BaseGenerator):
    """Generates database transaction isolation, connection pooling, and WAL recovery tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v36_db_transaction_isolation_savepoint")
        sub_type = spec.get("sub_type", "savepoint")

        if sub_type == "connection_pool" or "pool" in task_id:
            return self._generate_connection_pool_leak(task_id, spec, seed)
        elif sub_type == "optimistic_locking" or "locking" in task_id or "optimistic" in task_id:
            return self._generate_optimistic_locking(task_id, spec, seed)
        elif sub_type == "wal_recovery" or "wal" in task_id or "checkpoint" in task_id:
            return self._generate_wal_recovery(task_id, spec, seed)
        elif sub_type == "migration_rollback" or "migration" in task_id or "rollback" in task_id:
            return self._generate_migration_rollback(task_id, spec, seed)
        elif sub_type == "lsm_compaction" or "lsm" in task_id or "compaction" in task_id:
            return self._generate_lsm_compaction(task_id, spec, seed)
        return self._generate_savepoint_isolation(task_id, spec, seed)

    def _generate_savepoint_isolation(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "connection.py": (
                '"""Virtual database connection state."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class DBConnection:\n'
                '    def __init__(self):\n'
                '        self.storage: Dict[str, Any] = {}\n'
                '        self.is_open: bool = True\n'
            ),
            "savepoint.py": (
                '"""Savepoint snapshot record."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class Savepoint:\n'
                '    name: str\n'
                '    snapshot_data: Dict[str, Any]\n'
            ),
            "transaction.py": (
                '"""Transaction session with nested savepoint support."""\n\n'
                'from typing import Any, Dict, List, Optional\n'
                'from connection import DBConnection\n'
                'from savepoint import Savepoint\n\n\n'
                'class TransactionSession:\n'
                '    def __init__(self, conn: DBConnection):\n'
                '        self.conn = conn\n'
                '        self.active_data: Dict[str, Any] = dict(conn.storage)\n'
                '        self.savepoints: List[Savepoint] = []\n'
                '        self.is_active: bool = True\n\n'
                '    def create_savepoint(self, name: str) -> None:\n'
                '        # Capture immutable snapshot\n'
                '        sp = Savepoint(name=name, snapshot_data=dict(self.active_data))\n'
                '        self.savepoints.append(sp)\n\n'
                '    def rollback_to_savepoint(self, name: str) -> bool:\n'
                '        target_idx = -1\n'
                '        for i, sp in enumerate(self.savepoints):\n'
                '            if sp.name == name:\n'
                '                target_idx = i\n'
                '                break\n'
                '        if target_idx == -1:\n'
                '            return False\n\n'
                '        target_sp = self.savepoints[target_idx]\n'
                '        self.active_data = dict(target_sp.snapshot_data)\n'
                '        # BUG: Fails to remove subsequent savepoints defined after target_idx,\n'
                '        # leaving orphaned future savepoints on the stack!\n'
                '        return True\n\n'
                '    def commit(self) -> None:\n'
                '        if not self.is_active:\n'
                '            raise RuntimeError("Transaction is inactive")\n'
                '        self.conn.storage = dict(self.active_data)\n'
                '        self.is_active = False\n\n'
                '    def rollback(self) -> None:\n'
                '        self.active_data = dict(self.conn.storage)\n'
                '        self.savepoints.clear()\n'
                '        self.is_active = False\n'
            ),
            "manager.py": (
                '"""Database transaction manager orchestrator."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from connection import DBConnection\n'
                'from transaction import TransactionSession\n\n\n'
                'class TransactionManager:\n'
                '    def __init__(self, conn: DBConnection):\n'
                '        self.conn = conn\n'
                '        self.current_tx: Optional[TransactionSession] = None\n\n'
                '    def begin(self) -> TransactionSession:\n'
                '        self.current_tx = TransactionSession(self.conn)\n'
                '        return self.current_tx\n\n'
                '    def write_record(self, key: str, value: Any) -> None:\n'
                '        if not self.current_tx:\n'
                '            raise RuntimeError("No active transaction")\n'
                '        self.current_tx.active_data[key] = value\n\n'
                '    def read_record(self, key: str) -> Optional[Any]:\n'
                '        if self.current_tx:\n'
                '            return self.current_tx.active_data.get(key)\n'
                '        return self.conn.storage.get(key)\n'
            ),
        }

        reference_fix = {
            "transaction.py": (
                '"""Transaction session with nested savepoint support."""\n\n'
                'from typing import Any, Dict, List, Optional\n'
                'from connection import DBConnection\n'
                'from savepoint import Savepoint\n\n\n'
                'class TransactionSession:\n'
                '    def __init__(self, conn: DBConnection):\n'
                '        self.conn = conn\n'
                '        self.active_data: Dict[str, Any] = dict(conn.storage)\n'
                '        self.savepoints: List[Savepoint] = []\n'
                '        self.is_active: bool = True\n\n'
                '    def create_savepoint(self, name: str) -> None:\n'
                '        # Remove existing savepoint with same name if already present\n'
                '        self.savepoints = [sp for sp in self.savepoints if sp.name != name]\n'
                '        sp = Savepoint(name=name, snapshot_data=dict(self.active_data))\n'
                '        self.savepoints.append(sp)\n\n'
                '    def rollback_to_savepoint(self, name: str) -> bool:\n'
                '        target_idx = -1\n'
                '        for i, sp in enumerate(self.savepoints):\n'
                '            if sp.name == name:\n'
                '                target_idx = i\n'
                '                break\n'
                '        if target_idx == -1:\n'
                '            return False\n\n'
                '        target_sp = self.savepoints[target_idx]\n'
                '        self.active_data = dict(target_sp.snapshot_data)\n'
                '        # Truncate savepoints stack to target_idx + 1 (keeping target savepoint, purging newer ones)\n'
                '        self.savepoints = self.savepoints[: target_idx + 1]\n'
                '        return True\n\n'
                '    def commit(self) -> None:\n'
                '        if not self.is_active:\n'
                '            raise RuntimeError("Transaction is inactive")\n'
                '        self.conn.storage = dict(self.active_data)\n'
                '        self.is_active = False\n\n'
                '    def rollback(self) -> None:\n'
                '        self.active_data = dict(self.conn.storage)\n'
                '        self.savepoints.clear()\n'
                '        self.is_active = False\n'
            )
        }

        tests = {
            "test_db_savepoints.py": (
                'from connection import DBConnection\n'
                'from manager import TransactionManager\n\n\n'
                'def test_basic_commit_persists():\n'
                '    conn = DBConnection()\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    mgr.write_record("user_1", {"name": "Alice"})\n'
                '    tx.commit()\n'
                '    assert conn.storage["user_1"] == {"name": "Alice"}\n\n\n'
                'def test_savepoint_partial_rollback():\n'
                '    conn = DBConnection()\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    mgr.write_record("k1", "v1")\n'
                '    tx.create_savepoint("sp_1")\n'
                '    mgr.write_record("k2", "v2")\n'
                '    assert mgr.read_record("k2") == "v2"\n'
                '    # Rollback to sp_1: k2 should be discarded, k1 kept\n'
                '    res = tx.rollback_to_savepoint("sp_1")\n'
                '    assert res is True\n'
                '    assert mgr.read_record("k1") == "v1"\n'
                '    assert mgr.read_record("k2") is None\n'
                '    tx.commit()\n'
                '    assert "k1" in conn.storage\n'
                '    assert "k2" not in conn.storage\n\n\n'
                'def test_nested_savepoints_truncates_downstream_stack():\n'
                '    conn = DBConnection()\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    mgr.write_record("a", 1)\n'
                '    tx.create_savepoint("sp_a")\n'
                '    mgr.write_record("b", 2)\n'
                '    tx.create_savepoint("sp_b")\n'
                '    mgr.write_record("c", 3)\n'
                '    tx.create_savepoint("sp_c")\n'
                '    # Rolling back to sp_a must purge sp_b and sp_c from stack!\n'
                '    tx.rollback_to_savepoint("sp_a")\n'
                '    assert [sp.name for sp in tx.savepoints] == ["sp_a"]\n'
                '    # Attempting to rollback to sp_b must now fail (it was purged)\n'
                '    assert tx.rollback_to_savepoint("sp_b") is False\n\n\n'
                'def test_rollback_nonexistent_savepoint_returns_false():\n'
                '    conn = DBConnection()\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    assert tx.rollback_to_savepoint("sp_missing") is False\n\n\n'
                'def test_full_rollback_discards_all_uncommitted():\n'
                '    conn = DBConnection()\n'
                '    conn.storage["init"] = "val"\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    mgr.write_record("k_new", "temp")\n'
                '    tx.rollback()\n'
                '    assert "k_new" not in conn.storage\n'
                '    assert conn.storage["init"] == "val"\n\n\n'
                'def test_duplicate_savepoint_name_replaces_snapshot():\n'
                '    conn = DBConnection()\n'
                '    mgr = TransactionManager(conn)\n'
                '    tx = mgr.begin()\n'
                '    mgr.write_record("x", 10)\n'
                '    tx.create_savepoint("sp_x")\n'
                '    mgr.write_record("x", 20)\n'
                '    tx.create_savepoint("sp_x")  # Replaces previous sp_x with x=20\n'
                '    mgr.write_record("x", 30)\n'
                '    tx.rollback_to_savepoint("sp_x")\n'
                '    assert mgr.read_record("x") == 20\n\n\n'
                'def test_read_outside_transaction_reads_connection_storage():\n'
                '    conn = DBConnection()\n'
                '    conn.storage["persisted"] = 999\n'
                '    mgr = TransactionManager(conn)\n'
                '    assert mgr.read_record("persisted") == 999\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "database_nested_savepoint_stack_truncation_failure",
            "categories": ["I", "D", "E"],
            "description": "Database transaction session fails to truncate subsequent savepoints when rolling back to an ancestor savepoint, violating SQL-92 isolation.",
            "spec_notes": "TransactionSession.rollback_to_savepoint must purge all savepoints created after the target savepoint.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database",
            },
        }

    def _generate_connection_pool_leak(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "errors.py": (
                '"""Database query errors."""\n\n'
                'class QueryTimeoutException(Exception):\n'
                '    pass\n'
            ),
            "pool.py": (
                '"""Managed database connection pool."""\n\n'
                'from typing import List, Optional\n\n\n'
                'class ConnectionHandle:\n'
                '    def __init__(self, conn_id: int):\n'
                '        self.conn_id = conn_id\n'
                '        self.in_use: bool = False\n\n\n'
                'class ConnectionPool:\n'
                '    def __init__(self, size: int = 3):\n'
                '        self.size = size\n'
                '        self.handles = [ConnectionHandle(i) for i in range(size)]\n\n'
                '    def acquire(self) -> Optional[ConnectionHandle]:\n'
                '        for h in self.handles:\n'
                '            if not h.in_use:\n'
                '                h.in_use = True\n'
                '                return h\n'
                '        return None\n\n'
                '    def release(self, handle: ConnectionHandle) -> None:\n'
                '        handle.in_use = False\n\n'
                '    @property\n'
                '    def available_count(self) -> int:\n'
                '        return sum(1 for h in self.handles if not h.in_use)\n'
            ),
            "client.py": (
                '"""Database client executing queries with connection leases."""\n\n'
                'from typing import Any, Callable\n'
                'from errors import QueryTimeoutException\n'
                'from pool import ConnectionPool\n\n\n'
                'class DBClient:\n'
                '    def __init__(self, pool: ConnectionPool):\n'
                '        self.pool = pool\n\n'
                '    def run_query(self, query_fn: Callable[[], Any]) -> Any:\n'
                '        conn = self.pool.acquire()\n'
                '        if not conn:\n'
                '            raise RuntimeError("Connection pool exhausted")\n\n'
                '        # BUG: Missing try/finally block around query execution!\n'
                '        # When query_fn raises QueryTimeoutException or error, release() is bypassed!\n'
                '        res = query_fn()\n'
                '        self.pool.release(conn)\n'
                '        return res\n'
            ),
        }

        reference_fix = {
            "client.py": (
                '"""Database client executing queries with connection leases."""\n\n'
                'from typing import Any, Callable\n'
                'from errors import QueryTimeoutException\n'
                'from pool import ConnectionPool\n\n\n'
                'class DBClient:\n'
                '    def __init__(self, pool: ConnectionPool):\n'
                '        self.pool = pool\n\n'
                '    def run_query(self, query_fn: Callable[[], Any]) -> Any:\n'
                '        conn = self.pool.acquire()\n'
                '        if not conn:\n'
                '            raise RuntimeError("Connection pool exhausted")\n\n'
                '        try:\n'
                '            return query_fn()\n'
                '        finally:\n'
                '            self.pool.release(conn)\n'
            )
        }

        tests = {
            "test_pool_leak.py": (
                'import pytest\n'
                'from pool import ConnectionPool\n'
                'from client import DBClient\n'
                'from errors import QueryTimeoutException\n\n\n'
                'def test_successful_query_releases_connection():\n'
                '    pool = ConnectionPool(size=2)\n'
                '    client = DBClient(pool)\n'
                '    res = client.run_query(lambda: "ROWS_OK")\n'
                '    assert res == "ROWS_OK"\n'
                '    assert pool.available_count == 2\n\n\n'
                'def test_timeout_exception_releases_connection():\n'
                '    pool = ConnectionPool(size=2)\n'
                '    client = DBClient(pool)\n'
                '    def timeout_query():\n'
                '        raise QueryTimeoutException("Query exceeded 30s")\n\n'
                '    with pytest.raises(QueryTimeoutException):\n'
                '        client.run_query(timeout_query)\n\n'
                '    # Connection handle must be returned back to pool!\n'
                '    assert pool.available_count == 2\n\n\n'
                'def test_consecutive_failing_queries_do_not_exhaust_pool():\n'
                '    pool = ConnectionPool(size=2)\n'
                '    client = DBClient(pool)\n'
                '    for _ in range(5):\n'
                '        try:\n'
                '            client.run_query(lambda: 1 / 0)\n'
                '        except ZeroDivisionError:\n'
                '            pass\n'
                '    assert pool.available_count == 2\n'
                '    # Subsequent query succeeds\n'
                '    assert client.run_query(lambda: 42) == 42\n\n\n'
                'def test_pool_exhaustion_when_all_held():\n'
                '    pool = ConnectionPool(size=1)\n'
                '    client = DBClient(pool)\n'
                '    h = pool.acquire()\n'
                '    with pytest.raises(RuntimeError):\n'
                '        client.run_query(lambda: 1)\n'
                '    pool.release(h)\n'
                '    assert client.run_query(lambda: "NOW_OK") == "NOW_OK"\n\n\n'
                'def test_custom_exception_propagation():\n'
                '    pool = ConnectionPool(size=3)\n'
                '    client = DBClient(pool)\n'
                '    class CustomDBError(Exception): pass\n'
                '    with pytest.raises(CustomDBError):\n'
                '        client.run_query(lambda: (_ for _ in ()).throw(CustomDBError("db lock")))\n'
                '    assert pool.available_count == 3\n\n\n'
                'def test_nested_pool_state_initialization():\n'
                '    pool = ConnectionPool(size=5)\n'
                '    assert pool.available_count == 5\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "connection_pool_leak_unhandled_exception_bypass",
            "categories": ["I", "K"],
            "description": "Database client does not use try/finally around query execution, permanently leaking connection leases upon timeouts or errors.",
            "spec_notes": "DBClient.run_query must ensure pool.release(conn) is executed in a finally block.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database",
            },
        }

    def _generate_optimistic_locking(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "record.py": (
                '"""Entity record with version identifier."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class VersionedRecord:\n'
                '    record_id: str\n'
                '    data: Dict[str, Any]\n'
                '    version: int\n'
            ),
            "storage.py": (
                '"""Optimistic locking document store."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from record import VersionedRecord\n\n\n'
                'class OptimisticStore:\n'
                '    def __init__(self):\n'
                '        self._store: Dict[str, VersionedRecord] = {}\n\n'
                '    def insert(self, record_id: str, data: Dict[str, Any]) -> VersionedRecord:\n'
                '        rec = VersionedRecord(record_id, dict(data), version=1)\n'
                '        self._store[record_id] = rec\n'
                '        return rec\n\n'
                '    def get(self, record_id: str) -> Optional[VersionedRecord]:\n'
                '        rec = self._store.get(record_id)\n'
                '        if rec:\n'
                '            return VersionedRecord(rec.record_id, dict(rec.data), rec.version)\n'
                '        return None\n\n'
                '    def update(self, record_id: str, new_data: Dict[str, Any], expected_version: int) -> bool:\n'
                '        curr = self._store.get(record_id)\n'
                '        if not curr:\n'
                '            return False\n\n'
                '        # BUG: Overwrites curr.data immediately BEFORE checking version!\n'
                '        curr.data = dict(new_data)\n'
                '        if curr.version != expected_version:\n'
                '            return False\n\n'
                '        curr.version += 1\n'
                '        return True\n'
            ),
            "session.py": (
                '"""Data session worker updating shared records."""\n\n'
                'from typing import Any, Dict\n'
                'from storage import OptimisticStore\n\n\n'
                'class DocumentSession:\n'
                '    def __init__(self, store: OptimisticStore):\n'
                '        self.store = store\n\n'
                '    def patch_document(self, record_id: str, field_updates: Dict[str, Any]) -> bool:\n'
                '        rec = self.store.get(record_id)\n'
                '        if not rec:\n'
                '            return False\n'
                '        merged = dict(rec.data)\n'
                '        merged.update(field_updates)\n'
                '        return self.store.update(record_id, merged, rec.version)\n'
            ),
        }

        reference_fix = {
            "storage.py": (
                '"""Optimistic locking document store."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from record import VersionedRecord\n\n\n'
                'class OptimisticStore:\n'
                '    def __init__(self):\n'
                '        self._store: Dict[str, VersionedRecord] = {}\n\n'
                '    def insert(self, record_id: str, data: Dict[str, Any]) -> VersionedRecord:\n'
                '        rec = VersionedRecord(record_id, dict(data), version=1)\n'
                '        self._store[record_id] = rec\n'
                '        return rec\n\n'
                '    def get(self, record_id: str) -> Optional[VersionedRecord]:\n'
                '        rec = self._store.get(record_id)\n'
                '        if rec:\n'
                '            return VersionedRecord(rec.record_id, dict(rec.data), rec.version)\n'
                '        return None\n\n'
                '    def update(self, record_id: str, new_data: Dict[str, Any], expected_version: int) -> bool:\n'
                '        curr = self._store.get(record_id)\n'
                '        if not curr:\n'
                '            return False\n\n'
                '        if curr.version != expected_version:\n'
                '            return False\n\n'
                '        curr.data = dict(new_data)\n'
                '        curr.version += 1\n'
                '        return True\n'
            )
        }

        tests = {
            "test_optimistic_locking.py": (
                'from storage import OptimisticStore\n'
                'from session import DocumentSession\n\n\n'
                'def test_sequential_updates():\n'
                '    store = OptimisticStore()\n'
                '    store.insert("doc_1", {"title": "Draft", "views": 0})\n'
                '    s1 = DocumentSession(store)\n'
                '    res1 = s1.patch_document("doc_1", {"title": "Published"})\n'
                '    assert res1 is True\n'
                '    rec = store.get("doc_1")\n'
                '    assert rec.version == 2\n'
                '    assert rec.data["title"] == "Published"\n\n\n'
                'def test_concurrent_conflict_rejected_without_corrupting_data():\n'
                '    store = OptimisticStore()\n'
                '    store.insert("doc_2", {"balance": 100})\n'
                '    # Worker 1 and Worker 2 both read version 1\n'
                '    s1 = DocumentSession(store)\n'
                '    s2 = DocumentSession(store)\n'
                '    rec1 = store.get("doc_2")\n'
                '    rec2 = store.get("doc_2")\n'
                '    assert rec1.version == 1 and rec2.version == 1\n\n'
                '    # Worker 1 commits update to balance 150 (version becomes 2)\n'
                '    assert store.update("doc_2", {"balance": 150}, expected_version=1) is True\n'
                '    assert store.get("doc_2").version == 2\n\n'
                '    # Worker 2 tries to commit stale update to balance 200 using expected_version=1\n'
                '    assert store.update("doc_2", {"balance": 200}, expected_version=1) is False\n'
                '    # CRITICAL: Document data MUST retain Worker 1 update (150), NOT be corrupted with 200!\n'
                '    assert store.get("doc_2").data["balance"] == 150\n'
                '    assert store.get("doc_2").version == 2\n\n\n'
                'def test_update_missing_record():\n'
                '    store = OptimisticStore()\n'
                '    assert store.update("missing", {"k": 1}, 1) is False\n\n\n'
                'def test_version_increments_monotonically():\n'
                '    store = OptimisticStore()\n'
                '    store.insert("d", {"v": 0})\n'
                '    for i in range(1, 6):\n'
                '        assert store.update("d", {"v": i}, expected_version=i) is True\n'
                '    assert store.get("d").version == 6\n'
                '    assert store.get("d").data["v"] == 5\n\n\n'
                'def test_patch_document_missing():\n'
                '    store = OptimisticStore()\n'
                '    s = DocumentSession(store)\n'
                '    assert s.patch_document("ghost", {"a": 1}) is False\n\n\n'
                'def test_record_snapshot_immutability():\n'
                '    store = OptimisticStore()\n'
                '    store.insert("d1", {"meta": "original"})\n'
                '    snap = store.get("d1")\n'
                '    snap.data["meta"] = "tampered"\n'
                '    assert store.get("d1").data["meta"] == "original"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "optimistic_locking_dirty_write_before_version_check",
            "categories": ["I", "D"],
            "description": "Optimistic store mutates record data before validating expected version, corrupting shared data when conflicts occur.",
            "spec_notes": "OptimisticStore.update must verify curr.version == expected_version prior to applying data mutations.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database",
            },
        }

    def _generate_wal_recovery(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "wal_entry.py": (
                '"""Write-ahead log entry definition."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any\n\n\n'
                '@dataclass\n'
                'class WALEntry:\n'
                '    lsn: int\n'
                '    op_type: str  # "SET" or "DEL"\n'
                '    key: str\n'
                '    value: Any\n'
            ),
            "checkpoint.py": (
                '"""Database checkpoint metadata."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class CheckpointState:\n'
                '    checkpoint_lsn: int\n'
                '    data: Dict[str, Any]\n'
            ),
            "log_reader.py": (
                '"""Log sequential reader and filter."""\n\n'
                'from typing import List\n'
                'from wal_entry import WALEntry\n\n\n'
                'class WALLogReader:\n'
                '    def __init__(self, entries: List[WALEntry]):\n'
                '        self.entries = list(entries)\n\n'
                '    def get_entries_since(self, after_lsn: int) -> List[WALEntry]:\n'
                '        # BUG: Uses >= instead of > when filtering after_lsn, re-applying the checkpoint entry itself!\n'
                '        return [e for e in self.entries if e.lsn >= after_lsn]\n'
            ),
            "state_engine.py": (
                '"""Database recovery and replay state engine."""\n\n'
                'from typing import Any, Dict\n'
                'from checkpoint import CheckpointState\n'
                'from log_reader import WALLogReader\n\n\n'
                'class RecoveryEngine:\n'
                '    def __init__(self, reader: WALLogReader):\n'
                '        self.reader = reader\n\n'
                '    def recover(self, cp: CheckpointState) -> Dict[str, Any]:\n'
                '        state = dict(cp.data)\n'
                '        # Replay log entries committed strictly AFTER checkpoint_lsn\n'
                '        entries = self.reader.get_entries_since(cp.checkpoint_lsn)\n'
                '        for e in entries:\n'
                '            if e.op_type == "SET":\n'
                '                state[e.key] = e.value\n'
                '            elif e.op_type == "DEL":\n'
                '                state.pop(e.key, None)\n'
                '        return state\n'
            ),
        }

        reference_fix = {
            "log_reader.py": (
                '"""Log sequential reader and filter."""\n\n'
                'from typing import List\n'
                'from wal_entry import WALEntry\n\n\n'
                'class WALLogReader:\n'
                '    def __init__(self, entries: List[WALEntry]):\n'
                '        self.entries = list(entries)\n\n'
                '    def get_entries_since(self, after_lsn: int) -> List[WALEntry]:\n'
                '        return [e for e in self.entries if e.lsn > after_lsn]\n'
            )
        }

        tests = {
            "test_wal_recovery.py": (
                'from wal_entry import WALEntry\n'
                'from checkpoint import CheckpointState\n'
                'from log_reader import WALLogReader\n'
                'from state_engine import RecoveryEngine\n\n\n'
                'def test_basic_replay_after_checkpoint():\n'
                '    # Checkpoint at LSN 10: {"k1": "v1_old"}\n'
                '    cp = CheckpointState(10, {"k1": "v1_old"})\n'
                '    log = [\n'
                '        WALEntry(10, "SET", "k1", "v1_old"),\n'
                '        WALEntry(11, "SET", "k1", "v1_new"),\n'
                '        WALEntry(12, "SET", "k2", "v2"),\n'
                '    ]\n'
                '    reader = WALLogReader(log)\n'
                '    engine = RecoveryEngine(reader)\n'
                '    recovered = engine.recover(cp)\n'
                '    assert recovered == {"k1": "v1_new", "k2": "v2"}\n\n\n'
                'def test_checkpoint_lsn_entry_not_replayed_over_del():\n'
                '    # LSN 5 was a SET. Checkpoint captured at LSN 5 has {"k": "val"}.\n'
                '    # Later, at LSN 6, DEL is executed.\n'
                '    # If LSN 5 is replayed on recovery, but a sequence of edits occurred, re-evaluating must not corrupt delete!\n'
                '    cp = CheckpointState(5, {"counter": 10})\n'
                '    log = [\n'
                '        WALEntry(5, "SET", "counter", 10),\n'
                '        WALEntry(6, "DEL", "counter", None),\n'
                '    ]\n'
                '    reader = WALLogReader(log)\n'
                '    engine = RecoveryEngine(reader)\n'
                '    res = engine.recover(cp)\n'
                '    assert "counter" not in res\n\n\n'
                'def test_no_entries_after_checkpoint():\n'
                '    cp = CheckpointState(20, {"active": True, "num": 100})\n'
                '    log = [WALEntry(19, "SET", "active", False), WALEntry(20, "SET", "num", 100)]\n'
                '    reader = WALLogReader(log)\n'
                '    engine = RecoveryEngine(reader)\n'
                '    assert engine.recover(cp) == {"active": True, "num": 100}\n\n\n'
                'def test_multiple_mutations_and_deletions():\n'
                '    cp = CheckpointState(100, {"a": 1, "b": 2})\n'
                '    log = [\n'
                '        WALEntry(101, "SET", "c", 3),\n'
                '        WALEntry(102, "DEL", "a", None),\n'
                '        WALEntry(103, "SET", "b", 20),\n'
                '        WALEntry(104, "SET", "d", 4),\n'
                '    ]\n'
                '    reader = WALLogReader(log)\n'
                '    engine = RecoveryEngine(reader)\n'
                '    res = engine.recover(cp)\n'
                '    assert res == {"b": 20, "c": 3, "d": 4}\n\n\n'
                'def test_empty_log_recovery():\n'
                '    cp = CheckpointState(0, {"init": "data"})\n'
                '    reader = WALLogReader([])\n'
                '    engine = RecoveryEngine(reader)\n'
                '    assert engine.recover(cp) == {"init": "data"}\n\n\n'
                'def test_log_reader_boundary_condition():\n'
                '    entries = [WALEntry(1, "SET", "a", 1), WALEntry(2, "SET", "b", 2)]\n'
                '    r = WALLogReader(entries)\n'
                '    # Since LSN 1 must strictly return LSN 2\n'
                '    assert [e.lsn for e in r.get_entries_since(1)] == [2]\n'
                '    assert [e.lsn for e in r.get_entries_since(2)] == []\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "wal_log_replay_checkpoint_boundary_inclusive_error",
            "categories": ["I", "D", "E"],
            "description": "WAL log reader includes the checkpoint LSN itself during replay (>= instead of >), re-applying pre-checkpoint state mutations.",
            "spec_notes": "WALLogReader.get_entries_since must strictly check e.lsn > after_lsn.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database",
            },
        }

    def _generate_migration_rollback(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "migration.py": (
                '"""Database migration step definition."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Callable, List, Optional\n\n\n'
                '@dataclass\n'
                'class MigrationStep:\n'
                '    name: str\n'
                '    dependencies: List[str] = field(default_factory=list)\n'
                '    applied: bool = False\n'
            ),
            "dependency_graph.py": (
                '"""Migration DAG dependency resolver and topological planner."""\n\n'
                'from typing import Dict, List, Set\n'
                'from migration import MigrationStep\n\n\n'
                'class MigrationDAG:\n'
                '    def __init__(self, steps: Dict[str, MigrationStep]):\n'
                '        self.steps = steps\n\n'
                '    def get_forward_order(self) -> List[str]:\n'
                '        # Standard Kahn topological sort\n'
                '        in_degree = {k: 0 for k in self.steps}\n'
                '        dependents: Dict[str, List[str]] = {k: [] for k in self.steps}\n'
                '        for name, step in self.steps.items():\n'
                '            for dep in step.dependencies:\n'
                '                if dep in in_degree:\n'
                '                    in_degree[name] += 1\n'
                '                    dependents[dep].append(name)\n'
                '        queue = [k for k, d in in_degree.items() if d == 0]\n'
                '        order = []\n'
                '        while queue:\n'
                '            curr = queue.pop(0)\n'
                '            order.append(curr)\n'
                '            for dep in dependents[curr]:\n'
                '                in_degree[dep] -= 1\n'
                '                if in_degree[dep] == 0:\n'
                '                    queue.append(dep)\n'
                '        return order\n\n'
                '    def get_rollback_order_for(self, target_migration: str) -> List[str]:\n'
                '        # Must rollback target_migration and ALL migrations that depend on it\n'
                '        # BUG: Only returns target_migration itself without recursively finding\n'
                '        # all downstream dependent migrations in reverse dependency order!\n'
                '        if target_migration not in self.steps:\n'
                '            return []\n'
                '        return [target_migration]\n'
            ),
            "executor.py": (
                '"""Migration SQL executor and state tracker."""\n\n'
                'from typing import Any, Dict, List\n'
                'from migration import MigrationStep\n\n\n'
                'class MigrationExecutor:\n'
                '    def __init__(self, steps: Dict[str, MigrationStep]):\n'
                '        self.steps = steps\n'
                '        self.applied_history: List[str] = []\n\n'
                '    def apply_migration(self, name: str) -> None:\n'
                '        step = self.steps[name]\n'
                '        for dep in step.dependencies:\n'
                '            if not self.steps[dep].applied:\n'
                '                raise RuntimeError(f"Cannot apply {name}: dependency {dep} not applied")\n'
                '        step.applied = True\n'
                '        self.applied_history.append(name)\n\n'
                '    def rollback_migration(self, name: str) -> None:\n'
                '        step = self.steps[name]\n'
                '        # Check if any currently applied migration depends on this one\n'
                '        for other_name, other in self.steps.items():\n'
                '            if other.applied and name in other.dependencies:\n'
                '                raise RuntimeError(f"Cannot rollback {name}: active migration {other_name} depends on it")\n'
                '        step.applied = False\n'
                '        if name in self.applied_history:\n'
                '            self.applied_history.remove(name)\n'
            ),
            "engine.py": (
                '"""High level migration engine orchestrating apply and rollback flows."""\n\n'
                'from typing import Dict, List\n'
                'from dependency_graph import MigrationDAG\n'
                'from executor import MigrationExecutor\n'
                'from migration import MigrationStep\n\n\n'
                'class MigrationEngine:\n'
                '    def __init__(self, steps: Dict[str, MigrationStep]):\n'
                '        self.steps = steps\n'
                '        self.dag = MigrationDAG(steps)\n'
                '        self.executor = MigrationExecutor(steps)\n\n'
                '    def migrate_all(self) -> None:\n'
                '        order = self.dag.get_forward_order()\n'
                '        for m in order:\n'
                '            if not self.steps[m].applied:\n'
                '                self.executor.apply_migration(m)\n\n'
                '    def rollback_target(self, target: str) -> None:\n'
                '        # Plan rollback sequence\n'
                '        rollback_steps = self.dag.get_rollback_order_for(target)\n'
                '        for m in rollback_steps:\n'
                '            if self.steps[m].applied:\n'
                '                self.executor.rollback_migration(m)\n'
            ),
        }

        reference_fix = {
            "dependency_graph.py": (
                '"""Migration DAG dependency resolver and topological planner."""\n\n'
                'from typing import Dict, List, Set\n'
                'from migration import MigrationStep\n\n\n'
                'class MigrationDAG:\n'
                '    def __init__(self, steps: Dict[str, MigrationStep]):\n'
                '        self.steps = steps\n\n'
                '    def get_forward_order(self) -> List[str]:\n'
                '        in_degree = {k: 0 for k in self.steps}\n'
                '        dependents: Dict[str, List[str]] = {k: [] for k in self.steps}\n'
                '        for name, step in self.steps.items():\n'
                '            for dep in step.dependencies:\n'
                '                if dep in in_degree:\n'
                '                    in_degree[name] += 1\n'
                '                    dependents[dep].append(name)\n'
                '        queue = [k for k, d in in_degree.items() if d == 0]\n'
                '        order = []\n'
                '        while queue:\n'
                '            curr = queue.pop(0)\n'
                '            order.append(curr)\n'
                '            for dep in dependents[curr]:\n'
                '                in_degree[dep] -= 1\n'
                '                if in_degree[dep] == 0:\n'
                '                    queue.append(dep)\n'
                '        return order\n\n'
                '    def get_rollback_order_for(self, target_migration: str) -> List[str]:\n'
                '        if target_migration not in self.steps:\n'
                '            return []\n'
                '        # Find all downstream dependents recursively\n'
                '        dependents_map: Dict[str, List[str]] = {k: [] for k in self.steps}\n'
                '        for name, step in self.steps.items():\n'
                '            for dep in step.dependencies:\n'
                '                if dep in dependents_map:\n'
                '                    dependents_map[dep].append(name)\n\n'
                '        affected: Set[str] = set()\n'
                '        def collect(m: str):\n'
                '            affected.add(m)\n'
                '            for child in dependents_map.get(m, []):\n'
                '                if child not in affected:\n'
                '                    collect(child)\n'
                '        collect(target_migration)\n\n'
                '        # Topological sort restricted to affected set, then reversed\n'
                '        forward_order = self.get_forward_order()\n'
                '        filtered_forward = [m for m in forward_order if m in affected]\n'
                '        return list(reversed(filtered_forward))\n'
            )
        }

        tests = {
            "test_migration_rollback.py": (
                'from migration import MigrationStep\n'
                'from dependency_graph import MigrationDAG\n'
                'from engine import MigrationEngine\n\n\n'
                'def test_forward_migration_order():\n'
                '    steps = {\n'
                '        "001_users": MigrationStep("001_users"),\n'
                '        "002_posts": MigrationStep("002_posts", ["001_users"]),\n'
                '        "003_comments": MigrationStep("003_comments", ["002_posts"]),\n'
                '    }\n'
                '    engine = MigrationEngine(steps)\n'
                '    engine.migrate_all()\n'
                '    assert all(s.applied for s in steps.values())\n'
                '    assert engine.executor.applied_history == ["001_users", "002_posts", "003_comments"]\n\n\n'
                'def test_cascading_rollback_order_reverses_dependencies():\n'
                '    # Tree: 001_users -> 002_posts -> 003_comments\n'
                '    #                -> 004_profiles\n'
                '    steps = {\n'
                '        "001_users": MigrationStep("001_users"),\n'
                '        "002_posts": MigrationStep("002_posts", ["001_users"]),\n'
                '        "003_comments": MigrationStep("003_comments", ["002_posts"]),\n'
                '        "004_profiles": MigrationStep("004_profiles", ["001_users"]),\n'
                '    }\n'
                '    engine = MigrationEngine(steps)\n'
                '    engine.migrate_all()\n'
                '    # Rolling back 002_posts must rollback 003_comments first, then 002_posts\n'
                '    engine.rollback_target("002_posts")\n'
                '    assert steps["003_comments"].applied is False\n'
                '    assert steps["002_posts"].applied is False\n'
                '    # 001_users and 004_profiles must remain active\n'
                '    assert steps["001_users"].applied is True\n'
                '    assert steps["004_profiles"].applied is True\n\n\n'
                'def test_root_migration_rollback_rolls_back_entire_tree():\n'
                '    steps = {\n'
                '        "001_users": MigrationStep("001_users"),\n'
                '        "002_posts": MigrationStep("002_posts", ["001_users"]),\n'
                '        "003_comments": MigrationStep("003_comments", ["002_posts"]),\n'
                '    }\n'
                '    engine = MigrationEngine(steps)\n'
                '    engine.migrate_all()\n'
                '    engine.rollback_target("001_users")\n'
                '    assert not any(s.applied for s in steps.values())\n\n\n'
                'def test_leaf_migration_rollback():\n'
                '    steps = {\n'
                '        "001_users": MigrationStep("001_users"),\n'
                '        "002_posts": MigrationStep("002_posts", ["001_users"]),\n'
                '    }\n'
                '    engine = MigrationEngine(steps)\n'
                '    engine.migrate_all()\n'
                '    engine.rollback_target("002_posts")\n'
                '    assert steps["001_users"].applied is True\n'
                '    assert steps["002_posts"].applied is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "database_migration_rollback_dependency_cascade_omission",
            "categories": ["I", "E", "D"],
            "description": "Migration DAG planner fails to cascade rollbacks to downstream dependents, causing foreign key conflicts when rolling back parent tables.",
            "spec_notes": "MigrationDAG.get_rollback_order_for must recursively find all dependent migrations and sort them in reverse topological order.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database-migrations",
            },
        }

    def _generate_lsm_compaction(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "sstable.py": (
                '"""Immutable Sorted String Table (SSTable) file representation."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict, List, Optional, Tuple\n\n\n'
                '@dataclass\n'
                'class SSTable:\n'
                '    table_id: str\n'
                '    level: int\n'
                '    # Stored as sorted list of (key, value) pairs; value=None is a tombstone\n'
                '    entries: List[Tuple[str, Optional[Any]]]\n\n'
                '    def get(self, key: str) -> Tuple[bool, Optional[Any]]:\n'
                '        for k, v in self.entries:\n'
                '            if k == key:\n'
                '                return True, v\n'
                '        return False, None\n'
            ),
            "compactor.py": (
                '"""LSM-tree multi-level SSTable compaction and merge sorter."""\n\n'
                'from typing import Any, Dict, List, Optional, Tuple\n'
                'from sstable import SSTable\n\n\n'
                'class CompactionEngine:\n'
                '    def __init__(self, max_level: int = 2):\n'
                '        self.max_level = max_level\n\n'
                '    def merge_sstables(self, target_level: int, tables: List[SSTable], new_table_id: str) -> SSTable:\n'
                '        # Multi-way merge sort: later tables in list represent newer timestamps\n'
                '        merged_map: Dict[str, Optional[Any]] = {}\n'
                '        for table in tables:\n'
                '            for k, v in table.entries:\n'
                '                merged_map[k] = v\n\n'
                '        # Sort by key\n'
                '        sorted_pairs = sorted(merged_map.items(), key=lambda p: p[0])\n\n'
                '        # BUG: Retains tombstones (value=None) even when target_level == self.max_level (bottom tier)!\n'
                '        # At max_level, no older tables exist below, so tombstones should be purged!\n'
                '        return SSTable(table_id=new_table_id, level=target_level, entries=sorted_pairs)\n'
            ),
            "lsm_engine.py": (
                '"""High level LSM storage engine."""\n\n'
                'from typing import Any, Dict, List, Optional\n'
                'from compactor import CompactionEngine\n'
                'from sstable import SSTable\n\n\n'
                'class LSMStorageEngine:\n'
                '    def __init__(self, max_level: int = 2):\n'
                '        self.compactor = CompactionEngine(max_level=max_level)\n'
                '        self.levels: Dict[int, List[SSTable]] = {lvl: [] for lvl in range(max_level + 1)}\n\n'
                '    def compact_level(self, level: int, out_id: str) -> SSTable:\n'
                '        tables = self.levels.get(level, [])\n'
                '        target_lvl = min(self.compactor.max_level, level + 1)\n'
                '        merged = self.compactor.merge_sstables(target_lvl, tables, out_id)\n'
                '        self.levels[level] = []\n'
                '        self.levels[target_lvl].append(merged)\n'
                '        return merged\n'
            ),
        }

        reference_fix = {
            "compactor.py": (
                '"""LSM-tree multi-level SSTable compaction and merge sorter."""\n\n'
                'from typing import Any, Dict, List, Optional, Tuple\n'
                'from sstable import SSTable\n\n\n'
                'class CompactionEngine:\n'
                '    def __init__(self, max_level: int = 2):\n'
                '        self.max_level = max_level\n\n'
                '    def merge_sstables(self, target_level: int, tables: List[SSTable], new_table_id: str) -> SSTable:\n'
                '        merged_map: Dict[str, Optional[Any]] = {}\n'
                '        for table in tables:\n'
                '            for k, v in table.entries:\n'
                '                merged_map[k] = v\n\n'
                '        sorted_pairs = sorted(merged_map.items(), key=lambda p: p[0])\n\n'
                '        # Purge tombstones (value is None) when compacting into bottom level (max_level)\n'
                '        if target_level >= self.max_level:\n'
                '            sorted_pairs = [(k, v) for k, v in sorted_pairs if v is not None]\n\n'
                '        return SSTable(table_id=new_table_id, level=target_level, entries=sorted_pairs)\n'
            )
        }

        tests = {
            "test_lsm_compaction.py": (
                'from sstable import SSTable\n'
                'from compactor import CompactionEngine\n'
                'from lsm_engine import LSMStorageEngine\n\n\n'
                'def test_basic_sst_merge_overwrites():\n'
                '    engine = CompactionEngine(max_level=2)\n'
                '    t1 = SSTable("t1", 0, [("a", 1), ("b", 2)])\n'
                '    t2 = SSTable("t2", 0, [("b", 20), ("c", 3)])\n'
                '    merged = engine.merge_sstables(1, [t1, t2], "m1")\n'
                '    assert merged.entries == [("a", 1), ("b", 20), ("c", 3)]\n\n\n'
                'def test_bottom_level_compaction_purges_tombstones():\n'
                '    engine = CompactionEngine(max_level=2)\n'
                '    t1 = SSTable("t1", 1, [("user_1", "Alice"), ("user_2", "Bob")])\n'
                '    t2 = SSTable("t2", 1, [("user_1", None)])  # Deletion tombstone for user_1\n'
                '    # Compacting into max_level=2 must PURGE user_1 tombstone!\n'
                '    merged = engine.merge_sstables(2, [t1, t2], "m_final")\n'
                '    assert merged.entries == [("user_2", "Bob")]\n'
                '    assert not any(k == "user_1" for k, v in merged.entries)\n\n\n'
                'def test_intermediate_level_preserves_tombstones():\n'
                '    engine = CompactionEngine(max_level=3)\n'
                '    t1 = SSTable("t1", 0, [("x", "val")])\n'
                '    t2 = SSTable("t2", 0, [("x", None)])\n'
                '    # Compacting into intermediate level 1 must preserve tombstone for lower levels\n'
                '    merged = engine.merge_sstables(1, [t1, t2], "m_inter")\n'
                '    assert merged.entries == [("x", None)]\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "lsm_tree_bottom_tier_tombstone_purge_omission",
            "categories": ["I", "K"],
            "description": "LSM compactor retains deletion tombstones during bottom-tier (max_level) merges, leaking storage space indefinitely.",
            "spec_notes": "CompactionEngine.merge_sstables must filter out (k, None) tombstones when target_level >= max_level.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "storage-engines",
            },
        }


