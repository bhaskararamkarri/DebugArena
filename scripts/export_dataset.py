"""Dataset exporter: converts AgentGym trajectories into SFT and DPO training-ready JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Export AgentGym trajectories to SFT or DPO format.")
    parser.add_argument(
        "--run",
        type=str,
        default="all",
        help="Run identifier or 'all' to aggregate across all runs",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["sft", "dpo"],
        default="sft",
        help="Export format: 'sft' (chat trajectories) or 'dpo' (chosen vs rejected pairs)",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="Minimum final pass rate to include for SFT (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for exported dataset (defaults to dataset/agentgym_<format>.jsonl)",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Export train/val splits (80/20) alongside the main dataset",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic train/val split",
    )
    return parser.parse_args()


def load_episodes(run_target: str) -> Dict[str, List[Dict[str, Any]]]:
    runs_dir = Path("runs")
    if not runs_dir.exists():
        console.print("[red]No runs/ directory found![/red]")
        return {}

    if run_target.lower() == "all":
        trajectory_files = list(runs_dir.glob("*/trajectories.jsonl"))
    else:
        trajectory_files = [runs_dir / run_target / "trajectories.jsonl"]

    trajectory_files = [p for p in trajectory_files if p.exists()]
    if not trajectory_files:
        console.print(f"[red]No trajectories.jsonl found for run '{run_target}'[/red]")
        return {}

    episodes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for tf in trajectory_files:
        with open(tf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    key = f"{record.get('run_id')}_{record.get('episode_id')}"
                    episodes[key].append(record)
                except Exception:
                    continue
    return episodes


def build_messages(steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Builds standard multi-turn conversation messages from step records."""
    messages: List[Dict[str, str]] = []
    if steps[0].get("prompt"):
        for m in steps[0]["prompt"]:
            messages.append({"role": m["role"], "content": m["content"]})
    else:
        messages.append({"role": "system", "content": "You are an autonomous AI coding agent fixing bugs."})

    messages.append({"role": "assistant", "content": json.dumps(steps[0]["action"])})

    for s in steps[1:]:
        obs_content = f"OBSERVATION:\nLast execution output: {s.get('output', '')}\nPass rate: {s.get('pass_rate', 0.0)}"
        messages.append({"role": "user", "content": obs_content})
        messages.append({"role": "assistant", "content": json.dumps(s["action"])})

    return messages


def validate_messages(messages: List[Dict[str, str]]) -> bool:
    """Validates message structure and non-empty content."""
    if not messages:
        return False
    for m in messages:
        if not isinstance(m, dict) or "role" not in m or "content" not in m:
            return False
        if not m["content"] or not isinstance(m["content"], str):
            return False
    return True


def trajectory_fingerprint(item: Dict[str, Any]) -> str:
    """Generates a stable SHA-256 fingerprint for deduplication."""
    serialized = json.dumps(item.get("messages") or item.get("chosen"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def export_sft(
    episodes: Dict[str, List[Dict[str, Any]]],
    min_pass_rate: float,
) -> List[Dict[str, Any]]:
    dataset = []
    seen_hashes = set()

    for ep_key, steps in episodes.items():
        steps.sort(key=lambda x: x["step"])
        final_step = steps[-1]
        final_pass_rate = final_step.get("pass_rate", 0.0)

        if final_pass_rate < min_pass_rate:
            continue

        task_id = final_step.get("task_id", "")
        total_return = round(sum(s.get("reward", 0.0) for s in steps), 4)
        messages = build_messages(steps)

        if not validate_messages(messages):
            continue

        item = {
            "task_id": task_id,
            "messages": messages,
            "return": total_return,
            "steps": len(steps),
            "model": final_step.get("model", ""),
            "judge_score": final_step.get("judge_score"),
        }

        fp = trajectory_fingerprint(item)
        if fp in seen_hashes:
            continue
        seen_hashes.add(fp)
        dataset.append(item)

    return dataset


def export_dpo(episodes: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Exports DPO pairs (prompt, chosen, rejected) for tasks with contrasting outcomes."""
    # Group episodes by task_id
    by_task: Dict[str, List[Tuple[float, float, List[Dict[str, Any]]]]] = defaultdict(list)

    for ep_key, steps in episodes.items():
        steps.sort(key=lambda x: x["step"])
        final_step = steps[-1]
        pass_rate = final_step.get("pass_rate", 0.0)
        tot_return = sum(s.get("reward", 0.0) for s in steps)
        task_id = final_step.get("task_id", "")
        if task_id:
            by_task[task_id].append((pass_rate, tot_return, steps))

    dpo_items = []
    seen_pairs = set()

    for task_id, candidate_list in by_task.items():
        # Look for chosen (pass_rate == 1.0) and rejected (pass_rate < 1.0 or significantly lower return)
        successful = [c for c in candidate_list if c[0] >= 1.0]
        unsuccessful = [c for c in candidate_list if c[0] < 1.0]

        if successful and unsuccessful:
            for succ in successful:
                for unsucc in unsuccessful:
                    chosen_msgs = build_messages(succ[2])
                    rejected_msgs = build_messages(unsucc[2])

                    if not validate_messages(chosen_msgs) or not validate_messages(rejected_msgs):
                        continue

                    # Extract the shared initial prompt
                    prompt = chosen_msgs[0]["content"] if chosen_msgs else ""

                    dpo_item = {
                        "task_id": task_id,
                        "prompt": prompt,
                        "chosen": chosen_msgs[1:],  # assistant & subsequent turns
                        "rejected": rejected_msgs[1:],
                        "chosen_return": round(succ[1], 4),
                        "rejected_return": round(unsucc[1], 4),
                        "chosen_pass_rate": succ[0],
                        "rejected_pass_rate": unsucc[0],
                    }

                    pair_key = (
                        json.dumps(dpo_item["chosen"], sort_keys=True),
                        json.dumps(dpo_item["rejected"], sort_keys=True),
                    )
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    dpo_items.append(dpo_item)

    return dpo_items


def write_jsonl(items: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def main():
    args = parse_args()
    episodes = load_episodes(args.run)
    if not episodes:
        return

    default_output = f"dataset/agentgym_{args.format}.jsonl"
    output_path = Path(args.output or default_output)

    if args.format == "sft":
        dataset = export_sft(episodes, args.min_pass_rate)
    else:
        dataset = export_dpo(episodes)

    if not dataset:
        console.print(f"[yellow]No items matched the export criteria for format '{args.format}'.[/yellow]")
        return

    write_jsonl(dataset, output_path)
    console.print(f"[bold green]Exported {len(dataset)} unique verified items to:[/bold green] [cyan]{output_path}[/cyan]")

    if args.split and len(dataset) >= 5:
        random.seed(args.seed)
        shuffled = list(dataset)
        random.shuffle(shuffled)
        val_size = max(1, int(len(shuffled) * args.val_ratio))
        val_items = shuffled[:val_size]
        train_items = shuffled[val_size:]

        stem = output_path.stem
        train_path = output_path.parent / f"{stem}_train.jsonl"
        val_path = output_path.parent / f"{stem}_val.jsonl"

        write_jsonl(train_items, train_path)
        write_jsonl(val_items, val_path)

        console.print(f"  |-- Train split ({len(train_items)} items): [yellow]{train_path}[/yellow]")
        console.print(f"  |-- Val split ({len(val_items)} items): [yellow]{val_path}[/yellow]")


if __name__ == "__main__":
    main()
