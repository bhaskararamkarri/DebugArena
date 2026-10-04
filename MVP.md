# DebugArena — MVP Document

**DebugArena — an arena where coding agents compete on real bugs, scored by hidden tests in a Docker sandbox, and every attempt becomes training data.**
*Formerly named AgentGym; the Python package keeps the name `agentgym` for compatibility.*
Nebius × NVIDIA Global AI Hackathon · Track: Agent Gym & Coding Environments
Author: Bhaskar · Document date: 2 Oct 2026 · Build window: 10 days

---

## 1. One-line pitch

DebugArena gives an AI agent a broken Python repo, lets it edit and run code inside an isolated Docker sandbox, scores it automatically with hidden pytest tests, and saves every step as a training-ready dataset, so the environment doesn't just test agents, it produces the data to improve them.

## 2. Problem and opportunity

- Everyone is building coding agents. Very few people are building the place where agents are measured and improved.
- Frontier labs train coding agents with reinforcement learning environments, but open, small, reusable ones are rare.
- Existing benchmarks give a score. They don't hand you clean trajectories you can reuse for fine-tuning.

**Opportunity:** a lightweight, open environment built on NVIDIA Nemotron and Nebius infrastructure that (a) compares open models fairly and (b) exports their trajectories as a dataset.

## 3. Goals and non-goals

**MVP goals**
1. Run an agent end to end on a task: reset → act → test → reward → done.
2. Execute all agent actions safely inside Docker.
3. Compute an automatic, reproducible reward from hidden tests.
4. Compare at least two Nemotron models on a leaderboard.
5. Save every episode to JSONL and export a clean training dataset.
6. Show results and replay any episode in a dashboard.

**Non-goals (explicitly out of the MVP)**
- Running a real RL training loop (PPO/GRPO). We export data and show it is ready for SFT or RL.
- Multi-language tasks (Python only).
- Multi-file refactors or large repos (small repos, 1–3 files).
- User accounts, auth, or hosted multi-tenant service.

## 4. Users

| User | Need | How AgentGym helps |
|---|---|---|
| Agent builder | Know which model/prompt fixes bugs better | Leaderboard, per-task pass rates |
| Researcher / ML engineer | Data to fine-tune a coding model | JSONL trajectory export |
| Hackathon judge | Understand value in under 2 minutes | Clear demo: replay + leaderboard + dataset |

## 5. MVP scope

### 5.1 Feature list (priority order)

| # | Feature | Priority | Acceptance criteria |
|---|---|---|---|
| F1 | Task set (20 tasks) | Must | Each task fails its tests before the fix and passes after the reference fix. Verified 3 times for flakiness. |
| F2 | Gymnasium-style environment | Must | `reset(task_id)` returns an observation. `step(action)` returns `(obs, reward, done, info)`. |
| F3 | Docker sandbox | Must | No network, memory/CPU/time limits, hidden tests unreadable by the agent. |
| F4 | Reward function | Must | Computed from test results plus step and regression penalties. Deterministic. |
| F5 | Agent loop (Nemotron via Token Factory) | Must | Agent completes at least 1 task end to end. Invalid JSON is retried once, then logged as a failed step. |
| F6 | Trajectory logging | Must | Every step written to JSONL with the full schema (section 7). |
| F7 | Parallel runner | Must | N episodes run concurrently with a thread pool. |
| F8 | Leaderboard | Must | At least 2 models compared by pass rate, average steps and average reward. |
| F9 | Replay viewer | Should | Pick any episode and step through action, output and reward. |
| F10 | Nemotron judge score | Should | Optional 1–5 code-quality score stored next to the test result. |
| F11 | Dataset export | Should | One command writes successful trajectories as chat-style JSONL. |
| F12 | Batch run on Nebius Serverless Jobs | Could | One large batch executed as a Serverless Job, with results collected. |

### 5.2 Definition of "MVP done"

- 20 tasks verified.
- At least 2 models evaluated on all 20 tasks, with at least 1 run each.
- Results visible in the dashboard, including replay of any episode.
- Dataset export file produced.
- Public GitHub repo with README, demo video recorded, submission filed.

## 6. System architecture

