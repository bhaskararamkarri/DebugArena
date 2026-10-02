"""Parallel episode runner and trajectory logging system."""

from __future__ import annotations

import datetime
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from agentgym.agent import Agent, MockAgent
from agentgym.env import BugFixEnv
from agentgym.judge import CodeJudge

console = Console()


class EpisodeRunner:
    """Manages execution of single and batch evaluation episodes."""

    def __init__(
        self,
        tasks_dir: str = "tasks",
        runs_dir: str = "runs",
        config_path: str = "config.yaml",
        enable_judge: bool = True,
    ):
        self.tasks_dir = tasks_dir
        self.runs_dir = Path(runs_dir)
        self.config_path = config_path
        self.enable_judge = enable_judge
        self.file_lock = threading.Lock()
        self.judge = CodeJudge(config_path=config_path) if enable_judge else None

    def run_episode(
        self,
        task_id: str,
        model_name: str,
        run_id: str,
        episode_id: str,
        agent: Optional[Agent] = None,
        max_steps: int = 10,
        sandbox_mode: str = "auto",
    ) -> Dict[str, Any]:
        """Runs one full episode on a single task."""
        env = BugFixEnv(
            tasks_dir=self.tasks_dir,
            max_steps=max_steps,
            config_path=self.config_path,
            sandbox_mode=sandbox_mode,
        )

        obs = env.reset(task_id)
        original_files = dict(obs.get("files", {}))

        if agent is None:
            agent = Agent(model_name=model_name, config_path=self.config_path)

        if isinstance(agent, MockAgent) and env.current_task:
            agent.set_reference_fix(env.current_task.get("reference_fix", {}))

        agent.reset()

        trajectory_file = self.runs_dir / run_id / "trajectories.jsonl"
        trajectory_file.parent.mkdir(parents=True, exist_ok=True)

        step_records: List[Dict[str, Any]] = []
        done = False
        step_idx = 0
        final_info: Dict[str, Any] = {}

        while not done:
            step_idx += 1
            # Agent decides action
            action, latency_ms, messages_snapshot = agent.act(obs)

            # Step in environment
            next_obs, step_reward, done, info = env.step(action)
            final_info = info

            # Judge score on final step
            judge_score = None
            if done and self.judge:
                judge_eval = self.judge.evaluate(
                    description=env.current_task.get("description", "") if env.current_task else "",
                    original_files=original_files,
                    final_files=dict(next_obs.get("files", {})),
                    pass_rate=info["pass_rate"],
                )
                judge_score = judge_eval.get("score")

            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            record = {
                "run_id": run_id,
                "model": model_name,
                "episode_id": episode_id,
                "task_id": task_id,
                "step": step_idx,
                "prompt": messages_snapshot,
                "action": action,
                "output": obs.get("last_output", ""),
                "pass_rate": info["pass_rate"],
                "reward": step_reward,
                "done": done,
                "judge_score": judge_score,
                "latency_ms": latency_ms,
                "timestamp": timestamp,
            }

            step_records.append(record)

            # Write step to trajectories.jsonl thread-safely
            with self.file_lock:
                with open(trajectory_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            obs = next_obs

        cumulative_return = final_info.get("cumulative_return", 0.0)
        success = (final_info.get("pass_rate", 0.0) >= 1.0)
        env.close()

        summary = {
            "episode_id": episode_id,
            "task_id": task_id,
            "model": model_name,
            "success": success,
            "final_pass_rate": final_info.get("pass_rate", 0.0),
            "steps": step_idx,
            "return": cumulative_return,
            "judge_score": judge_score,
            "regression_occurred": final_info.get("regression", False),
        }
        return summary

    def run_batch(
        self,
        task_ids: List[str],
        model_name: str,
        run_id: str,
        workers: int = 4,
        max_steps: int = 10,
        sandbox_mode: str = "auto",
        use_mock_solver: bool = False,
    ) -> List[Dict[str, Any]]:
        """Runs a batch of tasks in parallel using a thread pool."""
        results: List[Dict[str, Any]] = []
        run_folder = self.runs_dir / run_id
        run_folder.mkdir(parents=True, exist_ok=True)

        tasks_to_run = []
        for i, tid in enumerate(task_ids):
            ep_id = f"ep_{i+1:04d}"
            tasks_to_run.append((tid, ep_id))

        console.print(f"[bold cyan]Starting batch run:[/bold cyan] {run_id} | Model: {model_name} | Tasks: {len(tasks_to_run)} | Workers: {workers}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_bar = progress.add_task("[green]Evaluating...", total=len(tasks_to_run))

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {}
                for tid, ep_id in tasks_to_run:
                    agent = MockAgent(mode="solver") if use_mock_solver else None
                    fut = executor.submit(
                        self.run_episode,
                        task_id=tid,
                        model_name=model_name,
                        run_id=run_id,
                        episode_id=ep_id,
                        agent=agent,
                        max_steps=max_steps,
                        sandbox_mode=sandbox_mode,
                    )
                    futures[fut] = (tid, ep_id)

                for fut in as_completed(futures):
                    tid, ep_id = futures[fut]
                    try:
                        res = fut.result()
                        results.append(res)
                    except Exception as e:
                        console.print(f"[red]Error on task {tid}: {e}[/red]")
                        results.append({
                            "episode_id": ep_id,
                            "task_id": tid,
                            "model": model_name,
                            "success": False,
                            "final_pass_rate": 0.0,
                            "steps": 0,
                            "return": -1.0,
                            "judge_score": 1,
                            "error": str(e),
                        })
                    finally:
                        progress.advance(task_bar)

        # Write overall summary JSON
        summary_file = run_folder / "summary.json"
        total = len(results)
        solved = sum(1 for r in results if r.get("success", False))
        avg_steps = (sum(r.get("steps", 0) for r in results) / total) if total else 0.0
        avg_return = (sum(r.get("return", 0.0) for r in results) / total) if total else 0.0
        scores = [r.get("judge_score") for r in results if r.get("judge_score") is not None]
        avg_judge = (sum(scores) / len(scores)) if scores else None

        summary_data = {
            "run_id": run_id,
            "model": model_name,
            "total_tasks": total,
            "solved_tasks": solved,
            "success_rate": round(solved / total, 4) if total else 0.0,
            "avg_steps": round(avg_steps, 2),
            "avg_return": round(avg_return, 4),
            "avg_judge_score": round(avg_judge, 2) if avg_judge is not None else None,
            "episodes": sorted(results, key=lambda x: x.get("task_id", "")),
        }

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        console.print(f"[bold green]Run completed![/bold green] Success Rate: [cyan]{summary_data['success_rate']:.1%}[/cyan] ({solved}/{total}) | Avg Return: [yellow]{avg_return:.2f}[/yellow]")
        return results
