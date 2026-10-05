"""Category L: Sandboxed Security & Validation Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class SecurityTaskGenerator(BaseGenerator):
    """Generates realistic path sanitization and boundary validation security tasks."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v19_path_traversal_sanitizer")
        sub_type = spec.get("sub_type", "path_traversal")

        if sub_type == "payload_boundary" or "payload" in task_id:
            return self._generate_payload_boundary(task_id, spec, seed)
        elif sub_type == "ssrf" or "ssrf" in task_id or "whitelist" in task_id:
            return self._generate_ssrf_validator(task_id, spec, seed)
        elif sub_type == "oauth_pkce" or "oauth" in task_id or "pkce" in task_id:
            return self._generate_oauth_pkce_replay(task_id, spec, seed)
        elif sub_type == "merkle_proof" or "merkle" in task_id or "membership" in task_id:
            return self._generate_merkle_membership_proof(task_id, spec, seed)
        return self._generate_path_traversal(task_id, spec, seed)

    def _generate_path_traversal(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "errors.py": (
                '"""Security and storage boundary errors."""\n\n'
                'class SecurityBoundaryError(Exception):\n'
                '    """Raised when an asset path attempts to escape the root jail."""\n'
                '    pass\n'
            ),
            "sanitizer.py": (
                '"""File path sanitization and canonicalization routines."""\n\n'
                'import os\n'
                'import urllib.parse\n'
                'from errors import SecurityBoundaryError\n\n\n'
                'class PathSanitizer:\n'
                '    def __init__(self, root_dir: str):\n'
                '        self.root_dir = os.path.abspath(root_dir)\n\n'
                '    def resolve_safe_path(self, user_path: str) -> str:\n'
                '        # URL decode path once\n'
                '        decoded = urllib.parse.unquote(user_path)\n'
                '        # BUG: Uses naive single-pass replacement for "../" which can be bypassed\n'
                '        # via nested patterns like "....//"\n'
                '        cleaned = decoded.replace("../", "").replace("..\\\\", "")\n'
                '        cleaned = cleaned.lstrip("/\\\\")\n'
                '        target = os.path.join(self.root_dir, cleaned)\n'
                '        # BUG: Does not check os.path.abspath() or os.path.commonpath() against root_dir!\n'
                '        return target\n'
            ),
            "file_store.py": (
                '"""Jailed asset storage service."""\n\n'
                'import os\n'
                'from errors import SecurityBoundaryError\n'
                'from sanitizer import PathSanitizer\n\n\n'
                'class JailedFileStore:\n'
                '    def __init__(self, base_directory: str):\n'
                '        self.base_dir = os.path.abspath(base_directory)\n'
                '        self.sanitizer = PathSanitizer(self.base_dir)\n'
                '        self._virtual_fs: dict[str, str] = {}\n\n'
                '    def write_virtual(self, relative_path: str, data: str) -> str:\n'
                '        safe_target = self.sanitizer.resolve_safe_path(relative_path)\n'
                '        self._virtual_fs[safe_target] = data\n'
                '        return safe_target\n\n'
                '    def read_virtual(self, relative_path: str) -> str:\n'
                '        safe_target = self.sanitizer.resolve_safe_path(relative_path)\n'
                '        if safe_target not in self._virtual_fs:\n'
                '            raise FileNotFoundError(f"Asset not found: {relative_path}")\n'
                '        return self._virtual_fs[safe_target]\n'
            ),
        }

        reference_fix = {
            "sanitizer.py": (
                '"""File path sanitization and canonicalization routines."""\n\n'
                'import os\n'
                'import urllib.parse\n'
                'from errors import SecurityBoundaryError\n\n\n'
                'class PathSanitizer:\n'
                '    def __init__(self, root_dir: str):\n'
                '        self.root_dir = os.path.abspath(root_dir)\n\n'
                '    def resolve_safe_path(self, user_path: str) -> str:\n'
                '        curr = user_path\n'
                '        for _ in range(3):\n'
                '            decoded = urllib.parse.unquote(curr)\n'
                '            if decoded == curr:\n'
                '                break\n'
                '            curr = decoded\n\n'
                '        clean = curr.replace("\\x00", "").replace("\\\\", "/")\n'
                '        segments = [s for s in clean.split("/") if s and s != "."]\n'
                '        resolved: list[str] = []\n'
                '        for seg in segments:\n'
                '            if seg == ".." or seg.startswith("..") or ".." in seg:\n'
                '                raise SecurityBoundaryError(f"Path traversal detected: {user_path}")\n'
                '            resolved.append(seg)\n\n'
                '        target = os.path.abspath(os.path.join(self.root_dir, *resolved))\n'
                '        if not target.startswith(self.root_dir):\n'
                '            raise SecurityBoundaryError(f"Path traversal detected: {user_path}")\n'
                '        return target\n'
            )
        }

        tests = {
            "test_path_sanitization.py": (
                'import pytest\n'
                'from errors import SecurityBoundaryError\n'
                'from file_store import JailedFileStore\n\n\n'
                'def test_safe_relative_path_resolution():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    store.write_virtual("docs/report.pdf", "data-1")\n'
                '    content = store.read_virtual("docs/report.pdf")\n'
                '    assert content == "data-1"\n\n\n'
                'def test_nested_path_traversal_blocked():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    with pytest.raises(SecurityBoundaryError):\n'
                '        store.write_virtual("....//....//etc/passwd", "evil")\n\n\n'
                'def test_double_url_encoded_traversal_blocked():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    # %252e%252e%252f decodes to %2e%2e%2f then to ../\n'
                '    with pytest.raises(SecurityBoundaryError):\n'
                '        store.write_virtual("%252e%252e%252f%252e%252e%252fsecret.key", "evil")\n\n\n'
                'def test_null_byte_injection_cleaned():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    store.write_virtual("file.txt\\x00.png", "safe_content")\n'
                '    assert store.read_virtual("file.txt.png") == "safe_content"\n\n\n'
                'def test_absolute_path_escape_blocked():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    store.write_virtual("/sub/item.json", "data-2")\n'
                '    assert store.read_virtual("sub/item.json") == "data-2"\n'
                '    # Sibling path escape like /var/data/storage_secret\n'
                '    with pytest.raises(SecurityBoundaryError):\n'
                '        store.write_virtual("../storage_secret/key.pem", "evil")\n\n\n'
                'def test_windows_backslash_traversal_blocked():\n'
                '    store = JailedFileStore("/var/data/storage")\n'
                '    with pytest.raises(SecurityBoundaryError):\n'
                '        store.write_virtual("..\\\\..\\\\boot.ini", "evil")\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "path_traversal_sanitization_bypass",
            "categories": ["L", "E", "F"],
            "description": "Path sanitizer uses a single-pass string replacement, allowing nested and double-encoded traversal sequences to escape the root directory.",
            "spec_notes": "PathSanitizer must canonicalize decoded paths and enforce strict root_dir containment via os.path.commonpath.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "security",
            },
        }

    def _generate_payload_boundary(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "schema_rule.py": (
                '"""Schema rule constraints for payload fields."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class FieldRule:\n'
                '    name: str\n'
                '    field_type: type\n'
                '    max_len: Optional[int] = None\n'
                '    required: bool = True\n'
            ),
            "request_context.py": (
                '"""Request validation context and violation aggregator."""\n\n'
                'from typing import List\n\n\n'
                'class ValidationContext:\n'
                '    def __init__(self):\n'
                '        self.violations: List[str] = []\n\n'
                '    def add_violation(self, msg: str) -> None:\n'
                '        self.violations.append(msg)\n\n'
                '    @property\n'
                '    def is_valid(self) -> bool:\n'
                '        return len(self.violations) == 0\n'
            ),
            "validator.py": (
                '"""JSON payload boundary and recursion depth validator."""\n\n'
                'from typing import Any, Dict, List\n'
                'from request_context import ValidationContext\n'
                'from schema_rule import FieldRule\n\n\n'
                'class PayloadValidator:\n'
                '    def __init__(self, max_depth: int = 3, max_keys: int = 10):\n'
                '        self.max_depth = max_depth\n'
                '        self.max_keys = max_keys\n'
                '        self.rules: dict[str, FieldRule] = {}\n\n'
                '    def register_rule(self, rule: FieldRule) -> None:\n'
                '        self.rules[rule.name] = rule\n\n'
                '    def validate(self, payload: Any, ctx: ValidationContext, current_depth: int = 1) -> None:\n'
                '        if not isinstance(payload, dict):\n'
                '            ctx.add_violation("Payload must be a dictionary")\n'
                '            return\n\n'
                '        # BUG: Depth limit check is > instead of >= and is not tracked across lists/subdicts properly\n'
                '        if current_depth > self.max_depth + 1:\n'
                '            ctx.add_violation(f"Payload depth exceeds limit of {self.max_depth}")\n'
                '            return\n\n'
                '        if len(payload) > self.max_keys:\n'
                '            ctx.add_violation(f"Payload key count exceeds limit of {self.max_keys}")\n'
                '            return\n\n'
                '        # Check for forbidden dunder / prototype pollution keys\n'
                '        for key, val in payload.items():\n'
                '            # BUG: Only checks exact string "__proto__" and misses "__class__", "__globals__"\n'
                '            if key == "__proto__":\n'
                '                ctx.add_violation("Forbidden special attribute in payload")\n\n'
                '            if isinstance(val, dict):\n'
                '                self.validate(val, ctx, current_depth + 1)\n'
            ),
        }

        reference_fix = {
            "validator.py": (
                '"""JSON payload boundary and recursion depth validator."""\n\n'
                'from typing import Any, Dict, List\n'
                'from request_context import ValidationContext\n'
                'from schema_rule import FieldRule\n\n\n'
                'FORBIDDEN_PREFIXES = ("__", "constructor", "prototype")\n\n\n'
                'class PayloadValidator:\n'
                '    def __init__(self, max_depth: int = 3, max_keys: int = 10):\n'
                '        self.max_depth = max_depth\n'
                '        self.max_keys = max_keys\n'
                '        self.rules: dict[str, FieldRule] = {}\n\n'
                '    def register_rule(self, rule: FieldRule) -> None:\n'
                '        self.rules[rule.name] = rule\n\n'
                '    def validate(self, payload: Any, ctx: ValidationContext, current_depth: int = 1) -> None:\n'
                '        if not isinstance(payload, dict):\n'
                '            ctx.add_violation("Payload must be a dictionary")\n'
                '            return\n\n'
                '        if current_depth > self.max_depth:\n'
                '            ctx.add_violation(f"Payload depth exceeds limit of {self.max_depth}")\n'
                '            return\n\n'
                '        if len(payload) > self.max_keys:\n'
                '            ctx.add_violation(f"Payload key count exceeds limit of {self.max_keys}")\n'
                '            return\n\n'
                '        for key, val in payload.items():\n'
                '            if any(key == fp or key.startswith("__") for fp in FORBIDDEN_PREFIXES):\n'
                '                ctx.add_violation(f"Forbidden special attribute in payload: {key}")\n\n'
                '            if isinstance(val, dict):\n'
                '                self.validate(val, ctx, current_depth + 1)\n'
                '            elif isinstance(val, list):\n'
                '                for item in val:\n'
                '                    if isinstance(item, dict):\n'
                '                        self.validate(item, ctx, current_depth + 1)\n'
            )
        }

        tests = {
            "test_payload_boundary.py": (
                'from request_context import ValidationContext\n'
                'from validator import PayloadValidator\n\n\n'
                'def test_valid_shallow_payload():\n'
                '    v = PayloadValidator(max_depth=3, max_keys=5)\n'
                '    ctx = ValidationContext()\n'
                '    v.validate({"name": "item", "count": 10}, ctx)\n'
                '    assert ctx.is_valid is True\n'
                '    assert len(ctx.violations) == 0\n\n\n'
                'def test_deeply_nested_payload_depth_violation():\n'
                '    v = PayloadValidator(max_depth=2, max_keys=10)\n'
                '    ctx = ValidationContext()\n'
                '    # Depth 4 payload: level1 -> level2 -> level3 -> level4\n'
                '    nested = {"a": {"b": {"c": {"d": 1}}}}\n'
                '    v.validate(nested, ctx)\n'
                '    assert ctx.is_valid is False\n'
                '    assert any("depth exceeds limit" in err for err in ctx.violations)\n\n\n'
                'def test_dunder_attribute_injection_blocked():\n'
                '    v = PayloadValidator(max_depth=3, max_keys=10)\n'
                '    for bad_key in ["__proto__", "__class__", "__globals__", "__dict__"]:\n'
                '        ctx = ValidationContext()\n'
                '        v.validate({"user": {bad_key: "exploit"}}, ctx)\n'
                '        assert ctx.is_valid is False\n'
                '        assert any("Forbidden special attribute" in err for err in ctx.violations)\n\n\n'
                'def test_key_count_limit_enforced():\n'
                '    v = PayloadValidator(max_depth=3, max_keys=3)\n'
                '    ctx = ValidationContext()\n'
                '    v.validate({"k1": 1, "k2": 2, "k3": 3, "k4": 4}, ctx)\n'
                '    assert ctx.is_valid is False\n'
                '    assert any("key count exceeds limit" in err for err in ctx.violations)\n\n\n'
                'def test_nested_list_dictionary_depth_tracked():\n'
                '    v = PayloadValidator(max_depth=2, max_keys=10)\n'
                '    ctx = ValidationContext()\n'
                '    # Depth 3 via list of dicts\n'
                '    v.validate({"items": [{"meta": {"deep": "val"}}]}, ctx)\n'
                '    assert ctx.is_valid is False\n'
                '    assert any("depth exceeds limit" in err for err in ctx.violations)\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "medium",
            "bug_type": "payload_boundary_validation_bypass",
            "categories": ["L", "F"],
            "description": "Payload validator allows prototype/dunder key injection and fails to enforce recursion depth bounds on nested structures.",
            "spec_notes": "PayloadValidator must enforce max_depth and block dunder/special attributes across all nested dicts and lists.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "security",
            },
        }

    def _generate_ssrf_validator(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "url_parser.py": (
                '"""URL component extractor."""\n\n'
                'import urllib.parse\n'
                'from typing import Optional\n\n\n'
                'class ParsedURL:\n'
                '    def __init__(self, scheme: str, host: str, port: Optional[int], path: str):\n'
                '        self.scheme = scheme\n'
                '        self.host = host\n'
                '        self.port = port\n'
                '        self.path = path\n\n\n'
                'def parse_url(raw_url: str) -> Optional[ParsedURL]:\n'
                '    try:\n'
                '        p = urllib.parse.urlparse(raw_url.strip())\n'
                '        if not p.scheme or not p.netloc:\n'
                '            return None\n'
                '        host = p.hostname or ""\n'
                '        port = p.port\n'
                '        return ParsedURL(p.scheme.lower(), host.lower(), port, p.path)\n'
                '    except Exception:\n'
                '        return None\n'
            ),
            "ssrf_guard.py": (
                '"""SSRF protection and private IP subnet filter."""\n\n'
                'import ipaddress\n'
                'from url_parser import ParsedURL, parse_url\n\n\n'
                'FORBIDDEN_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "metadata.google.internal"}\n\n\n'
                'class SSRFGuard:\n'
                '    def __init__(self, allowed_schemes: set[str] = None):\n'
                '        self.allowed_schemes = allowed_schemes or {"http", "https"}\n\n'
                '    def is_safe_url(self, raw_url: str) -> bool:\n'
                '        parsed = parse_url(raw_url)\n'
                '        if not parsed:\n'
                '            return False\n'
                '        if parsed.scheme not in self.allowed_schemes:\n'
                '            return False\n'
                '        if parsed.host in FORBIDDEN_HOSTNAMES:\n'
                '            return False\n\n'
                '        # BUG: Attempts string prefix checks instead of ipaddress.ip_address() validation,\n'
                '        # failing on decimal IPs (e.g. 2130706433 for 127.0.0.1), hex IPs, or 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16!\n'
                '        if parsed.host.startswith("10.") or parsed.host.startswith("192.168."):\n'
                '            return False\n'
                '        return True\n'
            ),
            "fetcher.py": (
                '"""Webhook dispatch fetcher."""\n\n'
                'from typing import Any, Dict\n'
                'from ssrf_guard import SSRFGuard\n\n\n'
                'class WebhookFetcher:\n'
                '    def __init__(self):\n'
                '        self.guard = SSRFGuard()\n\n'
                '    def dispatch(self, target_url: str, payload: Dict[str, Any]) -> bool:\n'
                '        if not self.guard.is_safe_url(target_url):\n'
                '            return False\n'
                '        return True\n'
            ),
        }

        reference_fix = {
            "ssrf_guard.py": (
                '"""SSRF protection and private IP subnet filter."""\n\n'
                'import ipaddress\n'
                'import socket\n'
                'from url_parser import ParsedURL, parse_url\n\n\n'
                'FORBIDDEN_HOSTNAMES = {"localhost", "metadata.google.internal", "instance-data"}\n\n\n'
                'class SSRFGuard:\n'
                '    def __init__(self, allowed_schemes: set[str] = None):\n'
                '        self.allowed_schemes = allowed_schemes or {"http", "https"}\n\n'
                '    def is_safe_url(self, raw_url: str) -> bool:\n'
                '        parsed = parse_url(raw_url)\n'
                '        if not parsed:\n'
                '            return False\n'
                '        if parsed.scheme not in self.allowed_schemes:\n'
                '            return False\n'
                '        if parsed.host in FORBIDDEN_HOSTNAMES:\n'
                '            return False\n\n'
                '        # Resolve and check IP address against private/loopback/link-local ranges\n'
                '        try:\n'
                '            ip = ipaddress.ip_address(parsed.host)\n'
                '            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:\n'
                '                return False\n'
                '        except ValueError:\n'
                '            # If hostname is a numeric string (e.g. decimal IP 2130706433), parse as integer IP\n'
                '            if parsed.host.isdigit():\n'
                '                try:\n'
                '                    ip = ipaddress.ip_address(int(parsed.host))\n'
                '                    if ip.is_private or ip.is_loopback or ip.is_link_local:\n'
                '                        return False\n'
                '                except Exception:\n'
                '                    return False\n'
                '        return True\n'
            )
        }

        tests = {
            "test_ssrf_validator.py": (
                'from ssrf_guard import SSRFGuard\n'
                'from fetcher import WebhookFetcher\n\n\n'
                'def test_public_domain_allowed():\n'
                '    fetcher = WebhookFetcher()\n'
                '    assert fetcher.dispatch("https://api.github.com/webhook", {"data": 1}) is True\n'
                '    assert fetcher.dispatch("http://webhook.site/test", {}) is True\n\n\n'
                'def test_localhost_and_loopback_blocked():\n'
                '    fetcher = WebhookFetcher()\n'
                '    assert fetcher.dispatch("http://localhost:8080/admin", {}) is False\n'
                '    assert fetcher.dispatch("http://127.0.0.1/status", {}) is False\n'
                '    assert fetcher.dispatch("http://127.0.0.2:9000", {}) is False\n\n\n'
                'def test_decimal_ip_loopback_bypass_blocked():\n'
                '    # 2130706433 is integer decimal representation of 127.0.0.1 (0x7F000001)\n'
                '    fetcher = WebhookFetcher()\n'
                '    assert fetcher.dispatch("http://2130706433/internal", {}) is False\n\n\n'
                'def test_private_subnets_blocked():\n'
                '    fetcher = WebhookFetcher()\n'
                '    # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254 (cloud metadata)\n'
                '    assert fetcher.dispatch("http://10.1.2.3/secret", {}) is False\n'
                '    assert fetcher.dispatch("http://172.16.0.1/db", {}) is False\n'
                '    assert fetcher.dispatch("http://192.168.1.1/router", {}) is False\n'
                '    assert fetcher.dispatch("http://169.254.169.254/latest/meta-data/", {}) is False\n\n\n'
                'def test_unsupported_schemes_rejected():\n'
                '    fetcher = WebhookFetcher()\n'
                '    assert fetcher.dispatch("file:///etc/passwd", {}) is False\n'
                '    assert fetcher.dispatch("gopher://127.0.0.1:6379", {}) is False\n'
                '    assert fetcher.dispatch("ftp://public.mirror.org", {}) is False\n\n\n'
                'def test_cloud_metadata_hostname_blocked():\n'
                '    fetcher = WebhookFetcher()\n'
                '    assert fetcher.dispatch("http://metadata.google.internal/computeMetadata/v1/", {}) is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "ssrf_decimal_ip_and_private_subnet_bypass",
            "categories": ["L", "H"],
            "description": "SSRF guard uses naive string prefix checks, allowing decimal IP representations and 172.16.0.0/12 private addresses to bypass firewall.",
            "spec_notes": "SSRFGuard must parse IP addresses via ipaddress library and block private, loopback, and cloud metadata addresses.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "security",
            },
        }

    def _generate_oauth_pkce_replay(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "auth_code.py": (
                '"""Authorization code payload."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class AuthCode:\n'
                '    code: str\n'
                '    client_id: str\n'
                '    user_id: str\n'
                '    code_challenge: str\n'
                '    code_challenge_method: str  # "S256" or "plain"\n'
                '    used: bool = False\n'
            ),
            "pkce.py": (
                '"""PKCE code challenge verification."""\n\n'
                'import base64\n'
                'import hashlib\n\n\n'
                'class PKCEVerifier:\n'
                '    @staticmethod\n'
                '    def verify(verifier: str, challenge: str, method: str) -> bool:\n'
                '        if method == "plain":\n'
                '            return verifier == challenge\n'
                '        elif method == "S256":\n'
                '            # Compute SHA-256 and base64url encoding without padding\n'
                '            digest = hashlib.sha256(verifier.encode("utf-8")).digest()\n'
                '            encoded = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")\n'
                '            return encoded == challenge\n'
                '        return False\n'
            ),
            "token_store.py": (
                '"""Issued access and refresh token storage."""\n\n'
                'import uuid\n'
                'from typing import Dict\n\n\n'
                'class TokenStore:\n'
                '    def __init__(self):\n'
                '        self.tokens: Dict[str, str] = {}\n\n'
                '    def issue(self, user_id: str, client_id: str) -> str:\n'
                '        tok = f"access_{uuid.uuid4().hex}"\n'
                '        self.tokens[tok] = user_id\n'
                '        return tok\n'
            ),
            "exchange.py": (
                '"""OAuth 2.0 Authorization code token exchange handler."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from auth_code import AuthCode\n'
                'from pkce import PKCEVerifier\n'
                'from token_store import TokenStore\n\n\n'
                'class TokenExchangeHandler:\n'
                '    def __init__(self, token_store: TokenStore):\n'
                '        self.codes: Dict[str, AuthCode] = {}\n'
                '        self.token_store = token_store\n\n'
                '    def register_code(self, auth_code: AuthCode) -> None:\n'
                '        self.codes[auth_code.code] = auth_code\n\n'
                '    def exchange(self, client_id: str, code_str: str, code_verifier: str) -> Dict[str, Any]:\n'
                '        code = self.codes.get(code_str)\n'
                '        if not code:\n'
                '            return {"error": "invalid_grant"}\n\n'
                '        if code.client_id != client_id:\n'
                '            return {"error": "invalid_client"}\n\n'
                '        # BUG: Fails to check code.used or mark code.used = True,\n'
                '        # allowing malicious attackers to replay authorization codes!\n'
                '        if not PKCEVerifier.verify(code_verifier, code.code_challenge, code.code_challenge_method):\n'
                '            return {"error": "invalid_grant"}\n\n'
                '        access_token = self.token_store.issue(code.user_id, client_id)\n'
                '        return {"access_token": access_token, "token_type": "Bearer"}\n'
            ),
        }

        reference_fix = {
            "exchange.py": (
                '"""OAuth 2.0 Authorization code token exchange handler."""\n\n'
                'from typing import Any, Dict, Optional\n'
                'from auth_code import AuthCode\n'
                'from pkce import PKCEVerifier\n'
                'from token_store import TokenStore\n\n\n'
                'class TokenExchangeHandler:\n'
                '    def __init__(self, token_store: TokenStore):\n'
                '        self.codes: Dict[str, AuthCode] = {}\n'
                '        self.token_store = token_store\n\n'
                '    def register_code(self, auth_code: AuthCode) -> None:\n'
                '        self.codes[auth_code.code] = auth_code\n\n'
                '    def exchange(self, client_id: str, code_str: str, code_verifier: str) -> Dict[str, Any]:\n'
                '        code = self.codes.get(code_str)\n'
                '        if not code or code.used:\n'
                '            return {"error": "invalid_grant"}\n\n'
                '        if code.client_id != client_id:\n'
                '            return {"error": "invalid_client"}\n\n'
                '        # Invalidate code immediately upon first attempt\n'
                '        code.used = True\n\n'
                '        if not PKCEVerifier.verify(code_verifier, code.code_challenge, code.code_challenge_method):\n'
                '            return {"error": "invalid_grant"}\n\n'
                '        access_token = self.token_store.issue(code.user_id, client_id)\n'
                '        return {"access_token": access_token, "token_type": "Bearer"}\n'
            )
        }

        tests = {
            "test_oauth_pkce.py": (
                'from auth_code import AuthCode\n'
                'from exchange import TokenExchangeHandler\n'
                'from pkce import PKCEVerifier\n'
                'from token_store import TokenStore\n\n\n'
                'def test_successful_pkce_s256_exchange():\n'
                '    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"\n'
                '    # SHA-256 base64url of verifier\n'
                '    import base64, hashlib\n'
                '    digest = hashlib.sha256(verifier.encode()).digest()\n'
                '    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")\n'
                '    code = AuthCode("c1", "client_app", "user_100", challenge, "S256")\n'
                '    store = TokenStore()\n'
                '    handler = TokenExchangeHandler(store)\n'
                '    handler.register_code(code)\n'
                '    res = handler.exchange("client_app", "c1", verifier)\n'
                '    assert "access_token" in res\n'
                '    assert res["token_type"] == "Bearer"\n\n\n'
                'def test_authorization_code_replay_rejected():\n'
                '    verifier = "plain_verifier_token"\n'
                '    code = AuthCode("c2", "client_app", "user_200", verifier, "plain")\n'
                '    store = TokenStore()\n'
                '    handler = TokenExchangeHandler(store)\n'
                '    handler.register_code(code)\n'
                '    # First exchange succeeds\n'
                '    res1 = handler.exchange("client_app", "c2", verifier)\n'
                '    assert "access_token" in res1\n'
                '    # Replay attack with same code must be REJECTED with invalid_grant!\n'
                '    res2 = handler.exchange("client_app", "c2", verifier)\n'
                '    assert res2.get("error") == "invalid_grant"\n\n\n'
                'def test_invalid_verifier_mismatch():\n'
                '    code = AuthCode("c3", "client_app", "user_300", "expected_challenge", "plain")\n'
                '    store = TokenStore()\n'
                '    handler = TokenExchangeHandler(store)\n'
                '    handler.register_code(code)\n'
                '    res = handler.exchange("client_app", "c3", "wrong_verifier")\n'
                '    assert res.get("error") == "invalid_grant"\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "oauth_pkce_authorization_code_replay_leak",
            "categories": ["L", "H", "E"],
            "description": "OAuth 2.0 PKCE token exchange handler fails to invalidate authorization codes upon use, allowing token replay attacks.",
            "spec_notes": "TokenExchangeHandler must mark AuthCode.used = True and reject replayed codes.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "security",
            },
        }

    def _generate_merkle_membership_proof(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "hash_util.py": (
                '"""Cryptographic hashing utility."""\n\n'
                'import hashlib\n\n\n'
                'def hash_leaf(data: str) -> str:\n'
                '    return hashlib.sha256(b"\\x00" + data.encode("utf-8")).hexdigest()\n\n\n'
                'def hash_pair(left: str, right: str) -> str:\n'
                '    return hashlib.sha256(b"\\x01" + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()\n'
            ),
            "proof.py": (
                '"""Merkle tree membership proof."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import List, Tuple\n\n\n'
                '@dataclass\n'
                'class MembershipProof:\n'
                '    leaf_data: str\n'
                '    leaf_index: int\n'
                '    # Each step is (sibling_hash, is_sibling_right)\n'
                '    audit_path: List[Tuple[str, bool]]\n'
            ),
            "verifier.py": (
                '"""Merkle membership proof verifier."""\n\n'
                'from hash_util import hash_leaf, hash_pair\n'
                'from proof import MembershipProof\n\n\n'
                'class MerkleProofVerifier:\n'
                '    @staticmethod\n'
                '    def verify(proof: MembershipProof, root_hash: str) -> bool:\n'
                '        curr = hash_leaf(proof.leaf_data)\n'
                '        for sibling, is_right in proof.audit_path:\n'
                '            # BUG: Always hashes curr as left and sibling as right,\n'
                '            # ignoring is_right boolean direction indicator!\n'
                '            curr = hash_pair(curr, sibling)\n'
                '        return curr == root_hash\n'
            ),
            "merkle_tree.py": (
                '"""Binary Merkle tree construction and proof generator."""\n\n'
                'from typing import List\n'
                'from hash_util import hash_leaf, hash_pair\n'
                'from proof import MembershipProof\n\n\n'
                'class MerkleTree:\n'
                '    def __init__(self, leaves: List[str]):\n'
                '        self.leaves = list(leaves)\n'
                '        self.layers: List[List[str]] = []\n'
                '        self._build()\n\n'
                '    def _build(self):\n'
                '        curr = [hash_leaf(l) for l in self.leaves]\n'
                '        self.layers.append(curr)\n'
                '        while len(curr) > 1:\n'
                '            if len(curr) % 2 != 0:\n'
                '                curr.append(curr[-1])\n'
                '            nxt = []\n'
                '            for i in range(0, len(curr), 2):\n'
                '                nxt.append(hash_pair(curr[i], curr[i + 1]))\n'
                '            self.layers.append(nxt)\n'
                '            curr = nxt\n\n'
                '    @property\n'
                '    def root(self) -> str:\n'
                '        return self.layers[-1][0] if self.layers and self.layers[-1] else ""\n\n'
                '    def generate_proof(self, index: int) -> MembershipProof:\n'
                '        path = []\n'
                '        idx = index\n'
                '        for layer in self.layers[:-1]:\n'
                '            is_right_child = (idx % 2 == 1)\n'
                '            sibling_idx = idx - 1 if is_right_child else idx + 1\n'
                '            if sibling_idx >= len(layer):\n'
                '                sibling_idx = idx\n'
                '            sibling_hash = layer[sibling_idx]\n'
                '            # is_sibling_right is True if sibling is on the right\n'
                '            path.append((sibling_hash, not is_right_child))\n'
                '            idx //= 2\n'
                '        return MembershipProof(self.leaves[index], index, path)\n'
            ),
        }

        reference_fix = {
            "verifier.py": (
                '"""Merkle membership proof verifier."""\n\n'
                'from hash_util import hash_leaf, hash_pair\n'
                'from proof import MembershipProof\n\n\n'
                'class MerkleProofVerifier:\n'
                '    @staticmethod\n'
                '    def verify(proof: MembershipProof, root_hash: str) -> bool:\n'
                '        curr = hash_leaf(proof.leaf_data)\n'
                '        for sibling, is_right in proof.audit_path:\n'
                '            if is_right:\n'
                '                curr = hash_pair(curr, sibling)\n'
                '            else:\n'
                '                curr = hash_pair(sibling, curr)\n'
                '        return curr == root_hash\n'
            )
        }

        tests = {
            "test_merkle_proof.py": (
                'from merkle_tree import MerkleTree\n'
                'from verifier import MerkleProofVerifier\n'
                'from proof import MembershipProof\n\n\n'
                'def test_valid_inclusion_proof_for_all_leaves():\n'
                '    leaves = ["leaf_0", "leaf_1", "leaf_2", "leaf_3", "leaf_4"]\n'
                '    tree = MerkleTree(leaves)\n'
                '    root = tree.root\n'
                '    for i in range(len(leaves)):\n'
                '        proof = tree.generate_proof(i)\n'
                '        assert MerkleProofVerifier.verify(proof, root) is True\n\n\n'
                'def test_tampered_leaf_data_rejected():\n'
                '    leaves = ["a", "b", "c", "d"]\n'
                '    tree = MerkleTree(leaves)\n'
                '    proof = tree.generate_proof(1)\n'
                '    tampered = MembershipProof("tampered_data", proof.leaf_index, proof.audit_path)\n'
                '    assert MerkleProofVerifier.verify(tampered, tree.root) is False\n\n\n'
                'def test_wrong_root_rejected():\n'
                '    tree = MerkleTree(["a", "b"])\n'
                '    proof = tree.generate_proof(0)\n'
                '    assert MerkleProofVerifier.verify(proof, "00" * 32) is False\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "merkle_proof_sibling_ordering_hash_inversion",
            "categories": ["L", "C"],
            "description": "Merkle membership proof verifier ignores sibling side bit when combining hashes, failing inclusion proofs on right-hand leaves.",
            "spec_notes": "MerkleProofVerifier.verify must concatenate left and right hashes according to is_sibling_right direction.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": False,
                "multi_file": True,
                "domain": "cryptography",
            },
        }

