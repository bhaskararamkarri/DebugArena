"""Category G: Async & Concurrency Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class ConcurrencyTaskGenerator(BaseGenerator):
    """Generates thread-safe queue and async task cancellation debugging tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v26_async_task_executor_cancellation")
        sub_type = spec.get("sub_type", "cancellation")

        if sub_type == "cache_coherence" or "coherence" in task_id:
            return self._generate_cache_coherence(task_id, spec, seed)
        elif sub_type == "backpressure_deadlock" or "backpressure" in task_id:
            return self._generate_backpressure_deadlock(task_id, spec, seed)
        elif sub_type == "queue_dedup" or "dedup" in task_id:
            return self._generate_queue_dedup(task_id, spec, seed)
        elif sub_type == "leader_election" or "election" in task_id:
            return self._generate_leader_election(task_id, spec, seed)
        elif sub_type == "raft_consensus" or "raft" in task_id or "split_vote" in task_id:
            return self._generate_raft_split_vote(task_id, spec, seed)
        elif sub_type == "byzantine_quorum" or "byzantine" in task_id or "quorum" in task_id:
            return self._generate_byzantine_quorum(task_id, spec, seed)
        elif sub_type == "actor_mailbox" or "actor" in task_id or "mailbox" in task_id:
            return self._generate_actor_mailbox_cycle(task_id, spec, seed)
        return self._generate_task_executor(task_id, spec, seed)

    def _generate_task_executor(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Job task definition and status."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Callable, Optional\n\n\n'
                '@dataclass\n'
                'class TaskJob:\n'
                '    job_id: str\n'
                '    fn: Callable[[], Any]\n'
                '    status: str = "QUEUED"\n'
                '    result: Optional[Any] = None\n'
                '    error: Optional[str] = None\n'
            ),
            "task_queue.py": (
                '"""Thread-safe task queue with cancellation tracking."""\n\n'
                'import threading\n'
                'from typing import Optional\n'
                'from models import TaskJob\n\n\n'
                'class SafeTaskQueue:\n'
                '    def __init__(self):\n'
                '        self._queue: list[TaskJob] = []\n'
                '        self._cancelled: set[str] = set()\n'
                '        self._lock = threading.Lock()\n\n'
                '    def push(self, job: TaskJob) -> None:\n'
                '        with self._lock:\n'
                '            self._queue.append(job)\n\n'
                '    def cancel(self, job_id: str) -> bool:\n'
                '        with self._lock:\n'
                '            if any(j.job_id == job_id for j in self._queue):\n'
                '                # BUG: Registers ID in cancelled set, but does not update job.status\n'
                '                # or synchronize status during pop_next() retrieval!\n'
                '                self._cancelled.add(job_id)\n'
                '                return True\n'
                '            return False\n\n'
                '    def pop_next(self) -> Optional[TaskJob]:\n'
                '        with self._lock:\n'
                '            # BUG: Pops raw job without checking if job.job_id was cancelled in _cancelled set\n'
                '            if self._queue:\n'
                '                return self._queue.pop(0)\n'
                '            return None\n'
            ),
            "executor.py": (
                '"""Task worker executor running queued jobs."""\n\n'
                'from typing import Dict, List\n'
                'from models import TaskJob\n'
                'from task_queue import SafeTaskQueue\n\n\n'
                'class TaskExecutor:\n'
                '    def __init__(self, queue: SafeTaskQueue):\n'
                '        self.queue = queue\n'
                '        self.completed: Dict[str, TaskJob] = {}\n\n'
                '    def drain_and_run(self) -> int:\n'
                '        executed_count = 0\n'
                '        while True:\n'
                '            job = self.queue.pop_next()\n'
                '            if not job:\n'
                '                break\n'
                '            # BUG: If job was cancelled while in queue, executor still executes fn()!\n'
                '            if job.status == "CANCELLED":\n'
                '                self.completed[job.job_id] = job\n'
                '                continue\n'
                '            try:\n'
                '                job.result = job.fn()\n'
                '                job.status = "COMPLETED"\n'
                '                executed_count += 1\n'
                '            except Exception as exc:\n'
                '                job.error = str(exc)\n'
                '                job.status = "FAILED"\n'
                '            self.completed[job.job_id] = job\n'
                '        return executed_count\n'
            ),
        }

        reference_fix = {
            "task_queue.py": (
                '"""Thread-safe task queue with cancellation tracking."""\n\n'
                'import threading\n'
                'from typing import Optional\n'
                'from models import TaskJob\n\n\n'
                'class SafeTaskQueue:\n'
                '    def __init__(self):\n'
                '        self._queue: list[TaskJob] = []\n'
                '        self._cancelled: set[str] = set()\n'
                '        self._lock = threading.Lock()\n\n'
                '    def push(self, job: TaskJob) -> None:\n'
                '        with self._lock:\n'
                '            self._queue.append(job)\n\n'
                '    def cancel(self, job_id: str) -> bool:\n'
                '        with self._lock:\n'
                '            self._cancelled.add(job_id)\n'
                '            for job in self._queue:\n'
                '                if job.job_id == job_id:\n'
                '                    job.status = "CANCELLED"\n'
                '                    return True\n'
                '            return False\n\n'
                '    def is_cancelled(self, job_id: str) -> bool:\n'
                '        with self._lock:\n'
                '            return job_id in self._cancelled\n\n'
                '    def pop_next(self) -> Optional[TaskJob]:\n'
                '        with self._lock:\n'
                '            if self._queue:\n'
                '                job = self._queue.pop(0)\n'
                '                if job.job_id in self._cancelled:\n'
                '                    job.status = "CANCELLED"\n'
                '                return job\n'
                '            return None\n'
            )
        }

        tests = {
            "test_task_executor.py": (
                'from models import TaskJob\n'
                'from task_queue import SafeTaskQueue\n'
                'from executor import TaskExecutor\n\n\n'
                'def test_fifo_execution():\n'
                '    q = SafeTaskQueue()\n'
                '    ex = TaskExecutor(q)\n'
                '    q.push(TaskJob("j1", lambda: 10))\n'
                '    q.push(TaskJob("j2", lambda: 20))\n'
                '    count = ex.drain_and_run()\n'
                '    assert count == 2\n'
                '    assert ex.completed["j1"].result == 10\n'
                '    assert ex.completed["j2"].result == 20\n\n\n'
                'def test_cancelled_job_is_skipped_without_running_fn():\n'
                '    q = SafeTaskQueue()\n'
                '    ex = TaskExecutor(q)\n'
                '    ran_flag = False\n'
                '    def side_effect():\n'
                '        nonlocal ran_flag\n'
                '        ran_flag = True\n'
                '        return "BAD"\n\n'
                '    q.push(TaskJob("j_cancel", side_effect))\n'
                '    res = q.cancel("j_cancel")\n'
                '    assert res is True\n'
                '    count = ex.drain_and_run()\n'
                '    assert count == 0\n'
                '    assert ran_flag is False\n'
                '    assert ex.completed["j_cancel"].status == "CANCELLED"\n'
                '    assert ex.completed["j_cancel"].result is None\n\n\n'
                'def test_cancel_nonexistent_job():\n'
                '    q = SafeTaskQueue()\n'
                '    assert q.cancel("missing") is False\n\n\n'
                'def test_failed_job_records_error():\n'
                '    q = SafeTaskQueue()\n'
                '    ex = TaskExecutor(q)\n'
                '    def will_crash():\n'
                '        raise ValueError("corrupt payload")\n\n'
                '    q.push(TaskJob("j_err", will_crash))\n'
                '    count = ex.drain_and_run()\n'
                '    assert count == 0\n'
                '    assert ex.completed["j_err"].status == "FAILED"\n'
                '    assert "corrupt payload" in ex.completed["j_err"].error\n\n\n'
                'def test_multiple_jobs_with_interleaved_cancellation():\n'
                '    q = SafeTaskQueue()\n'
                '    ex = TaskExecutor(q)\n'
                '    q.push(TaskJob("a", lambda: "A"))\n'
                '    q.push(TaskJob("b", lambda: "B"))\n'
                '    q.push(TaskJob("c", lambda: "C"))\n'
                '    q.cancel("b")\n'
                '    count = ex.drain_and_run()\n'
                '    assert count == 2\n'
                '    assert ex.completed["a"].status == "COMPLETED"\n'
                '    assert ex.completed["b"].status == "CANCELLED"\n'
                '    assert ex.completed["c"].status == "COMPLETED"\n\n\n'
                'def test_empty_queue_drain():\n'
                '    q = SafeTaskQueue()\n'
                '    ex = TaskExecutor(q)\n'
                '    assert ex.drain_and_run() == 0\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "task_queue_cancellation_status_bypass",
            "categories": ["G", "D"],
            "description": "Task queue pop_next ignores cancellation flags set during queue residency, causing cancelled jobs to execute.",
            "spec_notes": "SafeTaskQueue.pop_next must ensure cancelled jobs return with CANCELLED status.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }

    def _generate_cache_coherence(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "message.py": (
                '"""Inter-node cache invalidation protocol messages."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any\n\n\n'
                '@dataclass\n'
                'class InvalidationMessage:\n'
                '    sender_id: str\n'
                '    key: str\n'
                '    version: int\n'
            ),
            "invalidation_bus.py": (
                '"""Broadcast message bus distributing cache invalidations."""\n\n'
                'from typing import List\n'
                'from message import InvalidationMessage\n\n\n'
                'class InvalidationBus:\n'
                '    def __init__(self):\n'
                '        self.listeners = []\n\n'
                '    def register_node(self, node) -> None:\n'
                '        self.listeners.append(node)\n\n'
                '    def broadcast(self, msg: InvalidationMessage) -> None:\n'
                '        for node in self.listeners:\n'
                '            if node.node_id != msg.sender_id:\n'
                '                node.on_invalidation(msg)\n'
            ),
            "cache_node.py": (
                '"""Distributed cache node maintaining local key-value replica."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from invalidation_bus import InvalidationBus\n'
                'from message import InvalidationMessage\n\n\n'
                'class CacheNode:\n'
                '    def __init__(self, node_id: str, bus: InvalidationBus):\n'
                '        self.node_id = node_id\n'
                '        self.bus = bus\n'
                '        self.store: Dict[str, Any] = {}\n'
                '        self.versions: Dict[str, int] = {}\n'
                '        bus.register_node(self)\n\n'
                '    def put(self, key: str, val: Any, version: int) -> None:\n'
                '        # Write local update\n'
                '        self.store[key] = val\n'
                '        self.versions[key] = version\n'
                '        # Broadcast invalidation to peer nodes\n'
                '        self.bus.broadcast(InvalidationMessage(self.node_id, key, version))\n\n'
                '    def get(self, key: str) -> Optional[Any]:\n'
                '        return self.store.get(key)\n\n'
                '    def on_invalidation(self, msg: InvalidationMessage) -> None:\n'
                '        # BUG: Ignores message version and unconditionally deletes or fails to update local version,\n'
                '        # allowing stale older invalidation broadcasts to evict newer local writes!\n'
                '        curr_ver = self.versions.get(msg.key, 0)\n'
                '        self.store.pop(msg.key, None)\n'
                '        self.versions[msg.key] = msg.version  # Sets version to stale remote version!\n'
            ),
            "cluster.py": (
                '"""Distributed cluster orchestrator."""\n\n'
                'from typing import List\n'
                'from cache_node import CacheNode\n'
                'from invalidation_bus import InvalidationBus\n\n\n'
                'class CacheCluster:\n'
                '    def __init__(self, node_count: int = 3):\n'
                '        self.bus = InvalidationBus()\n'
                '        self.nodes = [CacheNode(f"node_{i}", self.bus) for i in range(node_count)]\n'
            ),
        }

        reference_fix = {
            "cache_node.py": (
                '"""Distributed cache node maintaining local key-value replica."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from invalidation_bus import InvalidationBus\n'
                'from message import InvalidationMessage\n\n\n'
                'class CacheNode:\n'
                '    def __init__(self, node_id: str, bus: InvalidationBus):\n'
                '        self.node_id = node_id\n'
                '        self.bus = bus\n'
                '        self.store: Dict[str, Any] = {}\n'
                '        self.versions: Dict[str, int] = {}\n'
                '        bus.register_node(self)\n\n'
                '    def put(self, key: str, val: Any, version: int) -> None:\n'
                '        self.store[key] = val\n'
                '        self.versions[key] = version\n'
                '        self.bus.broadcast(InvalidationMessage(self.node_id, key, version))\n\n'
                '    def get(self, key: str) -> Optional[Any]:\n'
                '        return self.store.get(key)\n\n'
                '    def on_invalidation(self, msg: InvalidationMessage) -> None:\n'
                '        curr_ver = self.versions.get(msg.key, 0)\n'
                '        # Only invalidate if remote message has higher or equal version\n'
                '        if msg.version >= curr_ver:\n'
                '            self.store.pop(msg.key, None)\n'
                '            self.versions[msg.key] = msg.version\n'
            )
        }

        tests = {
            "test_cache_coherence.py": (
                'from cluster import CacheCluster\n'
                'from message import InvalidationMessage\n\n\n'
                'def test_peer_invalidation_broadcast():\n'
                '    cluster = CacheCluster(node_count=3)\n'
                '    n0, n1, n2 = cluster.nodes\n'
                '    # Pre-populate all nodes\n'
                '    n0.store["k1"] = "val0"\n'
                '    n1.store["k1"] = "val0"\n'
                '    n2.store["k1"] = "val0"\n\n'
                '    # n0 updates k1 to version 2\n'
                '    n0.put("k1", "val_v2", 2)\n'
                '    assert n0.get("k1") == "val_v2"\n'
                '    # Peers n1 and n2 must have had k1 invalidated\n'
                '    assert n1.get("k1") is None\n'
                '    assert n2.get("k1") is None\n\n\n'
                'def test_stale_invalidation_message_ignored():\n'
                '    cluster = CacheCluster(node_count=2)\n'
                '    n0, n1 = cluster.nodes\n'
                '    # n0 writes version 5\n'
                '    n0.put("k2", "fresh_data", 5)\n'
                '    assert n0.get("k2") == "fresh_data"\n'
                '    # Stale out-of-order broadcast from past version 3 arrives at n0\n'
                '    n0.on_invalidation(InvalidationMessage("n1", "k2", version=3))\n'
                '    # Fresh data at version 5 MUST NOT be evicted by stale version 3 message!\n'
                '    assert n0.get("k2") == "fresh_data"\n'
                '    assert n0.versions["k2"] == 5\n\n\n'
                'def test_equal_version_invalidation_applies():\n'
                '    cluster = CacheCluster(node_count=2)\n'
                '    n0, n1 = cluster.nodes\n'
                '    n0.store["x"] = 100\n'
                '    n0.versions["x"] = 2\n'
                '    n0.on_invalidation(InvalidationMessage("n1", "x", version=2))\n'
                '    assert n0.get("x") is None\n\n\n'
                'def test_independent_keys_unaffected():\n'
                '    cluster = CacheCluster(node_count=2)\n'
                '    n0, n1 = cluster.nodes\n'
                '    n0.put("key_a", "A", 1)\n'
                '    n0.put("key_b", "B", 1)\n'
                '    n1.put("key_a", "A_updated", 2)\n'
                '    assert n0.get("key_a") is None\n'
                '    assert n0.get("key_b") == "B"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "cache_coherence_stale_invalidation_version_check_omission",
            "categories": ["G", "E", "D"],
            "description": "Distributed cache node applies invalidation messages without version checking, allowing stale messages to evict newer writes.",
            "spec_notes": "CacheNode.on_invalidation must verify msg.version >= curr_ver before clearing cache entry.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }

    def _generate_backpressure_deadlock(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "channel.py": (
                '"""Bounded producer-consumer channel."""\n\n'
                'import threading\n'
                'from typing import Any, Optional\n\n\n'
                'class BoundedChannel:\n'
                '    def __init__(self, capacity: int = 2):\n'
                '        self.capacity = capacity\n'
                '        self.queue = []\n'
                '        self.lock = threading.Lock()\n'
                '        self.not_empty = threading.Condition(self.lock)\n'
                '        self.not_full = threading.Condition(self.lock)\n'
                '        self.closed = False\n\n'
                '    def put(self, item: Any, timeout: float = 0.5) -> bool:\n'
                '        with self.lock:\n'
                '            while len(self.queue) >= self.capacity and not self.closed:\n'
                '                if not self.not_full.wait(timeout=timeout):\n'
                '                    return False\n'
                '            if self.closed:\n'
                '                return False\n'
                '            self.queue.append(item)\n'
                '            self.not_empty.notify()\n'
                '            return True\n\n'
                '    def get(self, timeout: float = 0.5) -> Optional[Any]:\n'
                '        with self.lock:\n'
                '            while not self.queue and not self.closed:\n'
                '                if not self.not_empty.wait(timeout=timeout):\n'
                '                    return None\n'
                '            if self.queue:\n'
                '                item = self.queue.pop(0)\n'
                '                self.not_full.notify()\n'
                '                return item\n'
                '            return None\n\n'
                '    def close(self) -> None:\n'
                '        with self.lock:\n'
                '            self.closed = True\n'
                '            # BUG: Only notifies not_empty condition, forgetting not_full condition,\n'
                '            # deadlocking blocked producers on pipeline shutdown!\n'
                '            self.not_empty.notify_all()\n'
            ),
            "worker.py": (
                '"""Pipeline worker stage."""\n\n'
                'from typing import Callable, List\n'
                'from channel import BoundedChannel\n\n\n'
                'class StageWorker:\n'
                '    def __init__(self, in_ch: BoundedChannel, out_ch: BoundedChannel, transform_fn: Callable[[int], int]):\n'
                '        self.in_ch = in_ch\n'
                '        self.out_ch = out_ch\n'
                '        self.transform_fn = transform_fn\n\n'
                '    def process_batch(self, max_items: int = 10) -> int:\n'
                '        count = 0\n'
                '        for _ in range(max_items):\n'
                '            item = self.in_ch.get(timeout=0.05)\n'
                '            if item is None:\n'
                '                break\n'
                '            res = self.transform_fn(item)\n'
                '            if not self.out_ch.put(res, timeout=0.05):\n'
                '                break\n'
                '            count += 1\n'
                '        return count\n'
            ),
            "pipeline.py": (
                '"""Multi-stage processing pipeline."""\n\n'
                'from channel import BoundedChannel\n'
                'from worker import StageWorker\n\n\n'
                'class ProcessingPipeline:\n'
                '    def __init__(self, capacity: int = 2):\n'
                '        self.in_ch = BoundedChannel(capacity=capacity)\n'
                '        self.out_ch = BoundedChannel(capacity=capacity)\n'
                '        self.worker = StageWorker(self.in_ch, self.out_ch, lambda x: x * 2)\n\n'
                '    def stop(self) -> None:\n'
                '        self.in_ch.close()\n'
                '        self.out_ch.close()\n'
            ),
        }

        reference_fix = {
            "channel.py": (
                '"""Bounded producer-consumer channel."""\n\n'
                'import threading\n'
                'from typing import Any, Optional\n\n\n'
                'class BoundedChannel:\n'
                '    def __init__(self, capacity: int = 2):\n'
                '        self.capacity = capacity\n'
                '        self.queue = []\n'
                '        self.lock = threading.Lock()\n'
                '        self.not_empty = threading.Condition(self.lock)\n'
                '        self.not_full = threading.Condition(self.lock)\n'
                '        self.closed = False\n\n'
                '    def put(self, item: Any, timeout: float = 0.5) -> bool:\n'
                '        with self.lock:\n'
                '            while len(self.queue) >= self.capacity and not self.closed:\n'
                '                if not self.not_full.wait(timeout=timeout):\n'
                '                    return False\n'
                '            if self.closed:\n'
                '                return False\n'
                '            self.queue.append(item)\n'
                '            self.not_empty.notify()\n'
                '            return True\n\n'
                '    def get(self, timeout: float = 0.5) -> Optional[Any]:\n'
                '        with self.lock:\n'
                '            while not self.queue and not self.closed:\n'
                '                if not self.not_empty.wait(timeout=timeout):\n'
                '                    return None\n'
                '            if self.queue:\n'
                '                item = self.queue.pop(0)\n'
                '                self.not_full.notify()\n'
                '                return item\n'
                '            return None\n\n'
                '    def close(self) -> None:\n'
                '        with self.lock:\n'
                '            self.closed = True\n'
                '            self.not_empty.notify_all()\n'
                '            self.not_full.notify_all()\n'
            )
        }

        tests = {
            "test_pipeline_deadlock.py": (
                'import threading\n'
                'import time\n'
                'from channel import BoundedChannel\n'
                'from pipeline import ProcessingPipeline\n\n\n'
                'def test_basic_pipeline_flow():\n'
                '    pipe = ProcessingPipeline(capacity=5)\n'
                '    pipe.in_ch.put(10)\n'
                '    pipe.in_ch.put(20)\n'
                '    processed = pipe.worker.process_batch(10)\n'
                '    assert processed == 2\n'
                '    assert pipe.out_ch.get() == 20\n'
                '    assert pipe.out_ch.get() == 40\n\n\n'
                'def test_channel_close_unblocks_waiting_producers():\n'
                '    ch = BoundedChannel(capacity=1)\n'
                '    ch.put("item1")  # Channel is full\n\n'
                '    blocked_flag = True\n'
                '    put_success = None\n'
                '    def blocked_producer():\n'
                '        nonlocal blocked_flag, put_success\n'
                '        put_success = ch.put("item2", timeout=5.0)\n'
                '        blocked_flag = False\n\n'
                '    t = threading.Thread(target=blocked_producer)\n'
                '    t.start()\n'
                '    time.sleep(0.05)\n'
                '    assert blocked_flag is True\n\n'
                '    # Closing channel must immediately unblock producer thread\n'
                '    ch.close()\n'
                '    t.join(timeout=0.5)\n'
                '    assert blocked_flag is False\n'
                '    assert put_success is False\n\n\n'
                'def test_channel_close_allows_draining_remaining_items():\n'
                '    ch = BoundedChannel(capacity=3)\n'
                '    ch.put(1)\n'
                '    ch.put(2)\n'
                '    ch.close()\n'
                '    assert ch.get() == 1\n'
                '    assert ch.get() == 2\n'
                '    assert ch.get() is None\n\n\n'
                'def test_pipeline_shutdown():\n'
                '    pipe = ProcessingPipeline(capacity=1)\n'
                '    pipe.stop()\n'
                '    assert pipe.in_ch.closed is True\n'
                '    assert pipe.out_ch.closed is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "channel_backpressure_producer_condition_deadlock",
            "categories": ["G", "E"],
            "description": "Bounded channel close() fails to notify waiting full condition, deadlocking backpressured producer threads.",
            "spec_notes": "BoundedChannel.close must call self.not_full.notify_all() in addition to not_empty.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }

    def _generate_queue_dedup(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "message.py": (
                '"""Broker message payload."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any\n\n\n'
                '@dataclass\n'
                'class QueueMessage:\n'
                '    msg_id: str\n'
                '    body: Any\n'
                '    sequence: int\n'
            ),
            "dedup_window.py": (
                '"""Sliding deduplication window for streaming queues."""\n\n'
                'class DedupWindow:\n'
                '    def __init__(self, max_size: int = 5):\n'
                '        self.max_size = max_size\n'
                '        self.seen_ids = set()\n'
                '        self.order = []\n\n'
                '    def is_duplicate_and_record(self, msg_id: str) -> bool:\n'
                '        if msg_id in self.seen_ids:\n'
                '            return True\n'
                '        self.seen_ids.add(msg_id)\n'
                '        self.order.append(msg_id)\n'
                '        if len(self.order) > self.max_size:\n'
                '            # BUG: Pops from back self.order.pop() instead of self.order.pop(0)!\n'
                '            # Evicting the NEWEST element instead of the OLDEST element!\n'
                '            evicted = self.order.pop()\n'
                '            self.seen_ids.discard(evicted)\n'
                '        return False\n'
            ),
            "broker.py": (
                '"""Message queue broker with deduplication filter."""\n\n'
                'from typing import List, Optional\n'
                'from dedup_window import DedupWindow\n'
                'from message import QueueMessage\n\n\n'
                'class QueueBroker:\n'
                '    def __init__(self, dedup_size: int = 4):\n'
                '        self.dedup = DedupWindow(max_size=dedup_size)\n'
                '        self.queue: List[QueueMessage] = []\n\n'
                '    def publish(self, msg: QueueMessage) -> bool:\n'
                '        if self.dedup.is_duplicate_and_record(msg.msg_id):\n'
                '            return False\n'
                '        self.queue.append(msg)\n'
                '        return True\n\n'
                '    def consume(self) -> Optional[QueueMessage]:\n'
                '        if self.queue:\n'
                '            return self.queue.pop(0)\n'
                '        return None\n'
            ),
            "consumer.py": (
                '"""Message consumer client."""\n\n'
                'from typing import List\n'
                'from broker import QueueBroker\n\n\n'
                'class MessageConsumer:\n'
                '    def __init__(self, broker: QueueBroker):\n'
                '        self.broker = broker\n\n'
                '    def drain_all(self) -> List[str]:\n'
                '        out = []\n'
                '        while True:\n'
                '            m = self.broker.consume()\n'
                '            if not m:\n'
                '                break\n'
                '            out.append(m.msg_id)\n'
                '        return out\n'
            ),
        }

        reference_fix = {
            "dedup_window.py": (
                '"""Sliding deduplication window for streaming queues."""\n\n'
                'class DedupWindow:\n'
                '    def __init__(self, max_size: int = 5):\n'
                '        self.max_size = max_size\n'
                '        self.seen_ids = set()\n'
                '        self.order = []\n\n'
                '    def is_duplicate_and_record(self, msg_id: str) -> bool:\n'
                '        if msg_id in self.seen_ids:\n'
                '            return True\n'
                '        self.seen_ids.add(msg_id)\n'
                '        self.order.append(msg_id)\n'
                '        if len(self.order) > self.max_size:\n'
                '            evicted = self.order.pop(0)\n'
                '            self.seen_ids.discard(evicted)\n'
                '        return False\n'
            )
        }

        tests = {
            "test_queue_dedup.py": (
                'from message import QueueMessage\n'
                'from broker import QueueBroker\n'
                'from consumer import MessageConsumer\n\n\n'
                'def test_basic_deduplication():\n'
                '    broker = QueueBroker(dedup_size=3)\n'
                '    assert broker.publish(QueueMessage("m1", "data", 1)) is True\n'
                '    assert broker.publish(QueueMessage("m1", "data", 2)) is False  # duplicate\n'
                '    assert broker.publish(QueueMessage("m2", "data", 3)) is True\n'
                '    consumer = MessageConsumer(broker)\n'
                '    assert consumer.drain_all() == ["m1", "m2"]\n\n\n'
                'def test_fifo_window_eviction_order():\n'
                '    broker = QueueBroker(dedup_size=2)\n'
                '    # Push m1, m2 (window holds {m1, m2})\n'
                '    broker.publish(QueueMessage("m1", "", 1))\n'
                '    broker.publish(QueueMessage("m2", "", 2))\n'
                '    # Push m3: window size 2 exceeded -> m1 (OLDEST) must be evicted, m2 & m3 kept\n'
                '    broker.publish(QueueMessage("m3", "", 3))\n'
                '    # Immediate re-send of m3 must be recognized as duplicate (m3 is in window)\n'
                '    assert broker.publish(QueueMessage("m3", "", 4)) is False\n'
                '    # m1 was evicted, so m1 can now enter again\n'
                '    assert broker.publish(QueueMessage("m1", "", 5)) is True\n\n\n'
                'def test_empty_broker_consume():\n'
                '    broker = QueueBroker()\n'
                '    assert broker.consume() is None\n\n\n'
                'def test_sequential_unique_messages():\n'
                '    broker = QueueBroker(dedup_size=5)\n'
                '    for i in range(5):\n'
                '        assert broker.publish(QueueMessage(f"id_{i}", "", i)) is True\n'
                '    consumer = MessageConsumer(broker)\n'
                '    assert len(consumer.drain_all()) == 5\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "queue_dedup_window_fifo_eviction_inversion",
            "categories": ["G", "E"],
            "description": "Deduplication window evicts newest messages (pop()) instead of oldest (pop(0)) when capacity is exceeded.",
            "spec_notes": "DedupWindow.is_duplicate_and_record must pop from index 0 on overflow.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }

    def _generate_leader_election(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "lease.py": (
                '"""Leader election lease contract."""\n\n'
                'from dataclasses import dataclass\n\n\n'
                '@dataclass\n'
                'class LeaderLease:\n'
                '    leader_id: str\n'
                '    expires_at: float\n\n'
                '    def is_expired(self, now: float) -> bool:\n'
                '        return now >= self.expires_at\n'
            ),
            "election_fsm.py": (
                '"""Raft/Paxos-style leader election coordinator."""\n\n'
                'from typing import Optional\n'
                'from lease import LeaderLease\n\n\n'
                'class ElectionCoordinator:\n'
                '    def __init__(self, lease_duration: float = 10.0):\n'
                '        self.lease_duration = lease_duration\n'
                '        self.current_lease: Optional[LeaderLease] = None\n\n'
                '    def acquire_or_renew(self, candidate_id: str, now: float) -> bool:\n'
                '        if not self.current_lease or self.current_lease.is_expired(now):\n'
                '            self.current_lease = LeaderLease(candidate_id, now + self.lease_duration)\n'
                '            return True\n'
                '        # Existing active leader renewing\n'
                '        if self.current_lease.leader_id == candidate_id:\n'
                '            # BUG: Renews lease by adding duration to now instead of extending, but fails to return True!\n'
                '            self.current_lease = LeaderLease(candidate_id, now + self.lease_duration)\n'
                '            return False  # BUG: Returns False on renewal!\n'
                '        return False\n\n'
                '    def get_current_leader(self, now: float) -> Optional[str]:\n'
                '        if self.current_lease and not self.current_lease.is_expired(now):\n'
                '            return self.current_lease.leader_id\n'
                '        return None\n'
            ),
            "cluster.py": (
                '"""Cluster node participating in leader election."""\n\n'
                'from election_fsm import ElectionCoordinator\n\n\n'
                'class ClusterNode:\n'
                '    def __init__(self, node_id: str, coord: ElectionCoordinator):\n'
                '        self.node_id = node_id\n'
                '        self.coord = coord\n\n'
                '    def heartbeat(self, now: float) -> bool:\n'
                '        return self.coord.acquire_or_renew(self.node_id, now)\n'
            ),
        }

        reference_fix = {
            "election_fsm.py": (
                '"""Raft/Paxos-style leader election coordinator."""\n\n'
                'from typing import Optional\n'
                'from lease import LeaderLease\n\n\n'
                'class ElectionCoordinator:\n'
                '    def __init__(self, lease_duration: float = 10.0):\n'
                '        self.lease_duration = lease_duration\n'
                '        self.current_lease: Optional[LeaderLease] = None\n\n'
                '    def acquire_or_renew(self, candidate_id: str, now: float) -> bool:\n'
                '        if not self.current_lease or self.current_lease.is_expired(now):\n'
                '            self.current_lease = LeaderLease(candidate_id, now + self.lease_duration)\n'
                '            return True\n'
                '        if self.current_lease.leader_id == candidate_id:\n'
                '            self.current_lease = LeaderLease(candidate_id, now + self.lease_duration)\n'
                '            return True\n'
                '        return False\n\n'
                '    def get_current_leader(self, now: float) -> Optional[str]:\n'
                '        if self.current_lease and not self.current_lease.is_expired(now):\n'
                '            return self.current_lease.leader_id\n'
                '        return None\n'
            )
        }

        tests = {
            "test_leader_election.py": (
                'from election_fsm import ElectionCoordinator\n'
                'from cluster import ClusterNode\n\n\n'
                'def test_initial_leader_acquisition():\n'
                '    coord = ElectionCoordinator(lease_duration=10.0)\n'
                '    n1 = ClusterNode("node_1", coord)\n'
                '    assert n1.heartbeat(now=100.0) is True\n'
                '    assert coord.get_current_leader(now=100.0) == "node_1"\n\n\n'
                'def test_competing_node_rejected_during_active_lease():\n'
                '    coord = ElectionCoordinator(lease_duration=10.0)\n'
                '    n1 = ClusterNode("node_1", coord)\n'
                '    n2 = ClusterNode("node_2", coord)\n'
                '    n1.heartbeat(now=100.0)\n'
                '    # n2 tries to take leadership at t=105 while n1 lease expires at 110\n'
                '    assert n2.heartbeat(now=105.0) is False\n'
                '    assert coord.get_current_leader(now=105.0) == "node_1"\n\n\n'
                'def test_leader_lease_renewal():\n'
                '    coord = ElectionCoordinator(lease_duration=10.0)\n'
                '    n1 = ClusterNode("node_1", coord)\n'
                '    n1.heartbeat(now=100.0)\n'
                '    # n1 renews at t=105 (new expiration 115)\n'
                '    assert n1.heartbeat(now=105.0) is True\n'
                '    assert coord.get_current_leader(now=112.0) == "node_1"\n\n\n'
                'def test_expired_lease_allows_new_leader():\n'
                '    coord = ElectionCoordinator(lease_duration=5.0)\n'
                '    n1 = ClusterNode("node_1", coord)\n'
                '    n2 = ClusterNode("node_2", coord)\n'
                '    n1.heartbeat(now=50.0)  # expires at 55.0\n'
                '    # At t=60, n2 acquires leadership\n'
                '    assert n2.heartbeat(now=60.0) is True\n'
                '    assert coord.get_current_leader(now=60.0) == "node_2"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "leader_election_lease_renewal_return_value_inversion",
            "categories": ["G", "D"],
            "description": "Leader election coordinator returns False on successful leader lease renewals, causing leader nodes to believe they lost leadership.",
            "spec_notes": "ElectionCoordinator.acquire_or_renew must return True when the active leader successfully extends its lease.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }

    def _generate_raft_split_vote(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "log_entry.py": (
                '"""Raft log entry definition."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any\n\n\n'
                '@dataclass\n'
                'class LogEntry:\n'
                '    index: int\n'
                '    term: int\n'
                '    command: Any\n'
            ),
            "rpc.py": (
                '"""Raft RPC request and response payloads."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, List\n'
                'from log_entry import LogEntry\n\n\n'
                '@dataclass\n'
                'class RequestVoteArgs:\n'
                '    term: int\n'
                '    candidate_id: str\n'
                '    last_log_index: int\n'
                '    last_log_term: int\n\n\n'
                '@dataclass\n'
                'class RequestVoteReply:\n'
                '    term: int\n'
                '    vote_granted: bool\n'
            ),
            "raft_node.py": (
                '"""Raft consensus protocol node."""\n\n'
                'from typing import List, Optional\n'
                'from log_entry import LogEntry\n'
                'from rpc import RequestVoteArgs, RequestVoteReply\n\n\n'
                'class RaftNode:\n'
                '    def __init__(self, node_id: str):\n'
                '        self.node_id = node_id\n'
                '        self.current_term = 0\n'
                '        self.voted_for: Optional[str] = None\n'
                '        self.log: List[LogEntry] = []\n\n'
                '    @property\n'
                '    def last_log_index(self) -> int:\n'
                '        return self.log[-1].index if self.log else 0\n\n'
                '    @property\n'
                '    def last_log_term(self) -> int:\n'
                '        return self.log[-1].term if self.log else 0\n\n'
                '    def handle_request_vote(self, args: RequestVoteArgs) -> RequestVoteReply:\n'
                '        if args.term < self.current_term:\n'
                '            return RequestVoteReply(self.current_term, False)\n\n'
                '        if args.term > self.current_term:\n'
                '            self.current_term = args.term\n'
                '            self.voted_for = None\n\n'
                '        # BUG: Only checks if voted_for is None or equals candidate_id,\n'
                '        # completely ignoring §5.4.1 log up-to-dateness check!\n'
                '        # Allows stale candidate with shorter/older log to receive votes.\n'
                '        can_vote = self.voted_for is None or self.voted_for == args.candidate_id\n'
                '        if can_vote:\n'
                '            self.voted_for = args.candidate_id\n'
                '            return RequestVoteReply(self.current_term, True)\n'
                '        return RequestVoteReply(self.current_term, False)\n'
            ),
        }

        reference_fix = {
            "raft_node.py": (
                '"""Raft consensus protocol node."""\n\n'
                'from typing import List, Optional\n'
                'from log_entry import LogEntry\n'
                'from rpc import RequestVoteArgs, RequestVoteReply\n\n\n'
                'class RaftNode:\n'
                '    def __init__(self, node_id: str):\n'
                '        self.node_id = node_id\n'
                '        self.current_term = 0\n'
                '        self.voted_for: Optional[str] = None\n'
                '        self.log: List[LogEntry] = []\n\n'
                '    @property\n'
                '    def last_log_index(self) -> int:\n'
                '        return self.log[-1].index if self.log else 0\n\n'
                '    @property\n'
                '    def last_log_term(self) -> int:\n'
                '        return self.log[-1].term if self.log else 0\n\n'
                '    def handle_request_vote(self, args: RequestVoteArgs) -> RequestVoteReply:\n'
                '        if args.term < self.current_term:\n'
                '            return RequestVoteReply(self.current_term, False)\n\n'
                '        if args.term > self.current_term:\n'
                '            self.current_term = args.term\n'
                '            self.voted_for = None\n\n'
                '        can_vote = self.voted_for is None or self.voted_for == args.candidate_id\n'
                '        # Raft §5.4.1: Candidate log must be at least as up-to-date as receiver log\n'
                '        log_ok = (\n'
                '            args.last_log_term > self.last_log_term\n'
                '            or (\n'
                '                args.last_log_term == self.last_log_term\n'
                '                and args.last_log_index >= self.last_log_index\n'
                '            )\n'
                '        )\n'
                '        if can_vote and log_ok:\n'
                '            self.voted_for = args.candidate_id\n'
                '            return RequestVoteReply(self.current_term, True)\n'
                '        return RequestVoteReply(self.current_term, False)\n'
            )
        }

        tests = {
            "test_raft_election.py": (
                'from log_entry import LogEntry\n'
                'from raft_node import RaftNode\n'
                'from rpc import RequestVoteArgs\n\n\n'
                'def test_vote_granted_when_candidate_up_to_date():\n'
                '    node = RaftNode("n1")\n'
                '    node.current_term = 1\n'
                '    node.log = [LogEntry(1, 1, "cmd1")]\n'
                '    args = RequestVoteArgs(term=2, candidate_id="cand_2", last_log_index=1, last_log_term=1)\n'
                '    reply = node.handle_request_vote(args)\n'
                '    assert reply.vote_granted is True\n'
                '    assert node.voted_for == "cand_2"\n\n\n'
                'def test_vote_denied_when_candidate_log_term_is_stale():\n'
                '    node = RaftNode("n2")\n'
                '    node.current_term = 3\n'
                '    node.log = [LogEntry(1, 1, "c1"), LogEntry(2, 3, "c2")]\n'
                '    # Candidate has term 4 (higher term), but last_log_term is 2 (< node term 3)\n'
                '    args = RequestVoteArgs(term=4, candidate_id="stale_cand", last_log_index=5, last_log_term=2)\n'
                '    reply = node.handle_request_vote(args)\n'
                '    # Stale candidate MUST NOT be granted vote!\n'
                '    assert reply.vote_granted is False\n'
                '    assert node.voted_for is None\n\n\n'
                'def test_vote_denied_when_candidate_log_shorter_at_same_term():\n'
                '    node = RaftNode("n3")\n'
                '    node.current_term = 2\n'
                '    node.log = [LogEntry(1, 1, "c1"), LogEntry(2, 2, "c2"), LogEntry(3, 2, "c3")]\n'
                '    # Candidate has last_log_index 2 at term 2 (node has index 3 at term 2)\n'
                '    args = RequestVoteArgs(term=3, candidate_id="shorter_cand", last_log_index=2, last_log_term=2)\n'
                '    reply = node.handle_request_vote(args)\n'
                '    assert reply.vote_granted is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "raft_request_vote_log_completeness_omission",
            "categories": ["G", "E"],
            "description": "Raft node grants votes without checking candidate log up-to-dateness (§5.4.1), electing stale leaders that lose committed state.",
            "spec_notes": "RaftNode.handle_request_vote must verify candidate's last_log_term and last_log_index before granting vote.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "distributed-consensus",
            },
        }

    def _generate_byzantine_quorum(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "bft_message.py": (
                '"""BFT consensus vote messages."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any\n\n\n'
                '@dataclass\n'
                'class CommitVote:\n'
                '    view: int\n'
                '    sequence: int\n'
                '    block_hash: str\n'
                '    node_id: str\n'
            ),
            "validator_set.py": (
                '"""Validator set membership and quorum threshold calculator."""\n\n'
                'class ValidatorSet:\n'
                '    def __init__(self, validators: list[str]):\n'
                '        self.validators = list(validators)\n\n'
                '    @property\n'
                '    def size(self) -> int:\n'
                '        return len(self.validators)\n\n'
                '    def required_commit_quorum(self) -> int:\n'
                '        # In PBFT (3f + 1), required commit quorum is 2f + 1\n'
                '        # BUG: Uses naive (2 * N) // 3 which undercounts when N=4 (returns 2 instead of 3)!\n'
                '        return (2 * self.size) // 3\n'
            ),
            "bft_engine.py": (
                '"""BFT block finalization engine."""\n\n'
                'from typing import Dict, List\n'
                'from bft_message import CommitVote\n'
                'from validator_set import ValidatorSet\n\n\n'
                'class BFTEngine:\n'
                '    def __init__(self, val_set: ValidatorSet):\n'
                '        self.val_set = val_set\n'
                '        self.commit_votes: Dict[str, set[str]] = {}  # block_hash -> set(node_ids)\n\n'
                '    def receive_vote(self, vote: CommitVote) -> bool:\n'
                '        if vote.node_id not in self.val_set.validators:\n'
                '            return False\n'
                '        if vote.block_hash not in self.commit_votes:\n'
                '            self.commit_votes[vote.block_hash] = set()\n'
                '        self.commit_votes[vote.block_hash].add(vote.node_id)\n'
                '        threshold = self.val_set.required_commit_quorum()\n'
                '        return len(self.commit_votes[vote.block_hash]) >= threshold\n'
            ),
        }

        reference_fix = {
            "validator_set.py": (
                '"""Validator set membership and quorum threshold calculator."""\n\n'
                'import math\n\n\n'
                'class ValidatorSet:\n'
                '    def __init__(self, validators: list[str]):\n'
                '        self.validators = list(validators)\n\n'
                '    @property\n'
                '    def size(self) -> int:\n'
                '        return len(self.validators)\n\n'
                '    def required_commit_quorum(self) -> int:\n'
                '        # For N = 3f + 1, f = (N - 1) // 3, required quorum = 2f + 1\n'
                '        f = (self.size - 1) // 3\n'
                '        return 2 * f + 1\n'
            )
        }

        tests = {
            "test_bft_quorum.py": (
                'from bft_message import CommitVote\n'
                'from bft_engine import BFTEngine\n'
                'from validator_set import ValidatorSet\n\n\n'
                'def test_validator_set_size_and_membership():\n'
                '    vs = ValidatorSet(["v1", "v2", "v3"])\n'
                '    assert vs.size == 3\n'
                '    engine = BFTEngine(vs)\n'
                '    assert engine.receive_vote(CommitVote(1, 1, "blk", "unknown")) is False\n\n\n'
                'def test_four_node_cluster_requires_three_votes():\n'
                '    # N=4 (f=1) requires 2f+1 = 3 votes for finality\n'
                '    vals = ["v0", "v1", "v2", "v3"]\n'
                '    vs = ValidatorSet(vals)\n'
                '    engine = BFTEngine(vs)\n'
                '    # 2 votes must NOT finalize block\n'
                '    assert engine.receive_vote(CommitVote(1, 1, "blk_a", "v0")) is False\n'
                '    assert engine.receive_vote(CommitVote(1, 1, "blk_a", "v1")) is False\n'
                '    # 3rd vote reaches 2f+1 quorum -> finalized\n'
                '    assert engine.receive_vote(CommitVote(1, 1, "blk_a", "v2")) is True\n\n\n'
                'def test_seven_node_cluster_requires_five_votes():\n'
                '    # N=7 (f=2) requires 2(2)+1 = 5 votes\n'
                '    vs = ValidatorSet([f"v_{i}" for i in range(7)])\n'
                '    assert vs.required_commit_quorum() == 5\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "bft_quorum_calculation_undercount_error",
            "categories": ["G", "L"],
            "description": "BFT consensus quorum calculator uses truncated integer division, accepting 2 votes instead of 3 in a 4-node PBFT cluster.",
            "spec_notes": "ValidatorSet.required_commit_quorum must enforce 2f + 1 where f = (N - 1) // 3.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "distributed-consensus",
            },
        }

    def _generate_actor_mailbox_cycle(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "message.py": (
                '"""Actor message envelope."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Optional\n\n\n'
                '@dataclass\n'
                'class ActorMessage:\n'
                '    sender: Optional[str]\n'
                '    target: str\n'
                '    payload: Any\n'
                '    is_ask: bool = False\n'
                '    correlation_id: Optional[str] = None\n'
            ),
            "mailbox.py": (
                '"""Actor message mailbox with priority queue."""\n\n'
                'from typing import List, Optional\n'
                'from message import ActorMessage\n\n\n'
                'class Mailbox:\n'
                '    def __init__(self):\n'
                '        self.messages: List[ActorMessage] = []\n\n'
                '    def enqueue(self, msg: ActorMessage) -> None:\n'
                '        # Responses to ask requests get priority\n'
                '        if msg.correlation_id:\n'
                '            self.messages.insert(0, msg)\n'
                '        else:\n'
                '            self.messages.append(msg)\n\n'
                '    def dequeue(self) -> Optional[ActorMessage]:\n'
                '        return self.messages.pop(0) if self.messages else None\n'
            ),
            "actor_ref.py": (
                '"""Actor reference and message dispatch."""\n\n'
                'from typing import Any, Callable, Dict, Optional\n'
                'from mailbox import Mailbox\n'
                'from message import ActorMessage\n\n\n'
                'class ActorRef:\n'
                '    def __init__(self, name: str, handler: Callable[[ActorMessage], Any]):\n'
                '        self.name = name\n'
                '        self.handler = handler\n'
                '        self.mailbox = Mailbox()\n'
                '        self.outbox_replies: Dict[str, Any] = {}\n\n'
                '    def tell(self, target: "ActorRef", payload: Any) -> None:\n'
                '        msg = ActorMessage(sender=self.name, target=target.name, payload=payload)\n'
                '        target.mailbox.enqueue(msg)\n\n'
                '    def process_one(self) -> bool:\n'
                '        msg = self.mailbox.dequeue()\n'
                '        if not msg:\n'
                '            return False\n'
                '        res = self.handler(msg)\n'
                '        if msg.is_ask and msg.correlation_id and msg.sender:\n'
                '            # BUG: Stores response locally in self.outbox_replies instead of sending response message to sender.mailbox!\n'
                '            self.outbox_replies[msg.correlation_id] = res\n'
                '        return True\n'
            ),
        }

        reference_fix = {
            "actor_ref.py": (
                '"""Actor reference and message dispatch."""\n\n'
                'from typing import Any, Callable, Dict, Optional\n'
                'from mailbox import Mailbox\n'
                'from message import ActorMessage\n\n\n'
                'class ActorRef:\n'
                '    def __init__(self, name: str, handler: Callable[[ActorMessage], Any]):\n'
                '        self.name = name\n'
                '        self.handler = handler\n'
                '        self.mailbox = Mailbox()\n'
                '        self.system_registry: Dict[str, "ActorRef"] = {}\n\n'
                '    def tell(self, target: "ActorRef", payload: Any) -> None:\n'
                '        msg = ActorMessage(sender=self.name, target=target.name, payload=payload)\n'
                '        target.mailbox.enqueue(msg)\n\n'
                '    def process_one(self) -> bool:\n'
                '        msg = self.mailbox.dequeue()\n'
                '        if not msg:\n'
                '            return False\n'
                '        res = self.handler(msg)\n'
                '        if msg.is_ask and msg.correlation_id and msg.sender:\n'
                '            sender_ref = self.system_registry.get(msg.sender)\n'
                '            if sender_ref:\n'
                '                reply = ActorMessage(sender=self.name, target=msg.sender, payload=res, correlation_id=msg.correlation_id)\n'
                '                sender_ref.mailbox.enqueue(reply)\n'
                '        return True\n'
            )
        }

        tests = {
            "test_actor_mailbox.py": (
                'from actor_ref import ActorRef\n'
                'from message import ActorMessage\n\n\n'
                'def test_basic_tell_delivery():\n'
                '    a1 = ActorRef("sender", lambda m: None)\n'
                '    a2 = ActorRef("receiver", lambda m: None)\n'
                '    a1.tell(a2, "hello")\n'
                '    msg = a2.mailbox.dequeue()\n'
                '    assert msg is not None\n'
                '    assert msg.payload == "hello"\n\n\n'
                'def test_empty_mailbox_returns_false():\n'
                '    a = ActorRef("idle", lambda m: None)\n'
                '    assert a.process_one() is False\n\n\n'
                'def test_actor_ask_response_routing():\n'
                '    a1 = ActorRef("worker", lambda m: f"processed_{m.payload}")\n'
                '    a2 = ActorRef("caller", lambda m: None)\n'
                '    a1.system_registry = {"caller": a2, "worker": a1}\n'
                '    a2.system_registry = {"caller": a2, "worker": a1}\n\n'
                '    # Caller sends ask message to worker\n'
                '    ask_msg = ActorMessage(sender="caller", target="worker", payload="task_1", is_ask=True, correlation_id="req_100")\n'
                '    a1.mailbox.enqueue(ask_msg)\n'
                '    # Worker processes message\n'
                '    a1.process_one()\n'
                '    # Reply must be queued into caller mailbox with priority correlation_id!\n'
                '    reply = a2.mailbox.dequeue()\n'
                '    assert reply is not None\n'
                '    assert reply.correlation_id == "req_100"\n'
                '    assert reply.payload == "processed_task_1"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "actor_ask_reply_mailbox_dispatch_omission",
            "categories": ["G", "E"],
            "description": "Actor reference fails to dispatch response messages back to caller mailbox on ask requests, deadlocking callers.",
            "spec_notes": "ActorRef.process_one must enqueue replies to the sender mailbox via registry lookup.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "concurrency",
            },
        }


