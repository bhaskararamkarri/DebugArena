"""Provider policy enforcement and execution mode resolution for DebugArena."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


class ExecutionMode(str, Enum):
    """Authoritative execution modes for DebugArena."""
    HACKATHON = "hackathon"
    DEVELOPMENT = "development"


HACKATHON_TRACK_NAME: str = "Coding and Agentic Engineering"
NEBIUS_CANONICAL_ENDPOINT: str = "https://api.tokenfactory.nebius.com/v1"


class ProviderPolicyError(ValueError):
    """Raised when provider configuration or execution mode contracts are violated."""
    pass


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration YAML safely."""
    p = Path(config_path)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


def validate_execution_config(
    execution_mode: Union[str, ExecutionMode] = "hackathon",
    provider: Optional[str] = None,
    fallback: Optional[str] = None,
    config_path: str = "config.yaml",
    use_mock_solver: bool = False,
    use_noop_solver: bool = False,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Validates and resolves provider configuration against execution mode policy.

    Invariants for HACKATHON mode:
    1. Provider must be 'nebius' (or None/empty, which resolves to 'nebius').
    2. Fallback provider must be None. Any non-empty fallback is rejected.
    3. If not using an explicit mock/noop baseline agent, required Nebius credentials
       (NEBIUS_API_KEY) must be present and non-empty in the environment.
    4. Silent fallback to OpenRouter, NVIDIA, or other providers is strictly forbidden.

    Args:
        execution_mode: 'hackathon' or 'development'.
        provider: Requested provider name.
        fallback: Optional fallback provider name.
        config_path: Path to config.yaml.
        use_mock_solver: Whether mock reference solver is explicitly enabled.
        use_noop_solver: Whether no-op submit baseline is explicitly enabled.
        model_name: Optional model identifier.

    Returns:
        Dict with authoritative resolved configuration:
        {
            "execution_mode": "hackathon" | "development",
            "provider": str,
            "fallback": Optional[str],
        }

    Raises:
        ProviderPolicyError: If any policy rule is violated.
    """
    raw_mode = execution_mode.value if isinstance(execution_mode, ExecutionMode) else str(execution_mode)
    mode_clean = raw_mode.lower().strip()

    if mode_clean not in [ExecutionMode.HACKATHON.value, ExecutionMode.DEVELOPMENT.value]:
        raise ProviderPolicyError(
            f"Invalid execution mode '{execution_mode}'. Must be 'hackathon' or 'development'."
        )

    config = load_config(config_path)
    providers_cfg = config.get("providers", {})

    if mode_clean == ExecutionMode.HACKATHON.value:
        # Provider must be Nebius
        if provider is not None and str(provider).strip():
            prov_clean = str(provider).lower().strip()
            if prov_clean != "nebius":
                raise ProviderPolicyError(
                    f"Hackathon execution requires Nebius. Provider '{provider}' is not allowed in hackathon mode."
                )
        resolved_provider = "nebius"

        # Fallback must be None
        if fallback is not None and str(fallback).strip() and str(fallback).lower().strip() not in ["none", "null", ""]:
            raise ProviderPolicyError(
                f"No provider fallback is enabled in hackathon mode. Fallback '{fallback}' is not allowed."
            )
        resolved_fallback = None

        # Validate Nebius credentials unless running an offline baseline
        if not (use_mock_solver or use_noop_solver):
            nebius_cfg = providers_cfg.get("nebius", {})
            key_env = nebius_cfg.get("api_key_env", "NEBIUS_API_KEY")
            api_key = os.getenv(key_env, "").strip()

            if not api_key:
                raise ProviderPolicyError(
                    "Hackathon execution requires Nebius.\n"
                    f"Nebius API configuration is missing (environment variable '{key_env}' is not set or empty).\n"
                    "Set the required Nebius credentials/configuration before launching the official evaluation.\n"
                    "No provider fallback is enabled in hackathon mode."
                )

        return {
            "execution_mode": ExecutionMode.HACKATHON.value,
            "provider": resolved_provider,
            "fallback": resolved_fallback,
        }

    else:
        # Development mode
        resolved_provider = (str(provider).lower().strip() if provider else config.get("default_provider", "openrouter"))
        resolved_fallback = str(fallback).lower().strip() if (fallback and str(fallback).lower().strip() not in ["none", "null", ""]) else None

        return {
            "execution_mode": ExecutionMode.DEVELOPMENT.value,
            "provider": resolved_provider,
            "fallback": resolved_fallback,
        }


def resolve_provider_config(
    provider: str,
    config_path: str = "config.yaml",
) -> Dict[str, Any]:
    """Retrieves base URL and API key for a resolved provider from authoritative configuration."""
    config = load_config(config_path)
    providers_cfg = config.get("providers", {})
    prov_cfg = providers_cfg.get(provider, {})
    default_url = NEBIUS_CANONICAL_ENDPOINT if provider == "nebius" else "https://openrouter.ai/api/v1"
    base_url = prov_cfg.get("base_url", default_url)
    key_env = prov_cfg.get("api_key_env", "NEBIUS_API_KEY" if provider == "nebius" else "")
    api_key = os.getenv(key_env, "") if key_env else ""
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key_env": key_env,
        "api_key": api_key,
    }
