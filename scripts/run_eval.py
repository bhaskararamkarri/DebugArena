"""Evaluation runner script for AgentGym."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console
from rich.table import Table

from agentgym.env import BugFixEnv
from agentgym.runner import EpisodeRunner

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Run AgentGym evaluations across models and tasks.")
    parser.add_argument(
        "--model",
        type=str,
        default="nvidia/llama-3.1-nemotron-nano-4b-instruct",
        help="Model ID or alias (e.g., nemotron_nano, nemotron_super)",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="all",
        help="Comma-separated task IDs or 'all'",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent episodes (default: 4)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional unique run identifier",
    )
    parser.add_argument(
        "--sandbox",
        type=str,
        default="auto",
        choices=["auto", "docker", "local"],
        help="Sandbox execution mode",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum steps allowed per episode",
    )
    parser.add_argument(
        "--mock-solver",
        action="store_true",
        help="Use built-in mock solver agent (offline testing)",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable Nemotron judge code quality scoring",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable LangSmith tracing for episodes",
    )
    return parser.parse_args()


def resolve_model_name(model_arg: str, config_path: str = "config.yaml") -> str:
    import yaml
    if Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                models_cfg = cfg.get("models", {})
                if model_arg in models_cfg:
                    return models_cfg[model_arg].get("name", model_arg)
        except Exception:
            pass
    aliases = {
        "nemotron_nano": "nvidia/nemotron-3-nano-30b-a3b",
        "nemotron_super": "nvidia/nemotron-3-super-120b-a12b",
        "nemotron_judge": "nvidia/nemotron-3-ultra-550b-a55b",
    }
    return aliases.get(model_arg, model_arg)


def main():
    args = parse_args()
    model_name = resolve_model_name(args.model)

    # Check config for default tracing if not specified on CLI
    import yaml
    trace_enabled = args.trace
    if not trace_enabled and Path("config.yaml").exists():
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                trace_enabled = cfg.get("observability", {}).get("langsmith_enabled", False)
        except Exception:
            pass

    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    clean_model_tag = model_name.split("/")[-1].replace("-", "_")
    run_id = args.run_id or f"{now_str}_{clean_model_tag}"

    # Determine tasks to evaluate
    env_probe = BugFixEnv()
    all_available_tasks = env_probe.list_task_ids()

    if args.tasks.strip().lower() == "all":
        task_ids = all_available_tasks
    else:
        requested = [t.strip() for t in args.tasks.split(",") if t.strip()]
        task_ids = [t for t in requested if t in all_available_tasks]
        missing = [t for t in requested if t not in all_available_tasks]
        if missing:
            console.print(f"[yellow]Warning: Tasks not found: {missing}[/yellow]")

    if not task_ids:
        console.print("[red]No valid tasks selected to evaluate.[/red]")
        sys.exit(1)

    runner = EpisodeRunner(
        tasks_dir="tasks",
        runs_dir="runs",
        config_path="config.yaml",
        enable_judge=not args.no_judge,
        enable_tracing=trace_enabled,
    )

    console.print(f"\n[bold green]AgentGym Evaluation Run: {run_id}[/bold green]")
    console.print(f"Model: [cyan]{model_name}[/cyan] | Sandbox: [yellow]{args.sandbox}[/yellow] | Tasks: [magenta]{len(task_ids)}[/magenta]\n")

    results = runner.run_batch(
        task_ids=task_ids,
        model_name=model_name,
        run_id=run_id,
        workers=args.workers,
        max_steps=args.max_steps,
        sandbox_mode=args.sandbox,
        use_mock_solver=args.mock_solver,
    )

    # Render summary table
    table = Table(title=f"Evaluation Results — {run_id}")
    table.add_column("Task ID", style="cyan")
    table.add_column("Success", justify="center")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Steps", justify="right")
    table.add_column("Return", justify="right")
    table.add_column("Judge (1-5)", justify="center")
    table.add_column("Regression", justify="center")

    for r in sorted(results, key=lambda x: x["task_id"]):
        succ_str = "[bold green]PASS[/bold green]" if r["success"] else "[bold red]FAIL[/bold red]"
        pass_rate_str = f"{r['final_pass_rate']:.1%}"
        reg_str = "[red]YES[/red]" if r.get("regression_occurred") else "[green]NO[/green]"
        judge_str = str(r["judge_score"]) if r.get("judge_score") is not None else "N/A"

        table.add_row(
            r["task_id"],
            succ_str,
            pass_rate_str,
            str(r["steps"]),
            f"{r['return']:.2f}",
            judge_str,
            reg_str,
        )

    console.print("\n")
    console.print(table)
    console.print(f"\n[bold green]Trajectories saved to:[/bold green] runs/{run_id}/trajectories.jsonl")
    console.print(f"[bold green]Summary saved to:[/bold green] runs/{run_id}/summary.json\n")


if __name__ == "__main__":
    main()
