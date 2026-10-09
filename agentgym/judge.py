"""Nemotron Judge implementation for evaluating code quality (1-5 score)."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from agentgym.provider import NEBIUS_CANONICAL_ENDPOINT, resolve_provider_config
from agentgym.taxonomy import EvaluationStatus

load_dotenv()

JUDGE_PROMPT = """You are an expert Python code reviewer assessing a bug fix.
Given the bug description, original buggy code, and the agent's final modified code, evaluate the quality of the fix on a scale of 1 to 5:

1: Broken, unparseable, or completely wrong fix.
2: Hacky workaround that bypasses the root cause or introduces technical debt.
3: Functional fix but messy, non-idiomatic, or suboptimal.
4: Clean, pythonic fix that addresses the root cause directly.
5: Exemplary, idiomatic Python with clean structure and robust edge-case handling.

Respond with ONLY a JSON object in this format:
{"score": <int 1-5>, "rationale": "<brief 1-2 sentence explanation>"}
"""


class CodeJudge:
    """Evaluates code quality of agent solutions."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        config_path: str = "config.yaml",
        execution_mode: str = "hackathon",
    ):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.execution_mode = execution_mode
        self.model_name = model_name or self._resolve_judge_model()

        if self.execution_mode == "hackathon":
            self.provider = "nebius"
        else:
            self.provider = provider or self.config.get("models", {}).get("nemotron_judge", {}).get("provider", "nebius")

        self.client = self._init_client()

    def _resolve_judge_model(self) -> str:
        models_cfg = self.config.get("models", {})
        if "nemotron_judge" in models_cfg and "name" in models_cfg["nemotron_judge"]:
            return models_cfg["nemotron_judge"]["name"]
        if "judge" in self.config and isinstance(self.config["judge"], dict) and "model" in self.config["judge"]:
            return self.config["judge"]["model"]
        raise ValueError(f"Judge model is not configured in '{self.config_path}'.")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_client(self) -> Optional[OpenAI]:
        prov_info = resolve_provider_config(self.provider, config_path=self.config_path)
        base_url = prov_info.get("base_url", NEBIUS_CANONICAL_ENDPOINT if self.provider == "nebius" else "https://openrouter.ai/api/v1")
        key_env = prov_info.get("api_key_env", "NEBIUS_API_KEY" if self.provider == "nebius" else "")
        api_key = os.getenv(key_env, "")

        if not api_key and self.execution_mode != "hackathon":
            for fb_name in ["nvidia", "openrouter"]:
                fb_info = resolve_provider_config(fb_name, config_path=self.config_path)
                candidate = os.getenv(fb_info.get("api_key_env", ""), "")
                if candidate:
                    base_url = fb_info.get("base_url")
                    api_key = candidate
                    break

        if not api_key:
            return None

        return OpenAI(base_url=base_url, api_key=api_key)

    def evaluate(
        self,
        description: str,
        original_files: Dict[str, str],
        final_files: Dict[str, str],
        pass_rate: float,
    ) -> Dict[str, Any]:
        """Evaluates code quality and returns score (1-5), status, and rationale."""
        # If tests failed, score is bounded
        if pass_rate < 1.0:
            score = 1 if pass_rate == 0.0 else 2
            return {
                "score": score,
                "status": EvaluationStatus.FAIL.value if pass_rate == 0.0 else EvaluationStatus.PARTIAL.value,
                "rationale": f"Tests did not fully pass (pass rate: {pass_rate:.1%}).",
            }

        # If LLM client is available, prompt judge model
        if self.client:
            try:
                user_content = (
                    f"BUG DESCRIPTION:\n{description}\n\n"
                    f"ORIGINAL CODE:\n{json.dumps(original_files, indent=2)}\n\n"
                    f"FINAL AGENT CODE:\n{json.dumps(final_files, indent=2)}\n"
                )
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": JUDGE_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                    max_tokens=300,
                )
                text = resp.choices[0].message.content or ""
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    data = json.loads(m.group(0))
                    score = int(data.get("score", 4))
                    score = max(1, min(5, score))
                    return {
                        "score": score,
                        "status": EvaluationStatus.PASS.value,
                        "rationale": data.get("rationale", "Evaluation completed by LLM judge."),
                    }
            except Exception as e:
                return {
                    "score": None,
                    "status": EvaluationStatus.JUDGE_UNAVAILABLE.value,
                    "rationale": f"LLM Judge evaluation failed: {str(e)}",
                    "error": str(e),
                }

        # Offline or API unavailable - never fabricate numeric scores
        return {
            "score": None,
            "status": EvaluationStatus.JUDGE_UNAVAILABLE.value,
            "rationale": "LLM Judge is offline or API credentials are not configured.",
        }
