"""Agent implementation with OpenAI-compatible API support and robust JSON action parsing."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from agentgym.provider import (
    ExecutionMode,
    NEBIUS_CANONICAL_ENDPOINT,
    ProviderPolicyError,
    resolve_provider_config,
    validate_execution_config,
)

load_dotenv()

SYSTEM_PROMPT = """You are an autonomous AI coding agent fixing a bug in a Python repository inside an isolated Linux sandbox.

ENVIRONMENT SPECIFICATION:
- Operating System: Linux x86_64 container.
- Python Environment: Python 3.11 with pytest installed.
- Shell: /bin/sh. Standard Linux utilities (ls, cat, grep, find, python3, pytest) are available.
- Workspace: Working directory is /workspace containing the repository files.
- Hidden Tests: Regression and verification tests are executed externally by the environment after each step. You cannot view, edit, or execute the hidden test suite.

INTERACTION PROTOCOL:
- You must interact with the environment ONLY by outputting a single JSON action object.
- DO NOT output conversational commentary, explanations, or thought prefixes.
- Reply with EXACTLY ONE JSON action object per turn.
- You have a limited number of steps (shown as steps_left in each observation); call submit before they run out.
- When you believe the bug is fixed and all tests will pass, call the "submit" action.

SUPPORTED JSON ACTION SCHEMAS:
1. Edit a file (replaces file with complete new content):
{"type": "edit", "path": "<filename>", "content": "<complete new file content>"}

2. Run a command in the sandbox:
{"type": "run", "cmd": "<command to execute>"}

