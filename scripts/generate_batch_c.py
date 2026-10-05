"""Generates, validates, and persists Batch C (Advanced Agent Reasoning: Tasks v57-v70)."""

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

BATCH_C_SPECS: List[Dict[str, Any]] = [
    {"task_id": "v57_raft_log_replication_split_vote", "category": "G", "sub_type": "raft_consensus", "difficulty": "hard", "domain": "distributed-consensus"},
    {"task_id": "v58_byzantine_fault_tolerant_quorum_consensus", "category": "G", "sub_type": "byzantine_quorum", "difficulty": "hard", "domain": "distributed-consensus"},
    {"task_id": "v59_jit_bytecode_optimizer_dead_code_elimination", "category": "B", "sub_type": "jit_optimizer", "difficulty": "hard", "domain": "compilers"},
    {"task_id": "v60_two_phase_commit_coordinator_crash_recovery", "category": "E", "sub_type": "two_phase_commit", "difficulty": "hard", "domain": "distributed-transactions"},
    {"task_id": "v61_graphql_federation_gateway_query_planner", "category": "H", "sub_type": "federation_planner", "difficulty": "hard", "domain": "api-gateways"},
    {"task_id": "v62_lsm_tree_compaction_sst_merge", "category": "I", "sub_type": "lsm_compaction", "difficulty": "hard", "domain": "storage-engines"},
    {"task_id": "v63_oauth2_token_exchange_pkce_replay_attack", "category": "L", "sub_type": "oauth_pkce", "difficulty": "hard", "domain": "security"},
    {"task_id": "v64_adversarial_telemetry_flaky_retry_storm", "category": "M", "sub_type": "flaky_retry_storm", "difficulty": "adversarial", "domain": "networking"},
    {"task_id": "v65_actor_system_mailbox_deadlock_cycle", "category": "G", "sub_type": "actor_mailbox", "difficulty": "hard", "domain": "concurrency"},
    {"task_id": "v66_ast_pattern_rewriter_variable_shadowing", "category": "B", "sub_type": "ast_rewriter", "difficulty": "hard", "domain": "compilers"},
    {"task_id": "v67_b_plus_tree_leaf_split_borrow_rebalance", "category": "C", "sub_type": "bplus_tree", "difficulty": "hard", "domain": "data-structures"},
    {"task_id": "v68_crdt_pn_counter_lww_element_set_convergence", "category": "E", "sub_type": "crdt", "difficulty": "hard", "domain": "distributed-systems"},
    {"task_id": "v69_service_mesh_circuit_breaker_half_open_oscillation", "category": "H", "sub_type": "circuit_breaker", "difficulty": "hard", "domain": "service-mesh"},
    {"task_id": "v70_zero_knowledge_merkle_membership_proof", "category": "L", "sub_type": "merkle_proof", "difficulty": "hard", "domain": "cryptography"},
]


def load_existing_corpus() -> List[Dict[str, Any]]:
    corpus = []
    tasks_dir = REPO_ROOT / "tasks"
    batch_c_ids = {s["task_id"] for s in BATCH_C_SPECS}
    for p in tasks_dir.rglob("task.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                task_dict = json.load(f)
                if task_dict.get("task_id") not in batch_c_ids:
                    corpus.append(task_dict)
        except Exception:
            pass
    return corpus


def main():
    console.print("[bold cyan]Starting TaskGenerator synthesis for Batch C (Advanced Agent Reasoning: v57-v70)...[/bold cyan]")
    generator = TaskGenerator(sandbox_mode="local", repetitions=3, min_quality=3.5, duplicate_threshold=0.85)
    existing_corpus = load_existing_corpus()
    console.print(f"Loaded {len(existing_corpus)} existing baseline tasks for deduplication protection.")

    table = Table(title="Benchmark V2 Batch C Synthesis & Verification")
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

    for spec in BATCH_C_SPECS:
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

    summary_path = REPO_ROOT / "batch_c_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[bold green]Batch C complete. Detailed results saved to {summary_path}[/bold green]")
    if not all_approved:
        sys.exit(1)


if __name__ == "__main__":
    main()
