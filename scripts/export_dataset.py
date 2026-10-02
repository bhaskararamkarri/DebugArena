"""Dataset exporter: converts successful AgentGym trajectories into SFT/RL-ready JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Export successful AgentGym trajectories to SFT-ready JSONL.")
    parser.add_argument(
        "--run",
        type=str,
        required=True,
        help="Run identifier or 'all' to aggregate across all runs",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="Minimum final pass rate to include (default: 1.0 for 100% solved tasks)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/agentgym_sft.jsonl",
        help="Output path for exported dataset",
    )
    return parser.parse_args()


def export_dataset(run_target: str, min_pass_rate: float, output_path: str):
    runs_dir = Path("runs")
    if not runs_dir.exists():
        console.print("[red]No runs/ directory found![/red]")
        return 0

    if run_target.lower() == "all":
        trajectory_files = list(runs_dir.glob("*/trajectories.jsonl"))
    else:
        trajectory_files = [runs_dir / run_target / "trajectories.jsonl"]

    trajectory_files = [p for p in trajectory_files if p.exists()]
    if not trajectory_files:
        console.print(f"[red]No trajectories.jsonl found for run '{run_target}'[/red]")
        return 0

    # Group records by (run_id, episode_id)
    episodes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for tf in trajectory_files:
        with open(tf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                key = f"{record.get('run_id')}_{record.get('episode_id')}"
                episodes[key].append(record)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    exported_count = 0
    with open(out_file, "w", encoding="utf-8") as out:
        for ep_key, steps in episodes.items():
            steps.sort(key=lambda x: x["step"])
            final_step = steps[-1]
            final_pass_rate = final_step.get("pass_rate", 0.0)

            if final_pass_rate < min_pass_rate:
                continue

            task_id = final_step.get("task_id", "")
            total_return = round(sum(s.get("reward", 0.0) for s in steps), 4)

            # Reconstruct clean conversation message chain
            # The prompt in step 1 contains the system message and initial observation
            messages: List[Dict[str, str]] = []
            if steps[0].get("prompt"):
                for m in steps[0]["prompt"]:
                    messages.append({"role": m["role"], "content": m["content"]})
            else:
                messages.append({"role": "system", "content": "You are an autonomous AI coding agent fixing bugs."})

            # Assistant response for step 1
            messages.append({"role": "assistant", "content": json.dumps(steps[0]["action"])})

            # Subsequent steps
            for s in steps[1:]:
                # Observation from previous step's output
                obs_content = f"OBSERVATION:\nLast execution output: {s.get('output', '')}\nPass rate: {s.get('pass_rate', 0.0)}"
                messages.append({"role": "user", "content": obs_content})
                messages.append({"role": "assistant", "content": json.dumps(s["action"])})

            export_item = {
                "task_id": task_id,
                "messages": messages,
                "return": total_return,
                "steps": len(steps),
                "model": final_step.get("model", ""),
                "judge_score": final_step.get("judge_score"),
            }

            out.write(json.dumps(export_item) + "\n")
            exported_count += 1

    console.print(f"[bold green]Dataset Export Complete![/bold green]")
    console.print(f"Exported [cyan]{exported_count}[/cyan] successful episodes to: [yellow]{output_path}[/yellow]")
    return exported_count


def main():
    args = parse_args()
    export_dataset(args.run, args.min_pass_rate, args.output)


if __name__ == "__main__":
    main()
