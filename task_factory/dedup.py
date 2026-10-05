"""AST-based structural and token deduplication engine for Benchmark V2."""

from __future__ import annotations

import ast
import hashlib
import re
from typing import Any, Dict, List, Set, Tuple


class ASTNormalizer(ast.NodeTransformer):
    """Normalizes AST by standardizing variable names, function names, and removing docstrings."""

    def __init__(self):
        super().__init__()
        self.var_map: Dict[str, str] = {}
        self.counter = 0

    def _get_norm_name(self, original: str) -> str:
        if original.startswith("__") and original.endswith("__"):
            return original
        if original not in self.var_map:
            self.counter += 1
            self.var_map[original] = f"v_{self.counter}"
        return self.var_map[original]

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = self._get_norm_name(node.id)
        return self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._get_norm_name(node.arg)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Strip docstrings
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))
        ):
            node.body.pop(0)
        node.name = self._get_norm_name(node.name)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))
        ):
            node.body.pop(0)
        node.name = self._get_norm_name(node.name)
        return self.generic_visit(node)


def compute_ast_fingerprint(code: str) -> str:
    """Parses code into AST, normalizes identifiers and docstrings, and produces SHA256 structural hash."""
    try:
        tree = ast.parse(code)
        normalizer = ASTNormalizer()
        norm_tree = normalizer.visit(tree)
        ast.fix_missing_locations(norm_tree)
        dumped = ast.dump(norm_tree, annotate_fields=False, include_attributes=False)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()
    except Exception:
        tokens = re.findall(r"\b\w+\b", code)
        return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()


def extract_code_ngrams(code: str, n: int = 3) -> Set[Tuple[str, ...]]:
    """Extracts word/symbol n-grams from code string."""
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[^\s\w]", code)
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def compute_token_jaccard(code_a: str, code_b: str, n: int = 3) -> float:
    """Computes Jaccard similarity over n-gram token sets."""
    ngrams_a = extract_code_ngrams(code_a, n=n)
    ngrams_b = extract_code_ngrams(code_b, n=n)
    if not ngrams_a or not ngrams_b:
        return 0.0
    intersection = ngrams_a.intersection(ngrams_b)
    union = ngrams_a.union(ngrams_b)
    return len(intersection) / len(union)


class DuplicateDetector:
    """Analyzes benchmark task collections for structural or syntactic duplicates."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def compute_similarity(self, task_a: Dict[str, Any], task_b: Dict[str, Any]) -> float:
        """Computes comprehensive structural similarity score (0.0 to 1.0) between two tasks."""
        files_a = task_a.get("repo_files", {})
        files_b = task_b.get("repo_files", {})
        repo_a = "".join(files_a[k] for k in sorted(files_a.keys()))
        repo_b = "".join(files_b[k] for k in sorted(files_b.keys()))
        ast_hash_a = compute_ast_fingerprint(repo_a)
        ast_hash_b = compute_ast_fingerprint(repo_b)

        if ast_hash_a == ast_hash_b and repo_a and repo_b:
            return 1.0

        token_sim = compute_token_jaccard(repo_a, repo_b, n=3)
        bug_type_match = (
            1.0 if task_a.get("bug_type") == task_b.get("bug_type") and task_a.get("bug_type") else 0.0
        )

        similarity = (0.75 * token_sim) + (0.25 * bug_type_match)
        return round(min(1.0, similarity), 3)

    def find_duplicates(self, tasks: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
        """Scans task list and returns pairs exceeding the similarity threshold."""
        duplicates: List[Tuple[str, str, float]] = []
        n = len(tasks)
        for i in range(n):
            for j in range(i + 1, n):
                tid_a = tasks[i].get("task_id", f"task_{i}")
                tid_b = tasks[j].get("task_id", f"task_{j}")
                sim = self.compute_similarity(tasks[i], tasks[j])
                if sim >= self.threshold:
                    duplicates.append((tid_a, tid_b, sim))
        return duplicates
