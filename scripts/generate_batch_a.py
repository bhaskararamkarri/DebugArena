"""Generates, validates, and persists Batch A (Tasks v29-v42)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console
from rich.table import Table
from task_factory.generator import TaskGenerator

console = Console()

BATCH_A_SPECS: List[Dict[str, Any]] = [
    {"task_id": "v29_datetime_timezone_normalization", "category": "A", "sub_type": "timezone", "difficulty": "easy", "domain": "datetime"},
    {"task_id": "v30_semver_comparator_precedence", "category": "A", "sub_type": "semver", "difficulty": "easy", "domain": "packaging"},
    {"task_id": "v31_binary_search_rotated_pivot", "category": "A", "sub_type": "rotated_search", "difficulty": "easy", "domain": "algorithms"},
    {"task_id": "v32_red_black_tree_color_inversion", "category": "C", "sub_type": "rb_tree", "difficulty": "medium", "domain": "data-structures"},
    {"task_id": "v33_min_heap_decrease_key_bubble", "category": "C", "sub_type": "min_heap", "difficulty": "medium", "domain": "data-structures"},
    {"task_id": "v34_trie_prefix_deletion_prune", "category": "C", "sub_type": "trie", "difficulty": "medium", "domain": "data-structures"},
    {"task_id": "v35_disjoint_set_union_rank", "category": "C", "sub_type": "dsu", "difficulty": "medium", "domain": "data-structures"},
    {"task_id": "v36_db_transaction_isolation_savepoint", "category": "I", "sub_type": "savepoint", "difficulty": "hard", "domain": "database"},
    {"task_id": "v37_connection_pool_leak_on_timeout", "category": "I", "sub_type": "connection_pool", "difficulty": "hard", "domain": "database"},
    {"task_id": "v38_optimistic_locking_version_check", "category": "I", "sub_type": "optimistic_locking", "difficulty": "hard", "domain": "database"},
    {"task_id": "v39_wal_replay_checkpoint_recovery", "category": "I", "sub_type": "wal_recovery", "difficulty": "hard", "domain": "database"},
    {"task_id": "v40_layered_feature_flag_evaluator", "category": "J", "sub_type": "feature_flags", "difficulty": "medium", "domain": "configuration"},
    {"task_id": "v41_circular_buffer_overwrite_overflow", "category": "K", "sub_type": "circular_buffer", "difficulty": "medium", "domain": "performance"},
    {"task_id": "v42_ssrf_url_whitelist_validator", "category": "L", "sub_type": "ssrf", "difficulty": "hard", "domain": "security"},
]


def load_existing_corpus() -> List[Dict[str, Any]]:
    corpus = []
    tasks_dir = REPO_ROOT / "tasks"
    for p in tasks_dir.rglob("task.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                corpus.append(json.load(f))
        except Exception:
            pass
    return corpus


def main():
    console.print("[bold cyan]Starting TaskGenerator synthesis for Batch A (Coverage Expansion: v29-v42)...[/bold cyan]")
    generator = TaskGenerator(sandbox_mode="local", repetitions=3, min_quality=3.5, duplicate_threshold=0.85)
    existing_corpus = load_existing_corpus()
    console.print(f"Loaded {len(existing_corpus)} existing baseline tasks for deduplication protection.")

    table = Table(title="Benchmark V2 Batch A Synthesis & Verification")
    table.add_column("Task ID", style="cyan")
    table.add_column("Cat", style="magenta")
    table.add_column("Diff", style="yellow")
    table.add_column("Files", justify="right")
    table.add_column("Fix Files", justify="right")
    table.add_column("Tests", justify="right")
    table.add_column("Quality", justify="right", style="green")
    table.add_column("Status", style="bold")

    results = []
    all_approved = True

    for spec in BATCH_A_SPECS:
        tid = spec["task_id"]
        schema_obj, report, candidate = generator.generate_and_validate(
            spec=spec,
            seed=42,
            existing_tasks=existing_corpus,
        )

        file_count = len(candidate.get("repo_files", {}))
        fix_files = len(candidate.get("reference_fix", {}))
        test_func_count = sum(
            c.count("def test_") or c.count("def test")
            for c in candidate.get("tests", {}).values()
        )
        avg_quality = report.quality.average_score

        if schema_obj and report.is_valid:
            generator.save_task(candidate, target_base_dir=str(REPO_ROOT / "tasks" / "v2"))
            existing_corpus.append(candidate)
            status = "[green]APPROVED & SAVED[/green]"
            results.append({
                "task_id": tid,
                "approved": True,
                "report": report.to_dict(),
                "metrics": {
                    "file_count": file_count,
                    "fix_files": fix_files,
                    "test_count": test_func_count,
                    "loc": sum(len(c.splitlines()) for c in candidate["repo_files"].values()),
                    "quality_score": avg_quality,
                }
            })
        else:
            all_approved = False
            status = f"[red]REJECTED ({', '.join(report.errors)})[/red]"
            results.append({
                "task_id": tid,
                "approved": False,
                "report": report.to_dict(),
                "metrics": {
                    "file_count": file_count,
                    "fix_files": fix_files,
                    "test_count": test_func_count,
                    "loc": sum(len(c.splitlines()) for c in candidate["repo_files"].values()),
                    "quality_score": avg_quality,
                }
            })

        table.add_row(
            tid,
            spec["category"],
            spec["difficulty"],
            str(file_count),
            str(fix_files),
            f"{test_func_count} funcs",
            f"{avg_quality:.2f}",
            status,
        )

    console.print(table)

    summary_path = REPO_ROOT / "batch_a_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]Batch A complete. Detailed results saved to {summary_path}[/bold green]")
    if not all_approved:
        sys.exit(1)


if __name__ == "__main__":
    main()
