"""Generates, validates, and persists the 14 Benchmark V2 pilot tasks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console
from rich.table import Table
from task_factory.generator import TaskGenerator

console = Console()

PILOT_SPECS: List[Dict[str, Any]] = [
    {
        "task_id": "v15_hierarchical_config_precedence",
        "category": "J",
        "sub_type": "precedence",
        "difficulty": "medium",
        "domain": "infrastructure",
    },
    {
        "task_id": "v16_env_interpolation_deep_merge",
        "category": "J",
        "sub_type": "deep_merge",
        "difficulty": "hard",
        "domain": "infrastructure",
    },
    {
        "task_id": "v17_memory_leak_bounded_cache",
        "category": "K",
        "sub_type": "cache_leak",
        "difficulty": "medium",
        "domain": "performance",
    },
    {
        "task_id": "v18_quadratic_event_dedup_pipeline",
        "category": "K",
        "sub_type": "quadratic_pipeline",
        "difficulty": "hard",
        "domain": "performance",
    },
    {
        "task_id": "v19_path_traversal_sanitizer",
        "category": "L",
        "sub_type": "path_traversal",
        "difficulty": "hard",
        "domain": "security",
    },
    {
        "task_id": "v20_payload_boundary_validator",
        "category": "L",
        "sub_type": "payload_boundary",
        "difficulty": "medium",
        "domain": "security",
    },
    {
        "task_id": "v21_misleading_retry_budget",
        "category": "M",
        "sub_type": "misleading_docstring",
        "difficulty": "adversarial",
        "domain": "networking",
    },
    {
        "task_id": "v22_distractor_middleware_auth",
        "category": "M",
        "sub_type": "distractor_module",
        "difficulty": "adversarial",
        "domain": "security",
    },
    {
        "task_id": "v23_deceptive_boundary_invariant",
        "category": "M",
        "sub_type": "boundary_invariant",
        "difficulty": "adversarial",
        "domain": "metrics",
    },
    {
        "task_id": "v24_order_processing_saga_rollback",
        "category": "D",
        "sub_type": "saga",
        "difficulty": "hard",
        "domain": "e-commerce",
    },
    {
        "task_id": "v25_service_data_contract_propagation",
        "category": "E",
        "sub_type": "contract",
        "difficulty": "hard",
        "domain": "service-architecture",
    },
    {
        "task_id": "v26_async_task_executor_cancellation",
        "category": "G",
        "sub_type": "concurrency",
        "difficulty": "hard",
        "domain": "concurrency",
    },
    {
        "task_id": "v27_cursor_time_pagination_drift",
        "category": "H",
        "sub_type": "pagination",
        "difficulty": "medium",
        "domain": "api-backend",
    },
    {
        "task_id": "v28_streaming_csv_escaped_state",
        "category": "F",
        "sub_type": "csv_parsing",
        "difficulty": "medium",
        "domain": "parsing",
    },
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
    console.print("[bold cyan]Starting TaskGenerator synthesis for 14 Benchmark V2 pilot tasks...[/bold cyan]")
    generator = TaskGenerator(sandbox_mode="local", repetitions=3, min_quality=3.5, duplicate_threshold=0.85)
    existing_corpus = load_existing_corpus()
    console.print(f"Loaded {len(existing_corpus)} existing baseline tasks for deduplication protection.")

    table = Table(title="Benchmark V2 TaskGenerator Pilot Synthesis & Verification")
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

    for spec in PILOT_SPECS:
        tid = spec["task_id"]
        schema_obj, report, candidate = generator.generate_and_validate(
            spec=spec,
            seed=42,
            existing_tasks=existing_corpus,
        )

        file_count = len(candidate.get("repo_files", {}))
        fix_files = len(candidate.get("reference_fix", {}))
        test_count = len(candidate.get("tests", {}))
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

    # Save summary report
    summary_path = REPO_ROOT / "task_factory_pilot_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]Generator pilot complete. Detailed results saved to {summary_path}[/bold green]")
    if not all_approved:
        sys.exit(1)


if __name__ == "__main__":
    main()
