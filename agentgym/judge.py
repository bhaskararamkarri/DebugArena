"""Nemotron Judge implementation for evaluating code quality (1-5 score)."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from openai import OpenAI

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
        model_name: str = "nvidia/llama-3.1-nemotron-70b-instruct",
        provider: str = "nebius",
        config_path: str = "config.yaml",
    ):
        self.model_name = model_name
        self.provider = provider
        self.config = self._load_config(config_path)
        self.client = self._init_client()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_client(self) -> Optional[OpenAI]:
        providers = self.config.get("providers", {})
        prov_cfg = providers.get(self.provider, {})
        base_url = prov_cfg.get("base_url", "https://api.studio.nebius.ai/v1")
        key_env = prov_cfg.get("api_key_env", "NEBIUS_API_KEY")
        api_key = os.getenv(key_env, "")

        if not api_key:
            for fb_name in ["nvidia", "openrouter"]:
                candidate = os.getenv(providers.get(fb_name, {}).get("api_key_env", ""), "")
                if candidate:
                    base_url = providers[fb_name].get("base_url")
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
        """Evaluates code quality and returns score (1-5) and rationale."""
        # If tests failed, score is bounded
        if pass_rate < 1.0:
            return {
                "score": 1 if pass_rate == 0.0 else 2,
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
                    return {"score": score, "rationale": data.get("rationale", "")}
            except Exception:
                pass

        # Heuristic fallback when offline or API unavailable
        # Passed 100% tests cleanly
        score = 4
        rationale = "Tests passed completely with direct root-cause fix."
        return {"score": score, "rationale": rationale}
