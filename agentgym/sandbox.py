"""Sandbox execution environments for AgentGym.

Supports Docker-based isolated container execution (with resource & network constraints)
and an automated Local Subprocess Sandbox fallback when Docker daemon is not available.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool = False

    @property
    def output(self) -> str:
        out = self.stdout.strip()
        err = self.stderr.strip()
        if out and err:
            return f"{out}\n{err}"
        return out or err or "(no output)"


@dataclass
class TestRunResult:
    passed_tests: Set[str] = field(default_factory=set)
    failed_tests: Set[str] = field(default_factory=set)
    total_tests: int = 0
    pass_rate: float = 0.0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration_seconds: float = 0.0


class BaseSandbox:
    """Base interface for sandbox environments."""

    def __init__(self, timeout: int = 10, max_output_chars: int = 4000):
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    def write_files(self, files: Dict[str, str]) -> None:
        raise NotImplementedError

    def get_files(self) -> Dict[str, str]:
        raise NotImplementedError

    def run_command(self, cmd: str, timeout: Optional[int] = None) -> SandboxResult:
        raise NotImplementedError

    def run_tests(self, test_files: Dict[str, str], timeout: Optional[int] = None) -> TestRunResult:
        raise NotImplementedError

    def cleanup(self) -> None:
        raise NotImplementedError

    def _truncate(self, text: str) -> str:
        if len(text) > self.max_output_chars:
            return text[: self.max_output_chars] + f"\n... [truncated, {len(text)} characters total]"
        return text


class LocalSandbox(BaseSandbox):
    """Isolated local filesystem sandbox using Python subprocess."""

    def __init__(self, timeout: int = 10, max_output_chars: int = 4000):
        super().__init__(timeout=timeout, max_output_chars=max_output_chars)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="agentgym_local_"))

    def write_files(self, files: Dict[str, str]) -> None:
        for rel_path, content in files.items():
            full_path = self.temp_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

    def get_files(self) -> Dict[str, str]:
        files: Dict[str, str] = {}
        for p in self.temp_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("test_") and p.name != "results.xml" and ".pytest_cache" not in str(p):
                rel = str(p.relative_to(self.temp_dir)).replace("\\", "/")
                files[rel] = p.read_text(encoding="utf-8", errors="replace")
        return files

    def run_command(self, cmd: str, timeout: Optional[int] = None) -> SandboxResult:
        t_limit = timeout or self.timeout
        start_time = time.time()
        timed_out = False

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.temp_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.temp_dir),
                shell=True,
                capture_output=True,
                text=True,
                timeout=t_limit,
                env=env,
            )
            stdout = self._truncate(res.stdout)
            stderr = self._truncate(res.stderr)
            exit_code = res.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = self._truncate(e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""))
            stderr = self._truncate((e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")) + "\nCommand timed out.")
            exit_code = -1
        except Exception as e:
            stdout = ""
            stderr = f"Execution error: {str(e)}"
            exit_code = 1

        duration = time.time() - start_time
        return SandboxResult(stdout=stdout, stderr=stderr, exit_code=exit_code, duration_seconds=duration, timed_out=timed_out)

    def run_tests(self, test_files: Dict[str, str], timeout: Optional[int] = None) -> TestRunResult:
        """Mounts hidden tests temporarily, executes pytest with junitxml, and cleans them up."""
        written_test_paths: list[Path] = []
        for rel_path, content in test_files.items():
            p = self.temp_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            written_test_paths.append(p)

        xml_path = self.temp_dir / "results.xml"
        if xml_path.exists():
            xml_path.unlink()

        cmd = f'"{sys.executable}" -m pytest --junitxml=results.xml -q -rA'
        res = self.run_command(cmd, timeout=timeout)

        passed, failed, total = self._parse_junit_xml(xml_path, res.stdout)

        # Clean up hidden test files and results so the agent cannot inspect them
        for p in written_test_paths:
            if p.exists():
                p.unlink()
        if xml_path.exists():
            xml_path.unlink()

        pytest_cache = self.temp_dir / ".pytest_cache"
        if pytest_cache.exists():
            shutil.rmtree(pytest_cache, ignore_errors=True)

        pass_rate = (len(passed) / total) if total > 0 else 0.0

        return TestRunResult(
            passed_tests=passed,
            failed_tests=failed,
            total_tests=total,
            pass_rate=pass_rate,
            stdout=res.stdout,
            stderr=res.stderr,
            timed_out=res.timed_out,
            duration_seconds=res.duration_seconds,
        )

    def _parse_junit_xml(self, xml_path: Path, fallback_stdout: str) -> tuple[Set[str], Set[str], int]:
        passed: Set[str] = set()
        failed: Set[str] = set()

        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for tc in root.iter("testcase"):
                    name = tc.attrib.get("name", "test")
                    classname = tc.attrib.get("classname", "")
                    full_name = f"{classname}::{name}" if classname else name
                    has_failure = tc.find("failure") is not None or tc.find("error") is not None
                    if has_failure:
                        failed.add(full_name)
                    else:
                        passed.add(full_name)
                total = len(passed) + len(failed)
                if total > 0:
                    return passed, failed, total
            except Exception:
                pass

        # Fallback stdout parsing
        for line in fallback_stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("PASSED "):
                test_name = line_str.split("PASSED ", 1)[1].strip()
                passed.add(test_name)
            elif line_str.startswith("FAILED "):
                test_name = line_str.split("FAILED ", 1)[1].strip().split(" - ")[0]
                failed.add(test_name)

        total = len(passed) + len(failed)
        return passed, failed, total

    def cleanup(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class DockerSandbox(BaseSandbox):
    """Isolated Docker container sandbox enforcing network isolation, memory, CPU and pids limits."""

    IMAGE_NAME = "agentgym-sandbox:python3.11"

    def __init__(
        self,
        timeout: int = 10,
        max_output_chars: int = 4000,
        mem_limit: str = "256m",
        cpu_limit: float = 0.5,
        pids_limit: int = 128,
    ):
        super().__init__(timeout=timeout, max_output_chars=max_output_chars)
        self.mem_limit = mem_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit
        self.host_dir = Path(tempfile.mkdtemp(prefix="agentgym_docker_"))

        import docker

        self.client = docker.from_env()
        self._ensure_image()

    def _ensure_image(self) -> None:
        """Verify image exists or create a slim container with pytest."""
        try:
            self.client.images.get(self.IMAGE_NAME)
        except Exception:
            # Build inline slim image
            dockerfile = "FROM python:3.11-slim\nRUN pip install --no-cache-dir pytest\nWORKDIR /workspace\n"
            dockerfile_path = self.host_dir / "Dockerfile"
            dockerfile_path.write_text(dockerfile)
            self.client.images.build(path=str(self.host_dir), tag=self.IMAGE_NAME, rm=True)
            dockerfile_path.unlink(missing_ok=True)

    def write_files(self, files: Dict[str, str]) -> None:
        for rel_path, content in files.items():
            p = self.host_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def get_files(self) -> Dict[str, str]:
        files: Dict[str, str] = {}
        for p in self.host_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("test_") and p.name != "results.xml" and ".pytest_cache" not in str(p):
                rel = str(p.relative_to(self.host_dir)).replace("\\", "/")
                files[rel] = p.read_text(encoding="utf-8", errors="replace")
        return files

    def run_command(self, cmd: str, timeout: Optional[int] = None) -> SandboxResult:
        t_limit = timeout or self.timeout
        start_time = time.time()
        timed_out = False

        volumes = {str(self.host_dir.resolve()): {"bind": "/workspace", "mode": "rw"}}

        try:
            container = self.client.containers.run(
                self.IMAGE_NAME,
                command=f"/bin/sh -c '{cmd}'",
                volumes=volumes,
                working_dir="/workspace",
                network_disabled=True,
                mem_limit=self.mem_limit,
                nano_cpus=int(self.cpu_limit * 1e9),
                pids_limit=self.pids_limit,
                detach=True,
                remove=False,
            )

            try:
                res = container.wait(timeout=t_limit)
                exit_code = res.get("StatusCode", 0)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                stdout = self._truncate(logs)
                stderr = ""
            except Exception:
                timed_out = True
                try:
                    container.kill()
                except Exception:
                    pass
                stdout = ""
                stderr = "Command timed out in Docker container."
                exit_code = -1
            finally:
                container.remove(force=True)

        except Exception as e:
            stdout = ""
            stderr = f"Docker execution error: {str(e)}"
            exit_code = 1

        duration = time.time() - start_time
        return SandboxResult(stdout=stdout, stderr=stderr, exit_code=exit_code, duration_seconds=duration, timed_out=timed_out)

    def run_tests(self, test_files: Dict[str, str], timeout: Optional[int] = None) -> TestRunResult:
        written_test_paths: list[Path] = []
        for rel_path, content in test_files.items():
            p = self.host_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            written_test_paths.append(p)

        xml_path = self.host_dir / "results.xml"
        if xml_path.exists():
            xml_path.unlink()

        res = self.run_command("pytest --junitxml=results.xml -q -rA", timeout=timeout)

        # Parse XML
        local_helper = LocalSandbox()
        passed, failed, total = local_helper._parse_junit_xml(xml_path, res.stdout)
        local_helper.cleanup()

        for p in written_test_paths:
            if p.exists():
                p.unlink()
        if xml_path.exists():
            xml_path.unlink()

        pass_rate = (len(passed) / total) if total > 0 else 0.0

        return TestRunResult(
            passed_tests=passed,
            failed_tests=failed,
            total_tests=total,
            pass_rate=pass_rate,
            stdout=res.stdout,
            stderr=res.stderr,
            timed_out=res.timed_out,
            duration_seconds=res.duration_seconds,
        )

    def cleanup(self) -> None:
        if self.host_dir.exists():
            shutil.rmtree(self.host_dir, ignore_errors=True)


class Sandbox:
    """Factory creating either DockerSandbox or LocalSandbox based on system availability."""

    @staticmethod
    def is_docker_available() -> bool:
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def create(
        mode: str = "auto",
        timeout: int = 10,
        max_output_chars: int = 4000,
        mem_limit: str = "256m",
        cpu_limit: float = 0.5,
        pids_limit: int = 128,
    ) -> BaseSandbox:
        if mode == "docker":
            return DockerSandbox(
                timeout=timeout,
                max_output_chars=max_output_chars,
                mem_limit=mem_limit,
                cpu_limit=cpu_limit,
                pids_limit=pids_limit,
            )
        elif mode == "local":
            return LocalSandbox(timeout=timeout, max_output_chars=max_output_chars)
        else:  # auto
            if Sandbox.is_docker_available():
                return DockerSandbox(
                    timeout=timeout,
                    max_output_chars=max_output_chars,
                    mem_limit=mem_limit,
                    cpu_limit=cpu_limit,
                    pids_limit=pids_limit,
                )
            return LocalSandbox(timeout=timeout, max_output_chars=max_output_chars)