```
 Task JSON (buggy repo + description + hidden tests)
        │
        ▼
 ┌───────────────┐   observation    ┌──────────────────────────┐
 │  BugFixEnv    │ ───────────────► │ Agent (Nemotron via      │
 │ reset()/step()│ ◄─────────────── │ Nebius Token Factory API)│
 └──────┬────────┘   JSON action    └──────────────────────────┘
        │ edit / run / submit
        ▼
 ┌───────────────┐   pytest results  ┌────────────┐
 │ Docker sandbox│ ────────────────► │  Reward    │
 └───────────────┘                   └─────┬──────┘
                                           ▼
                         Trajectory logger (JSONL)
                                           │
              ┌────────────────────────────┼───────────────────┐
              ▼                            ▼                   ▼
        Leaderboard                  Replay viewer      Dataset export
                          (Streamlit dashboard)         (SFT-ready JSONL)
```

**Parallel execution:** each episode is independent, so a thread pool runs many at once. Only the LLM calls are remote, so this works on a laptop. The final large batch can run as a Nebius Serverless Job.

## 7. Technical specification

### 7.1 Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Agent models | Nemotron Nano / Super through Nebius Token Factory (OpenAI-compatible API) |
| Judge (optional) | Nemotron 3 Ultra, if available on Token Factory |
| Fallback models | build.nvidia.com (free `nvapi-` key) and OpenRouter free Nemotron |
| Sandbox | Docker (`python:3.11-slim` with pytest preinstalled) |
| Environment API | Gymnasium-style class (own implementation, no hard dependency required) |
| Dashboard | Streamlit |
| Batch compute | Nebius Serverless Jobs |
| Data format | JSON for tasks, JSONL for trajectories |

Model names, base URL and keys live in `config.yaml` and `.env`. Copy the exact model IDs from the Token Factory console.

### 7.2 Task format (`tasks/<id>/task.json`)

```json
{
  "task_id": "t07_off_by_one",
  "difficulty": "easy",
  "bug_type": "off_by_one",
  "description": "sum_range(a, b) should include b but returns the wrong total.",
  "repo_files": { "mathutils.py": "def sum_range(a, b):\n    return sum(range(a, b))\n" },
  "tests": { "test_mathutils.py": "from mathutils import sum_range\n\ndef test_basic():\n    assert sum_range(1, 3) == 6\n" },
  "reference_fix": { "mathutils.py": "def sum_range(a, b):\n    return sum(range(a, b + 1))\n" }
}
```

`tests` are hidden: they are never shown in the observation and never mounted during agent `run` commands. They are copied in only at scoring time.

### 7.3 Environment interface

```python
env = BugFixEnv(tasks_dir="tasks", max_steps=10)
obs = env.reset(task_id)                 # returns observation dict
obs, reward, done, info = env.step(action)
```

**Observation**
```json
{
  "description": "...",
  "files": { "mathutils.py": "..." },
  "last_output": "stdout/stderr of the last run, or 'file updated'",
  "steps_left": 8
}
```

**Actions (the agent must answer with exactly one JSON object)**
```json
{"type": "edit",   "path": "mathutils.py", "content": "<full new file content>"}
{"type": "run",    "cmd": "python -c 'from mathutils import sum_range; print(sum_range(1,3))'"}
{"type": "submit"}
```

- `edit` replaces the whole file (simplest to parse and apply).
- `run` executes a command in the sandbox without the hidden tests present. Output is truncated to a fixed length.
- `submit` ends the episode. The episode also ends when all hidden tests pass or `max_steps` is reached.

### 7.4 Reward specification

After every step, hidden tests are run (in a separate, clean sandbox call) and `pass_rate = tests_passed / tests_total`.

```
step_reward = (pass_rate_t − pass_rate_{t−1})   # progress
              − 0.01                              # step cost
              − 0.20 × regression               # 1 if any previously passing test now fails
episode_return = sum of step_rewards
```

The progress terms add up to the final pass rate, so the return equals the final pass rate minus efficiency and regression penalties. Agents are rewarded for fixing bugs, using few steps, and not breaking working code.

**Primary metric for the leaderboard:** task success rate (pass_rate = 1.0 at the end). Secondary: average steps and average return.

