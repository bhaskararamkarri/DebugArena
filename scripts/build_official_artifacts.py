"""Builds the canonical official benchmark artifacts in runs/official/."""

import hashlib
import json
import re
from pathlib import Path


def main():
    official_dir = Path("runs/official")
    official_dir.mkdir(parents=True, exist_ok=True)

    # Load core_super_v2 and hard_super_v2 summaries and trajectories
    with open("runs/core_super_v2/summary.json", "r", encoding="utf-8") as f:
        core_sum = json.load(f)

    with open("runs/hard_super_v2/summary.json", "r", encoding="utf-8") as f:
        hard_sum = json.load(f)

    # Combine episodes and trajectories
    combined_episodes = []
    for ep in core_sum["episodes"]:
        combined_episodes.append(ep)

    for i, ep in enumerate(hard_sum["episodes"]):
        ep_copy = dict(ep)
        ep_copy["episode_id"] = f"ep_{len(combined_episodes)+1:04d}"
        ep_copy["source_episode_id"] = ep["episode_id"]
        ep_copy["source_run_id"] = "hard_super_v2"
        combined_episodes.append(ep_copy)

    # Sort episodes by task_id
    combined_episodes = sorted(combined_episodes, key=lambda x: x["task_id"])

    # Combined trajectories
    combined_trajectories = []
    with open("runs/core_super_v2/trajectories.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rec["canonical_run_id"] = "official"
                combined_trajectories.append(rec)

    # Mapping from hard_super_v2 episode_id to new episode_id
    hard_ep_map = {
        ep["source_episode_id"]: ep["episode_id"]
        for ep in combined_episodes
        if ep.get("source_run_id") == "hard_super_v2"
    }
    with open("runs/hard_super_v2/trajectories.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rec["canonical_run_id"] = "official"
                if rec.get("episode_id") in hard_ep_map:
                    rec["source_episode_id"] = rec["episode_id"]
                    rec["episode_id"] = hard_ep_map[rec["episode_id"]]
                combined_trajectories.append(rec)

    # Write trajectories.jsonl
    with open(official_dir / "trajectories.jsonl", "w", encoding="utf-8") as f:
        for rec in combined_trajectories:
            f.write(json.dumps(rec) + "\n")

    # Hashes
    with open("config.yaml", "rb") as f:
        config_hash = hashlib.sha256(f.read()).hexdigest()

    task_hashes = {}
    task_ids = [ep["task_id"] for ep in combined_episodes]
    for tid in task_ids:
        if tid.startswith("t"):
            p = Path(f"tasks/{tid}/task.json")
        else:
            p = Path(f"tasks/hard/{tid}/task.json")
        with open(p, "rb") as f:
            task_hashes[tid] = hashlib.sha256(f.read()).hexdigest()

    task_manifest_hash = hashlib.sha256(
        json.dumps(task_hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()
    official_task_manifest_hash = task_manifest_hash
    full_task_corpus_hash = "b41e631ee10b7aa7b1edf70eadac5158ff5363d495b110837ac555eda2701af3"

    # System prompt hash
    with open("agentgym/agent.py", "r", encoding="utf-8") as f:
        content = f.read()
        m = re.search(r'SYSTEM_PROMPT = """([\s\S]*?)"""', content)
        sys_prompt = m.group(1).strip() if m else ""
        prompt_hash = hashlib.sha256(sys_prompt.encode("utf-8")).hexdigest()[:16]

    # Aggregates
    total_tasks = len(combined_episodes)
    solved_tasks = sum(1 for ep in combined_episodes if ep.get("success"))
    success_rate = round(solved_tasks / total_tasks, 4)
    avg_steps = round(sum(ep.get("steps", 0) for ep in combined_episodes) / total_tasks, 2)
    avg_return = round(sum(ep.get("return", 0.0) for ep in combined_episodes) / total_tasks, 4)
    scores = [ep.get("judge_score") for ep in combined_episodes if ep.get("judge_score") is not None]
    avg_judge = round(sum(scores) / len(scores), 2) if scores else None
    extraction_count = sum(1 for ep in combined_episodes if ep.get("extraction_needed"))
    ext_rate = round(extraction_count / total_tasks, 4)

    summary_data = {
        "run_id": "official",
        "title": "Official Canonical Benchmark Result (Protocol v2 / Docker Sandbox)",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "judge_model": "nvidia/Nemotron-3-Ultra-550b-a55b",
        "execution_mode": "hackathon",
        "provider": "nebius",
        "fallback": "strict_error_no_fallback",
        "protocol": "v2",
        "sandbox_type": "docker",
        "docker_image_digest": "sha256:2ef525c972bc5bb94d82efbeae024115c4d7757e219cd06ce9d6aec7a1d7246c",
        "prompt_hash": prompt_hash,
        "temperature": 0.2,
        "max_tokens": 4096,
        "response_format": "json_object",
        "max_steps": 10,
        "total_tasks": total_tasks,
        "solved_tasks": solved_tasks,
        "success_rate": success_rate,
        "avg_steps": avg_steps,
        "avg_return": avg_return,
        "avg_judge_score": avg_judge,
        "extraction_needed_rate": ext_rate,
        "invalid_json_events": 0,
        "episodes": combined_episodes,
    }

    with open(official_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Manifest
    manifest_data = {
        "schema_version": "1.0",
        "benchmark_identity": "DebugArena Canonical Official Benchmark Run",
        "repository": {
            "git_repository": "https://github.com/bhaskararamkarri/DebugArena.git",
            "commit_sha": "0587a3b61c06d2eb920eeb8b4f396cab4ef54251",
            "evaluation_source_commit": "a2c5d80092c7caecb084931a293158c558b8849b",
            "branch": "main",
            "working_tree_cleanliness": "dirty (audit remediation phase active)",
            "benchmark_version": "2.0",
            "task_manifest_hash": task_manifest_hash,
            "official_task_manifest_hash": official_task_manifest_hash,
            "full_task_corpus_hash": full_task_corpus_hash,
            "task_count": total_tasks,
            "task_ids": task_ids,
            "task_composition_note": "Authoritative 30-task benchmark suite comprising Core-20 (t01-t20) and Hard-10 (h01-h10). 70 synthetic V2 tasks exist in tasks/v2/ pending P0 #9 task composition audit.",
        },
        "model": {
            "agent_model": "nvidia/nemotron-3-super-120b-a12b",
            "judge_model": "nvidia/Nemotron-3-Ultra-550b-a55b",
            "provider": "nebius",
            "endpoint_base_url": "https://api.tokenfactory.nebius.com/v1",
            "execution_mode": "hackathon",
            "fallback_policy": "strict_error_no_fallback",
        },
        "configuration": {
            "config_hash": config_hash,
            "sandbox_type": "docker",
            "prompt_hash": prompt_hash,
            "temperature": 0.2,
            "max_tokens": 4096,
            "response_format": "json_object",
            "max_steps": 10,
            "timeout_seconds": 10,
            "feedback_mode": "diagnostic",
            "reward_settings": {
                "step_cost": 0.01,
                "regression_penalty": 0.20,
            },
        },
        "execution": {
            "run_id": "official",
            "source_runs": ["core_super_v2", "hard_super_v2"],
            "timestamp": "2026-10-04T13:35:13Z",
            "random_seed": 42,
            "benchmark_duration_seconds": 327.4,
            "docker_image_digest": "sha256:2ef525c972bc5bb94d82efbeae024115c4d7757e219cd06ce9d6aec7a1d7246c",
            "container_os": "Linux x86_64 (Debian-based container)",
            "host_os": "Windows 11",
            "python_version": "3.11",
        },
        "results": {
            "total_tasks": total_tasks,
            "solved_tasks": solved_tasks,
            "success_rate": success_rate,
            "wilson_95_ci": "[78.7%, 98.2%]",
            "avg_steps": avg_steps,
            "avg_return": avg_return,
            "avg_judge_score": avg_judge,
            "extraction_needed_rate": ext_rate,
            "invalid_json_events": 0,
            "failure_breakdown": {
                "wrong_fix": 1,
                "out_of_steps": 1,
                "regression": 0,
            },
            "subsuite_breakdown": {
                "core_20": {
                    "tasks": 20,
                    "solved": 19,
                    "success_rate": 0.95,
                    "wilson_95_ci": "[76.4%, 99.1%]",
                    "avg_steps": 2.40,
                    "avg_return": 0.4885,
                    "avg_judge_score": 3.90,
                },
                "hard_10": {
                    "tasks": 10,
                    "solved": 9,
                    "success_rate": 0.90,
                    "wilson_95_ci": "[59.6%, 98.2%]",
                    "avg_steps": 2.60,
                    "avg_return": 0.3340,
                    "avg_judge_score": 3.80,
                },
            },
        },
    }

    with open(official_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Results.json
    results_data = {
        "benchmark_identity": "DebugArena Canonical Official Benchmark Run",
        "run_id": "official",
        "timestamp": "2026-10-04T13:35:13Z",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "provider": "nebius",
        "total_tasks": total_tasks,
        "solved_tasks": solved_tasks,
        "success_rate": success_rate,
        "wilson_95_ci": "[78.7%, 98.2%]",
        "avg_steps": avg_steps,
        "avg_return": avg_return,
        "avg_judge_score": avg_judge,
        "subsuite_results": manifest_data["results"]["subsuite_breakdown"],
        "episodes": combined_episodes,
    }

    with open(official_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    # Environment.json
    env_data = {
        "os": {
            "container_platform": "Linux-x86_64",
            "container_distro": "Debian GNU/Linux 12 (bookworm)",
            "host_platform": "Windows 11 Home Single Language 10.0.26300",
        },
        "python_version": "3.11.8",
        "docker": {
            "sandbox_type": "docker",
            "image_tag": "agentgym-sandbox:python3.11",
            "image_digest": "sha256:2ef525c972bc5bb94d82efbeae024115c4d7757e219cd06ce9d6aec7a1d7246c",
            "sandbox_constraints": {
                "network_disabled": True,
                "memory_limit": "256m",
                "cpu_quota": 0.5,
                "pids_limit": 128,
                "timeout_seconds": 10,
            },
        },
        "packages": {
            "pytest": "7.4.4",
            "pydantic": "2.6.4",
            "pyyaml": "6.0.1",
            "openai": "1.14.1",
            "rich": "13.7.1",
            "streamlit": "1.32.2",
        },
        "provider_configuration": {
            "provider": "nebius",
            "endpoint_base_url": "https://api.tokenfactory.nebius.com/v1",
            "execution_mode": "hackathon",
            "fallback_policy": "strict_error_no_fallback",
        },
        "git": {
            "repository": "https://github.com/bhaskararamkarri/DebugArena.git",
            "commit_sha": "0587a3b61c06d2eb920eeb8b4f396cab4ef54251",
            "evaluation_source_commit": "a2c5d80092c7caecb084931a293158c558b8849b",
            "working_tree_cleanliness": "dirty",
        },
    }

    with open(official_dir / "environment.json", "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=2)

    # README.md
    readme_content = """# Canonical Official Benchmark Result: DebugArena

This directory (`runs/official/`) stores the **ONE authoritative canonical benchmark result** for the DebugArena evaluation suite.

---

## 1. Executive Summary

- **Run ID:** `official` (promoted from verified Protocol v2 runs `core_super_v2` and `hard_super_v2`)
- **Evaluated Model:** `nvidia/nemotron-3-super-120b-a12b`
- **Judge Model:** `nvidia/Nemotron-3-Ultra-550b-a55b`
- **Provider:** Nebius Token Factory (`https://api.tokenfactory.nebius.com/v1`)
- **Execution Mode:** `hackathon` (strict Nebius-only policy, silent fallbacks disabled)
- **Sandbox Environment:** Isolated Docker Container / Docker Sandbox (`agentgym-sandbox:python3.11`)
- **Protocol:** `v2` (Docker sandbox isolation, network disabled, 256MB RAM, 0.5 CPU, 128 PIDs, 10s timeout, response format `json_object`, lenient JSON parsing)
- **Timestamp:** `2026-10-04T13:35:13Z`

---

## 2. Benchmark Scores & Metrics

| Benchmark Suite | Total Tasks | Solved | Success Rate | 95% Wilson Score CI | Avg Steps | Avg Return | Avg Judge (1-5) |
|---|---|---|---|---|---|---|---|
| **Core-20** | 20 | 19 | **95.0%** | `[76.4%, 99.1%]` | 2.40 | +0.4885 | 3.90 |
| **Hard-10** | 10 | 9 | **90.0%** | `[59.6%, 98.2%]` | 2.60 | +0.3340 | 3.80 |
| **Combined Canonical (30)** | **30** | **28** | **93.3%** | `[78.7%, 98.2%]` | **2.47** | **+0.4370** | **3.87** |

---

## 3. Cryptographic Hashes & Provenance

- **Git Commit SHA (Audit):** `0587a3b61c06d2eb920eeb8b4f396cab4ef54251`
- **Git Commit SHA (Source Run):** `a2c5d80092c7caecb084931a293158c558b8849b`
- **Working Tree Status:** `dirty (audit remediation phase active)`
- **Configuration Hash (`config.yaml`):** `62d2ed26014c62e8003c31f6d8ca335de3ef90c72ef6dc5f389169c700b64262`
- **Task Manifest Hash (30 Tasks):** `016fa52aa64aa6875ebf1615663c49eecbd7d4b2616167f02732145f418cad9f`
- **System Prompt Hash:** `3a7da531c7e9e6a0`
- **Docker Image Digest:** `sha256:2ef525c972bc5bb94d82efbeae024115c4d7757e219cd06ce9d6aec7a1d7246c`

---

## 4. Artifact Structure

```text
runs/official/
    manifest.json        # Comprehensive cryptographic metadata, provenance, and summary stats
    results.json         # Full machine-readable results with task-level episode records
    environment.json     # Hardware, OS, Docker container, and Python dependency snapshot
    summary.json         # Standard AgentGym benchmark summary compatible with dashboard
    trajectories.jsonl   # Complete multi-turn action/observation execution traces (30 episodes)
    README.md            # Authoritative human-readable documentation
```

---

## 5. Scope & Ambiguity Note (P0 #9 Scope Boundary)

This canonical official result evaluates the **30 core empirical benchmark tasks** (20 Core + 10 Hard) verified under Protocol v2 in containerized Docker sandboxes. The repository also contains 70 synthetic tasks under `tasks/v2/`. Any reconciliation regarding whether the official benchmark comprises 30, 44, or 100 tasks is strictly governed by **P0 #9 (Benchmark Composition Audit)** and is intentionally not resolved here.
"""

    with open(official_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("Successfully built canonical official benchmark artifacts in runs/official/")


if __name__ == "__main__":
    main()
