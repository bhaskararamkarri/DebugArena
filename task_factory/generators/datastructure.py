"""Category C: Data Structure Invariants Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class DataStructureTaskGenerator(BaseGenerator):
    """Generates complex data structure invariant debugging tasks (RB trees, min heaps, tries, DSU)."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v32_red_black_tree_color_inversion")
        sub_type = spec.get("sub_type", "rb_tree")

        if sub_type == "min_heap" or "heap" in task_id:
            return self._generate_min_heap_decrease_key(task_id, spec, seed)
        elif sub_type == "trie" or "trie" in task_id:
            return self._generate_trie_pruning(task_id, spec, seed)
        elif sub_type == "dsu" or "disjoint" in task_id or "rank" in task_id:
            return self._generate_dsu_rank(task_id, spec, seed)
        elif sub_type == "bplus_tree" or "b_plus" in task_id or "bplus" in task_id:
            return self._generate_b_plus_tree_split(task_id, spec, seed)
        return self._generate_rb_tree(task_id, spec, seed)

    def _generate_rb_tree(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "node.py": (
                '"""Red-Black Tree node definitions."""\n\n'
                'from typing import Optional\n\n\n'
                'RED = True\n'
                'BLACK = False\n\n\n'
                'class RBNode:\n'
                '    def __init__(self, val: int, color: bool = RED):\n'
                '        self.val = val\n'
                '        self.color = color\n'
                '        self.left: Optional["RBNode"] = None\n'
                '        self.right: Optional["RBNode"] = None\n'
                '        self.parent: Optional["RBNode"] = None\n'
            ),
            "rb_tree.py": (
                '"""Red-Black Tree with insertion balancing."""\n\n'
                'from typing import List, Optional\n'
                'from node import BLACK, RED, RBNode\n\n\n'
                'class RedBlackTree:\n'
                '    def __init__(self):\n'
                '        self.root: Optional[RBNode] = None\n\n'
                '    def insert(self, val: int) -> None:\n'
                '        new_node = RBNode(val, color=RED)\n'
                '        if not self.root:\n'
                '            new_node.color = BLACK\n'
                '            self.root = new_node\n'
                '            return\n\n'
                '        curr = self.root\n'
                '        parent = None\n'
                '        while curr:\n'
                '            parent = curr\n'
                '            if val < curr.val:\n'
                '                curr = curr.left\n'
                '            else:\n'
                '                curr = curr.right\n\n'
                '        new_node.parent = parent\n'
                '        if val < parent.val:\n'
                '            parent.left = new_node\n'
                '        else:\n'
                '            parent.right = new_node\n\n'
                '        self._fixup_insertion(new_node)\n\n'
                '    def _rotate_left(self, x: RBNode) -> None:\n'
                '        y = x.right\n'
                '        assert y is not None\n'
                '        x.right = y.left\n'
                '        if y.left:\n'
                '            y.left.parent = x\n'
                '        y.parent = x.parent\n'
                '        if not x.parent:\n'
                '            self.root = y\n'
                '        elif x == x.parent.left:\n'
                '            x.parent.left = y\n'
                '        else:\n'
                '            x.parent.right = y\n'
                '        y.left = x\n'
                '        x.parent = y\n\n'
                '    def _rotate_right(self, y: RBNode) -> None:\n'
                '        x = y.left\n'
                '        assert x is not None\n'
                '        y.left = x.right\n'
                '        if x.right:\n'
                '            x.right.parent = y\n'
                '        x.parent = y.parent\n'
                '        if not y.parent:\n'
                '            self.root = x\n'
                '        elif y == y.parent.right:\n'
                '            y.parent.right = x\n'
                '        else:\n'
                '            y.parent.left = x\n'
                '        x.right = y\n'
                '        y.parent = x\n\n'
                '    def _fixup_insertion(self, z: RBNode) -> None:\n'
                '        while z.parent and z.parent.color == RED:\n'
                '            gp = z.parent.parent\n'
                '            if not gp:\n'
                '                break\n'
                '            if z.parent == gp.left:\n'
                '                uncle = gp.right\n'
                '                if uncle and uncle.color == RED:\n'
                '                    z.parent.color = BLACK\n'
                '                    uncle.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    # BUG: Fails to advance z to gp (z = gp), leaving z at bottom level\n'
                '                    # and terminating loop prematurely without checking grandparent color violations!\n'
                '                    break\n'
                '                else:\n'
                '                    if z == z.parent.right:\n'
                '                        z = z.parent\n'
                '                        self._rotate_left(z)\n'
                '                    z.parent.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    self._rotate_right(gp)\n'
                '            else:\n'
                '                uncle = gp.left\n'
                '                if uncle and uncle.color == RED:\n'
                '                    z.parent.color = BLACK\n'
                '                    uncle.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    break\n'
                '                else:\n'
                '                    if z == z.parent.left:\n'
                '                        z = z.parent\n'
                '                        self._rotate_right(z)\n'
                '                    z.parent.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    self._rotate_left(gp)\n'
                '        if self.root:\n'
                '            self.root.color = BLACK\n'
            ),
            "visualizer.py": (
                '"""Inorder and level order verification helper."""\n\n'
                'from typing import List\n'
                'from node import BLACK, RED, RBNode\n'
                'from rb_tree import RedBlackTree\n\n\n'
                'class RBValidator:\n'
                '    @staticmethod\n'
                '    def validate_invariants(tree: RedBlackTree) -> bool:\n'
                '        if not tree.root:\n'
                '            return True\n'
                '        if tree.root.color != BLACK:\n'
                '            return False\n\n'
                '        def check_node(node: RBNode) -> tuple[bool, int]:\n'
                '            if not node:\n'
                '                return True, 1\n'
                '            # No two consecutive RED nodes\n'
                '            if node.color == RED:\n'
                '                if node.left and node.left.color == RED:\n'
                '                    return False, 0\n'
                '                if node.right and node.right.color == RED:\n'
                '                    return False, 0\n'
                '            ok_l, bh_l = check_node(node.left)\n'
                '            ok_r, bh_r = check_node(node.right)\n'
                '            if not ok_l or not ok_r or bh_l != bh_r:\n'
                '                return False, 0\n'
                '            return True, bh_l + (1 if node.color == BLACK else 0)\n\n'
                '        valid, _ = check_node(tree.root)\n'
                '        return valid\n'
            ),
        }

        reference_fix = {
            "rb_tree.py": (
                '"""Red-Black Tree with insertion balancing."""\n\n'
                'from typing import List, Optional\n'
                'from node import BLACK, RED, RBNode\n\n\n'
                'class RedBlackTree:\n'
                '    def __init__(self):\n'
                '        self.root: Optional[RBNode] = None\n\n'
                '    def insert(self, val: int) -> None:\n'
                '        new_node = RBNode(val, color=RED)\n'
                '        if not self.root:\n'
                '            new_node.color = BLACK\n'
                '            self.root = new_node\n'
                '            return\n\n'
                '        curr = self.root\n'
                '        parent = None\n'
                '        while curr:\n'
                '            parent = curr\n'
                '            if val < curr.val:\n'
                '                curr = curr.left\n'
                '            else:\n'
                '                curr = curr.right\n\n'
                '        new_node.parent = parent\n'
                '        if val < parent.val:\n'
                '            parent.left = new_node\n'
                '        else:\n'
                '            parent.right = new_node\n\n'
                '        self._fixup_insertion(new_node)\n\n'
                '    def _rotate_left(self, x: RBNode) -> None:\n'
                '        y = x.right\n'
                '        assert y is not None\n'
                '        x.right = y.left\n'
                '        if y.left:\n'
                '            y.left.parent = x\n'
                '        y.parent = x.parent\n'
                '        if not x.parent:\n'
                '            self.root = y\n'
                '        elif x == x.parent.left:\n'
                '            x.parent.left = y\n'
                '        else:\n'
                '            x.parent.right = y\n'
                '        y.left = x\n'
                '        x.parent = y\n\n'
                '    def _rotate_right(self, y: RBNode) -> None:\n'
                '        x = y.left\n'
                '        assert x is not None\n'
                '        y.left = x.right\n'
                '        if x.right:\n'
                '            x.right.parent = y\n'
                '        x.parent = y.parent\n'
                '        if not y.parent:\n'
                '            self.root = x\n'
                '        elif y == y.parent.right:\n'
                '            y.parent.right = x\n'
                '        else:\n'
                '            y.parent.left = x\n'
                '        x.right = y\n'
                '        y.parent = x\n\n'
                '    def _fixup_insertion(self, z: RBNode) -> None:\n'
                '        while z.parent and z.parent.color == RED:\n'
                '            gp = z.parent.parent\n'
                '            if not gp:\n'
                '                break\n'
                '            if z.parent == gp.left:\n'
                '                uncle = gp.right\n'
                '                if uncle and uncle.color == RED:\n'
                '                    z.parent.color = BLACK\n'
                '                    uncle.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    z = gp\n'
                '                else:\n'
                '                    if z == z.parent.right:\n'
                '                        z = z.parent\n'
                '                        self._rotate_left(z)\n'
                '                    z.parent.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    self._rotate_right(gp)\n'
                '            else:\n'
                '                uncle = gp.left\n'
                '                if uncle and uncle.color == RED:\n'
                '                    z.parent.color = BLACK\n'
                '                    uncle.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    z = gp\n'
                '                else:\n'
                '                    if z == z.parent.left:\n'
                '                        z = z.parent\n'
                '                        self._rotate_right(z)\n'
                '                    z.parent.color = BLACK\n'
                '                    gp.color = RED\n'
                '                    self._rotate_left(gp)\n'
                '        if self.root:\n'
                '            self.root.color = BLACK\n'
            )
        }

        tests = {
            "test_rb_tree.py": (
                'from rb_tree import RedBlackTree\n'
                'from visualizer import RBValidator\n\n\n'
                'def test_root_insertion_is_black():\n'
                '    tree = RedBlackTree()\n'
                '    tree.insert(10)\n'
                '    assert tree.root is not None\n'
                '    assert RBValidator.validate_invariants(tree) is True\n\n\n'
                'def test_simple_rotations():\n'
                '    tree = RedBlackTree()\n'
                '    for val in [10, 20, 30]:\n'
                '        tree.insert(val)\n'
                '    assert RBValidator.validate_invariants(tree) is True\n'
                '    assert tree.root.val == 20\n\n\n'
                'def test_uncle_recoloring_cascading_propagation():\n'
                '    tree = RedBlackTree()\n'
                '    # Sequence triggering cascading uncle recoloring and rotation at root\n'
                '    for val in [50, 20, 80, 10, 30, 5, 25]:\n'
                '        tree.insert(val)\n'
                '        assert RBValidator.validate_invariants(tree) is True\n\n\n'
                'def test_large_sequential_inserts():\n'
                '    tree = RedBlackTree()\n'
                '    for i in range(1, 25):\n'
                '        tree.insert(i)\n'
                '    assert RBValidator.validate_invariants(tree) is True\n\n\n'
                'def test_inorder_binary_search_invariant():\n'
                '    tree = RedBlackTree()\n'
                '    values = [15, 8, 24, 4, 11, 19, 30, 2, 7]\n'
                '    for v in values:\n'
                '        tree.insert(v)\n'
                '    inorder: list[int] = []\n'
                '    def traverse(node):\n'
                '        if not node: return\n'
                '        traverse(node.left)\n'
                '        inorder.append(node.val)\n'
                '        traverse(node.right)\n'
                '    traverse(tree.root)\n'
                '    assert inorder == sorted(values)\n'
                '    assert RBValidator.validate_invariants(tree) is True\n\n\n'
                'def test_reverse_ordered_inserts():\n'
                '    tree = RedBlackTree()\n'
                '    for i in range(20, 0, -1):\n'
                '        tree.insert(i)\n'
                '    assert RBValidator.validate_invariants(tree) is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "rb_tree_uncle_recoloring_propagation_omission",
            "categories": ["C", "B"],
            "description": "Red-Black Tree insertion balancing terminates recoloring loop early without updating z to grandparent, violating RB invariants.",
            "spec_notes": "RedBlackTree._fixup_insertion must advance z = gp when recoloring red uncle nodes.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "data-structures",
            },
        }

    def _generate_min_heap_decrease_key(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "heap.py": (
                '"""Indexed min heap implementation."""\n\n'
                'from typing import Any, Dict, List, Optional, Tuple\n\n\n'
                'class IndexedMinHeap:\n'
                '    def __init__(self):\n'
                '        self.heap: List[Tuple[float, str, Any]] = []  # (priority, item_id, payload)\n'
                '        self.pos_map: Dict[str, int] = {}\n\n'
                '    def push(self, item_id: str, priority: float, payload: Any = None) -> None:\n'
                '        idx = len(self.heap)\n'
                '        self.heap.append((priority, item_id, payload))\n'
                '        self.pos_map[item_id] = idx\n'
                '        self._sift_up(idx)\n\n'
                '    def decrease_key(self, item_id: str, new_priority: float) -> bool:\n'
                '        if item_id not in self.pos_map:\n'
                '            return False\n'
                '        idx = self.pos_map[item_id]\n'
                '        curr_priority, _, payload = self.heap[idx]\n'
                '        if new_priority >= curr_priority:\n'
                '            return False\n'
                '        self.heap[idx] = (new_priority, item_id, payload)\n'
                '        self._sift_up(idx)\n'
                '        return True\n\n'
                '    def pop_min(self) -> Optional[Tuple[float, str, Any]]:\n'
                '        if not self.heap:\n'
                '            return None\n'
                '        min_item = self.heap[0]\n'
                '        del self.pos_map[min_item[1]]\n'
                '        last_item = self.heap.pop()\n'
                '        if self.heap:\n'
                '            self.heap[0] = last_item\n'
                '            self.pos_map[last_item[1]] = 0\n'
                '            self._sift_down(0)\n'
                '        return min_item\n\n'
                '    def _sift_up(self, idx: int) -> None:\n'
                '        while idx > 0:\n'
                '            parent = (idx - 1) // 2\n'
                '            if self.heap[idx][0] < self.heap[parent][0]:\n'
                '                # Swap elements\n'
                '                self.heap[idx], self.heap[parent] = self.heap[parent], self.heap[idx]\n'
                '                # BUG: Fails to update pos_map during sift-up swaps, desynchronizing item positions!\n'
                '                idx = parent\n'
                '            else:\n'
                '                break\n\n'
                '    def _sift_down(self, idx: int) -> None:\n'
                '        n = len(self.heap)\n'
                '        while 2 * idx + 1 < n:\n'
                '            left = 2 * idx + 1\n'
                '            right = 2 * idx + 2\n'
                '            smallest = left\n'
                '            if right < n and self.heap[right][0] < self.heap[left][0]:\n'
                '                smallest = right\n'
                '            if self.heap[smallest][0] < self.heap[idx][0]:\n'
                '                self.pos_map[self.heap[idx][1]] = smallest\n'
                '                self.pos_map[self.heap[smallest][1]] = idx\n'
                '                self.heap[idx], self.heap[smallest] = self.heap[smallest], self.heap[idx]\n'
                '                idx = smallest\n'
                '            else:\n'
                '                break\n'
            ),
            "priority_queue.py": (
                '"""Task priority scheduler wrapping indexed min-heap."""\n\n'
                'from typing import Any, Optional\n'
                'from heap import IndexedMinHeap\n\n\n'
                'class TaskScheduler:\n'
                '    def __init__(self):\n'
                '        self.heap = IndexedMinHeap()\n\n'
                '    def schedule_task(self, task_id: str, priority_score: float, task_name: str) -> None:\n'
                '        self.heap.push(task_id, priority_score, task_name)\n\n'
                '    def reprioritize(self, task_id: str, higher_urgency_score: float) -> bool:\n'
                '        return self.heap.decrease_key(task_id, higher_urgency_score)\n\n'
                '    def pop_next_task(self) -> Optional[tuple[str, str]]:\n'
                '        res = self.heap.pop_min()\n'
                '        if res:\n'
                '            _, task_id, task_name = res\n'
                '            return task_id, task_name\n'
                '        return None\n'
            ),
        }

        reference_fix = {
            "heap.py": (
                '"""Indexed min heap implementation."""\n\n'
                'from typing import Any, Dict, List, Optional, Tuple\n\n\n'
                'class IndexedMinHeap:\n'
                '    def __init__(self):\n'
                '        self.heap: List[Tuple[float, str, Any]] = []\n'
                '        self.pos_map: Dict[str, int] = {}\n\n'
                '    def push(self, item_id: str, priority: float, payload: Any = None) -> None:\n'
                '        idx = len(self.heap)\n'
                '        self.heap.append((priority, item_id, payload))\n'
                '        self.pos_map[item_id] = idx\n'
                '        self._sift_up(idx)\n\n'
                '    def decrease_key(self, item_id: str, new_priority: float) -> bool:\n'
                '        if item_id not in self.pos_map:\n'
                '            return False\n'
                '        idx = self.pos_map[item_id]\n'
                '        curr_priority, _, payload = self.heap[idx]\n'
                '        if new_priority >= curr_priority:\n'
                '            return False\n'
                '        self.heap[idx] = (new_priority, item_id, payload)\n'
                '        self._sift_up(idx)\n'
                '        return True\n\n'
                '    def pop_min(self) -> Optional[Tuple[float, str, Any]]:\n'
                '        if not self.heap:\n'
                '            return None\n'
                '        min_item = self.heap[0]\n'
                '        del self.pos_map[min_item[1]]\n'
                '        last_item = self.heap.pop()\n'
                '        if self.heap:\n'
                '            self.heap[0] = last_item\n'
                '            self.pos_map[last_item[1]] = 0\n'
                '            self._sift_down(0)\n'
                '        return min_item\n\n'
                '    def _sift_up(self, idx: int) -> None:\n'
                '        while idx > 0:\n'
                '            parent = (idx - 1) // 2\n'
                '            if self.heap[idx][0] < self.heap[parent][0]:\n'
                '                self.pos_map[self.heap[idx][1]] = parent\n'
                '                self.pos_map[self.heap[parent][1]] = idx\n'
                '                self.heap[idx], self.heap[parent] = self.heap[parent], self.heap[idx]\n'
                '                idx = parent\n'
                '            else:\n'
                '                break\n\n'
                '    def _sift_down(self, idx: int) -> None:\n'
                '        n = len(self.heap)\n'
                '        while 2 * idx + 1 < n:\n'
                '            left = 2 * idx + 1\n'
                '            right = 2 * idx + 2\n'
                '            smallest = left\n'
                '            if right < n and self.heap[right][0] < self.heap[left][0]:\n'
                '                smallest = right\n'
                '            if self.heap[smallest][0] < self.heap[idx][0]:\n'
                '                self.pos_map[self.heap[idx][1]] = smallest\n'
                '                self.pos_map[self.heap[smallest][1]] = idx\n'
                '                self.heap[idx], self.heap[smallest] = self.heap[smallest], self.heap[idx]\n'
                '                idx = smallest\n'
                '            else:\n'
                '                break\n'
            )
        }

        tests = {
            "test_indexed_heap.py": (
                'from priority_queue import TaskScheduler\n\n\n'
                'def test_standard_push_pop_ordering():\n'
                '    sched = TaskScheduler()\n'
                '    sched.schedule_task("t1", 50.0, "clean")\n'
                '    sched.schedule_task("t2", 10.0, "deploy")\n'
                '    sched.schedule_task("t3", 30.0, "build")\n'
                '    assert sched.pop_next_task() == ("t2", "deploy")\n'
                '    assert sched.pop_next_task() == ("t3", "build")\n'
                '    assert sched.pop_next_task() == ("t1", "clean")\n\n\n'
                'def test_decrease_key_promotes_task():\n'
                '    sched = TaskScheduler()\n'
                '    sched.schedule_task("t_low", 100.0, "backup")\n'
                '    sched.schedule_task("t_med", 50.0, "audit")\n'
                '    sched.schedule_task("t_other", 75.0, "log")\n'
                '    # Boost t_low priority from 100 to 5.0 (highest priority)\n'
                '    res = sched.reprioritize("t_low", 5.0)\n'
                '    assert res is True\n'
                '    # Must now be popped first\n'
                '    assert sched.pop_next_task() == ("t_low", "backup")\n'
                '    assert sched.pop_next_task() == ("t_med", "audit")\n\n\n'
                'def test_multiple_consecutive_reprioritizations():\n'
                '    sched = TaskScheduler()\n'
                '    sched.schedule_task("a", 100, "task_a")\n'
                '    sched.schedule_task("b", 200, "task_b")\n'
                '    sched.schedule_task("c", 300, "task_c")\n'
                '    sched.schedule_task("d", 400, "task_d")\n'
                '    sched.reprioritize("c", 50)\n'
                '    sched.reprioritize("d", 10)\n'
                '    sched.reprioritize("b", 5)\n'
                '    assert sched.pop_next_task() == ("b", "task_b")\n'
                '    assert sched.pop_next_task() == ("d", "task_d")\n'
                '    assert sched.pop_next_task() == ("c", "task_c")\n'
                '    assert sched.pop_next_task() == ("a", "task_a")\n\n\n'
                'def test_decrease_key_invalid_inputs():\n'
                '    sched = TaskScheduler()\n'
                '    sched.schedule_task("x", 20.0, "task_x")\n'
                '    assert sched.reprioritize("x", 30.0) is False  # Cannot increase key\n'
                '    assert sched.reprioritize("missing", 5.0) is False\n\n\n'
                'def test_empty_scheduler():\n'
                '    sched = TaskScheduler()\n'
                '    assert sched.pop_next_task() is None\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "indexed_heap_pos_map_siftup_desync",
            "categories": ["C", "B"],
            "description": "Indexed min heap fails to update internal position map during sift-up swaps, corrupting subsequent decrease-key operations.",
            "spec_notes": "IndexedMinHeap._sift_up must maintain pos_map entries whenever items swap slots.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "data-structures",
            },
        }

    def _generate_trie_pruning(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "trie_node.py": (
                '"""Trie node definition."""\n\n'
                'from typing import Dict\n\n\n'
                'class TrieNode:\n'
                '    def __init__(self):\n'
                '        self.children: Dict[str, "TrieNode"] = {}\n'
                '        self.is_terminal: bool = False\n'
            ),
            "trie.py": (
                '"""Prefix Trie with insertion and node pruning deletion."""\n\n'
                'from typing import List, Optional\n'
                'from trie_node import TrieNode\n\n\n'
                'class PrefixTrie:\n'
                '    def __init__(self):\n'
                '        self.root = TrieNode()\n\n'
                '    def insert(self, word: str) -> None:\n'
                '        curr = self.root\n'
                '        for ch in word:\n'
                '            if ch not in curr.children:\n'
                '                curr.children[ch] = TrieNode()\n'
                '            curr = curr.children[ch]\n'
                '        curr.is_terminal = True\n\n'
                '    def search(self, word: str) -> bool:\n'
                '        curr = self.root\n'
                '        for ch in word:\n'
                '            if ch not in curr.children:\n'
                '                return False\n'
                '            curr = curr.children[ch]\n'
                '        return curr.is_terminal\n\n'
                '    def delete(self, word: str) -> bool:\n'
                '        # BUG: Only unsets is_terminal flag at the leaf without recursive dead-branch child pruning\n'
                '        curr = self.root\n'
                '        for ch in word:\n'
                '            if ch not in curr.children:\n'
                '                return False\n'
                '            curr = curr.children[ch]\n'
                '        if not curr.is_terminal:\n'
                '            return False\n'
                '        curr.is_terminal = False\n'
                '        return True\n\n'
                '    def has_prefix(self, prefix: str) -> bool:\n'
                '        curr = self.root\n'
                '        for ch in prefix:\n'
                '            if ch not in curr.children:\n'
                '                return False\n'
                '            curr = curr.children[ch]\n'
                '        return True\n'
            ),
            "autocomplete.py": (
                '"""Autocomplete search index."""\n\n'
                'from typing import List\n'
                'from trie import PrefixTrie\n\n\n'
                'class AutocompleteIndex:\n'
                '    def __init__(self):\n'
                '        self.trie = PrefixTrie()\n\n'
                '    def add_keyword(self, kw: str) -> None:\n'
                '        self.trie.insert(kw)\n\n'
                '    def remove_keyword(self, kw: str) -> bool:\n'
                '        return self.trie.delete(kw)\n\n'
                '    def suggest_prefix_exists(self, prefix: str) -> bool:\n'
                '        return self.trie.has_prefix(prefix)\n'
            ),
        }

        reference_fix = {
            "trie.py": (
                '"""Prefix Trie with insertion and node pruning deletion."""\n\n'
                'from typing import List, Optional\n'
                'from trie_node import TrieNode\n\n\n'
                'class PrefixTrie:\n'
                '    def __init__(self):\n'
                '        self.root = TrieNode()\n\n'
                '    def insert(self, word: str) -> None:\n'
                '        curr = self.root\n'
                '        for ch in word:\n'
                '            if ch not in curr.children:\n'
                '                curr.children[ch] = TrieNode()\n'
                '            curr = curr.children[ch]\n'
                '        curr.is_terminal = True\n\n'
                '    def search(self, word: str) -> bool:\n'
                '        curr = self.root\n'
                '        for ch in word:\n'
                '            if ch not in curr.children:\n'
                '                return False\n'
                '            curr = curr.children[ch]\n'
                '        return curr.is_terminal\n\n'
                '    def delete(self, word: str) -> bool:\n'
                '        def _delete_helper(node: TrieNode, idx: int) -> bool:\n'
                '            if idx == len(word):\n'
                '                if not node.is_terminal:\n'
                '                    return False\n'
                '                node.is_terminal = False\n'
                '                return len(node.children) == 0\n\n'
                '            ch = word[idx]\n'
                '            if ch not in node.children:\n'
                '                return False\n'
                '            should_delete_child = _delete_helper(node.children[ch], idx + 1)\n'
                '            if should_delete_child:\n'
                '                del node.children[ch]\n'
                '                return len(node.children) == 0 and not node.is_terminal\n'
                '            return False\n\n'
                '        if not self.search(word):\n'
                '            return False\n'
                '        _delete_helper(self.root, 0)\n'
                '        return True\n\n'
                '    def has_prefix(self, prefix: str) -> bool:\n'
                '        curr = self.root\n'
                '        for ch in prefix:\n'
                '            if ch not in curr.children:\n'
                '                return False\n'
                '            curr = curr.children[ch]\n'
                '        return True\n'
            )
        }

        tests = {
            "test_trie_pruning.py": (
                'from autocomplete import AutocompleteIndex\n\n\n'
                'def test_insert_and_search():\n'
                '    idx = AutocompleteIndex()\n'
                '    idx.add_keyword("apple")\n'
                '    assert idx.trie.search("apple") is True\n'
                '    assert idx.trie.search("app") is False\n'
                '    assert idx.suggest_prefix_exists("app") is True\n\n\n'
                'def test_delete_prunes_isolated_branch_prefix():\n'
                '    idx = AutocompleteIndex()\n'
                '    idx.add_keyword("banana")\n'
                '    assert idx.suggest_prefix_exists("ban") is True\n'
                '    res = idx.remove_keyword("banana")\n'
                '    assert res is True\n'
                '    assert idx.trie.search("banana") is False\n'
                '    # Since "banana" was the only word with prefix "ban", the branch must be pruned!\n'
                '    assert idx.suggest_prefix_exists("ban") is False\n'
                '    assert idx.suggest_prefix_exists("b") is False\n\n\n'
                'def test_delete_shared_prefix_preserves_sibling():\n'
                '    idx = AutocompleteIndex()\n'
                '    idx.add_keyword("cat")\n'
                '    idx.add_keyword("caterpillar")\n'
                '    idx.remove_keyword("cat")\n'
                '    assert idx.trie.search("cat") is False\n'
                '    assert idx.trie.search("caterpillar") is True\n'
                '    assert idx.suggest_prefix_exists("cat") is True\n\n\n'
                'def test_delete_nonexistent_word():\n'
                '    idx = AutocompleteIndex()\n'
                '    idx.add_keyword("dog")\n'
                '    assert idx.remove_keyword("ghost") is False\n'
                '    assert idx.remove_keyword("do") is False\n\n\n'
                'def test_multiple_insertions_and_complete_clearing():\n'
                '    idx = AutocompleteIndex()\n'
                '    for w in ["he", "she", "his", "hers"]:\n'
                '        idx.add_keyword(w)\n'
                '    idx.remove_keyword("he")\n'
                '    assert idx.trie.search("he") is False\n'
                '    assert idx.suggest_prefix_exists("he") is True  # "hers" still present\n'
                '    idx.remove_keyword("hers")\n'
                '    assert idx.suggest_prefix_exists("he") is False\n'
                '    assert idx.trie.search("she") is True\n\n\n'
                'def test_empty_trie_search():\n'
                '    idx = AutocompleteIndex()\n'
                '    assert idx.suggest_prefix_exists("a") is False\n'
                '    assert idx.trie.search("a") is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "trie_node_pruning_dangling_branch_leak",
            "categories": ["C", "B"],
            "description": "Prefix trie deletion only unsets terminal flags without pruning dead branch nodes, causing ghost prefix matches in autocomplete.",
            "spec_notes": "PrefixTrie.delete must recursively delete empty child nodes when branch has 0 remaining words.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "data-structures",
            },
        }

    def _generate_dsu_rank(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "dsu.py": (
                '"""Disjoint Set Union (Union-Find) with rank and path compression."""\n\n'
                'from typing import Dict, List\n\n\n'
                'class DisjointSetUnion:\n'
                '    def __init__(self, elements: List[str]):\n'
                '        self.parent: Dict[str, str] = {x: x for x in elements}\n'
                '        self.rank: Dict[str, int] = {x: 0 for x in elements}\n\n'
                '    def find(self, x: str) -> str:\n'
                '        if self.parent[x] != x:\n'
                '            self.parent[x] = self.find(self.parent[x])\n'
                '        return self.parent[x]\n\n'
                '    def union(self, x: str, y: str) -> bool:\n'
                '        root_x = self.find(x)\n'
                '        root_y = self.find(y)\n'
                '        if root_x == root_y:\n'
                '            return False\n\n'
                '        # BUG: Rank logic unconditionally increments rank of root_x\n'
                '        # even when rank[root_x] > rank[root_y] or rank[root_y] > rank[root_x]\n'
                '        if self.rank[root_x] < self.rank[root_y]:\n'
                '            self.parent[root_x] = root_y\n'
                '        elif self.rank[root_x] > self.rank[root_y]:\n'
                '            self.parent[root_y] = root_x\n'
                '        else:\n'
                '            self.parent[root_y] = root_x\n'
                '        self.rank[root_x] += 1  # BUG: Must ONLY increment when ranks were equal!\n'
                '        return True\n'
            ),
            "cluster.py": (
                '"""Network node connectivity cluster manager."""\n\n'
                'from typing import List, Set\n'
                'from dsu import DisjointSetUnion\n\n\n'
                'class ClusterManager:\n'
                '    def __init__(self, node_ids: List[str]):\n'
                '        self.dsu = DisjointSetUnion(node_ids)\n\n'
                '    def connect(self, u: str, v: str) -> bool:\n'
                '        return self.dsu.union(u, v)\n\n'
                '    def is_connected(self, u: str, v: str) -> bool:\n'
                '        return self.dsu.find(u) == self.dsu.find(v)\n\n'
                '    def get_max_rank(self) -> int:\n'
                '        return max(self.dsu.rank.values())\n'
            ),
        }

        reference_fix = {
            "dsu.py": (
                '"""Disjoint Set Union (Union-Find) with rank and path compression."""\n\n'
                'from typing import Dict, List\n\n\n'
                'class DisjointSetUnion:\n'
                '    def __init__(self, elements: List[str]):\n'
                '        self.parent: Dict[str, str] = {x: x for x in elements}\n'
                '        self.rank: Dict[str, int] = {x: 0 for x in elements}\n\n'
                '    def find(self, x: str) -> str:\n'
                '        if self.parent[x] != x:\n'
                '            self.parent[x] = self.find(self.parent[x])\n'
                '        return self.parent[x]\n\n'
                '    def union(self, x: str, y: str) -> bool:\n'
                '        root_x = self.find(x)\n'
                '        root_y = self.find(y)\n'
                '        if root_x == root_y:\n'
                '            return False\n\n'
                '        if self.rank[root_x] < self.rank[root_y]:\n'
                '            self.parent[root_x] = root_y\n'
                '        elif self.rank[root_x] > self.rank[root_y]:\n'
                '            self.parent[root_y] = root_x\n'
                '        else:\n'
                '            self.parent[root_y] = root_x\n'
                '            self.rank[root_x] += 1\n'
                '        return True\n'
            )
        }

        tests = {
            "test_dsu.py": (
                'from cluster import ClusterManager\n\n\n'
                'def test_basic_connectivity():\n'
                '    nodes = ["n1", "n2", "n3", "n4"]\n'
                '    cm = ClusterManager(nodes)\n'
                '    assert cm.is_connected("n1", "n2") is False\n'
                '    cm.connect("n1", "n2")\n'
                '    assert cm.is_connected("n1", "n2") is True\n'
                '    assert cm.is_connected("n1", "n3") is False\n\n\n'
                'def test_transitive_connectivity():\n'
                '    nodes = ["a", "b", "c", "d"]\n'
                '    cm = ClusterManager(nodes)\n'
                '    cm.connect("a", "b")\n'
                '    cm.connect("b", "c")\n'
                '    assert cm.is_connected("a", "c") is True\n'
                '    assert cm.is_connected("a", "d") is False\n\n\n'
                'def test_rank_growth_bounded():\n'
                '    nodes = [f"node_{i}" for i in range(8)]\n'
                '    cm = ClusterManager(nodes)\n'
                '    cm.connect("node_0", "node_1")\n'
                '    cm.connect("node_2", "node_3")\n'
                '    cm.connect("node_4", "node_5")\n'
                '    cm.connect("node_6", "node_7")\n'
                '    cm.connect("node_0", "node_2")\n'
                '    cm.connect("node_4", "node_6")\n'
                '    cm.connect("node_0", "node_4")\n'
                '    assert cm.get_max_rank() == 3\n\n\n'
                'def test_unequal_rank_union_does_not_increment_rank():\n'
                '    cm = ClusterManager(["a", "b", "c", "d", "e"])\n'
                '    cm.connect("a", "b")\n'
                '    cm.connect("c", "d")\n'
                '    cm.connect("a", "c")\n'
                '    cm.connect("a", "e")\n'
                '    assert cm.get_max_rank() == 2\n\n\n'
                'def test_redundant_connection_returns_false():\n'
                '    cm = ClusterManager(["x", "y"])\n'
                '    assert cm.connect("x", "y") is True\n'
                '    assert cm.connect("x", "y") is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "dsu_union_by_rank_unconditional_increment",
            "categories": ["C", "B"],
            "description": "Disjoint Set Union unconditionally increments tree rank on unequal unions, violating logarithmic tree depth bounds.",
            "spec_notes": "DisjointSetUnion.union must only increment rank[root_x] when rank[root_x] == rank[root_y].",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "data-structures",
            },
        }

    def _generate_b_plus_tree_split(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "bplus_node.py": (
                '"""B+ Tree base node definition."""\n\n'
                'from typing import Any, List, Optional\n\n\n'
                'class BPlusNode:\n'
                '    def __init__(self, is_leaf: bool = False):\n'
                '        self.is_leaf = is_leaf\n'
                '        self.keys: List[int] = []\n'
            ),
            "leaf_node.py": (
                '"""B+ Tree leaf node with sequential sibling pointer."""\n\n'
                'from typing import Any, List, Optional, Tuple\n'
                'from bplus_node import BPlusNode\n\n\n'
                'class LeafNode(BPlusNode):\n'
                '    def __init__(self, max_keys: int = 3):\n'
                '        super().__init__(is_leaf=True)\n'
                '        self.max_keys = max_keys\n'
                '        self.values: List[Any] = []\n'
                '        self.next_leaf: Optional["LeafNode"] = None\n\n'
                '    def insert(self, key: int, value: Any) -> Optional[Tuple[int, "LeafNode"]]:\n'
                '        # Insert in sorted order\n'
                '        idx = 0\n'
                '        while idx < len(self.keys) and self.keys[idx] < key:\n'
                '            idx += 1\n'
                '        if idx < len(self.keys) and self.keys[idx] == key:\n'
                '            self.values[idx] = value\n'
                '            return None\n'
                '        self.keys.insert(idx, key)\n'
                '        self.values.insert(idx, value)\n\n'
                '        if len(self.keys) > self.max_keys:\n'
                '            return self.split()\n'
                '        return None\n\n'
                '    def split(self) -> Tuple[int, "LeafNode"]:\n'
                '        mid = len(self.keys) // 2\n'
                '        right_leaf = LeafNode(self.max_keys)\n'
                '        right_leaf.keys = self.keys[mid:]\n'
                '        right_leaf.values = self.values[mid:]\n'
                '        self.keys = self.keys[:mid]\n'
                '        self.values = self.values[:mid]\n'
                '        right_leaf.next_leaf = self.next_leaf\n'
                '        self.next_leaf = right_leaf\n'
                '        # BUG: Promotes last key of right leaf instead of first key (min) of right leaf!\n'
                '        promoted_key = right_leaf.keys[-1]\n'
                '        return promoted_key, right_leaf\n'
            ),
            "internal_node.py": (
                '"""B+ Tree internal routing node."""\n\n'
                'from typing import Any, List, Optional, Tuple\n'
                'from bplus_node import BPlusNode\n'
                'from leaf_node import LeafNode\n\n\n'
                'class InternalNode(BPlusNode):\n'
                '    def __init__(self, max_keys: int = 3):\n'
                '        super().__init__(is_leaf=False)\n'
                '        self.max_keys = max_keys\n'
                '        self.children: List[BPlusNode] = []\n'
            ),
            "bplus_tree.py": (
                '"""B+ Tree container supporting insert, search, and range query."""\n\n'
                'from typing import Any, List, Optional\n'
                'from internal_node import InternalNode\n'
                'from leaf_node import LeafNode\n\n\n'
                'class BPlusTree:\n'
                '    def __init__(self, max_keys: int = 3):\n'
                '        self.max_keys = max_keys\n'
                '        self.root: LeafNode | InternalNode = LeafNode(max_keys)\n\n'
                '    def insert(self, key: int, value: Any) -> None:\n'
                '        if self.root.is_leaf:\n'
                '            assert isinstance(self.root, LeafNode)\n'
                '            split_res = self.root.insert(key, value)\n'
                '            if split_res:\n'
                '                promoted_key, right_leaf = split_res\n'
                '                new_root = InternalNode(self.max_keys)\n'
                '                new_root.keys = [promoted_key]\n'
                '                new_root.children = [self.root, right_leaf]\n'
                '                self.root = new_root\n'
                '        else:\n'
                '            assert isinstance(self.root, InternalNode)\n'
                '            # Simple 2-level insertion\n'
                '            idx = 0\n'
                '            while idx < len(self.root.keys) and key >= self.root.keys[idx]:\n'
                '                idx += 1\n'
                '            child = self.root.children[idx]\n'
                '            assert isinstance(child, LeafNode)\n'
                '            split_res = child.insert(key, value)\n'
                '            if split_res:\n'
                '                promoted_key, right_leaf = split_res\n'
                '                self.root.keys.insert(idx, promoted_key)\n'
                '                self.root.children.insert(idx + 1, right_leaf)\n\n'
                '    def search(self, key: int) -> Optional[Any]:\n'
                '        curr = self.root\n'
                '        while not curr.is_leaf:\n'
                '            assert isinstance(curr, InternalNode)\n'
                '            idx = 0\n'
                '            while idx < len(curr.keys) and key >= curr.keys[idx]:\n'
                '                idx += 1\n'
                '            curr = curr.children[idx]\n'
                '        assert isinstance(curr, LeafNode)\n'
                '        for k, v in zip(curr.keys, curr.values):\n'
                '            if k == key:\n'
                '                return v\n'
                '        return None\n\n'
                '    def range_query(self, min_key: int, max_key: int) -> List[Any]:\n'
                '        curr = self.root\n'
                '        while not curr.is_leaf:\n'
                '            assert isinstance(curr, InternalNode)\n'
                '            idx = 0\n'
                '            while idx < len(curr.keys) and min_key >= curr.keys[idx]:\n'
                '                idx += 1\n'
                '            curr = curr.children[idx]\n'
                '        assert isinstance(curr, LeafNode)\n'
                '        results = []\n'
                '        leaf: Optional[LeafNode] = curr\n'
                '        while leaf:\n'
                '            for k, v in zip(leaf.keys, leaf.values):\n'
                '                if min_key <= k <= max_key:\n'
                '                    results.append(v)\n'
                '                elif k > max_key:\n'
                '                    return results\n'
                '            leaf = leaf.next_leaf\n'
                '        return results\n'
            ),
        }

        reference_fix = {
            "leaf_node.py": (
                '"""B+ Tree leaf node with sequential sibling pointer."""\n\n'
                'from typing import Any, List, Optional, Tuple\n'
                'from bplus_node import BPlusNode\n\n\n'
                'class LeafNode(BPlusNode):\n'
                '    def __init__(self, max_keys: int = 3):\n'
                '        super().__init__(is_leaf=True)\n'
                '        self.max_keys = max_keys\n'
                '        self.values: List[Any] = []\n'
                '        self.next_leaf: Optional["LeafNode"] = None\n\n'
                '    def insert(self, key: int, value: Any) -> Optional[Tuple[int, "LeafNode"]]:\n'
                '        idx = 0\n'
                '        while idx < len(self.keys) and self.keys[idx] < key:\n'
                '            idx += 1\n'
                '        if idx < len(self.keys) and self.keys[idx] == key:\n'
                '            self.values[idx] = value\n'
                '            return None\n'
                '        self.keys.insert(idx, key)\n'
                '        self.values.insert(idx, value)\n\n'
                '        if len(self.keys) > self.max_keys:\n'
                '            return self.split()\n'
                '        return None\n\n'
                '    def split(self) -> Tuple[int, "LeafNode"]:\n'
                '        mid = len(self.keys) // 2\n'
                '        right_leaf = LeafNode(self.max_keys)\n'
                '        right_leaf.keys = self.keys[mid:]\n'
                '        right_leaf.values = self.values[mid:]\n'
                '        self.keys = self.keys[:mid]\n'
                '        self.values = self.values[:mid]\n'
                '        right_leaf.next_leaf = self.next_leaf\n'
                '        self.next_leaf = right_leaf\n'
                '        # Promoted key is first key of the new right sibling\n'
                '        promoted_key = right_leaf.keys[0]\n'
                '        return promoted_key, right_leaf\n'
            )
        }

        tests = {
            "test_bplus_tree.py": (
                'from bplus_tree import BPlusTree\n\n\n'
                'def test_leaf_insert_and_search():\n'
                '    t = BPlusTree(max_keys=3)\n'
                '    t.insert(10, "val_10")\n'
                '    t.insert(20, "val_20")\n'
                '    assert t.search(10) == "val_10"\n'
                '    assert t.search(20) == "val_20"\n'
                '    assert t.search(30) is None\n\n\n'
                'def test_split_promotes_correct_separator_key():\n'
                '    t = BPlusTree(max_keys=3)\n'
                '    # Insert 4 keys to force split on leaf with max_keys=3\n'
                '    for k in [10, 20, 30, 40]:\n'
                '        t.insert(k, f"v_{k}")\n\n'
                '    # All 4 keys must be searchable across root routing\n'
                '    assert t.search(10) == "v_10"\n'
                '    assert t.search(20) == "v_20"\n'
                '    assert t.search(30) == "v_30"\n'
                '    assert t.search(40) == "v_40"\n\n\n'
                'def test_range_query_spans_leaf_chain():\n'
                '    t = BPlusTree(max_keys=3)\n'
                '    for k in [5, 15, 25, 35, 45, 55]:\n'
                '        t.insert(k, f"val_{k}")\n'
                '    res = t.range_query(15, 45)\n'
                '    assert res == ["val_15", "val_25", "val_35", "val_45"]\n\n\n'
                'def test_sequential_insert_large():\n'
                '    t = BPlusTree(max_keys=3)\n'
                '    for i in range(1, 15):\n'
                '        t.insert(i, f"item_{i}")\n'
                '    for i in range(1, 15):\n'
                '        assert t.search(i) == f"item_{i}"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "bplus_tree_leaf_split_promoted_key_inversion",
            "categories": ["C", "I"],
            "description": "B+ Tree leaf split promotes the maximum key of the right sibling instead of the minimum key, breaking internal router search navigation.",
            "spec_notes": "LeafNode.split must promote right_leaf.keys[0] as the separator key.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "database-storage",
            },
        }