### 7.5 Sandbox rules

- Fresh container per episode (or per run call) from a pre-built image.
- `network_disabled=True`, `mem_limit=256m`, CPU limit 0.5, pids limit 128, timeout 10 s per command.
- Agent-visible files are copied into a temp directory and mounted. Hidden tests are mounted read-only only in the scoring call.
- Test results parsed from pytest output (`-q -rA` or junit XML).

### 7.6 Agent prompt (system message, summary)

- You are fixing a bug in a small Python repo. You can edit files, run commands, and submit.
- Respond with exactly one JSON action and nothing else.
- Show only the schema above, plus one example per action.
- Each turn the user message contains the latest observation.

Parsing rule: strip code fences, `json.loads`, validate the schema. On failure, retry once with a "your last reply was not valid JSON" message. If it fails again, log a failed step with reward −0.01 and continue.

### 7.7 Trajectory schema (`runs/<run_id>/trajectories.jsonl`)

One line per step:

```json
{
  "run_id": "2026-10-05_super_v1",
  "model": "<model id>",
  "episode_id": "ep_0042",
  "task_id": "t07_off_by_one",
  "step": 3,
  "prompt": [ { "role": "user", "content": "..." } ],
  "action": { "type": "edit", "path": "mathutils.py", "content": "..." },
  "output": "file updated",
  "pass_rate": 1.0,
  "reward": 0.89,
  "done": true,
  "judge_score": 4,
  "latency_ms": 2100,
  "timestamp": "2026-10-05T10:21:33Z"
}
```

### 7.8 Dataset export

Command: `python export_dataset.py --run <run_id> --min-pass-rate 1.0`

Output `dataset/agentgym_sft.jsonl`, one episode per line, successful episodes only:

```json
{"task_id": "t07_off_by_one", "messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "<observation 0>"},
  {"role": "assistant", "content": "<action 0 JSON>"},
  {"role": "user", "content": "<observation 1>"},
  {"role": "assistant", "content": "<action 1 JSON>"}
], "return": 0.89, "steps": 2}
```

Include a short `DATASET_CARD.md` (fields, how it was made, intended use, limitations).

### 7.9 Dashboard (Streamlit, 3 pages)

1. **Leaderboard:** table per model with success rate, average steps, average return, average judge score. Bar chart of success rate.
2. **Task breakdown:** pass rate per task and per bug type, with a heatmap of model × task.
3. **Episode replay:** choose model → task → episode, then step through action, output, pass rate and reward.

## 8. Task set plan (20 tasks)

| Group | Count | Examples |
|---|---|---|
| Easy | 7 | off-by-one, wrong comparison operator, wrong return value, typo in variable name |
| Medium | 9 | missing edge case (empty list), mutable default argument, wrong string slicing, integer vs float division, wrong dictionary key handling |
| Harder | 4 | bug spread across 2 files, logic bug found only by running code, off-by-one inside a loop with state, incorrect sorting key |

Rules for every task: 1–3 files, under 60 lines total, 3–6 hidden tests, deterministic, no network or randomness, and at least one test that already passes before the fix (so regression penalties matter).

## 9. Evaluation plan

- Run all 20 tasks for each model, 1–3 runs each (depending on credits).
- Models: Nemotron Nano and Nemotron Super (add Ultra as agent only if time and credits allow).
- Report: success rate, average steps, average return, failure categories (invalid JSON, regression, ran out of steps, wrong fix).
- Include one failure analysis: which bug types are hardest for each model.

## 10. Repository structure

```
agentgym/
├── README.md
├── config.yaml
├── .env.example
├── requirements.txt
├── agentgym/
│   ├── env.py            # BugFixEnv
│   ├── sandbox.py        # Docker helpers
│   ├── reward.py
│   ├── agent.py          # prompt, API call, action parsing
│   ├── runner.py         # parallel episodes + logging
│   └── judge.py          # optional Nemotron judge
├── tasks/                # 20 task folders (task.json each)
├── scripts/
│   ├── verify_tasks.py   # fails-before / passes-after check
│   ├── run_eval.py
│   └── export_dataset.py
├── dashboard/app.py
├── runs/                 # trajectories (gitignored except a sample)
├── dataset/              # exported SFT data + DATASET_CARD.md
└── docs/                 # architecture diagram, screenshots
```

