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

from agentgym.agent import Agent, MockAgent, get_prompt_hash
from agentgym.env import BugFixEnv
from agentgym.judge import CodeJudge
from agentgym.tracer import EpisodeTracer

console = Console()


class EpisodeRunner:
    """Manages execution of single and batch evaluation episodes."""

    def __init__(
        self,
        tasks_dir: str = "tasks",
        runs_dir: str = "runs",
        config_path: str = "config.yaml",
        enable_judge: bool = True,
        enable_tracing: bool = False,
    ):
        self.tasks_dir = tasks_dir
        self.runs_dir = Path(runs_dir)
        self.config_path = config_path
        self.enable_judge = enable_judge
        self.file_lock = threading.Lock()
        self.judge = CodeJudge(config_path=config_path) if enable_judge else None
        self.tracer = EpisodeTracer(enabled=enable_tracing)

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

        task_desc = env.current_task.get("description", "") if env.current_task else ""
        root_trace = self.tracer.start_episode(
            run_id=run_id,
            model_name=model_name,
            task_id=task_id,
            task_description=task_desc,
        )

        step_records: List[Dict[str, Any]] = []
        done = False
        step_idx = 0
        final_info: Dict[str, Any] = {}

        while not done:
            step_idx += 1
            # Agent decides action
            act_res = agent.act(obs)
            if len(act_res) == 4:
                action, latency_ms, messages_snapshot, extraction_needed = act_res
            else:
                action, latency_ms, messages_snapshot = act_res[:3]
                extraction_needed = False

            self.tracer.log_llm_call(root_trace, step_idx, messages_snapshot, action, latency_ms)

            # Step in environment
            next_obs, step_reward, done, info = env.step(action)
            final_info = info
            self.tracer.log_env_step(
                root_trace,
                step_idx,
                action,
                next_obs.get("last_output", ""),
                step_reward,
                info["pass_rate"],
                info.get("regression", False),
            )

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
            sandbox_type = env.sandbox.sandbox_type if env.sandbox else "unknown"
            docker_image_digest = env.sandbox.get_image_digest() if env.sandbox else None

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
                "sandbox_type": sandbox_type,
                "docker_image_digest": docker_image_digest,
                "extraction_needed": extraction_needed,
            }

            step_records.append(record)

            # Write step to trajectories.jsonl thread-safely
            with self.file_lock:
                with open(trajectory_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            obs = next_obs

        cumulative_return = final_info.get("cumulative_return", 0.0)
        success = (final_info.get("pass_rate", 0.0) >= 1.0)
        self.tracer.end_episode(
            root_trace,
            success=success,
            total_return=cumulative_return,
            steps=step_idx,
            final_pass_rate=final_info.get("pass_rate", 0.0),
        )
        sandbox_type = env.sandbox.sandbox_type if env.sandbox else "unknown"
        docker_image_digest = env.sandbox.get_image_digest() if env.sandbox else None
        env.close()

        any_extraction = any(r.get("extraction_needed", False) for r in step_records)
        invalid_json_count = sum(1 for r in step_records if r.get("action", {}).get("type") == "run" and "echo 'Invalid JSON action'" in r.get("action", {}).get("cmd", ""))

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
            "sandbox_type": sandbox_type,
            "docker_image_digest": docker_image_digest,
            "extraction_needed": any_extraction,
            "invalid_json_count": invalid_json_count,
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
        use_noop_solver: bool = False,
    ) -> List[Dict[str, Any]]:
        """Runs a batch of tasks in parallel using a thread pool."""
        results: List[Dict[str, Any]] = []
        run_folder = self.runs_dir / run_id
        run_folder.mkdir(parents=True, exist_ok=True)

        # Check existing completed episodes for resumability
        completed_task_ids = set()
        trajectory_file = run_folder / "trajectories.jsonl"
        if trajectory_file.exists():
            with open(trajectory_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            if rec.get("done"):
                                completed_task_ids.add(rec.get("task_id"))
                        except Exception:
                            pass

        summary_file = run_folder / "summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    old_sum = json.load(f)
                    results = [ep for ep in old_sum.get("episodes", []) if ep.get("task_id") in completed_task_ids]
            except Exception:
                pass

        tasks_to_run = []
        for i, tid in enumerate(task_ids):
            if tid not in completed_task_ids:
                ep_id = f"ep_{i+1:04d}"
                tasks_to_run.append((tid, ep_id))

        if completed_task_ids:
            console.print(f"[yellow]Resuming run '{run_id}': skipping {len(completed_task_ids)} already completed tasks, {len(tasks_to_run)} remaining.[/yellow]")

        console.print(f"[bold cyan]Starting batch run:[/bold cyan] {run_id} | Model: {model_name} | Tasks: {len(tasks_to_run)} | Workers: {workers}")

        if not tasks_to_run:
            console.print("[green]All requested tasks already completed in this run![/green]")
            return results

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
                    if use_noop_solver:
                        agent = MockAgent(mode="noop_submit")
                    elif use_mock_solver:
                        agent = MockAgent(mode="solver")
                    else:
                        agent = None
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

        first_ep = results[0] if results else {}
        sandbox_type = first_ep.get("sandbox_type", "docker" if sandbox_mode != "local" else "local")
        docker_image_digest = first_ep.get("docker_image_digest")

        extraction_count = sum(1 for r in results if r.get("extraction_needed", False))
        extraction_rate = round(extraction_count / total, 4) if total else 0.0
        total_invalid_json = sum(r.get("invalid_json_count", 0) for r in results)

        summary_data = {
            "run_id": run_id,
            "model": model_name,
            "protocol": "v2",
            "sandbox_type": sandbox_type,
            "docker_image_digest": docker_image_digest,
            "prompt_hash": get_prompt_hash(),
            "temperature": 0.2,
            "max_tokens": 4096,
            "response_format": "json_object",
            "max_steps": max_steps,
            "total_tasks": total,
            "solved_tasks": solved,
            "success_rate": round(solved / total, 4) if total else 0.0,
            "avg_steps": round(avg_steps, 2),
            "avg_return": round(avg_return, 4),
            "avg_judge_score": round(avg_judge, 2) if avg_judge is not None else None,
            "extraction_needed_rate": extraction_rate,
            "invalid_json_events": total_invalid_json,
            "episodes": sorted(results, key=lambda x: x.get("task_id", "")),
        }

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        console.print(f"[bold green]Run completed![/bold green] Success Rate: [cyan]{summary_data['success_rate']:.1%}[/cyan] ({solved}/{total}) | Avg Return: [yellow]{avg_return:.2f}[/yellow]")
        return results
