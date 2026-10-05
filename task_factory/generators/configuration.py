"""Category J: Configuration & Layering Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class ConfigurationTaskGenerator(BaseGenerator):
    """Generates realistic multi-tier configuration precedence and deep-merge tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v15_hierarchical_config_precedence")
        sub_type = spec.get("sub_type", "precedence")

        if sub_type == "deep_merge" or "deep_merge" in task_id:
            return self._generate_env_interpolation_deep_merge(task_id, spec, seed)
        elif sub_type == "feature_flags" or "flag" in task_id:
            return self._generate_feature_flags(task_id, spec, seed)
        elif sub_type == "schema_evolution" or "schema_evolution" in task_id:
            return self._generate_schema_evolution(task_id, spec, seed)
        elif sub_type == "hierarchical_rate_limiter" or "rate_limiter" in task_id:
            return self._generate_hierarchical_rate_limiter(task_id, spec, seed)
        return self._generate_hierarchical_precedence(task_id, spec, seed)

    def _generate_hierarchical_precedence(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "defaults.py": (
                '"""Default configuration baseline."""\n\n'
                'DEFAULT_CONFIG = {\n'
                '    "server": {\n'
                '        "host": "0.0.0.0",\n'
                '        "port": 8080,\n'
                '        "workers": 4,\n'
                '    },\n'
                '    "database": {\n'
                '        "pool_size": 10,\n'
                '        "timeout_ms": 5000,\n'
                '        "read_only": False,\n'
                '    },\n'
                '    "logging": {\n'
                '        "level": "INFO",\n'
                '        "format": "json",\n'
                '    },\n'
                '}\n'
            ),
            "loader.py": (
                '"""Configuration source loader with precedence layers."""\n\n'
                'from typing import Any, Dict\n'
                'from defaults import DEFAULT_CONFIG\n\n\n'
                'def deep_clone(d: Dict[str, Any]) -> Dict[str, Any]:\n'
                '    res = {}\n'
                '    for k, v in d.items():\n'
                '        res[k] = deep_clone(v) if isinstance(v, dict) else v\n'
                '    return res\n\n\n'
                'class ConfigLoader:\n'
                '    """Loads configuration by applying layers in order: Defaults -> File -> Env -> Cli."""\n\n'
                '    def __init__(self):\n'
                '        self.layers: list[Dict[str, Any]] = []\n\n'
                '    def add_layer(self, layer_dict: Dict[str, Any]) -> None:\n'
                '        if layer_dict:\n'
                '            self.layers.append(deep_clone(layer_dict))\n\n'
                '    def build_effective_config(self) -> Dict[str, Any]:\n'
                '        result = deep_clone(DEFAULT_CONFIG)\n'
                '        # BUG: Layer merging is shallow and overwrites entire sub-dictionaries\n'
                '        # instead of performing recursive deep property updates.\n'
                '        for layer in self.layers:\n'
                '            for section, values in layer.items():\n'
                '                if section in result and isinstance(values, dict):\n'
                '                    result[section] = values  # Replaces entire section, losing unmentioned defaults!\n'
                '                else:\n'
                '                    result[section] = values\n'
                '        return result\n'
            ),
            "config.py": (
                '"""Application configuration accessor and validation."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from loader import ConfigLoader\n\n\n'
                'class AppConfig:\n'
                '    def __init__(self, loader: ConfigLoader):\n'
                '        self.loader = loader\n'
                '        self._data: Optional[Dict[str, Any]] = None\n\n'
                '    def reload(self) -> None:\n'
                '        self._data = self.loader.build_effective_config()\n\n'
                '    def get(self, path: str, default: Any = None) -> Any:\n'
                '        if self._data is None:\n'
                '            self.reload()\n'
                '        assert self._data is not None\n'
                '        keys = path.split(".")\n'
                '        curr: Any = self._data\n'
                '        for k in keys:\n'
                '            if not isinstance(curr, dict) or k not in curr:\n'
                '                return default\n'
                '            curr = curr[k]\n'
                '        # BUG: If the value in config is explicitly None, returns default instead of None\n'
                '        return default if curr is None else curr\n'
            ),
        }

        reference_fix = {
            "loader.py": (
                '"""Configuration source loader with precedence layers."""\n\n'
                'from typing import Any, Dict\n'
                'from defaults import DEFAULT_CONFIG\n\n\n'
                'def deep_clone(d: Dict[str, Any]) -> Dict[str, Any]:\n'
                '    res = {}\n'
                '    for k, v in d.items():\n'
                '        res[k] = deep_clone(v) if isinstance(v, dict) else v\n'
                '    return res\n\n\n'
                'def _deep_merge_into(base: Dict[str, Any], override: Dict[str, Any]) -> None:\n'
                '    for k, v in override.items():\n'
                '        if k in base and isinstance(base[k], dict) and isinstance(v, dict):\n'
                '            _deep_merge_into(base[k], v)\n'
                '        else:\n'
                '            base[k] = deep_clone(v) if isinstance(v, dict) else v\n\n\n'
                'class ConfigLoader:\n'
                '    """Loads configuration by applying layers in order: Defaults -> File -> Env -> Cli."""\n\n'
                '    def __init__(self):\n'
                '        self.layers: list[Dict[str, Any]] = []\n\n'
                '    def add_layer(self, layer_dict: Dict[str, Any]) -> None:\n'
                '        if layer_dict:\n'
                '            self.layers.append(deep_clone(layer_dict))\n\n'
                '    def build_effective_config(self) -> Dict[str, Any]:\n'
                '        result = deep_clone(DEFAULT_CONFIG)\n'
                '        for layer in self.layers:\n'
                '            _deep_merge_into(result, layer)\n'
                '        return result\n'
            ),
            "config.py": (
                '"""Application configuration accessor and validation."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from loader import ConfigLoader\n\n\n'
                'class AppConfig:\n'
                '    def __init__(self, loader: ConfigLoader):\n'
                '        self.loader = loader\n'
                '        self._data: Optional[Dict[str, Any]] = None\n\n'
                '    def reload(self) -> None:\n'
                '        self._data = self.loader.build_effective_config()\n\n'
                '    def get(self, path: str, default: Any = None) -> Any:\n'
                '        if self._data is None:\n'
                '            self.reload()\n'
                '        assert self._data is not None\n'
                '        keys = path.split(".")\n'
                '        curr: Any = self._data\n'
                '        for k in keys:\n'
                '            if not isinstance(curr, dict) or k not in curr:\n'
                '                return default\n'
                '            curr = curr[k]\n'
                '        return curr\n'
            ),
        }

        tests = {
            "test_config_precedence.py": (
                'from loader import ConfigLoader\n'
                'from config import AppConfig\n\n\n'
                'def test_defaults_preserved():\n'
                '    loader = ConfigLoader()\n'
                '    cfg = AppConfig(loader)\n'
                '    assert cfg.get("server.port") == 8080\n'
                '    assert cfg.get("server.host") == "0.0.0.0"\n'
                '    assert cfg.get("database.pool_size") == 10\n\n\n'
                'def test_partial_section_override_preserves_sibling_defaults():\n'
                '    loader = ConfigLoader()\n'
                '    # File layer only overrides server.port to 9090\n'
                '    loader.add_layer({"server": {"port": 9090}})\n'
                '    cfg = AppConfig(loader)\n'
                '    assert cfg.get("server.port") == 9090\n'
                '    assert cfg.get("server.host") == "0.0.0.0"  # Must preserve sibling host\n'
                '    assert cfg.get("server.workers") == 4        # Must preserve sibling workers\n\n\n'
                'def test_multi_layer_precedence_ordering():\n'
                '    loader = ConfigLoader()\n'
                '    # Layer 1: File\n'
                '    loader.add_layer({"database": {"pool_size": 20, "timeout_ms": 3000}})\n'
                '    # Layer 2: Env override takes precedence over File\n'
                '    loader.add_layer({"database": {"pool_size": 50}})\n'
                '    cfg = AppConfig(loader)\n'
                '    assert cfg.get("database.pool_size") == 50\n'
                '    assert cfg.get("database.timeout_ms") == 3000\n'
                '    assert cfg.get("database.read_only") is False\n\n\n'
                'def test_explicit_none_value_retrieval():\n'
                '    loader = ConfigLoader()\n'
                '    loader.add_layer({"custom": {"nullable_flag": None}})\n'
                '    cfg = AppConfig(loader)\n'
                '    assert cfg.get("custom.nullable_flag", default="FALLBACK") is None\n\n\n'
                'def test_missing_path_returns_specified_default():\n'
                '    loader = ConfigLoader()\n'
                '    cfg = AppConfig(loader)\n'
                '    assert cfg.get("server.ssl.cert", "default.crt") == "default.crt"\n'
                '    assert cfg.get("nonexistent.key") is None\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "configuration_precedence_shallow_merge",
            "categories": ["J", "E"],
            "description": "Hierarchical configuration loader shallow-merges section overrides, dropping unmentioned default properties.",
            "spec_notes": "ConfigLoader must recursively merge layer overrides while preserving defaults and explicit None values.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "infrastructure",
            },
        }

    def _generate_env_interpolation_deep_merge(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "schema.py": (
                '"""Configuration type schema and validations."""\n\n'
                'from typing import Any, Dict, List\n\n\n'
                'class SchemaValidator:\n'
                '    @staticmethod\n'
                '    def validate_type(value: Any, expected_type: type) -> bool:\n'
                '        return isinstance(value, expected_type)\n'
            ),
            "interpolator.py": (
                '"""Resolves environment variable expressions in configuration strings."""\n\n'
                'import re\n'
                'from typing import Any, Dict\n\n'
                'PATTERN = re.compile(r"\\$\\{([A-Za-z0-9_]+)(?::-([^}]*))?\\}")\n\n\n'
                'class EnvInterpolator:\n'
                '    def __init__(self, env: Dict[str, str]):\n'
                '        self.env = env\n\n'
                '    def interpolate_string(self, text: str) -> str:\n'
                '        def replace(match: re.Match) -> str:\n'
                '            var_name = match.group(1)\n'
                '            default_val = match.group(2) if match.group(2) is not None else ""\n'
                '            # BUG: Returns empty string when env var is missing and default is given as empty string vs None\n'
                '            if var_name in self.env:\n'
                '                return self.env[var_name]\n'
                '            if match.group(2) is not None:\n'
                '                return default_val\n'
                '            return match.group(0)  # Unresolved literal\n\n'
                '        # BUG: Only executes a single pass, failing nested or chained expressions like ${A:-${B}}\n'
                '        return PATTERN.sub(replace, text)\n\n'
                '    def interpolate_tree(self, obj: Any) -> Any:\n'
                '        if isinstance(obj, str):\n'
                '            return self.interpolate_string(obj)\n'
                '        if isinstance(obj, dict):\n'
                '            return {k: self.interpolate_tree(v) for k, v in obj.items()}\n'
                '        if isinstance(obj, list):\n'
                '            return [self.interpolate_tree(elem) for elem in obj]\n'
                '        return obj\n'
            ),
            "merger.py": (
                '"""Deep merging of nested configurations with conflict strategies."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:\n'
                '    result = dict(target)\n'
                '    for k, v in source.items():\n'
                '        if k in result and isinstance(result[k], dict) and isinstance(v, dict):\n'
                '            result[k] = deep_merge(result[k], v)\n'
                '        else:\n'
                '            result[k] = v\n'
                '    return result\n'
            ),
            "provider.py": (
                '"""Unified configuration provider combining interpolation and merging."""\n\n'
                'from typing import Any, Dict\n'
                'from interpolator import EnvInterpolator\n'
                'from merger import deep_merge\n\n\n'
                'class ConfigProvider:\n'
                '    def __init__(self, env: Dict[str, str]):\n'
                '        self.interpolator = EnvInterpolator(env)\n\n'
                '    def compose(self, base_cfg: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:\n'
                '        merged = deep_merge(base_cfg, overrides)\n'
                '        return self.interpolator.interpolate_tree(merged)\n'
            ),
        }

        reference_fix = {
            "interpolator.py": (
                '"""Resolves environment variable expressions in configuration strings."""\n\n'
                'import re\n'
                'from typing import Any, Dict\n\n'
                'PATTERN = re.compile(r"\\$\\{([A-Za-z0-9_]+)(?::-([^}]*))?\\}")\n\n\n'
                'class EnvInterpolator:\n'
                '    def __init__(self, env: Dict[str, str]):\n'
                '        self.env = env\n\n'
                '    def interpolate_string(self, text: str) -> str:\n'
                '        def replace_single(match: re.Match) -> str:\n'
                '            var_name = match.group(1)\n'
                '            default_val = match.group(2)\n'
                '            if var_name in self.env:\n'
                '                return self.env[var_name]\n'
                '            if default_val is not None:\n'
                '                return default_val\n'
                '            return match.group(0)\n\n'
                '        prev = text\n'
                '        for _ in range(5):\n'
                '            nxt = PATTERN.sub(replace_single, prev)\n'
                '            if nxt == prev:\n'
                '                break\n'
                '            prev = nxt\n'
                '        return prev\n\n'
                '    def interpolate_tree(self, obj: Any) -> Any:\n'
                '        if isinstance(obj, str):\n'
                '            return self.interpolate_string(obj)\n'
                '        if isinstance(obj, dict):\n'
                '            return {k: self.interpolate_tree(v) for k, v in obj.items()}\n'
                '        if isinstance(obj, list):\n'
                '            return [self.interpolate_tree(elem) for elem in obj]\n'
                '        return obj\n'
            )
        }

        tests = {
            "test_config_interpolation.py": (
                'from provider import ConfigProvider\n\n\n'
                'def test_basic_env_substitution():\n'
                '    env = {"DB_HOST": "postgres.internal", "DB_PORT": "5432"}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"db": {"host": "${DB_HOST}", "port": "${DB_PORT}"}}\n'
                '    cfg = provider.compose(base, {})\n'
                '    assert cfg["db"]["host"] == "postgres.internal"\n'
                '    assert cfg["db"]["port"] == "5432"\n\n\n'
                'def test_default_fallback_when_env_missing():\n'
                '    env = {}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"api": {"timeout": "${API_TIMEOUT:-30}", "prefix": "${API_PREFIX:-/v1}"}}\n'
                '    cfg = provider.compose(base, {})\n'
                '    assert cfg["api"]["timeout"] == "30"\n'
                '    assert cfg["api"]["prefix"] == "/v1"\n\n\n'
                'def test_nested_array_and_dict_interpolation():\n'
                '    env = {"NODE_1": "10.0.0.1", "NODE_2": "10.0.0.2"}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"cluster": {"nodes": ["${NODE_1}", "${NODE_2}", "${NODE_3:-10.0.0.3}"]}}\n'
                '    cfg = provider.compose(base, {})\n'
                '    assert cfg["cluster"]["nodes"] == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]\n\n\n'
                'def test_override_deep_merge_with_interpolation():\n'
                '    env = {"LOG_LEVEL": "DEBUG"}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"service": {"name": "auth", "log": {"level": "INFO", "format": "text"}}}\n'
                '    overrides = {"service": {"log": {"level": "${LOG_LEVEL}"}}}\n'
                '    cfg = provider.compose(base, overrides)\n'
                '    assert cfg["service"]["name"] == "auth"\n'
                '    assert cfg["service"]["log"]["level"] == "DEBUG"\n'
                '    assert cfg["service"]["log"]["format"] == "text"\n\n\n'
                'def test_unresolved_env_without_default_remains_literal():\n'
                '    env = {}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"custom": {"raw_template": "${UNSET_VAR}"}}\n'
                '    cfg = provider.compose(base, {})\n'
                '    assert cfg["custom"]["raw_template"] == "${UNSET_VAR}"\n\n\n'
                'def test_chained_nested_expression_resolution():\n'
                '    env = {"SECONDARY": "backup.server"}\n'
                '    provider = ConfigProvider(env)\n'
                '    base = {"host": "${PRIMARY:-${SECONDARY}}"}\n'
                '    cfg = provider.compose(base, {})\n'
                '    assert cfg["host"] == "backup.server"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "env_interpolation_chained_resolution",
            "categories": ["J", "E", "F"],
            "description": "Environment variable interpolator fails on chained fallback expressions and nested array structures.",
            "spec_notes": "EnvInterpolator must resolve nested variable expressions iteratively and handle deep merging.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "infrastructure",
            },
        }

    def _generate_feature_flags(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "flag_rule.py": (
                '"""Targeting rule definition for feature flags."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict, List, Optional\n\n\n'
                '@dataclass\n'
                'class TargetingRule:\n'
                '    attribute: str\n'
                '    operator: str  # "IN", "EQUALS", "PERCENTAGE"\n'
                '    values: List[Any]\n'
                '    serve_value: bool\n'
            ),
            "evaluator.py": (
                '"""Feature flag rules evaluation engine."""\n\n'
                'from typing import Any, Dict, List\n'
                'from flag_rule import TargetingRule\n\n\n'
                'class FlagEvaluator:\n'
                '    def __init__(self, flag_name: str, default_value: bool, rules: List[TargetingRule]):\n'
                '        self.flag_name = flag_name\n'
                '        self.default_value = default_value\n'
                '        self.rules = rules\n\n'
                '    def evaluate(self, user_context: Dict[str, Any]) -> bool:\n'
                '        # Rules are evaluated in strict priority order; first matching rule serves value\n'
                '        for rule in self.rules:\n'
                '            attr_val = user_context.get(rule.attribute)\n'
                '            if attr_val is None:\n'
                '                continue\n'
                '            if rule.operator == "EQUALS" and attr_val == rule.values[0]:\n'
                '                return rule.serve_value\n'
                '            elif rule.operator == "IN" and attr_val in rule.values:\n'
                '                return rule.serve_value\n'
                '            elif rule.operator == "PERCENTAGE":\n'
                '                # Hash user_id to compute bucket 0..99\n'
                '                user_id = str(user_context.get("user_id", ""))\n'
                '                bucket = sum(ord(c) for c in user_id) % 100\n'
                '                # BUG: Percentage comparison checks bucket > threshold instead of bucket < threshold!\n'
                '                threshold = int(rule.values[0])\n'
                '                if bucket > threshold:\n'
                '                    return rule.serve_value\n'
                '        return self.default_value\n'
            ),
            "client.py": (
                '"""Feature flag client service."""\n\n'
                'from typing import Any, Dict\n'
                'from evaluator import FlagEvaluator\n\n\n'
                'class FeatureFlagClient:\n'
                '    def __init__(self, flags: Dict[str, FlagEvaluator]):\n'
                '        self.flags = flags\n\n'
                '    def is_enabled(self, flag_name: str, context: Dict[str, Any]) -> bool:\n'
                '        evaluator = self.flags.get(flag_name)\n'
                '        if not evaluator:\n'
                '            return False\n'
                '        return evaluator.evaluate(context)\n'
            ),
        }

        reference_fix = {
            "evaluator.py": (
                '"""Feature flag rules evaluation engine."""\n\n'
                'from typing import Any, Dict, List\n'
                'from flag_rule import TargetingRule\n\n\n'
                'class FlagEvaluator:\n'
                '    def __init__(self, flag_name: str, default_value: bool, rules: List[TargetingRule]):\n'
                '        self.flag_name = flag_name\n'
                '        self.default_value = default_value\n'
                '        self.rules = rules\n\n'
                '    def evaluate(self, user_context: Dict[str, Any]) -> bool:\n'
                '        for rule in self.rules:\n'
                '            attr_val = user_context.get(rule.attribute)\n'
                '            if attr_val is None and rule.operator != "PERCENTAGE":\n'
                '                continue\n'
                '            if rule.operator == "EQUALS" and attr_val == rule.values[0]:\n'
                '                return rule.serve_value\n'
                '            elif rule.operator == "IN" and attr_val in rule.values:\n'
                '                return rule.serve_value\n'
                '            elif rule.operator == "PERCENTAGE":\n'
                '                user_id = str(user_context.get("user_id", ""))\n'
                '                bucket = sum(ord(c) for c in user_id) % 100\n'
                '                threshold = int(rule.values[0])\n'
                '                if bucket < threshold:\n'
                '                    return rule.serve_value\n'
                '        return self.default_value\n'
            )
        }

        tests = {
            "test_feature_flags.py": (
                'from flag_rule import TargetingRule\n'
                'from evaluator import FlagEvaluator\n'
                'from client import FeatureFlagClient\n\n\n'
                'def test_default_fallback_value():\n'
                '    ev = FlagEvaluator("beta_ui", default_value=False, rules=[])\n'
                '    client = FeatureFlagClient({"beta_ui": ev})\n'
                '    assert client.is_enabled("beta_ui", {"user_id": "u1"}) is False\n\n\n'
                'def test_user_in_whitelist_segment():\n'
                '    rule = TargetingRule("country", "IN", ["US", "CA"], True)\n'
                '    ev = FlagEvaluator("fast_checkout", default_value=False, rules=[rule])\n'
                '    client = FeatureFlagClient({"fast_checkout": ev})\n'
                '    assert client.is_enabled("fast_checkout", {"country": "US"}) is True\n'
                '    assert client.is_enabled("fast_checkout", {"country": "DE"}) is False\n\n\n'
                'def test_percentage_rollout_zero_percent_serves_none():\n'
                '    # 0% rollout must disable flag for all users\n'
                '    rule = TargetingRule("user_id", "PERCENTAGE", [0], True)\n'
                '    ev = FlagEvaluator("experimental", default_value=False, rules=[rule])\n'
                '    client = FeatureFlagClient({"experimental": ev})\n'
                '    for uid in ["user_1", "user_2", "user_3", "admin"]:\n'
                '        assert client.is_enabled("experimental", {"user_id": uid}) is False\n\n\n'
                'def test_percentage_rollout_100_percent_serves_all():\n'
                '    # 100% rollout must enable flag for all users\n'
                '    rule = TargetingRule("user_id", "PERCENTAGE", [100], True)\n'
                '    ev = FlagEvaluator("rollout_full", default_value=False, rules=[rule])\n'
                '    client = FeatureFlagClient({"rollout_full": ev})\n'
                '    for uid in ["a", "b", "c", "d", "e"]:\n'
                '        assert client.is_enabled("rollout_full", {"user_id": uid}) is True\n\n\n'
                'def test_targeting_rule_precedence_order():\n'
                '    # Whitelist rule has priority over general rollout\n'
                '    r1 = TargetingRule("email", "EQUALS", ["vip@corp.com"], True)\n'
                '    r2 = TargetingRule("tier", "IN", ["free"], False)\n'
                '    ev = FlagEvaluator("premium_feature", default_value=False, rules=[r1, r2])\n'
                '    client = FeatureFlagClient({"premium_feature": ev})\n'
                '    # VIP user with free tier gets True because r1 matches first\n'
                '    assert client.is_enabled("premium_feature", {"email": "vip@corp.com", "tier": "free"}) is True\n'
                '    assert client.is_enabled("premium_feature", {"email": "other@corp.com", "tier": "free"}) is False\n\n\n'
                'def test_missing_flag_returns_false():\n'
                '    client = FeatureFlagClient({})\n'
                '    assert client.is_enabled("unregistered", {}) is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "feature_flag_percentage_bucket_comparator_inversion",
            "categories": ["J", "H"],
            "description": "Feature flag percentage rollout comparator inverts bucket calculation (> instead of <), causing 0% rollouts to enable flags for majority of users.",
            "spec_notes": "FlagEvaluator must evaluate percentage rollout as bucket < threshold.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "configuration",
            },
        }

    def _generate_schema_evolution(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Schema payload representations."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Any, Dict, List, Optional\n\n\n'
                '@dataclass\n'
                'class SchemaRecord:\n'
                '    version: int\n'
                '    data: Dict[str, Any]\n'
            ),
            "migrator.py": (
                '"""Field-level schema migration functions."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class FieldMigrator:\n'
                '    @staticmethod\n'
                '    def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:\n'
                '        out = dict(data)\n'
                '        # Rename username -> user_name and combine first/last into full_name\n'
                '        if "username" in out:\n'
                '            out["user_name"] = out.pop("username")\n'
                '        fn = out.pop("first_name", "")\n'
                '        ln = out.pop("last_name", "")\n'
                '        out["full_name"] = f"{fn} {ln}".strip()\n'
                '        # BUG: Uses `or` defaulting which replaces explicit 0 / False / empty with fallback!\n'
                '        out["retry_count"] = out.get("retry_count") or 3\n'
                '        out["is_active"] = out.get("is_active") or True\n'
                '        return out\n\n'
                '    @staticmethod\n'
                '    def migrate_v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:\n'
                '        out = dict(data)\n'
                '        # Restructure full_name and wrap into profile\n'
                '        profile = {\n'
                '            "name": out.pop("full_name", ""),\n'
                '            "active": out.pop("is_active", True),\n'
                '        }\n'
                '        out["profile"] = profile\n'
                '        return out\n'
            ),
            "registry.py": (
                '"""Version step migration registry."""\n\n'
                'from typing import Callable, Dict, List, Tuple\n'
                'from migrator import FieldMigrator\n\n\n'
                'class MigrationRegistry:\n'
                '    def __init__(self):\n'
                '        self._steps: Dict[Tuple[int, int], Callable] = {}\n'
                '        self._register_default_steps()\n\n'
                '    def _register_default_steps(self):\n'
                '        self.register_step(1, 2, FieldMigrator.migrate_v1_to_v2)\n'
                '        self.register_step(2, 3, FieldMigrator.migrate_v2_to_v3)\n\n'
                '    def register_step(self, from_v: int, to_v: int, fn: Callable) -> None:\n'
                '        self._steps[(from_v, to_v)] = fn\n\n'
                '    def get_path(self, from_v: int, target_v: int) -> List[Callable]:\n'
                '        # Sequential single-step hop planner\n'
                '        path = []\n'
                '        curr = from_v\n'
                '        while curr < target_v:\n'
                '            # BUG: Lookups (curr, curr + 1) but terminates early if intermediate step missing\n'
                '            # and increments curr even on KeyError\n'
                '            step_fn = self._steps.get((curr, curr + 1))\n'
                '            if not step_fn:\n'
                '                raise ValueError(f"No migration path from {curr} to {curr+1}")\n'
                '            path.append(step_fn)\n'
                '            curr += 1\n'
                '        return path\n'
            ),
            "pipeline.py": (
                '"""Schema evolution pipeline executing multi-version transformations."""\n\n'
                'from models import SchemaRecord\n'
                'from registry import MigrationRegistry\n\n\n'
                'class SchemaEvolutionPipeline:\n'
                '    def __init__(self, registry: MigrationRegistry):\n'
                '        self.registry = registry\n\n'
                '    def upgrade(self, record: SchemaRecord, target_version: int) -> SchemaRecord:\n'
                '        if record.version == target_version:\n'
                '            return record\n'
                '        if record.version > target_version:\n'
                '            raise ValueError("Downgrades not supported")\n'
                '        fns = self.registry.get_path(record.version, target_version)\n'
                '        curr_data = dict(record.data)\n'
                '        for fn in fns:\n'
                '            curr_data = fn(curr_data)\n'
                '        return SchemaRecord(version=target_version, data=curr_data)\n'
            ),
        }

        reference_fix = {
            "migrator.py": (
                '"""Field-level schema migration functions."""\n\n'
                'from typing import Any, Dict\n\n\n'
                'class FieldMigrator:\n'
                '    @staticmethod\n'
                '    def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:\n'
                '        out = dict(data)\n'
                '        if "username" in out:\n'
                '            out["user_name"] = out.pop("username")\n'
                '        fn = out.pop("first_name", "")\n'
                '        ln = out.pop("last_name", "")\n'
                '        out["full_name"] = f"{fn} {ln}".strip()\n'
                '        if "retry_count" not in out or out["retry_count"] is None:\n'
                '            out["retry_count"] = 3\n'
                '        if "is_active" not in out or out["is_active"] is None:\n'
                '            out["is_active"] = True\n'
                '        return out\n\n'
                '    @staticmethod\n'
                '    def migrate_v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:\n'
                '        out = dict(data)\n'
                '        profile = {\n'
                '            "name": out.pop("full_name", ""),\n'
                '            "active": out.pop("is_active", True),\n'
                '        }\n'
                '        out["profile"] = profile\n'
                '        return out\n'
            )
        }

        tests = {
            "test_schema_migration.py": (
                'from models import SchemaRecord\n'
                'from registry import MigrationRegistry\n'
                'from pipeline import SchemaEvolutionPipeline\n\n\n'
                'def test_v1_to_v2_migration():\n'
                '    reg = MigrationRegistry()\n'
                '    pipe = SchemaEvolutionPipeline(reg)\n'
                '    rec = SchemaRecord(version=1, data={"username": "alice", "first_name": "Alice", "last_name": "Smith"})\n'
                '    up = pipe.upgrade(rec, 2)\n'
                '    assert up.version == 2\n'
                '    assert up.data["user_name"] == "alice"\n'
                '    assert up.data["full_name"] == "Alice Smith"\n'
                '    assert up.data["retry_count"] == 3\n'
                '    assert up.data["is_active"] is True\n\n\n'
                'def test_explicit_falsy_values_preserved_during_migration():\n'
                '    reg = MigrationRegistry()\n'
                '    pipe = SchemaEvolutionPipeline(reg)\n'
                '    # Explicit 0 retry count and False is_active must NOT be overwritten by defaults 3 and True!\n'
                '    rec = SchemaRecord(version=1, data={"username": "bob", "retry_count": 0, "is_active": False})\n'
                '    up = pipe.upgrade(rec, 2)\n'
                '    assert up.data["retry_count"] == 0\n'
                '    assert up.data["is_active"] is False\n\n\n'
                'def test_multi_hop_v1_to_v3_migration():\n'
                '    reg = MigrationRegistry()\n'
                '    pipe = SchemaEvolutionPipeline(reg)\n'
                '    rec = SchemaRecord(version=1, data={"username": "carol", "first_name": "Carol", "last_name": "Danvers", "is_active": False})\n'
                '    up = pipe.upgrade(rec, 3)\n'
                '    assert up.version == 3\n'
                '    assert up.data["user_name"] == "carol"\n'
                '    assert up.data["profile"]["name"] == "Carol Danvers"\n'
                '    assert up.data["profile"]["active"] is False\n\n\n'
                'def test_no_op_same_version():\n'
                '    reg = MigrationRegistry()\n'
                '    pipe = SchemaEvolutionPipeline(reg)\n'
                '    rec = SchemaRecord(version=2, data={"user_name": "dan", "full_name": "Dan"}) \n'
                '    assert pipe.upgrade(rec, 2).data == rec.data\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "schema_evolution_falsy_field_default_override",
            "categories": ["J", "E", "F"],
            "description": "Multi-hop schema evolution migrator inadvertently overwrites explicit falsy values (0, False) with default fallbacks.",
            "spec_notes": "FieldMigrator must check key existence and None rather than boolean truthiness when applying default values.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "schema-evolution",
            },
        }

    def _generate_hierarchical_rate_limiter(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "token_bucket.py": (
                '"""Atomic token bucket implementation."""\n\n'
                'import time\n'
                'from dataclasses import dataclass\n\n\n'
                '@dataclass\n'
                'class TokenBucket:\n'
                '    capacity: float\n'
                '    refill_rate_per_sec: float\n'
                '    tokens: float\n'
                '    last_refill_ts: float\n\n'
                '    @classmethod\n'
                '    def create(cls, capacity: float, refill_rate_per_sec: float) -> "TokenBucket":\n'
                '        return cls(capacity, refill_rate_per_sec, capacity, 0.0)\n\n'
                '    def refill(self, now: float) -> None:\n'
                '        if self.last_refill_ts == 0.0:\n'
                '            self.last_refill_ts = now\n'
                '            return\n'
                '        delta = max(0.0, now - self.last_refill_ts)\n'
                '        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate_per_sec)\n'
                '        self.last_refill_ts = now\n\n'
                '    def try_consume(self, amount: float, now: float) -> bool:\n'
                '        self.refill(now)\n'
                '        if self.tokens >= amount:\n'
                '            self.tokens -= amount\n'
                '            return True\n'
                '        return False\n'
            ),
            "hierarchy.py": (
                '"""Tiered hierarchy nodes for rate limiting."""\n\n'
                'from typing import Dict, Optional\n'
                'from token_bucket import TokenBucket\n\n\n'
                'class HierarchyNode:\n'
                '    def __init__(self, name: str, bucket: TokenBucket, parent: Optional["HierarchyNode"] = None):\n'
                '        self.name = name\n'
                '        self.bucket = bucket\n'
                '        self.parent = parent\n'
                '        self.children: Dict[str, "HierarchyNode"] = {}\n\n'
                '    def add_child(self, child: "HierarchyNode") -> None:\n'
                '        self.children[child.name] = child\n'
                '        child.parent = self\n'
            ),
            "limiter.py": (
                '"""Hierarchical multi-tier rate limiter."""\n\n'
                'from typing import List, Optional\n'
                'from hierarchy import HierarchyNode\n'
                'from token_bucket import TokenBucket\n\n\n'
                'class HierarchicalRateLimiter:\n'
                '    def __init__(self, root: HierarchyNode):\n'
                '        self.root = root\n\n'
                '    def _get_path_to_node(self, node: HierarchyNode) -> List[HierarchyNode]:\n'
                '        path = []\n'
                '        curr: Optional[HierarchyNode] = node\n'
                '        while curr:\n'
                '            path.append(curr)\n'
                '            curr = curr.parent\n'
                '        return list(reversed(path))\n\n'
                '    def allow_request(self, target_node: HierarchyNode, amount: float, now: float) -> bool:\n'
                '        path = self._get_path_to_node(target_node)\n'
                '        # BUG: Checks each bucket independently without 2-phase reserve or rollback\n'
                '        # If root fails after child consumed, child tokens are lost!\n'
                '        # AND child consumes without guaranteeing all ancestors can satisfy amount.\n'
                '        for n in path:\n'
                '            n.bucket.refill(now)\n'
                '            if n.bucket.tokens < amount:\n'
                '                return False\n'
                '        # Consume from child only instead of all tiers up the hierarchy!\n'
                '        target_node.bucket.tokens -= amount\n'
                '        return True\n'
            ),
        }

        reference_fix = {
            "limiter.py": (
                '"""Hierarchical multi-tier rate limiter."""\n\n'
                'from typing import List, Optional\n'
                'from hierarchy import HierarchyNode\n'
                'from token_bucket import TokenBucket\n\n\n'
                'class HierarchicalRateLimiter:\n'
                '    def __init__(self, root: HierarchyNode):\n'
                '        self.root = root\n\n'
                '    def _get_path_to_node(self, node: HierarchyNode) -> List[HierarchyNode]:\n'
                '        path = []\n'
                '        curr: Optional[HierarchyNode] = node\n'
                '        while curr:\n'
                '            path.append(curr)\n'
                '            curr = curr.parent\n'
                '        return list(reversed(path))\n\n'
                '    def allow_request(self, target_node: HierarchyNode, amount: float, now: float) -> bool:\n'
                '        path = self._get_path_to_node(target_node)\n'
                '        for n in path:\n'
                '            n.bucket.refill(now)\n'
                '            if n.bucket.tokens < amount:\n'
                '                return False\n'
                '        for n in path:\n'
                '            n.bucket.tokens -= amount\n'
                '        return True\n'
            )
        }

        tests = {
            "test_hierarchical_rate_limiter.py": (
                'from token_bucket import TokenBucket\n'
                'from hierarchy import HierarchyNode\n'
                'from limiter import HierarchicalRateLimiter\n\n\n'
                'def test_hierarchical_consumption_at_all_tiers():\n'
                '    # Global: cap=10, refill=1/s\n'
                '    root = HierarchyNode("global", TokenBucket.create(10, 1))\n'
                '    # Tenant 1: cap=5, refill=1/s\n'
                '    tenant1 = HierarchyNode("t1", TokenBucket.create(5, 1))\n'
                '    # Tenant 2: cap=5, refill=1/s\n'
                '    tenant2 = HierarchyNode("t2", TokenBucket.create(5, 1))\n'
                '    root.add_child(tenant1)\n'
                '    root.add_child(tenant2)\n'
                '    limiter = HierarchicalRateLimiter(root)\n'
                '    t = 100.0\n'
                '    # Consume 4 from tenant1 -> root should have 6 remaining\n'
                '    assert limiter.allow_request(tenant1, 4, t) is True\n'
                '    # Consume 4 from tenant2 -> root should have 2 remaining\n'
                '    assert limiter.allow_request(tenant2, 4, t) is True\n'
                '    # Tenant2 still has 1 token left, but root only has 2 tokens left. Requesting 3 on t2 must FAIL at root!\n'
                '    assert limiter.allow_request(tenant2, 3, t) is False\n\n\n'
                'def test_tenant_burst_does_not_exceed_global_capacity():\n'
                '    root = HierarchyNode("global", TokenBucket.create(10, 0))\n'
                '    t1 = HierarchyNode("t1", TokenBucket.create(10, 0))\n'
                '    t2 = HierarchyNode("t2", TokenBucket.create(10, 0))\n'
                '    root.add_child(t1)\n'
                '    root.add_child(t2)\n'
                '    limiter = HierarchicalRateLimiter(root)\n'
                '    t = 100.0\n'
                '    # Exhaust root via t1\n'
                '    assert limiter.allow_request(t1, 10, t) is True\n'
                '    # t2 has 10 initial tokens, but root has 0 -> must be blocked\n'
                '    assert limiter.allow_request(t2, 1, t) is False\n\n\n'
                'def test_child_failure_does_not_leak_parent_tokens():\n'
                '    root = HierarchyNode("global", TokenBucket.create(10, 0))\n'
                '    t1 = HierarchyNode("t1", TokenBucket.create(2, 0))\n'
                '    root.add_child(t1)\n'
                '    limiter = HierarchicalRateLimiter(root)\n'
                '    t = 100.0\n'
                '    # Request 5 tokens from t1 (t1 has only 2) -> rejected\n'
                '    assert limiter.allow_request(t1, 5, t) is False\n'
                '    # Root must still retain all 10 tokens!\n'
                '    assert root.bucket.tokens == 10.0\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "hierarchical_rate_limiter_ancestor_token_leak",
            "categories": ["J", "G", "H"],
            "description": "Hierarchical multi-tier rate limiter only deducts tokens from target child leaf, allowing tenants to collectively exceed parent capacity.",
            "spec_notes": "HierarchicalRateLimiter.allow_request must deduct consumed tokens across all ancestors along the tree path.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "rate-limiting",
            },
        }

