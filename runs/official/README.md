# Canonical Official Benchmark Result: DebugArena

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

- **Git Commit SHA (Audit):** `e97aa0f16a790c01f916cfb7019e931660b08664`
- **Git Commit SHA (Source Run):** `a2c5d80092c7caecb084931a293158c558b8849b`
- **Working Tree Status:** `dirty (audit remediation phase active)`
- **Configuration Hash (`config.yaml`):** `c63edf2858064fef90cf7b4940cb2f0196f6634345002492b753841e31edc84d`
- **Task Manifest Hash (30 Tasks):** `016fa52aa64aa6875ebf1615663c49eecbd7d4b2616167f02732145f418cad9f`
- **Full Task Corpus Hash (100 Tasks):** `b41e631ee10b7aa7b1edf70eadac5158ff5363d495b110837ac555eda2701af3`
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
