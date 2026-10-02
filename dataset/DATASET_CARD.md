# AgentGym SFT Trajectory Dataset Card

## Dataset Summary
The **AgentGym SFT Trajectory Dataset** contains multi-turn interaction traces of AI coding agents fixing real-world Python bugs inside isolated sandbox environments. Each trajectory includes the complete sequence of environment observations, shell execution outputs, file edits, and final verified submissions, paired with RL environment returns and code quality ratings.

## Dataset Structure
Each line in `agentgym_sft.jsonl` represents one solved episode with 100% test pass rate (`pass_rate == 1.0`):

```json
{
  "task_id": "t01_off_by_one",
  "messages": [
    {"role": "system", "content": "You are an autonomous AI coding agent fixing bugs..."},
    {"role": "user", "content": "OBSERVATION:\nDescription: sum_range(a, b) should return..."},
    {"role": "assistant", "content": "{\"type\": \"edit\", \"path\": \"mathutils.py\", \"content\": \"...\"}"},
    {"role": "user", "content": "OBSERVATION:\nLast execution output: File updated: mathutils.py\nPass rate: 1.0"},
    {"role": "assistant", "content": "{\"type\": \"submit\"}"}
  ],
  "return": 0.89,
  "steps": 2,
  "model": "nvidia/llama-3.1-nemotron-nano-4b-instruct",
  "judge_score": 5
}
```

## Fields
- `task_id`: Benchmark identifier for the coding bug.
- `messages`: Standard OpenAI / Hugging Face chat format containing the full reasoning and acting trace.
- `return`: Cumulative RL return earned by the agent (pass rate gains minus step costs and regression penalties).
- `steps`: Total number of interaction turns taken to solve the task.
- `model`: Generator model identifier.
- `judge_score`: Automated Nemotron code-quality score (1 to 5 scale).

## Verification & Quality
- Every trajectory in this dataset achieved 100% test pass rate on hidden pytest test suites.
- Sandboxed execution ensures no synthetic hallucination of test results or syntax validity.
- Clean JSON schema adherence for immediate ingestion into SFT training pipelines.

## Intended Uses
- Supervised Fine-Tuning (SFT) for instruction-following agent models.
- Preference modeling (DPO, KTO) comparing high-return vs low-return trajectories.
- Warm-starting Reinforcement Learning (PPO, GRPO) policies for coding agents.

## Limitations
- Repositories are targeted to small modules (1–3 files, <60 lines) focusing on logic, boundary conditions, state management, and edge cases.
- Currently restricted to Python 3.11+.
