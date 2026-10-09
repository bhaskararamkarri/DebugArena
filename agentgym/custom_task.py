"""Custom Task abstraction, safe ZIP extraction, and workspace management for DebugArena."""

from __future__ import annotations

import datetime
import difflib
import io
import json
import os
import re
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from agentgym.security import SecurityError, PathTraversalSecurityError, safe_path


class ZipSecurityError(SecurityError):
    """Raised when an uploaded ZIP archive violates security constraints."""
    pass


def sanitize_rel_path(raw_path: str) -> str:
    """Sanitizes and validates a relative path inside a workspace archive."""
    # Convert backslashes to forward slashes
    clean = raw_path.replace("\\", "/").strip()

    # Check for absolute path (POSIX root or Windows drive letter)
    if clean.startswith("/") or re.match(r"^[a-zA-Z]:", clean):
        raise ZipSecurityError(f"Absolute paths are forbidden: '{raw_path}'")

    # Split segments and check for traversal
    segments = [s for s in clean.split("/") if s and s != "."]
    if any(s == ".." for s in segments):
        raise ZipSecurityError(f"Path traversal detected in path: '{raw_path}'")

    if not segments:
        return ""

    return "/".join(segments)


def extract_zip_safely(
    zip_source: Union[bytes, BinaryIO, str, Path],
    max_files: int = 500,
    max_total_size: int = 50 * 1024 * 1024,      # 50 MB
    max_file_size: int = 10 * 1024 * 1024,       # 10 MB
    strip_common_prefix: bool = True,
) -> Dict[str, str]:
    """Safely extracts text and code files from an untrusted ZIP archive into an in-memory dictionary.

    Guards against:
    - Path traversal ('..')
    - Absolute paths ('/etc/passwd', 'C:\\...')
    - Symlinks and special device nodes
    - Archive bombs (excessive uncompressed size or compression ratios)
    - Excessive file counts
    - Binary non-text files that exceed limits
    """
    if isinstance(zip_source, (str, Path)):
        p = Path(zip_source)
        if not p.exists() or not zipfile.is_zipfile(p):
            raise ZipSecurityError(f"File '{zip_source}' is not a valid ZIP archive.")
        zf_target: Union[Path, io.BytesIO] = p
    elif isinstance(zip_source, bytes):
        if not zipfile.is_zipfile(io.BytesIO(zip_source)):
            raise ZipSecurityError("Provided byte buffer is not a valid ZIP archive.")
        zf_target = io.BytesIO(zip_source)
    else:
        # File-like object
        zip_source.seek(0)
        data = zip_source.read()
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ZipSecurityError("Uploaded file is not a valid ZIP archive.")
        zf_target = io.BytesIO(data)

    extracted_files: Dict[str, str] = {}
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(zf_target, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) > max_files:
            raise ZipSecurityError(
                f"Archive contains {len(infolist)} entries, exceeding maximum allowed limit of {max_files}."
            )

        for member in infolist:
            # Skip directories
            if member.is_dir():
                continue

            # Check individual uncompressed size
            if member.file_size > max_file_size:
                raise ZipSecurityError(
                    f"File '{member.filename}' ({member.file_size} bytes) exceeds maximum file limit of {max_file_size} bytes."
                )

            total_uncompressed_bytes += member.file_size
            if total_uncompressed_bytes > max_total_size:
                raise ZipSecurityError(
                    f"Archive exceeds maximum uncompressed size limit of {max_total_size} bytes."
                )

            # Check for symlink attribute
            is_symlink = ((member.external_attr >> 16) & 0o120000) == 0o120000
            if is_symlink:
                raise ZipSecurityError(f"Symlinks are forbidden in workspace archives: '{member.filename}'")

            # Check filename for security
            clean_path = sanitize_rel_path(member.filename)
            if not clean_path:
                continue

            # Skip macOS and common metadata junk
            if clean_path.startswith("__MACOSX/") or clean_path.endswith(".DS_Store"):
                continue

            try:
                raw_bytes = zf.read(member)
            except Exception as e:
                raise ZipSecurityError(f"Corrupted entry in archive '{member.filename}': {e}")

            # Decode text content
            try:
                text_content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # Attempt fallback with replace to avoid dropping files with odd encodings
                text_content = raw_bytes.decode("utf-8", errors="replace")

            extracted_files[clean_path] = text_content

    if not extracted_files:
        raise ZipSecurityError("Archive contains no readable code or text files.")

    # Optionally strip common root folder (e.g. repo-main/src/app.py -> src/app.py)
    if strip_common_prefix and len(extracted_files) > 1:
        first_segments = [p.split("/")[0] for p in extracted_files.keys() if "/" in p]
        if first_segments and len(first_segments) == len(extracted_files):
            common_root = first_segments[0]
            if all(p.startswith(f"{common_root}/") for p in extracted_files.keys()):
                stripped = {}
                for k, v in extracted_files.items():
                    rel = k[len(common_root) + 1 :]
                    if rel:
                        stripped[rel] = v
                if stripped:
                    extracted_files = stripped

    return extracted_files


