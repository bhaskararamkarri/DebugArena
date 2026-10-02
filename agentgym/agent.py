"""Agent implementation with OpenAI-compatible API support and strict JSON action parsing."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """You are an autonomous AI coding agent fixing a bug in a Python repository.
You interact with the environment by issuing JSON actions.

On every turn, analyze the bug description, repository files, and recent execution output.
Then, respond with EXACTLY ONE JSON object matching one of the following schemas:

1. Edit an entire file:
{"type": "edit", "path": "filename.py", "content": "<complete new file content>"}

2. Run a command in the isolated sandbox:
{"type": "run", "cmd": "python -c 'import filename; ...'"}

3. Submit your final fix:
{"type": "submit"}

RULES:
- Do not wrap your response in conversational text. Respond ONLY with valid JSON.
- Code blocks like ```json ... ``` are allowed but raw JSON is preferred.
- Only edit files that exist in the repository. Provide the complete file content on edit.
- Hidden test files are executed automatically to evaluate your fix.
"""


class Agent:
    """Agent that communicates with Nebius Token Factory or compatible LLM APIs."""

    def __init__(
        self,
        model_name: str = "nvidia/llama-3.1-nemotron-nano-4b-instruct",
        provider: str = "nebius",
        config_path: str = "config.yaml",
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ):
        self.model_name = model_name
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = self._load_config(config_path)
        self.client = self._init_client()
        self.conversation_history: List[Dict[str, str]] = []

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_client(self) -> OpenAI:
        providers = self.config.get("providers", {})
        prov_cfg = providers.get(self.provider, {})
        base_url = prov_cfg.get("base_url", "https://api.studio.nebius.ai/v1")
        key_env = prov_cfg.get("api_key_env", "NEBIUS_API_KEY")
        api_key = os.getenv(key_env, "dummy_key")

        # Check fallback if key is missing or dummy
        if (not api_key or api_key == "dummy_key") and self.provider != "mock":
            for fb_name in ["nvidia", "openrouter"]:
                fb_cfg = providers.get(fb_name, {})
                fb_key_env = fb_cfg.get("api_key_env", "")
                candidate = os.getenv(fb_key_env, "")
                if candidate:
                    base_url = fb_cfg.get("base_url")
                    api_key = candidate
                    self.provider = fb_name
                    break

        return OpenAI(base_url=base_url, api_key=api_key)

    def reset(self) -> None:
        """Reset conversation history for a new episode."""
        self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _clean_json_str(self, text: str) -> str:
        """Strips markdown code fences and extraneous whitespace."""
        text = text.strip()
        # Remove ```json ... ``` or ``` ... ```
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            text = m.group(1).strip()
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        return text

    def _validate_action(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(action, dict):
            return False, "Response is not a JSON object."
        act_type = action.get("type")
        if act_type not in ["edit", "run", "submit"]:
            return False, f"Action 'type' must be 'edit', 'run', or 'submit', got '{act_type}'."
        if act_type == "edit":
            if "path" not in action or not isinstance(action["path"], str):
                return False, "'edit' action requires a string 'path'."
            if "content" not in action or not isinstance(action["content"], str):
                return False, "'edit' action requires a string 'content'."
        if act_type == "run":
            if "cmd" not in action or not isinstance(action["cmd"], str):
                return False, "'run' action requires a string 'cmd'."
        return True, ""

    def act(self, observation: Dict[str, Any]) -> Tuple[Dict[str, Any], int, List[Dict[str, str]]]:
        """Sends observation to model, parses JSON action with 1 retry on invalid format.

        Returns:
            (parsed_action, latency_ms, messages_snapshot)
        """
        obs_text = (
            f"OBSERVATION:\n"
            f"Description: {observation.get('description', '')}\n"
            f"Steps remaining: {observation.get('steps_left', 0)}\n"
            f"Last execution output:\n{observation.get('last_output', '')}\n\n"
            f"Files in repository:\n"
        )
        for path, content in observation.get("files", {}).items():
            obs_text += f"--- {path} ---\n{content}\n"

        self.conversation_history.append({"role": "user", "content": obs_text})

        t0 = time.time()
        reply, latency_ms = self._call_model()

        # Attempt 1 parse
        clean_text = self._clean_json_str(reply)
        valid = False
        action = {}
        try:
            action = json.loads(clean_text)
            valid, err = self._validate_action(action)
        except Exception as e:
            err = str(e)

        if not valid:
            # Retry once with error feedback as required by Section 7.6
            retry_msg = (
                f"Your last reply was not valid JSON ({err}). "
                f"Please reply with ONLY a single valid JSON action object."
            )
            self.conversation_history.append({"role": "assistant", "content": reply})
            self.conversation_history.append({"role": "user", "content": retry_msg})

            t_retry_0 = time.time()
            reply2, lat2 = self._call_model()
            latency_ms += lat2
            clean_text2 = self._clean_json_str(reply2)
            try:
                action = json.loads(clean_text2)
                valid2, _ = self._validate_action(action)
                if valid2:
                    self.conversation_history.append({"role": "assistant", "content": reply2})
                    return action, latency_ms, list(self.conversation_history)
            except Exception:
                pass

            # If still invalid, fallback to failed step as specified
            action = {"type": "run", "cmd": "echo 'Invalid JSON action'"}
            self.conversation_history.append({"role": "assistant", "content": reply2})
            return action, latency_ms, list(self.conversation_history)

        self.conversation_history.append({"role": "assistant", "content": reply})
        return action, latency_ms, list(self.conversation_history)

    def _call_model(self) -> Tuple[str, int]:
        start = time.time()
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.conversation_history,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            latency_ms = int((time.time() - start) * 1000)
            return resp.choices[0].message.content or "", latency_ms
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            # Return raw string indicating error so parse triggers fallback
            return f'{{"error": "{str(e)}"}}', latency_ms


class MockAgent(Agent):
    """Deterministic Mock Agent for testing without live API keys."""

    def __init__(self, mode: str = "solver", reference_fix: Optional[Dict[str, str]] = None):
        self.mode = mode
        self.reference_fix = reference_fix or {}
        self.step_counter = 0
        self.conversation_history: List[Dict[str, str]] = []

    def set_reference_fix(self, reference_fix: Dict[str, str]) -> None:
        self.reference_fix = reference_fix

    def reset(self) -> None:
        self.step_counter = 0
        self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def act(self, observation: Dict[str, Any]) -> Tuple[Dict[str, Any], int, List[Dict[str, str]]]:
        self.step_counter += 1
        obs_text = f"OBSERVATION: steps_left={observation.get('steps_left')}"
        self.conversation_history.append({"role": "user", "content": obs_text})
        time.sleep(0.01)

        if self.mode == "solver":
            # Step 1: inspect code with run
            if self.step_counter == 1:
                action = {"type": "run", "cmd": "python -c 'print(\"Inspecting repository files...\")'"}
            # Step 2: apply reference fix
            elif self.step_counter == 2:
                if self.reference_fix:
                    path, content = next(iter(self.reference_fix.items()))
                    action = {"type": "edit", "path": path, "content": content}
                else:
                    action = {"type": "submit"}
            # Step 3: submit
            else:
                action = {"type": "submit"}
        elif self.mode == "regression":
            # Break something that was working
            action = {"type": "edit", "path": "mathutils.py", "content": "def broken(): raise Exception('Broken')"}
        else:  # no-op
            action = {"type": "run", "cmd": "python -c 'print(\"exploring...\")'"}

        self.conversation_history.append({"role": "assistant", "content": json.dumps(action)})
        return action, 15, list(self.conversation_history)
