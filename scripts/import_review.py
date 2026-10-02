"""Imports Tendem / Toloka human expert reviews and emits human-verified SFT dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="Import human reviews into verified SFT dataset.")
    parser.add_argument(
        "--reviews",
        type=str,
        default="review_pack/reviews.json",
        help="Path to filled-in reviews JSON file",
    )
    parser.add_argument(
        "--sft-dataset",
        type=str,
        default="dataset/agentgym_sft.jsonl",
        help="Input SFT dataset path",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/agentgym_sft_human_verified.jsonl",
        help="Output path for human-verified SFT dataset",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=4,
        help="Minimum human rating (1-5) required for inclusion (default: 4)",
    )
    return parser.parse_args()


def import_reviews(reviews_path: str, sft_path: str, output_path: str, min_score: int):
    rev_file = Path(reviews_path)
    if not rev_file.exists():
        console.print(f"[yellow]Review file '{reviews_path}' not found.[/yellow]")
        console.print("To run human evaluation: fill out 'review_pack/review_pack.md' via Tendem / Toloka and save results to 'review_pack/reviews.json'.")
        console.print("A template is available at: review_pack/reviews.json.example")
        return 0

    with open(rev_file, "r", encoding="utf-8") as f:
        reviews_data = json.load(f)

    # Normalize reviews into dict keyed by task_id
    reviews_by_task: Dict[str, Dict[str, Any]] = {}
    if isinstance(reviews_data, list):
        for item in reviews_data:
            tid = item.get("task_id")
            if tid:
                reviews_by_task[tid] = item
    elif isinstance(reviews_data, dict):
        reviews_by_task = reviews_data

    sft_file = Path(sft_path)
    if not sft_file.exists():
        console.print(f"[red]Input dataset '{sft_path}' does not exist![/red]")
        return 0

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    verified_count = 0
    table = Table(title="Human Verified SFT Episodes (Score >= 4)")
    table.add_column("Task ID", style="cyan")
    table.add_column("Score (1-5)", justify="center")
    table.add_column("Comment", style="green")

    with open(sft_file, "r", encoding="utf-8") as fin, open(out_file, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            episode = json.loads(line)
            tid = episode.get("task_id")
            review = reviews_by_task.get(tid)

            if review:
                score = int(review.get("human_score", 0))
                comment = str(review.get("human_comment", ""))
                if score >= min_score:
                    episode["human_score"] = score
                    episode["human_comment"] = comment
                    fout.write(json.dumps(episode) + "\n")
                    verified_count += 1
                    table.add_row(tid, f"{score}/5", comment[:50] + ("..." if len(comment) > 50 else ""))

    console.print(table)
    console.print(f"\n[bold green]Successfully exported {verified_count} human-verified episodes to:[/bold green] [cyan]{output_path}[/cyan]\n")
    return verified_count


def main():
    args = parse_args()
    import_reviews(args.reviews, args.sft_dataset, args.output, args.min_score)


if __name__ == "__main__":
    main()
