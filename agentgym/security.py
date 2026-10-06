"""Centralized security primitives and host filesystem path validation for DebugArena."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Union


class SecurityError(ValueError):
    """Base exception for all security violations in DebugArena."""
    pass


class PathTraversalSecurityError(SecurityError):
    """Raised when an untrusted or relative path escapes the designated workspace."""
    pass


def is_relative_to_compat(target: Path, base: Path) -> bool:
    """Checks if target is relative to base, compatible across Python versions."""
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def safe_path(workspace: Union[str, Path], rel_path: Union[str, Path]) -> Path:
    """Resolves and validates that a relative path strictly resides within the given workspace.

    Invariants enforced:
    1. Rejects null bytes and empty paths.
    2. Rejects absolute POSIX paths ('/etc/passwd') and absolute Windows paths ('C:\\...').
    3. Rejects Windows drive-relative ('C:foo'), rooted ('\\foo'), and UNC ('\\\\server\\share') paths.
    4. Rejects explicit directory traversal segments ('..').
    5. Resolves symlinks and ensures the final resolved target path is strictly contained
       within the resolved workspace directory.
    6. Verifies that all existing intermediate path components do not escape the workspace
       via directory symlinks.
    7. Prevents targeting the workspace root itself as a writable file.

    Args:
        workspace: The root directory for the sandbox or project workspace.
        rel_path: The untrusted relative path to validate.

    Returns:
        The validated Path object ready for safe host-side filesystem operations.

    Raises:
        PathTraversalSecurityError: If any path traversal or workspace escape is detected.
    """
    if rel_path is None:
        raise PathTraversalSecurityError("Relative path cannot be None.")

    raw_str = str(rel_path).strip()
    if not raw_str:
        raise PathTraversalSecurityError("Relative path cannot be empty.")

    if "\0" in raw_str:
        raise PathTraversalSecurityError("Null bytes in file paths are forbidden.")

    # Check for absolute POSIX paths or Windows drive / rooted / UNC paths
    if raw_str.startswith("/") or raw_str.startswith("\\"):
        raise PathTraversalSecurityError(f"Absolute or root-anchored paths are forbidden: '{raw_str}'")

    if re.match(r"^[a-zA-Z]:", raw_str):
        raise PathTraversalSecurityError(f"Windows drive-specific paths are forbidden: '{raw_str}'")

    if Path(raw_str).is_absolute():
        raise PathTraversalSecurityError(f"Absolute paths are forbidden: '{raw_str}'")

    # Normalize separators and segment checks
    normalized = raw_str.replace("\\", "/")
    segments = [s for s in normalized.split("/") if s and s != "."]

    if not segments:
        raise PathTraversalSecurityError(f"Path resolves to an empty target: '{raw_str}'")

    if any(s == ".." for s in segments):
        raise PathTraversalSecurityError(f"Directory traversal ('..') is forbidden: '{raw_str}'")

    # Resolve workspace root
    workspace_resolved = Path(workspace).resolve()

    # Construct the candidate path under the resolved workspace
    candidate = workspace_resolved
    for seg in segments:
        candidate = candidate / seg

    # Check that candidate path itself does not match workspace root
    if candidate == workspace_resolved:
        raise PathTraversalSecurityError(f"Cannot target the workspace root as a file: '{raw_str}'")

    # Resolve full target path
    target_resolved = candidate.resolve()

    # Invariant: resolved target must be strictly inside the resolved workspace
    if not is_relative_to_compat(target_resolved, workspace_resolved):
        raise PathTraversalSecurityError(
            f"Path escapes workspace: target '{target_resolved.name}' is outside workspace boundary."
        )

    # Invariant: Verify all existing ancestor components do not point outside workspace via symlinks
    curr = candidate
    while curr != workspace_resolved and curr != curr.parent:
        if curr.is_symlink() or curr.exists():
            resolved_curr = curr.resolve()
            if not is_relative_to_compat(resolved_curr, workspace_resolved):
                raise PathTraversalSecurityError(
                    f"Symlink escapes workspace: component '{curr.name}' resolves outside workspace boundary."
                )
        curr = curr.parent

    return candidate
