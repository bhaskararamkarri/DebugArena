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

SYSTEM_PROMPT = """You are an autonomous AI coding agent fixing a bug in a small Python repository.
You interact with the environment ONLY by outputting a single JSON action object.

CRITICAL INSTRUCTIONS:
- You must output NOTHING except a single valid JSON object.
- DO NOT write explanations, prose, greetings, or thoughts.
- DO NOT use markdown headers or conversational commentary.
- Your entire output must be valid JSON matching one of the three schemas below.

Supported JSON action schemas:
1. Edit a file:
{"type": "edit", "path": "filename.py", "content": "<complete new file content>"}

2. Run a command in sandbox:
{"type": "run", "cmd": "python -c '...'"}

3. Submit solution:
{"type": "submit"}
"""


class Agent:
    """Agent that communicates with Nebius Token Factory or compatible LLM APIs."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        config_path: str = "config.yaml",
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ):
        self.config = self._load_config(config_path)
        self.temperature = temperature
        self.max_tokens = max_tokens

        models_cfg = self.config.get("models", {})
        default_model = models_cfg.get("nemotron_nano", {}).get("name", "nvidia/nemotron-3-nano-30b-a3b")
        self.model_name = model_name or default_model

        if provider:
            self.provider = provider
        else:
            found_prov = None
            for m_key, m_info in models_cfg.items():
                if m_info.get("name") == self.model_name:
                    found_prov = m_info.get("provider")
                    break
            self.provider = found_prov or self.config.get("default_provider", "openrouter")

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
        base_url = prov_cfg.get("base_url", "https://openrouter.ai/api/v1")
        key_env = prov_cfg.get("api_key_env", "")
        api_key = os.getenv(key_env, "") if key_env else ""

        # If designated provider has no key, check alternatives in order
        if not api_key and self.provider != "mock":
            for candidate_prov in ["openrouter", "nebius", "nvidia"]:
                cand_cfg = providers.get(candidate_prov, {})
                cand_key_env = cand_cfg.get("api_key_env", "")
                cand_key = os.getenv(cand_key_env, "") if cand_key_env else ""
                if cand_key:
                    base_url = cand_cfg.get("base_url")
                    api_key = cand_key
                    self.provider = candidate_prov
                    break

        if not api_key:
            api_key = "dummy_key"

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

    def _normalize_and_validate_action(self, action: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        if not isinstance(action, dict):
            return False, "Response is not a JSON object.", action

        normalized = dict(action)

        # Normalize action type
        act_type = normalized.get("type") or normalized.get("action")
        if isinstance(act_type, str):
            act_type = act_type.lower().strip()
        normalized["type"] = act_type

        if act_type not in ["edit", "run", "submit"]:
            return False, f"Action 'type' must be 'edit', 'run', or 'submit', got '{act_type}'.", action

        if act_type == "edit":
            # Normalize path
            path = normalized.get("path") or normalized.get("file") or normalized.get("filename")
            normalized["path"] = path
            # Normalize content
            content = normalized.get("content") or normalized.get("code") or normalized.get("new_content")
            normalized["content"] = content

            if not path or not isinstance(path, str):
                return False, "'edit' action requires a valid string 'path'.", action
            if content is None or not isinstance(content, str):
                return False, "'edit' action requires string 'content'.", action

        if act_type == "run":
            cmd = normalized.get("cmd") or normalized.get("command")
            normalized["cmd"] = cmd
            if not cmd or not isinstance(cmd, str):
                return False, "'run' action requires a valid string 'cmd'.", action

        return True, "", normalized

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
            raw_action = json.loads(clean_text)
            valid, err, action = self._normalize_and_validate_action(raw_action)
        except Exception as e:
            err = str(e)

        if not valid:
            # Retry once with error feedback as required by Section 7.6
            retry_msg = (
                f"ERROR: Your previous response was not valid JSON ({err}). "
                f"You must respond with ONLY a single valid JSON object: "
                f'{{"type": "edit", "path": "<filename>", "content": "<new code>"}} or '
                f'{{"type": "run", "cmd": "<command>"}} or {{"type": "submit"}}. '
                f"Do not include any conversational sentences or explanations."
            )
            self.conversation_history.append({"role": "assistant", "content": reply})
            self.conversation_history.append({"role": "user", "content": retry_msg})

            reply2, lat2 = self._call_model()
            latency_ms += lat2
            clean_text2 = self._clean_json_str(reply2)
            try:
                raw_action2 = json.loads(clean_text2)
                valid2, _, action2 = self._normalize_and_validate_action(raw_action2)
                if valid2:
                    self.conversation_history.append({"role": "assistant", "content": reply2})
                    return action2, latency_ms, list(self.conversation_history)
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
        max_attempts = 4
        last_error = ""

        for attempt in range(max_attempts):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.conversation_history,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                latency_ms = int((time.time() - start) * 1000)
                choice = resp.choices[0]
                msg = choice.message
                content = msg.content or ""
                if not content and hasattr(msg, "reasoning") and msg.reasoning:
                    content = str(msg.reasoning)
                return content, latency_ms
            except Exception as e:
                last_error = str(e)
                # Check for rate limit or transient error
                if attempt < max_attempts - 1:
                    sleep_time = (2 ** attempt) * 1.5
                    time.sleep(sleep_time)

        latency_ms = int((time.time() - start) * 1000)
        return f'{{"error": "{last_error}"}}', latency_ms


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
