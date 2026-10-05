"""BugFixEnv: A Gymnasium-style RL environment for debugging and repairing code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from agentgym.reward import RewardCalculator
from agentgym.sandbox import BaseSandbox, Sandbox
from task_factory.feedback import get_feedback_adapter, BaseFeedbackAdapter


class BugFixEnv:
    """Gymnasium-style environment for coding agent bug fixing."""

    def __init__(
        self,
        tasks_dir: str = "tasks",
        max_steps: Optional[int] = None,
        config_path: Optional[str] = "config.yaml",
        sandbox_mode: Optional[str] = None,
        feedback_mode: Optional[str] = None,
    ):
        self.tasks_dir = Path(tasks_dir)
        self.config: Dict[str, Any] = {}

        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

        env_cfg = self.config.get("environment", {})
        if max_steps is not None:
            self.max_steps = max_steps
        else:
            self.max_steps = env_cfg.get("max_steps", 10)
        self.timeout = env_cfg.get("timeout_seconds", 10)
        self.sandbox_mode = sandbox_mode or env_cfg.get("sandbox_mode", "auto")
        self.feedback_mode = feedback_mode or env_cfg.get("feedback_mode", "diagnostic")
        self.feedback_adapter: BaseFeedbackAdapter = get_feedback_adapter(self.feedback_mode)
        self.mem_limit = env_cfg.get("mem_limit", "256m")
        self.cpu_limit = env_cfg.get("cpu_limit", 0.5)
        self.pids_limit = env_cfg.get("pids_limit", 128)
        self.max_output_chars = env_cfg.get("output_max_chars", 4000)

        rew_cfg = self.config.get("reward", {})
        self.step_cost = rew_cfg.get("step_cost", 0.01)
        self.regression_penalty = rew_cfg.get("regression_penalty", 0.20)

        self.sandbox: Optional[BaseSandbox] = None
        self.reward_calc = RewardCalculator(
            step_cost=self.step_cost,
            regression_penalty=self.regression_penalty,
        )

        self.current_task: Optional[Dict[str, Any]] = None
        self.task_id: Optional[str] = None
        self.steps_left = self.max_steps
        self.current_step = 0
        self.last_output = ""
        self.baseline_pass_rate = 0.0

    def load_task(self, task_id: str) -> Dict[str, Any]:
        """Loads a task JSON file by task_id."""
        target_path = self.tasks_dir / task_id / "task.json"
        if not target_path.exists():
            target_path = self.tasks_dir / "hard" / task_id / "task.json"
        if not target_path.exists():
            target_path = self.tasks_dir / "v2" / task_id / "task.json"
        if not target_path.exists():
            target_path = self.tasks_dir / f"{task_id}.json"
        if not target_path.exists():
            for p in self.tasks_dir.rglob("task.json"):
                if p.parent.name == task_id or p.parent.name.startswith(f"{task_id}_"):
                    target_path = p
                    break
        if not target_path or not target_path.exists():
            raise FileNotFoundError(f"Task '{task_id}' not found in {self.tasks_dir}")

        with open(target_path, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        return task_data

    def list_task_ids(self, suite: Optional[str] = None) -> list[str]:
        """Returns sorted list of all available task IDs, optionally filtered by suite ('core', 'hard', 'v2', 'all')."""
        task_ids = []
        if not self.tasks_dir.exists():
            return []

        for p in self.tasks_dir.rglob("task.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    tid = d.get("task_id", p.parent.name)
                    task_suite = d.get("suite", "core" if tid.startswith("t") else ("hard" if tid.startswith("h") else "v2"))
                    if suite is None or suite == "all" or task_suite == suite:
                        task_ids.append(tid)
            except Exception:
                pass
        return sorted(list(set(task_ids)))

    def reset(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Resets the environment for a new episode.

        Returns:
            Observation dictionary:
            {
                "description": str,
                "files": dict[str, str],
                "last_output": str,
                "steps_left": int
            }
        """
        if self.sandbox:
            self.sandbox.cleanup()

        if task_id is None:
            available = self.list_task_ids()
            if not available:
                raise ValueError(f"No tasks found in {self.tasks_dir}")
            task_id = available[0]

        self.task_id = task_id
        self.current_task = self.load_task(task_id)
        self.steps_left = self.max_steps
        self.current_step = 0
        self.last_output = "Environment initialized. Buggy repository loaded."

        # Create fresh sandbox
        self.sandbox = Sandbox.create(
            mode=self.sandbox_mode,
            timeout=self.timeout,
            max_output_chars=self.max_output_chars,
            mem_limit=self.mem_limit,
            cpu_limit=self.cpu_limit,
            pids_limit=self.pids_limit,
        )

        # Write repository files
        self.sandbox.write_files(self.current_task.get("repo_files", {}))

        # Run hidden tests to establish baseline
        tests = self.current_task.get("tests", {})
        baseline_res = self.sandbox.run_tests(tests, timeout=self.timeout)
        self.baseline_pass_rate = self.reward_calc.reset(
            initial_passed_tests=baseline_res.passed_tests,
            initial_total_tests=baseline_res.total_tests,
        )

        return self._get_observation()

    def _get_observation(self) -> Dict[str, Any]:
        files = self.sandbox.get_files() if self.sandbox else {}
        raw_obs = {
            "description": self.current_task.get("description", "") if self.current_task else "",
            "files": files,
            "last_output": self.last_output,
            "steps_left": self.steps_left,
        }
        return self.feedback_adapter.filter_observation(raw_obs)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Executes an action in the environment.

        Actions supported:
            {"type": "edit", "path": str, "content": str}
            {"type": "run", "cmd": str}
            {"type": "submit"}

        Returns:
            (observation, step_reward, done, info)
        """
        if not self.sandbox or not self.current_task:
            raise RuntimeError("Environment must be reset before calling step().")

        self.current_step += 1
        self.steps_left -= 1

        action_type = action.get("type", "").lower()
        submitted = False

        if action_type == "edit":
            path = action.get("path", "")
            content = action.get("content", "")
            if not path or not isinstance(content, str):
                self.last_output = "Error: 'edit' action requires valid 'path' and string 'content'."
            else:
                self.sandbox.write_files({path: content})
                self.last_output = f"File updated: {path}"

        elif action_type == "run":
            cmd = action.get("cmd", "")
            if not cmd:
                self.last_output = "Error: 'run' action requires non-empty 'cmd'."
            else:
                res = self.sandbox.run_command(cmd, timeout=self.timeout)
                self.last_output = res.output

        elif action_type == "submit":
            submitted = True
            self.last_output = "Solution submitted."

        else:
            self.last_output = f"Invalid action type: '{action_type}'. Valid types are 'edit', 'run', 'submit'."

        # Hidden tests are executed to evaluate the new state
        tests = self.current_task.get("tests", {})
        test_res = self.sandbox.run_tests(tests, timeout=self.timeout)

        # Reward computation
        step_reward, regression_flag, breakdown = self.reward_calc.compute_step_reward(
            current_passed_tests=test_res.passed_tests,
            total_tests=test_res.total_tests,
        )

        all_tests_passed = (test_res.pass_rate >= 1.0)
        ran_out_of_steps = (self.steps_left <= 0)
        done = all_tests_passed or submitted or ran_out_of_steps

        raw_info = {
            "task_id": self.task_id,
            "step": self.current_step,
            "action": action,
            "pass_rate": test_res.pass_rate,
            "tests_passed": len(test_res.passed_tests),
            "tests_total": test_res.total_tests,
            "passed_tests": sorted(list(test_res.passed_tests)),
            "failed_tests": sorted(list(test_res.failed_tests)),
            "regression": regression_flag,
            "step_reward": step_reward,
            "cumulative_return": self.reward_calc.cumulative_return,
            "breakdown": breakdown,
            "all_tests_passed": all_tests_passed,
            "submitted": submitted,
            "ran_out_of_steps": ran_out_of_steps,
        }

        observable_reward = self.feedback_adapter.filter_reward(step_reward, done, raw_info)
        info = self.feedback_adapter.filter_info(raw_info)
        return self._get_observation(), observable_reward, done, info

    def close(self) -> None:
        if self.sandbox:
            self.sandbox.cleanup()
            self.sandbox = None
