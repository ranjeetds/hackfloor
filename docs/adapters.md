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

A task directory follows a Harbor-like layout and is described by `hackfloor.toml`; see the
README and `fixtures/tasks/*/hackfloor.toml`. Every attempt copies `environment/` into a fresh
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

Planned: native Harbor `task.toml`, OpenEnv, `verifiers`, reasoning-gym, OpenRLHF and
inspect_ai adapters.
