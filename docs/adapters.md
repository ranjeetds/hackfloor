# Adapters

An adapter turns an environment into a `Subject` (see `src/hackfloor/core.py`):

| Method | Returns |
|---|---|
| `tasks()` | the tasks or rows to scan |
| `gold(task)` | the reference solution as an action |
| `null(task)` | the do-nothing policy: an empty completion or an untouched workspace |
| `grade(task, action)` | an `Attempt` with the reward from the real grader |
| `capabilities()` | what probes may do: `completion`, `workspace`, `python_entry`, `visible_tests`, `reward_file_writable` |
| `describe()` | metadata recorded in the card |

## Supported targets

| Target | Status | How |
|---|---|---|
| Plain Python reward function (`fn(completion, answer)`) | stable | `hackfloor scan file.py:fn --data rows.jsonl` |
| verl `compute_score(data_source, solution_str, ground_truth, extra_info)` | stable | `--flavor verl`, or detected from the signature |
| TRL `reward_funcs(prompts, completions, **columns)` | stable | `--flavor trl`, or detected from the signature |
| Harbor-style task directories | stable | `hackfloor.toml` beside the task; native `task.toml` reading is planned |
| reasoning-gym | stable | `hackfloor scan reasoning-gym:<dataset>`; tested against 0.1.25 |
| Prime Intellect `verifiers` (v1 API) | experimental | `hackfloor scan verifiers:<module:factory>`; trace-level rewards only; tested against 0.4.1 |
| OpenEnv `Environment` (single step, in process) | experimental | `subject:<module:factory>`; tested against openenv 0.15.0, including its `reasoning_gym_env` |
| OpenEnv RFC 008 `CheckResult` export | stable | `--openenv-checks checks.json`; validated against openenv 0.15.0's schema |
| GitHub Action, pre-commit hook, pytest fixture | stable | see [CI](ci.md) |
| OpenRLHF, multi-step and HTTP OpenEnv | planned | |
| Inspect AI scorers | experimental | Python API; model-free scorers only |

## Reward functions

```bash
hackfloor scan rewards.py:my_reward --data rows.jsonl --gold-template "<answer>{answer}</answer>"
```

Call conventions, picked from the parameter names or set with `--flavor`:

| Flavor | Signature |
|---|---|
| `plain` | `fn(completion, answer) -> float` |
| `verl` | `fn(data_source, solution_str, ground_truth, extra_info) -> float \| dict` |
| `trl` | `fn(prompts=[...], completions=[...], **columns) -> list[float]` |

### From Python

```python
from hackfloor import scan
from hackfloor.adapters import RewardFunctionSubject


def reward(completion: str, answer: str) -> float:
    return 1.0 if answer in completion else 0.0


rows = [{"prompt": f"What is {n} + 10?", "answer": str(n + 10)} for n in range(20)]
subject = RewardFunctionSubject(reward, rows, gold_template="<answer>{answer}</answer>")
result = scan(subject)
print(result.verdict, result.level)  # e.g. VULNERABLE 0
for p in result.findings:
    print(p.probe.id, p.severity, f"{p.hack_passes}/{p.n}")
```

A directory with a `hackfloor.toml` can describe the same thing:

```toml
[subject]
kind = "rlvr"
reward = "reward.py:reward"
data = "data.jsonl"
gold_template = "<answer>{answer}</answer>"

[reward]
min = 0.0
max = 1.0
```

## Task directories

A task directory follows a Harbor-like layout and is described by `hackfloor.toml`; see
`fixtures/tasks/*/hackfloor.toml` for working examples. Every attempt copies `environment/` into a fresh
temporary sandbox, applies the action to the workspace, and runs the verifier command with
these substitutions and variables:

| Placeholder | Environment variable | Value |
|---|---|---|
| `{python}` | | the interpreter running hackfloor |
| `{task}` | `HACKFLOOR_TASK` | the task directory |
| `{sandbox}` | `HACKFLOOR_SANDBOX` | the sandbox root |
| `{workspace}` | `HACKFLOOR_WORKSPACE` | the agent's workspace |
| `{logs}` | `HACKFLOOR_LOGS` | `sandbox/logs` |

The reward is read from `reward_file` (plain number, or JSON with a `reward` key) or from the
exit code. A directory whose subdirectories each hold a task `hackfloor.toml` is scanned as a
suite.

Two optional `[task]` keys model what an image build would do:

- `setup = ["{python}", "{task}/setup_env.py"]` runs once in each fresh sandbox, with the
  workspace as the working directory, before the action is applied (`setup_timeout`, in
  seconds, defaults to 60). A failing setup is reported as a grader error.
- `instruction = "instruction.md"` is what the agent is shown; the leak checks look for the
  reference answer in it.

## Framework adapters

