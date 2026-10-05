"""Generates, validates, and persists Batch B (Repository Complexity: Tasks v43-v56)."""

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

BATCH_B_SPECS: List[Dict[str, Any]] = [
    {"task_id": "v43_saga_distributed_orchestrator", "category": "E", "sub_type": "saga", "difficulty": "hard", "domain": "distributed-systems"},
    {"task_id": "v44_event_sourcing_aggregate_rehydrate", "category": "E", "sub_type": "event_sourcing", "difficulty": "hard", "domain": "distributed-systems"},
    {"task_id": "v45_schema_evolution_field_migrator", "category": "J", "sub_type": "schema_evolution", "difficulty": "hard", "domain": "schema-evolution"},
    {"task_id": "v46_cache_coherence_mesi_state_machine", "category": "G", "sub_type": "cache_coherence", "difficulty": "hard", "domain": "concurrency"},
    {"task_id": "v47_graphql_dataloader_batch_dedup", "category": "H", "sub_type": "dataloader", "difficulty": "hard", "domain": "api-backend"},
    {"task_id": "v48_channel_backpressure_buffer_deadlock", "category": "G", "sub_type": "channel_backpressure", "difficulty": "hard", "domain": "concurrency"},
    {"task_id": "v49_database_migration_dependency_rollback", "category": "I", "sub_type": "migration_rollback", "difficulty": "hard", "domain": "database"},
    {"task_id": "v50_websocket_heartbeat_reconnect_fsm", "category": "E", "sub_type": "websocket_fsm", "difficulty": "hard", "domain": "realtime-systems"},
    {"task_id": "v51_hierarchical_rate_limiter_burst_leak", "category": "J", "sub_type": "hierarchical_rate_limiter", "difficulty": "hard", "domain": "rate-limiting"},
    {"task_id": "v52_distributed_trace_context_propagation", "category": "F", "sub_type": "trace_correlation", "difficulty": "hard", "domain": "distributed-tracing"},
    {"task_id": "v53_message_queue_dedup_sliding_window", "category": "G", "sub_type": "sliding_window_dedup", "difficulty": "hard", "domain": "concurrency"},
    {"task_id": "v54_api_versioning_header_router", "category": "H", "sub_type": "versioning_router", "difficulty": "hard", "domain": "api-backend"},
    {"task_id": "v55_leader_election_lease_renewal_split_brain", "category": "G", "sub_type": "leader_lease", "difficulty": "hard", "domain": "distributed-consensus"},
    {"task_id": "v56_compensating_transaction_failure_recovery", "category": "E", "sub_type": "compensating_tx", "difficulty": "hard", "domain": "distributed-systems"},
]


def load_existing_corpus() -> List[Dict[str, Any]]:
    corpus = []
    tasks_dir = REPO_ROOT / "tasks"
    batch_b_ids = {s["task_id"] for s in BATCH_B_SPECS}
    for p in tasks_dir.rglob("task.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                task_dict = json.load(f)
                if task_dict.get("task_id") not in batch_b_ids:
                    corpus.append(task_dict)
        except Exception:
            pass
    return corpus


def main():
    console.print("[bold cyan]Starting TaskGenerator synthesis for Batch B (Repository Complexity: v43-v56)...[/bold cyan]")
    generator = TaskGenerator(sandbox_mode="local", repetitions=3, min_quality=3.5, duplicate_threshold=0.85)
    existing_corpus = load_existing_corpus()
    console.print(f"Loaded {len(existing_corpus)} existing baseline tasks for deduplication protection.")

    table = Table(title="Benchmark V2 Batch B Synthesis & Verification")
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

    for spec in BATCH_B_SPECS:
        tid = spec["task_id"]
        schema_obj, report, candidate = generator.generate_and_validate(
            spec=spec,
            seed=spec.get("seed", 42),
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

    summary_path = REPO_ROOT / "batch_b_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]Batch B complete. Detailed results saved to {summary_path}[/bold green]")
    if not all_approved:
        sys.exit(1)


if __name__ == "__main__":
    main()
