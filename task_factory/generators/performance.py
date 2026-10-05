"""Category K: Performance & Resource Leaks Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class PerformanceTaskGenerator(BaseGenerator):
    """Generates realistic performance bottlenecks and memory leak debugging tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v17_memory_leak_bounded_cache")
        sub_type = spec.get("sub_type", "cache_leak")

        if sub_type == "quadratic_pipeline" or "quadratic" in task_id:
            return self._generate_quadratic_pipeline(task_id, spec, seed)
        elif sub_type == "circular_buffer" or "buffer" in task_id:
            return self._generate_circular_buffer(task_id, spec, seed)
        return self._generate_bounded_cache_leak(task_id, spec, seed)

    def _generate_bounded_cache_leak(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "metrics.py": (
                '"""Resource telemetry metrics tracker."""\n\n'
                'class MemoryTracker:\n'
                '    def __init__(self):\n'
                '        self.active_handles: set[str] = set()\n\n'
                '    def register(self, handle_id: str) -> None:\n'
                '        self.active_handles.add(handle_id)\n\n'
                '    def unregister(self, handle_id: str) -> None:\n'
                '        self.active_handles.discard(handle_id)\n\n'
                '    @property\n'
                '    def live_count(self) -> int:\n'
                '        return len(self.active_handles)\n'
            ),
            "cache.py": (
                '"""Bounded cache store with entry expiration and cleanup hooks."""\n\n'
                'from collections import OrderedDict\n'
                'from typing import Any, Callable, Dict, Optional\n\n\n'
                'class BoundedCache:\n'
                '    def __init__(self, capacity: int = 5):\n'
                '        self.capacity = capacity\n'
                '        self._store: OrderedDict[str, Any] = OrderedDict()\n'
                '        self._listeners: list[Callable[[str, Any], None]] = []\n\n'
                '    def add_eviction_listener(self, fn: Callable[[str, Any], None]) -> None:\n'
                '        self._listeners.append(fn)\n\n'
                '    def put(self, key: str, value: Any) -> Optional[tuple[str, Any]]:\n'
                '        evicted = None\n'
                '        if key in self._store:\n'
                '            self._store.move_to_end(key)\n'
                '            self._store[key] = value\n'
                '            return None\n\n'
                '        if len(self._store) >= self.capacity:\n'
                '            # Evict oldest entry\n'
                '            old_key, old_val = self._store.popitem(last=False)\n'
                '            evicted = (old_key, old_val)\n'
                '            # BUG: Eviction listener is called, but exceptions or errors are unhandled\n'
                '            # and listener references are never notified during explicit remove/clear!\n'
                '            for listener in self._listeners:\n'
                '                listener(old_key, old_val)\n\n'
                '        self._store[key] = value\n'
                '        return evicted\n\n'
                '    def remove(self, key: str) -> Optional[Any]:\n'
                '        # BUG: remove() pops the item from _store but fails to invoke eviction listeners,\n'
                '        # leaving external resources/handles dangling and leaked in tracker!\n'
                '        return self._store.pop(key, None)\n\n'
                '    def clear(self) -> None:\n'
                '        # BUG: clear() simply resets dictionary without firing teardown hooks on existing items\n'
                '        self._store.clear()\n'
            ),
            "session_pool.py": (
                '"""Session manager that acquires and releases tracked resources."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from cache import BoundedCache\n'
                'from metrics import MemoryTracker\n\n\n'
                'class SessionPool:\n'
                '    def __init__(self, capacity: int = 3):\n'
                '        self.tracker = MemoryTracker()\n'
                '        self.cache = BoundedCache(capacity=capacity)\n'
                '        self.cache.add_eviction_listener(self._on_evict)\n\n'
                '    def _on_evict(self, key: str, value: Any) -> None:\n'
                '        self.tracker.unregister(key)\n\n'
                '    def acquire_session(self, session_id: str, session_data: Dict[str, Any]) -> None:\n'
                '        self.tracker.register(session_id)\n'
                '        self.cache.put(session_id, session_data)\n\n'
                '    def terminate_session(self, session_id: str) -> bool:\n'
                '        val = self.cache.remove(session_id)\n'
                '        return val is not None\n\n'
                '    def close_all(self) -> None:\n'
                '        self.cache.clear()\n'
            ),
        }

        reference_fix = {
            "cache.py": (
                '"""Bounded cache store with entry expiration and cleanup hooks."""\n\n'
                'from collections import OrderedDict\n'
                'from typing import Any, Callable, Dict, Optional\n\n\n'
                'class BoundedCache:\n'
                '    def __init__(self, capacity: int = 5):\n'
                '        self.capacity = capacity\n'
                '        self._store: OrderedDict[str, Any] = OrderedDict()\n'
                '        self._listeners: list[Callable[[str, Any], None]] = []\n\n'
                '    def add_eviction_listener(self, fn: Callable[[str, Any], None]) -> None:\n'
                '        self._listeners.append(fn)\n\n'
                '    def _notify_listeners(self, key: str, value: Any) -> None:\n'
                '        for listener in self._listeners:\n'
                '            listener(key, value)\n\n'
                '    def put(self, key: str, value: Any) -> Optional[tuple[str, Any]]:\n'
                '        evicted = None\n'
                '        if key in self._store:\n'
                '            self._store.move_to_end(key)\n'
                '            self._store[key] = value\n'
                '            return None\n\n'
                '        if len(self._store) >= self.capacity:\n'
                '            old_key, old_val = self._store.popitem(last=False)\n'
                '            evicted = (old_key, old_val)\n'
                '            self._notify_listeners(old_key, old_val)\n\n'
                '        self._store[key] = value\n'
                '        return evicted\n\n'
                '    def remove(self, key: str) -> Optional[Any]:\n'
                '        if key in self._store:\n'
                '            val = self._store.pop(key)\n'
                '            self._notify_listeners(key, val)\n'
                '            return val\n'
                '        return None\n\n'
                '    def clear(self) -> None:\n'
                '        items = list(self._store.items())\n'
                '        self._store.clear()\n'
                '        for k, v in items:\n'
                '            self._notify_listeners(k, v)\n'
            )
        }

        tests = {
            "test_memory_leak.py": (
                'from session_pool import SessionPool\n\n\n'
                'def test_automatic_eviction_unregisters_handle():\n'
                '    pool = SessionPool(capacity=2)\n'
                '    pool.acquire_session("s1", {"user": "alice"})\n'
                '    pool.acquire_session("s2", {"user": "bob"})\n'
                '    assert pool.tracker.live_count == 2\n\n'
                '    # Acquiring 3rd session triggers eviction of s1\n'
                '    pool.acquire_session("s3", {"user": "charlie"})\n'
                '    assert pool.tracker.live_count == 2\n'
                '    assert "s1" not in pool.tracker.active_handles\n'
                '    assert "s2" in pool.tracker.active_handles\n'
                '    assert "s3" in pool.tracker.active_handles\n\n\n'
                'def test_explicit_terminate_cleans_up_handle():\n'
                '    pool = SessionPool(capacity=3)\n'
                '    pool.acquire_session("sess_x", {"token": "abc"})\n'
                '    pool.acquire_session("sess_y", {"token": "def"})\n'
                '    assert pool.tracker.live_count == 2\n\n'
                '    # Explicit termination must release memory handle\n'
                '    res = pool.terminate_session("sess_x")\n'
                '    assert res is True\n'
                '    assert pool.tracker.live_count == 1\n'
                '    assert "sess_x" not in pool.tracker.active_handles\n\n\n'
                'def test_close_all_releases_all_dangling_sessions():\n'
                '    pool = SessionPool(capacity=5)\n'
                '    for i in range(4):\n'
                '        pool.acquire_session(f"s_{i}", {"idx": i})\n'
                '    assert pool.tracker.live_count == 4\n\n'
                '    pool.close_all()\n'
                '    assert pool.tracker.live_count == 0\n'
                '    assert len(pool.tracker.active_handles) == 0\n\n\n'
                'def test_access_existing_key_promotes_without_leaking():\n'
                '    pool = SessionPool(capacity=2)\n'
                '    pool.acquire_session("k1", {"count": 1})\n'
                '    pool.acquire_session("k2", {"count": 1})\n'
                '    pool.acquire_session("k1", {"count": 2})  # Update k1\n'
                '    assert pool.tracker.live_count == 2\n\n'
                '    pool.acquire_session("k3", {"count": 1})  # Evicts oldest (k2, since k1 was accessed)\n'
                '    assert "k2" not in pool.tracker.active_handles\n'
                '    assert "k1" in pool.tracker.active_handles\n'
                '    assert "k3" in pool.tracker.active_handles\n\n\n'
                'def test_terminate_nonexistent_returns_false_safely():\n'
                '    pool = SessionPool(capacity=2)\n'
                '    assert pool.terminate_session("ghost") is False\n'
                '    assert pool.tracker.live_count == 0\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "resource_leak_eviction_cleanup_bypass",
            "categories": ["K", "D", "E"],
            "description": "Bounded cache store fails to invoke eviction listeners on explicit removal and clear, leaking session handles in memory.",
            "spec_notes": "BoundedCache must guarantee all eviction listeners fire whenever items leave the cache.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "performance",
            },
        }

    def _generate_quadratic_pipeline(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "event_model.py": (
                '"""Event payload model definition."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class IngestionEvent:\n'
                '    event_id: str\n'
                '    timestamp: int\n'
                '    topic: str\n'
                '    payload: Dict[str, Any]\n'
            ),
            "sink.py": (
                '"""Destination storage sink for processed events."""\n\n'
                'from typing import List\n'
                'from event_model import IngestionEvent\n\n\n'
                'class EventSink:\n'
                '    def __init__(self):\n'
                '        self.flushed: List[IngestionEvent] = []\n\n'
                '    def write_batch(self, events: List[IngestionEvent]) -> int:\n'
                '        self.flushed.extend(events)\n'
                '        return len(events)\n'
            ),
            "dedup_stream.py": (
                '"""Streaming deduplication processor with window tracking."""\n\n'
                'from typing import List\n'
                'from event_model import IngestionEvent\n\n\n'
                'class DeduplicationStream:\n'
                '    def __init__(self, window_size: int = 1000):\n'
                '        self.window_size = window_size\n'
                '        # BUG: Uses a plain list for seen IDs without recency promotion or O(1) set index.\n'
                '        # When an existing event is re-encountered, it is not moved to the back of the window,\n'
                '        # causing premature eviction of active events.\n'
                '        self._seen_ids: list[str] = []\n\n'
                '    def filter_duplicates(self, events: List[IngestionEvent]) -> List[IngestionEvent]:\n'
                '        unique_events: List[IngestionEvent] = []\n'
                '        for ev in events:\n'
                '            if ev.event_id not in self._seen_ids:\n'
                '                self._seen_ids.append(ev.event_id)\n'
                '                unique_events.append(ev)\n'
                '                if len(self._seen_ids) > self.window_size:\n'
                '                    self._seen_ids.pop(0)\n'
                '        return unique_events\n'
            ),
            "ingestion.py": (
                '"""Batch ingestion pipeline orchestrator."""\n\n'
                'from typing import List\n'
                'from dedup_stream import DeduplicationStream\n'
                'from event_model import IngestionEvent\n'
                'from sink import EventSink\n\n\n'
                'class IngestionPipeline:\n'
                '    def __init__(self, sink: EventSink, window_size: int = 500):\n'
                '        self.sink = sink\n'
                '        self.dedup = DeduplicationStream(window_size=window_size)\n\n'
                '    def process_stream(self, raw_events: List[IngestionEvent]) -> int:\n'
                '        filtered = self.dedup.filter_duplicates(raw_events)\n'
                '        # Sort by timestamp to maintain deterministic ingestion ordering\n'
                '        sorted_events = sorted(filtered, key=lambda e: (e.timestamp, e.event_id))\n'
                '        return self.sink.write_batch(sorted_events)\n'
            ),
        }

        reference_fix = {
            "dedup_stream.py": (
                '"""Streaming deduplication processor with window tracking."""\n\n'
                'from collections import OrderedDict\n'
                'from typing import List\n'
                'from event_model import IngestionEvent\n\n\n'
                'class DeduplicationStream:\n'
                '    def __init__(self, window_size: int = 1000):\n'
                '        self.window_size = window_size\n'
                '        self._seen: OrderedDict[str, None] = OrderedDict()\n\n'
                '    def filter_duplicates(self, events: List[IngestionEvent]) -> List[IngestionEvent]:\n'
                '        unique_events: List[IngestionEvent] = []\n'
                '        for ev in events:\n'
                '            if ev.event_id in self._seen:\n'
                '                self._seen.move_to_end(ev.event_id)\n'
                '            else:\n'
                '                self._seen[ev.event_id] = None\n'
                '                unique_events.append(ev)\n'
                '                if len(self._seen) > self.window_size:\n'
                '                    self._seen.popitem(last=False)\n'
                '        return unique_events\n'
            )
        }

        tests = {
            "test_dedup_pipeline.py": (
                'from event_model import IngestionEvent\n'
                'from sink import EventSink\n'
                'from ingestion import IngestionPipeline\n\n\n'
                'def test_basic_deduplication():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink, window_size=10)\n'
                '    events = [\n'
                '        IngestionEvent("e1", 100, "metrics", {"v": 1}),\n'
                '        IngestionEvent("e2", 101, "metrics", {"v": 2}),\n'
                '        IngestionEvent("e1", 102, "metrics", {"v": 3}),\n'
                '    ]\n'
                '    written = pipeline.process_stream(events)\n'
                '    assert written == 2\n'
                '    assert [e.event_id for e in sink.flushed] == ["e1", "e2"]\n\n\n'
                'def test_reseen_event_refreshes_window_recency():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink, window_size=2)\n'
                '    # e1, e2 entered -> e1 re-seen (refreshes recency) -> e3 enters (evicts oldest e2, keeping e1)\n'
                '    pipeline.process_stream([\n'
                '        IngestionEvent("e1", 1, "t", {}),\n'
                '        IngestionEvent("e2", 2, "t", {}),\n'
                '        IngestionEvent("e1", 3, "t", {}),\n'
                '        IngestionEvent("e3", 4, "t", {}),\n'
                '    ])\n'
                '    # Presenting e1 again: e1 is still in window -> must be filtered out\n'
                '    written_e1 = pipeline.process_stream([IngestionEvent("e1", 5, "t", {})])\n'
                '    assert written_e1 == 0\n'
                '    # Presenting e2: e2 was evicted -> accepted\n'
                '    written_e2 = pipeline.process_stream([IngestionEvent("e2", 6, "t", {})])\n'
                '    assert written_e2 == 1\n\n\n'
                'def test_dedup_window_eviction():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink, window_size=2)\n'
                '    pipeline.process_stream([\n'
                '        IngestionEvent("e1", 1, "t", {}),\n'
                '        IngestionEvent("e2", 2, "t", {}),\n'
                '    ])\n'
                '    pipeline.process_stream([\n'
                '        IngestionEvent("e3", 3, "t", {}),\n'
                '    ])\n'
                '    written = pipeline.process_stream([\n'
                '        IngestionEvent("e1", 4, "t", {}),\n'
                '    ])\n'
                '    assert written == 1\n'
                '    assert [e.event_id for e in sink.flushed] == ["e1", "e2", "e3", "e1"]\n\n\n'
                'def test_interleaved_duplicates_batch():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink, window_size=100)\n'
                '    events = [\n'
                '        IngestionEvent("a", 10, "t", {}),\n'
                '        IngestionEvent("b", 20, "t", {}),\n'
                '        IngestionEvent("a", 30, "t", {}),\n'
                '        IngestionEvent("c", 40, "t", {}),\n'
                '        IngestionEvent("b", 50, "t", {}),\n'
                '    ]\n'
                '    count = pipeline.process_stream(events)\n'
                '    assert count == 3\n'
                '    assert [e.event_id for e in sink.flushed] == ["a", "b", "c"]\n\n\n'
                'def test_empty_stream():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink)\n'
                '    assert pipeline.process_stream([]) == 0\n'
                '    assert len(sink.flushed) == 0\n\n\n'
                'def test_timestamp_deterministic_sorting():\n'
                '    sink = EventSink()\n'
                '    pipeline = IngestionPipeline(sink, window_size=10)\n'
                '    events = [\n'
                '        IngestionEvent("z", 300, "t", {}),\n'
                '        IngestionEvent("x", 100, "t", {}),\n'
                '        IngestionEvent("y", 200, "t", {}),\n'
                '    ]\n'
                '    pipeline.process_stream(events)\n'
                '    assert [e.event_id for e in sink.flushed] == ["x", "y", "z"]\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "quadratic_event_dedup_bottleneck",
            "categories": ["K", "B", "E"],
            "description": "Event deduplication pipeline uses O(N) list membership checks and array shifting, causing quadratic slowdown under high volume.",
            "spec_notes": "DeduplicationStream must use O(1) hash-set indexing with ordered eviction to maintain sub-linear throughput.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "performance",
            },
        }

    def _generate_circular_buffer(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "buffer.py": (
                '"""Fixed-capacity ring buffer with overwrite policy."""\n\n'
                'from typing import Any, List, Optional\n\n\n'
                'class CircularBuffer:\n'
                '    def __init__(self, capacity: int = 5):\n'
                '        self.capacity = capacity\n'
                '        self.buf: List[Optional[Any]] = [None] * capacity\n'
                '        self.head = 0  # Write pointer\n'
                '        self.tail = 0  # Read pointer\n'
                '        self.count = 0\n\n'
                '    def write(self, item: Any) -> Optional[Any]:\n'
                '        overwritten = None\n'
                '        if self.count == self.capacity:\n'
                '            overwritten = self.buf[self.head]\n'
                '            self.buf[self.head] = item\n'
                '            self.head = (self.head + 1) % self.capacity\n'
                '            # BUG: When buffer is full and overwrites, tail pointer must also advance\n'
                '            # to maintain valid FIFO order! Fails to update tail pointer.\n'
                '        else:\n'
                '            self.buf[self.head] = item\n'
                '            self.head = (self.head + 1) % self.capacity\n'
                '            self.count += 1\n'
                '        return overwritten\n\n'
                '    def read(self) -> Optional[Any]:\n'
                '        if self.count == 0:\n'
                '            return None\n'
                '        val = self.buf[self.tail]\n'
                '        self.buf[self.tail] = None\n'
                '        self.tail = (self.tail + 1) % self.capacity\n'
                '        self.count -= 1\n'
                '        return val\n\n'
                '    def is_full(self) -> bool:\n'
                '        return self.count == self.capacity\n'
            ),
            "ring_stream.py": (
                '"""Streaming circular telemetry buffer."""\n\n'
                'from typing import Any, List\n'
                'from buffer import CircularBuffer\n\n\n'
                'class RingStreamLogger:\n'
                '    def __init__(self, capacity: int = 3):\n'
                '        self.buffer = CircularBuffer(capacity=capacity)\n\n'
                '    def log_event(self, event_name: str) -> None:\n'
                '        self.buffer.write(event_name)\n\n'
                '    def drain_all(self) -> List[str]:\n'
                '        items: list[str] = []\n'
                '        while True:\n'
                '            val = self.buffer.read()\n'
                '            if val is None:\n'
                '                break\n'
                '            items.append(val)\n'
                '        return items\n'
            ),
            "consumer.py": (
                '"""Metrics consumer draining logger stream."""\n\n'
                'from typing import List\n'
                'from ring_stream import RingStreamLogger\n\n\n'
                'class StreamConsumer:\n'
                '    def __init__(self, logger: RingStreamLogger):\n'
                '        self.logger = logger\n\n'
                '    def consume_latest_batch(self) -> List[str]:\n'
                '        return self.logger.drain_all()\n'
            ),
        }

        reference_fix = {
            "buffer.py": (
                '"""Fixed-capacity ring buffer with overwrite policy."""\n\n'
                'from typing import Any, List, Optional\n\n\n'
                'class CircularBuffer:\n'
                '    def __init__(self, capacity: int = 5):\n'
                '        self.capacity = capacity\n'
                '        self.buf: List[Optional[Any]] = [None] * capacity\n'
                '        self.head = 0\n'
                '        self.tail = 0\n'
                '        self.count = 0\n\n'
                '    def write(self, item: Any) -> Optional[Any]:\n'
                '        overwritten = None\n'
                '        if self.count == self.capacity:\n'
                '            overwritten = self.buf[self.head]\n'
                '            self.buf[self.head] = item\n'
                '            self.head = (self.head + 1) % self.capacity\n'
                '            self.tail = (self.tail + 1) % self.capacity\n'
                '        else:\n'
                '            self.buf[self.head] = item\n'
                '            self.head = (self.head + 1) % self.capacity\n'
                '            self.count += 1\n'
                '        return overwritten\n\n'
                '    def read(self) -> Optional[Any]:\n'
                '        if self.count == 0:\n'
                '            return None\n'
                '        val = self.buf[self.tail]\n'
                '        self.buf[self.tail] = None\n'
                '        self.tail = (self.tail + 1) % self.capacity\n'
                '        self.count -= 1\n'
                '        return val\n\n'
                '    def is_full(self) -> bool:\n'
                '        return self.count == self.capacity\n'
            )
        }

        tests = {
            "test_circular_buffer.py": (
                'from ring_stream import RingStreamLogger\n'
                'from consumer import StreamConsumer\n\n\n'
                'def test_basic_fifo_drain():\n'
                '    logger = RingStreamLogger(capacity=3)\n'
                '    logger.log_event("e1")\n'
                '    logger.log_event("e2")\n'
                '    consumer = StreamConsumer(logger)\n'
                '    assert consumer.consume_latest_batch() == ["e1", "e2"]\n'
                '    assert consumer.consume_latest_batch() == []\n\n\n'
                'def test_overwrite_on_overflow_preserves_most_recent_items():\n'
                '    logger = RingStreamLogger(capacity=3)\n'
                '    # Write 5 events into capacity 3 buffer: e1, e2, e3, e4, e5\n'
                '    # e1 and e2 are overwritten. Buffer must contain [e3, e4, e5] in order!\n'
                '    for ev in ["e1", "e2", "e3", "e4", "e5"]:\n'
                '        logger.log_event(ev)\n'
                '    consumer = StreamConsumer(logger)\n'
                '    assert consumer.consume_latest_batch() == ["e3", "e4", "e5"]\n\n\n'
                'def test_repeated_wraparound_continuous_streaming():\n'
                '    logger = RingStreamLogger(capacity=2)\n'
                '    logger.log_event("a")\n'
                '    logger.log_event("b")\n'
                '    logger.log_event("c")  # Overwrites "a", tail points to "b"\n'
                '    consumer = StreamConsumer(logger)\n'
                '    assert consumer.consume_latest_batch() == ["b", "c"]\n'
                '    # Write again after drain\n'
                '    logger.log_event("d")\n'
                '    assert consumer.consume_latest_batch() == ["d"]\n\n\n'
                'def test_empty_buffer_drain():\n'
                '    logger = RingStreamLogger(capacity=5)\n'
                '    consumer = StreamConsumer(logger)\n'
                '    assert consumer.consume_latest_batch() == []\n\n\n'
                'def test_interleaved_write_and_reads():\n'
                '    logger = RingStreamLogger(capacity=2)\n'
                '    logger.log_event("1")\n'
                '    assert logger.buffer.read() == "1"\n'
                '    logger.log_event("2")\n'
                '    logger.log_event("3")\n'
                '    logger.log_event("4")  # Overwrites 2\n'
                '    assert logger.drain_all() == ["3", "4"]\n\n\n'
                'def test_is_full_predicate():\n'
                '    logger = RingStreamLogger(capacity=2)\n'
                '    assert logger.buffer.is_full() is False\n'
                '    logger.log_event("x")\n'
                '    assert logger.buffer.is_full() is False\n'
                '    logger.log_event("y")\n'
                '    assert logger.buffer.is_full() is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "circular_buffer_overwrite_tail_pointer_desync",
            "categories": ["K", "C", "D"],
            "description": "Circular ring buffer overwriting old items on overflow fails to advance tail read pointer, corrupting FIFO read order.",
            "spec_notes": "CircularBuffer.write must advance tail when count == capacity to maintain correct unread queue head.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "performance",
            },
        }