3. Submit solution when fixed:
{"type": "submit"}
"""


def get_prompt_hash() -> str:
    import hashlib
    return hashlib.sha256(SYSTEM_PROMPT.strip().encode("utf-8")).hexdigest()[:16]


def validate_action_schema(action: Any) -> Tuple[bool, str, Dict[str, Any]]:
    """Validates and normalizes action dictionary against AgentGym schema."""
    if not isinstance(action, dict):
        return False, "Response is not a JSON object.", {}

    normalized = dict(action)
    act_type = normalized.get("type") or normalized.get("action")
    if isinstance(act_type, str):
        act_type = act_type.lower().strip()
    normalized["type"] = act_type

    if act_type not in ["edit", "run", "submit"]:
        return False, f"Action 'type' must be 'edit', 'run', or 'submit', got '{act_type}'.", {}

    if act_type == "edit":
        path = normalized.get("path") or normalized.get("file") or normalized.get("filename")
        content = normalized.get("content") or normalized.get("code") or normalized.get("new_content")
        normalized["path"] = path
        normalized["content"] = content

        if not path or not isinstance(path, str):
            return False, "'edit' action requires a valid string 'path'.", {}
        if "\x00" in path:
            return False, "'edit' action path contains illegal null bytes.", {}
        if content is None or not isinstance(content, str):
            return False, "'edit' action requires string 'content'.", {}
        if len(content) > 5_000_000:
            return False, "'edit' action content exceeds maximum size limit (5MB).", {}

    if act_type == "run":
        cmd = normalized.get("cmd") or normalized.get("command")
        normalized["cmd"] = cmd
        if not cmd or not isinstance(cmd, str):
            return False, "'run' action requires a valid string 'cmd'.", {}
        if "\x00" in cmd:
            return False, "'run' action cmd contains illegal null bytes.", {}
        if len(cmd) > 10_000:
            return False, "'run' action cmd exceeds maximum length limit (10KB).", {}

    return True, "", normalized


def _sanitize_json_text(text: str) -> str:
    """Cleans Python triple quotes, trailing commas, and unescaped newlines inside JSON."""
    s = text

    # Convert triple double-quotes """...""" or escaped triple double-quotes \"\"\"...\"\"\" to escaped JSON string
    def replace_triple(m):
        content = m.group(1)
        # Unescape already escaped quotes if needed
        content = content.replace(r'\"', '"').replace(r"\'", "'")
        return json.dumps(content)

    s = re.sub(r'"""([\s\S]*?)"""', replace_triple, s)
    s = re.sub(r"'''([\s\S]*?)'''", replace_triple, s)
    s = re.sub(r'\\\"\\\"\\\"([\s\S]*?)\\\"\\\"\\\"', replace_triple, s)

    # Strip trailing commas before closing braces/brackets
    s = re.sub(r',\s*([}\]])', r'\1', s)
    return s


def extract_action_json(text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Robustly extracts valid JSON action object from model reply.

    Handles:
    - Clean JSON objects (no extraction needed -> returns action, False)
    - Python-style triple quotes (\"\"\"...\"\"\" and '''...''')
    - <think>...</think> reasoning blocks
    - Markdown code fences (```json ... ```)
    - Commentary before/after JSON
    - Multiple JSON objects (returns the LAST valid action object)
    - Trailing commas
    """
    if not text or not isinstance(text, str):
        return None, False

    raw = text.strip()

    # 1. First test: direct clean JSON parse
    try:
        data = json.loads(raw)
        valid, _, norm_action = validate_action_schema(data)
        if valid:
            return norm_action, False
    except Exception:
        pass

    # 2. Try sanitized direct parse
    try:
        sanitized_raw = _sanitize_json_text(raw)
        data = json.loads(sanitized_raw)
        valid, _, norm_action = validate_action_schema(data)
        if valid:
            return norm_action, True
    except Exception:
        pass

    # 3. Strip <think>...</think> or <thought>...</thought> blocks
    cleaned = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", raw, flags=re.IGNORECASE).strip()

    # 4. Check for markdown code fences
    fence_matches = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
    candidate_texts = list(fence_matches) if fence_matches else []
    candidate_texts.append(cleaned)

    valid_actions = []

    for c_text in candidate_texts:
        c_san = _sanitize_json_text(c_text.strip())

        # Try direct parse of candidate text
        try:
            d = json.loads(c_san)
            valid, _, norm = validate_action_schema(d)
            if valid:
                valid_actions.append(norm)
        except Exception:
            pass

        # Search for all balanced JSON objects { ... } in the text
        stack = []
        start_idx = None
        for i, ch in enumerate(c_san):
            if ch == "{":
                if not stack:
                    start_idx = i
                stack.append("{")
            elif ch == "}":
                if stack:
                    stack.pop()
                    if not stack and start_idx is not None:
                        substr = c_san[start_idx : i + 1]
                        try:
                            obj = json.loads(substr)
                            valid, _, norm = validate_action_schema(obj)
                            if valid:
                                valid_actions.append(norm)
                        except Exception:
                            # Try further sanitization on the substring
                            try:
                                obj2 = json.loads(_sanitize_json_text(substr))
                                valid2, _, norm2 = validate_action_schema(obj2)
                                if valid2:
                                    valid_actions.append(norm2)
                            except Exception:
                                pass
                        start_idx = None

    if valid_actions:
        return valid_actions[-1], True

    return None, True