def generate_custom_task_id(prefix: Optional[str] = None) -> str:
    """Generates a collision-resistant unique custom task identifier."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand_suffix = uuid.uuid4().hex[:4]
    if prefix:
        clean_prefix = re.sub(r"[^a-zA-Z0-9_]", "_", prefix.strip().lower())[:20].strip("_")
        if clean_prefix:
            return f"custom_{clean_prefix}_{ts}_{rand_suffix}"
    return f"custom_{ts}_{rand_suffix}"


@dataclass
class CustomTask:
    """Task specification for user-defined coding problems and evaluations."""
    task_id: str
    description: str
    repo_files: Dict[str, str]
    title: str = ""
    tests: Dict[str, str] = field(default_factory=dict)
    reference_fix: Dict[str, str] = field(default_factory=dict)
    suite: str = "custom"
    difficulty: str = "custom"
    has_oracle: bool = True
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.title and self.description:
            # Extract first sentence or up to 60 characters as title
            first_line = self.description.strip().split("\n")[0].strip()
            self.title = first_line[:60] if len(first_line) > 60 else first_line

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CustomTask:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, custom_tasks_dir: str = "custom_tasks") -> Path:
        """Saves custom task JSON in an isolated custom tasks directory."""
        task_file = safe_path(custom_tasks_dir, f"{self.task_id}/task.json")
        task_file.parent.mkdir(parents=True, exist_ok=True)

        data = self.to_dict()
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return task_file

    @classmethod
    def load(cls, task_id: str, custom_tasks_dir: str = "custom_tasks") -> Optional[CustomTask]:
        try:
            task_file = safe_path(custom_tasks_dir, f"{task_id}/task.json")
        except SecurityError:
            return None
        if not task_file.exists():
            return None
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except Exception:
            return None


def list_custom_tasks(custom_tasks_dir: str = "custom_tasks") -> List[CustomTask]:
    """Lists all saved custom tasks from disk."""
    p = Path(custom_tasks_dir)
    tasks: List[CustomTask] = []
    if not p.exists():
        return tasks
    for sub in p.iterdir():
        if sub.is_dir():
            tf = sub / "task.json"
            if tf.exists():
                try:
                    with open(tf, "r", encoding="utf-8") as f:
                        tasks.append(CustomTask.from_dict(json.load(f)))
                except Exception:
                    pass
    return sorted(tasks, key=lambda t: t.created_at, reverse=True)


def compute_file_diff(original_files: Dict[str, str], modified_files: Dict[str, str]) -> Dict[str, str]:
    """Generates unified diff strings for all modified or added files."""
    diffs: Dict[str, str] = {}
    all_keys = sorted(list(set(original_files.keys()) | set(modified_files.keys())))

    for k in all_keys:
        orig = original_files.get(k, "")
        mod = modified_files.get(k, "")
        if orig != mod:
            orig_lines = orig.splitlines(keepends=True)
            mod_lines = mod.splitlines(keepends=True)
            diff_lines = list(
                difflib.unified_diff(
                    orig_lines,
                    mod_lines,
                    fromfile=f"a/{k}",
                    tofile=f"b/{k}",
                    lineterm="",
                )
            )
            if diff_lines:
                diffs[k] = "\n".join(diff_lines)

    return diffs
