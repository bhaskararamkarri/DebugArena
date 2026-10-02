"""Verification script for AgentGym tasks.

Verifies:
1. Before fix: passes at least 1 test (for regression testing) and fails at least 1 test.
2. After fix: passes 100% of tests.
3. Flakiness check: runs 3 times in each state and confirms deterministic results.
Parallelized with ThreadPoolExecutor for fast execution.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console
from rich.table import Table

from agentgym.sandbox import Sandbox

console = Console()


def verify_task(task_path: Path, repeat: int = 3) -> dict:
    with open(task_path, "r", encoding="utf-8") as f:
        task = json.load(f)

    tid = task["task_id"]
    tests = task["tests"]
    repo_files = task["repo_files"]
    ref_fix = task["reference_fix"]

    # 1. Verify Before Fix (repeat times)
    before_passes = []
    before_fails = []
    for _ in range(repeat):
        sb = Sandbox.create(mode="local")
        sb.write_files(repo_files)
        res = sb.run_tests(tests)
        sb.cleanup()
        before_passes.append(res.passed_tests)
        before_fails.append(res.failed_tests)

    # Flakiness check before
    flaky_before = not all(p == before_passes[0] for p in before_passes)
    initial_passed_count = len(before_passes[0])
    initial_failed_count = len(before_fails[0])
    total_count = initial_passed_count + initial_failed_count

    has_partial_pass = initial_passed_count > 0
    has_failure = initial_failed_count > 0

    # 2. Verify After Reference Fix (repeat times)
    after_passes = []
    after_fails = []
    for _ in range(repeat):
        sb = Sandbox.create(mode="local")
        merged = dict(repo_files)
        merged.update(ref_fix)
        sb.write_files(merged)
        res = sb.run_tests(tests)
        sb.cleanup()
        after_passes.append(res.passed_tests)
        after_fails.append(res.failed_tests)

    flaky_after = not all(p == after_passes[0] for p in after_passes)
    all_passed_after = len(after_fails[0]) == 0 and len(after_passes[0]) == total_count

    valid = (
        not flaky_before
        and not flaky_after
        and has_partial_pass
        and has_failure
        and all_passed_after
    )

    return {
        "task_id": tid,
        "difficulty": task.get("difficulty", "easy"),
        "total_tests": total_count,
        "before_passed": initial_passed_count,
        "before_failed": initial_failed_count,
        "after_passed": len(after_passes[0]),
        "flaky": flaky_before or flaky_after,
        "valid": valid,
    }


def main():
    tasks_dir = Path("tasks")
    task_files = sorted(list(tasks_dir.glob("*/task.json")))

    if not task_files:
        console.print("[red]No task.json files found in tasks/![/red]")
        sys.exit(1)

    console.print(f"[bold cyan]Verifying {len(task_files)} benchmark tasks (3x flakiness checks in parallel)...[/bold cyan]")

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(verify_task, tf, 3): tf for tf in task_files}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)

    results.sort(key=lambda x: x["task_id"])

    table = Table(title="AgentGym 20-Task Benchmark Verification (3x Repetitions)")
    table.add_column("Task ID", style="cyan")
    table.add_column("Difficulty", style="magenta")
    table.add_column("Tests", justify="right")
    table.add_column("Before Fix (Pass/Fail)", justify="center")
    table.add_column("After Fix (Pass/Fail)", justify="center")
    table.add_column("Flaky?", justify="center")
    table.add_column("Status", justify="center")

    all_ok = True
    for res in results:
        status_str = "[bold green]PASS[/bold green]" if res["valid"] else "[bold red]FAIL[/bold red]"
        flaky_str = "[red]YES[/red]" if res["flaky"] else "[green]NO[/green]"
        before_str = f"{res['before_passed']} pass / {res['before_failed']} fail"
        after_str = f"{res['after_passed']} pass / 0 fail"

        if not res["valid"]:
            all_ok = False

        table.add_row(
            res["task_id"],
            res["difficulty"],
            str(res["total_tests"]),
            before_str,
            after_str,
            flaky_str,
            status_str,
        )

    console.print(table)

    if all_ok:
        console.print(f"\n[bold green]Success: All {len(task_files)} tasks verified! (0 flakiness, regression-ready, 100% reference fix pass).[/bold green]\n")
        sys.exit(0)
    else:
        console.print(f"\n[bold red]Error: Verification failed for one or more tasks.[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