class Agent:
    """Agent that communicates with Nebius Token Factory or compatible LLM APIs."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        config_path: str = "config.yaml",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        execution_mode: str = "hackathon",
        fallback_provider: Optional[str] = None,
    ):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.execution_mode = execution_mode
        self.fallback_provider = fallback_provider

        models_cfg = self.config.get("models", {})
        default_model = models_cfg.get("nemotron_nano", {}).get("name", "nvidia/nemotron-3-nano-30b-a3b")
        self.model_name = model_name or default_model

        # Authoritative validation of provider policy
        val_res = validate_execution_config(
            execution_mode=self.execution_mode,
            provider=provider,
            fallback=self.fallback_provider,
            config_path=config_path,
            model_name=self.model_name,
        )
        self.provider = val_res["provider"]
        self.fallback_provider = val_res["fallback"]

        self.client = self._init_client()
        self.conversation_history: List[Dict[str, str]] = []

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_client(self) -> OpenAI:
        prov_info = resolve_provider_config(self.provider, config_path=self.config_path)
        base_url = prov_info.get("base_url", NEBIUS_CANONICAL_ENDPOINT if self.provider == "nebius" else "https://openrouter.ai/api/v1")
        key_env = prov_info.get("api_key_env", "NEBIUS_API_KEY" if self.provider == "nebius" else "")
        api_key = os.getenv(key_env, "") if key_env else ""

        if self.execution_mode == "hackathon":
            if not api_key and self.provider != "mock":
                raise ProviderPolicyError(
                    "Hackathon execution requires Nebius.\n"
                    f"Nebius API configuration is missing (environment variable '{key_env}' is not set or empty).\n"
                    "Set the required Nebius credentials/configuration before launching the official evaluation.\n"
                    "No provider fallback is enabled in hackathon mode."
                )
        else:
            # Development mode fallback if configured and primary key is missing
            if not api_key and self.fallback_provider:
                fb_info = resolve_provider_config(self.fallback_provider, config_path=self.config_path)
                fb_key = os.getenv(fb_info.get("api_key_env", ""), "")
                if fb_key:
                    base_url = fb_info.get("base_url", base_url)
                    api_key = fb_key
                    self.provider = self.fallback_provider

        if not api_key:
            api_key = "dummy_key"

        return OpenAI(base_url=base_url, api_key=api_key)

    def reset(self) -> None:
        """Reset conversation history for a new episode."""
        self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def act(self, observation: Dict[str, Any]) -> Tuple[Dict[str, Any], int, List[Dict[str, str]], bool]:
        """Sends observation to model, parses JSON action with 1 retry on invalid format.

        Returns:
            (parsed_action, latency_ms, messages_snapshot, extraction_needed)
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

        # Attempt 1 extraction
        action, extraction_needed = extract_action_json(reply)

        if action is None:
            # Retry once with error feedback
            retry_msg = (
                f"ERROR: Your previous response did not contain a valid JSON action. "
                f"You must respond with ONLY a single valid JSON object: "
                f'{{"type": "edit", "path": "<filename>", "content": "<new code>"}} or '
                f'{{"type": "run", "cmd": "<command>"}} or {{"type": "submit"}}. '
                f"Do not include any conversational sentences or explanations."
            )
            self.conversation_history.append({"role": "assistant", "content": reply})
            self.conversation_history.append({"role": "user", "content": retry_msg})

            reply2, lat2 = self._call_model()
            latency_ms += lat2
            action2, _ = extract_action_json(reply2)
            if action2 is not None:
                self.conversation_history.append({"role": "assistant", "content": reply2})
                return action2, latency_ms, list(self.conversation_history), True

            # If still invalid, fallback to failed step as specified
            action = {"type": "run", "cmd": "echo 'Invalid JSON action'"}
            self.conversation_history.append({"role": "assistant", "content": reply2})
            return action, latency_ms, list(self.conversation_history), True

        self.conversation_history.append({"role": "assistant", "content": reply})
        return action, latency_ms, list(self.conversation_history), extraction_needed

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
                    response_format={"type": "json_object"},
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

    def act(self, observation: Dict[str, Any]) -> Tuple[Dict[str, Any], int, List[Dict[str, str]], bool]:
        self.step_counter += 1
        obs_text = f"OBSERVATION: steps_left={observation.get('steps_left')}"
        self.conversation_history.append({"role": "user", "content": obs_text})
        time.sleep(0.01)

        if self.mode == "solver":
            # Apply all reference fix files sequentially, then submit
            files_list = list(self.reference_fix.items())
            if self.step_counter <= len(files_list):
                path, content = files_list[self.step_counter - 1]
                action = {"type": "edit", "path": path, "content": content}
            else:
                action = {"type": "submit"}
        elif self.mode == "noop_submit":
            action = {"type": "submit"}
        elif self.mode == "regression":
            action = {"type": "edit", "path": "mathutils.py", "content": "def broken(): raise Exception('Broken')"}
        else:  # no-op
            action = {"type": "run", "cmd": "python -c 'print(\"exploring...\")'"}

        self.conversation_history.append({"role": "assistant", "content": json.dumps(action)})
        return action, 15, list(self.conversation_history), False