Install the framework with its extra (`pip install "hackfloor[reasoning-gym]"`,
`"hackfloor[verifiers]"`, `"hackfloor[openenv]"`, or `"hackfloor[inspect-ai]"`).
Use `"hackfloor[integrations]"` to install all integration dependencies.
Each adapter calls the framework's own scoring code; hackfloor never reimplements a
grader. These adapters grade one completion per task, so the completion probes apply.

| Target | Adapter | Status |
|---|---|---|
| `reasoning-gym:<dataset>` | `ReasoningGymSubject` | tested against reasoning-gym 0.1.25 |
| `verifiers:<module:factory>` | `VerifiersSubject` | experimental; tested against verifiers 0.4.1 (v1 API) |
| `subject:<module:factory>` | any `Subject`, for example `OpenEnvSubject` | experimental; tested against openenv 0.15.0 |
| `InspectScorerSubject` | `InspectScorerSubject` | experimental; tested against inspect-ai 0.3.292 |

### reasoning-gym

```bash
hackfloor scan reasoning-gym:basic_arithmetic --tasks 50 --seed 0
```

`--tasks` is the dataset size and `--seed` its seed. A completion is scored as reasoning-gym's
recipes do it: `extract_answer(completion)` on the `<answer>` tag, then the dataset's
`score_answer`. The gold completion is `<answer>{answer}</answer>`.

### verifiers (experimental)

`factory` returns a v1 `Taskset` (or any iterable of `Task` objects):

```bash
hackfloor scan verifiers:my_env.tasks:load --gold-template "<answer>{answer}</answer>"
```

Each completion becomes a two-node trace (the prompt as a user message, the completion as the
sampled assistant reply) and is scored with the task's own `Task.score(trace)`; the reward is
`trace.reward`. Rewards that need a sandbox runtime are skipped by verifiers when no runtime is
attached, so only trace-level rewards are probed. The gold completion fills the template with the
task data's `answer` field, so the template has to match what the rewards parse.

### OpenEnv (experimental)

`OpenEnvSubject` drives an in-process, single-step `Environment`:

```python
from hackfloor.adapters import OpenEnvSubject
from reasoning_gym_env.models import ReasoningGymAction
from reasoning_gym_env.server.reasoning_gym_environment import ReasoningGymEnvironment


def build():
    return OpenEnvSubject(
        ReasoningGymEnvironment,
        [
            {"dataset_name": "basic_arithmetic", "dataset_config": {}, "seed": i, "size": 1}
            for i in range(20)
        ],
        make_action=lambda text: ReasoningGymAction(answer=text),
        gold=lambda env, obs, kwargs: env._current_entry["answer"],
    )
```

```bash
hackfloor scan subject:my_scan:build
```

Every grade builds a fresh environment, calls `reset(**task_kwargs)` and one
`step(make_action(completion))`, and reads `obs.reward`. An episode that does not end after one
step is reported as an error. Environments rarely reveal the reference before a step, so you
pass `gold(env, observation, task_kwargs)`. Multi-step environments, and environments reached over
HTTP or in a container, are not covered yet.

### Inspect AI scorers (experimental)

`InspectScorerSubject` adapts Inspect AI samples and scorers into a hackfloor
`CompletionSubject`. It is built in Python; there is no `hackfloor scan` target for it yet.

```python
from inspect_ai.dataset import Sample
from inspect_ai.scorer import exact

from hackfloor import scan
from hackfloor.adapters import InspectScorerSubject

samples = [
    Sample(input="What is 2 + 2?", target="4", id="addition"),
]

subject = InspectScorerSubject(
    scorer=exact(),
    samples=samples,
)

result = scan(subject)
print(result.verdict, result.level)
```

Install with `pip install "hackfloor[inspect-ai]"`.

The adapter supports model-free scorers that return numeric rewards or Inspect's
standard Correct (`C`) and Incorrect (`I`) verdicts. Any other score value, including
`P` (partial) and `N` (no answer), is reported as a grader error, so the scan is
`INCONCLUSIVE` rather than a false `RESISTED`. Known model-graded scorers are rejected.
Custom scorers must not require model calls; hackfloor cannot automatically detect every
custom scorer that invokes a model.

The reference answer is the sample's `target`, and the calibration run submits
`gold_template` with `{answer}` replaced by it (default: the bare target). Scorers that
parse a marked answer, such as `answer("line")`, need a matching template, for example
`gold_template="ANSWER: {answer}"`; otherwise the scan reports `UNCALIBRATED`.

### OpenEnv check results

```bash
hackfloor scan <target> --openenv-checks checks.json
```

This writes the card's RFC 008 checks as OpenEnv `CheckResult` records (`check_id`, lowercase
`status`, `measured`, `evidence`, `remediation`, `duration_s`), validated in CI against
`report-v2.schema.json` from openenv 0.15.0. Checks hackfloor does not measure are written as
`skip` with the reason. An uncalibrated scan writes `skip` for every check.

Planned: native Harbor `task.toml`, multi-step and HTTP OpenEnv environments, and OpenRLHF.