## 11. 10-day build timeline

(Treating 11 Oct as your own deadline, one day before the stated 10 days. Confirm the official deadline and timezone on the hackathon page.)

| Day | Date | Deliverable |
|---|---|---|
| 1 | Fri 2 Oct | Keys, credits, repo, Docker tested, one Nemotron API call working |
| 2 | Sat 3 Oct | First 10 tasks written and verified (`verify_tasks.py`) |
| 3 | Sun 4 Oct | `BugFixEnv` and Docker sandbox working on 3 tasks |
| 4 | Mon 5 Oct | Reward function, remaining 10 tasks |
| 5 | Tue 6 Oct | Agent loop with Nemotron, one task solved end to end |
| 6 | Wed 7 Oct | Full 20-task run with JSONL logging |
| 7 | Thu 8 Oct | Parallel runner, second model run, first leaderboard numbers |
| 8 | Fri 9 Oct | Dashboard (leaderboard, task breakdown, replay), optional judge |
| 9 | Sat 10 Oct | Serverless Jobs batch, dataset export, README, architecture diagram |
| 10 | Sun 11 Oct | Demo video, final testing, submission |

**Cut order if you fall behind:** Serverless Jobs → judge score → task breakdown page → tasks 16–20. Never cut: sandbox, reward, trajectories, leaderboard, replay.

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Docker problems on Windows | Blocks the whole project | Use WSL2, test Docker on day 1 |
| Agent returns invalid JSON | Wasted steps | Strict prompt, one retry, log as failed step |
| Credits or rate limits run out | Cannot run evaluations | Develop on free OpenRouter/NVIDIA keys, spend Nebius credits on final runs |
| Flaky or wrong tasks | Unfair results | `verify_tasks.py` runs each task 3 times before and after the fix |
| Agent sees hidden tests | Invalid benchmark | Tests never mounted during `run` commands |
| Serverless Jobs setup is slow | Lost time | Treat as "could have"; do it on day 9 only if the rest is done |
| Running out of time | Incomplete demo | Fixed cut order above; record the video by midday on day 10 |

## 13. Success metrics

**Build metrics**
- 20 verified tasks, 2+ models evaluated, 100% of episodes logged.
- Dataset file exported, with at least 20 successful episodes of training-ready data (more if success rates allow).

**Demo metrics (what judges should see)**
- A live replay of one episode in under 60 seconds.
- A leaderboard with clear differences between models.
- The exported dataset and a sentence on how it would be used for training.

## 14. Demo script (about 2.5 minutes)

1. **Hook (20 s):** "Everyone builds agents. We built the gym where agents get better."
2. **How it works (30 s):** show the architecture: buggy repo → Nemotron → sandbox → tests = reward.
3. **Live replay (60 s):** replay one episode: the agent reads the bug, edits, runs, gets the reward.
4. **Leaderboard (30 s):** Nano vs Super: success rate, steps, failure types.
5. **Dataset (20 s):** show the JSONL export and say it is ready for SFT or RL.
6. **Close (10 s):** open, reusable, built on Nemotron and Nebius.

## 15. Submission checklist

- [ ] Registered and on the right track (Coding & Agentic Engineering)
- [ ] Public GitHub repo, no keys in the code or commit history
- [ ] README: overview, architecture diagram, setup, how to run, results table, dataset description
- [ ] Demo video (2–3 min), public or unlisted link works in incognito
- [ ] Project description names Nemotron, Nebius Token Factory and Serverless Jobs (only if actually used)
- [ ] Screenshots of dashboard and replay
- [ ] Sample trajectories and dataset file included (small version in the repo)
- [ ] Submission form filled and submitted at least 24 hours before the official deadline

## 16. Honest limitations to state in the README

- Python-only, small single-purpose tasks, so results are not comparable with SWE-bench.
- The MVP exports data for training but does not run an RL training loop.
- Results depend on prompt design and a small number of runs per model.

Stating these builds credibility and shows you understand the field.
