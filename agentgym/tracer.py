"""Optional LangSmith Observability Integration for AgentGym."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agentgym.tracer")


class NullRun:
    """No-op run tree for offline execution or when tracing is disabled."""

    def create_child(self, *args, **kwargs) -> NullRun:
        return self

    def end(self, *args, **kwargs) -> None:
        pass

    def post(self) -> None:
        pass

    def patch(self) -> None:
        pass


class EpisodeTracer:
    """Manages LangSmith tracing for AgentGym evaluation episodes."""

    def __init__(self, enabled: bool = False, project_name: str = "agentgym"):
        self.enabled = enabled
        self.project_name = os.getenv("LANGSMITH_PROJECT", project_name)
        self.client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        if not self.enabled:
            return

        api_key = os.getenv("LANGSMITH_API_KEY", "")
        if not api_key:
            logger.warning("LANGSMITH_API_KEY is not set. LangSmith tracing will run in offline mode.")
            self.enabled = False
            return

        try:
            from langsmith import Client

            self.client = Client()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Failed to initialize LangSmith client: {e}. Running without tracing.")
            self.enabled = False

    def start_episode(
        self,
        run_id: str,
        model_name: str,
        task_id: str,
        task_description: str,
    ) -> Any:
        """Starts a root trace span for an episode."""
        if not self.enabled or not self.client:
            return NullRun()

        try:
            from langsmith.run_trees import RunTree

            short_model = model_name.split("/")[-1]
            root = RunTree(
                name=f"{run_id}/{short_model}/{task_id}",
                run_type="chain",
                project_name=self.project_name,
                inputs={
                    "task_id": task_id,
                    "model": model_name,
                    "description": task_description,
                },
                extra={
                    "metadata": {
                        "run_id": run_id,
                        "model": model_name,
                        "task_id": task_id,
                    }
                },
            )
            root.post()
            return root
        except Exception as e:
            logger.warning(f"Error starting LangSmith trace: {e}")
            return NullRun()

    def log_llm_call(
        self,
        parent_run: Any,
        step_idx: int,
        prompt_snapshot: List[Dict[str, str]],
        action: Dict[str, Any],
        latency_ms: int,
    ) -> Any:
        """Logs an LLM action step as a child span."""
        if not self.enabled or isinstance(parent_run, NullRun):
            return NullRun()

        try:
            # Safe sanitization: exclude any sensitive markers
            child = parent_run.create_child(
                name=f"step_{step_idx}_llm_act",
                run_type="llm",
                inputs={"prompt": prompt_snapshot[-1] if prompt_snapshot else {}},
                outputs={"action": action},
                extra={"latency_ms": latency_ms},
            )
            child.post()
            child.end()
            return child
        except Exception as e:
            logger.warning(f"Error logging LLM span: {e}")
            return NullRun()

    def log_env_step(
        self,
        parent_run: Any,
        step_idx: int,
        action: Dict[str, Any],
        execution_output: str,
        step_reward: float,
        pass_rate: float,
        regression: bool,
    ) -> Any:
        """Logs an environment interaction as a child tool span without hidden tests."""
        if not self.enabled or isinstance(parent_run, NullRun):
            return NullRun()

        try:
            # Notice: hidden test code is strictly NEVER sent
            child = parent_run.create_child(
                name=f"step_{step_idx}_env_exec",
                run_type="tool",
                inputs={"action": action},
                outputs={"output": execution_output},
                extra={
                    "step_reward": step_reward,
                    "pass_rate": pass_rate,
                    "regression": regression,
                },
            )
            child.post()
            child.end()
            return child
        except Exception as e:
            logger.warning(f"Error logging env span: {e}")
            return NullRun()

    def end_episode(
        self,
        parent_run: Any,
        success: bool,
        total_return: float,
        steps: int,
        final_pass_rate: float,
    ) -> None:
        """Closes the episode root trace span with final metrics."""
        if not self.enabled or isinstance(parent_run, NullRun):
            return

        try:
            parent_run.end(
                outputs={
                    "success": success,
                    "return": total_return,
                    "steps": steps,
                    "final_pass_rate": final_pass_rate,
                }
            )
            parent_run.patch()
        except Exception as e:
            logger.warning(f"Error ending LangSmith trace: {e}")
