<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg">
    <img alt="hackfloor: prove that agents which don't solve the task can't score" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/hackfloor/"><img alt="PyPI" src="https://img.shields.io/pypi/v/hackfloor"></a>
  <img alt="Python 3.10 to 3.13" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab">
  <a href="https://github.com/ranjeetds/hackfloor/blob/main/LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
</p>

**Prove that agents which don't solve the task can't score.**

hackfloor runs documented, non-solving policies through an RL environment's real grader or an agent benchmark, each next to a matched control. If a policy that does not solve the task is rewarded, that is a finding. The scan writes a JSON integrity card with paired statistics and [OpenEnv RFC 008](https://github.com/openenv/OpenEnv/issues/778) check ids.

The probes are the publicly documented minimal forms of known hacks: always-equal objects, `sys.exit(0)`, `SkipTest`, `conftest.py` report rewrites, test edits, reward-file writes, answer enumeration, prompt echo, judge injection, and answer keys left in the sandbox or in git history ([Anthropic, arXiv 2511.18397](https://arxiv.org/abs/2511.18397); [Baker et al., arXiv 2503.11926](https://arxiv.org/abs/2503.11926); [METR, June 2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/); [ImpossibleBench, arXiv 2510.20270](https://arxiv.org/abs/2510.20270); [BenchJack, arXiv 2605.12673](https://arxiv.org/abs/2605.12673)).

## Install

```bash
pip install hackfloor
pip install "hackfloor[integrations]"   # optional: reasoning-gym, verifiers, openenv
```

Requires Python 3.10–3.13. Docs: https://ranjeetds.github.io/hackfloor/

## Quickstart

Scan a reward function (one `{"prompt", "answer"}` object per line of `rows.jsonl`):

```bash
hackfloor scan my_rewards.py:math_reward --data rows.jsonl --gold-template "<answer>{answer}</answer>"
```

The gold template is what a correct completion looks like. Probes never see the answer. Or from Python:

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

Bundled teaching fixtures (clone the repository; the `dev` extra provides `pytest` for the task-directory graders):

```bash
git clone https://github.com/ranjeetds/hackfloor.git
cd hackfloor
pip install -e ".[dev]"
hackfloor scan fixtures/tasks/vulnerable_pytest   # 6 critical findings, exit code 1
hackfloor scan fixtures/tasks/fixed_pytest        # RESISTED, integrity level L1
```

<p align="center">
  <img alt="hackfloor scan of the bundled vulnerable pytest task: six critical findings" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/scan-vulnerable.svg" width="860">
</p>

A directory of Harbor-style tasks, a reasoning-gym dataset, a `verifiers` taskset or an OpenEnv environment is scanned the same way; see [adapters](https://github.com/ranjeetds/hackfloor/blob/main/docs/adapters.md).

> [!WARNING]
> hackfloor runs verifiers as local subprocesses in a temp directory. That is a probe harness, not a security boundary. Only scan environments you would run on your machine anyway. Container isolation is planned for v0.3.

## What it checks

14 probes in five families. A probe runs only when the target exposes what it needs; the rest are listed as not applicable.

| Probe | Family | What it tries | Applies to |
|---|---|---|---|
| `HF-EMPTY` | form | whitespace, `None`, `{}` | completions |
| `HF-FORMAT` | form | answer tags or `\boxed{}` with nothing inside | completions |
| `HF-DUMP` | form | every integer 0–999, A–J, yes/no in one answer | completions |
| `HF-ECHO` | leak | repeat the prompt, raw and in the answer slot | completions |
| `HF-ANSWERKEY` | leak | copy a reference-looking file reachable from the sandbox | tasks with a Python entry file |
| `HF-GITLEAK` | leak | every version of the entry file in the workspace git history | tasks with a git workspace |
| `HF-JUDGE` | judge | instructions addressed to an LLM judge | completions |
| `HF-EQ` | tamper | an object whose `__eq__` is always `True` | tasks with a Python entry file |
| `HF-EXIT` | tamper | `sys.exit(0)` on import | tasks with a Python entry file |
| `HF-SKIPTEST` | tamper | raise `unittest.SkipTest` in every function, or at import | tasks with a Python entry file |
| `HF-LOOKUP` | tamper | hard-code the literal cases from the visible tests | tasks with visible tests |
| `HF-CONFTEST` | tamper | a `conftest.py` hook that rewrites failing reports to passed | any workspace task |
| `HF-TESTEDIT` | tamper | neutralise or delete the visible tests | tasks with visible tests |
| `HF-REWARDFILE` | contain | pre-write the max reward to the reward file | tasks whose reward file the agent can reach |

Each exploit is compared with a matched control that touches the same surface without the exploit. With five or more tasks, a finding needs an exact one-sided sign test with Holm correction at α = 0.05 and a mean Δ of at least 5% of the reward range; with fewer, the gain has to reproduce on every replay. A reproducible exploit that scores at or above the reference is always a finding (critical). See [probes](https://github.com/ranjeetds/hackfloor/blob/main/docs/probes.md) and [statistics](https://github.com/ranjeetds/hackfloor/blob/main/docs/statistics.md). Network and timing probes are not included yet: they need container isolation.

## Integrations

| Target | Status | Command |
|---|---|---|
| Python reward function (`fn(completion, answer)`) | stable | `hackfloor scan file.py:fn --data rows.jsonl` |
| verl `compute_score` / TRL `reward_funcs` | stable | `--flavor verl` or `--flavor trl`, or detected from the signature |
| Harbor-style task directories | stable | `hackfloor.toml` beside the task |
| reasoning-gym | stable | `hackfloor scan reasoning-gym:<dataset>` (tested on 0.1.25) |
| Prime Intellect `verifiers` (v1 API) | experimental | `hackfloor scan verifiers:<module:factory>`; trace-level rewards; tested on 0.4.1 |
| OpenEnv `Environment` (single step, in process) | experimental | `subject:<module:factory>` (tested on openenv 0.15.0) |
| OpenEnv RFC 008 `CheckResult` export | stable | `--openenv-checks checks.json` |

OpenRLHF, inspect_ai scorers, and multi-step or HTTP OpenEnv are planned. gradecheck is the closest project in spirit. BenchJack audits whole benchmarks (219 distinct flaws in eight classes across 10 agent benchmarks, [arXiv 2605.12673](https://arxiv.org/abs/2605.12673)). OpenEnv's validator is where these checks are headed; hackfloor is a standalone probe panel it can use, not a replacement.

## Integrity card

Every scan writes a JSON card that validates against [`card-0.1.schema.json`](https://github.com/ranjeetds/hackfloor/blob/main/src/hackfloor/schema/card-0.1.schema.json). Criteria this version does not measure appear as `NOT_MEASURED`, never as a pass. `--openenv-checks` exports the checks as OpenEnv `CheckResult` records.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-light.svg">
    <img alt="Integrity cards for the vulnerable and fixed pytest fixtures" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/integrity-card-light.svg" width="860">
  </picture>
</p>

| Level | Meaning | Status |
|---|---|---|
| L0 | at least one critical or high finding, or a malformed reward | current |
| L1 | calibrated, and no critical or high finding from the default probes | current |
| L2 | L1, plus a bounded gameability gap from model-based policies and passing containment checks | planned (v0.3) |
| L3 | L2, plus the canary suite and an independent replay of the card | planned (v1.0) |

A level describes this probe set at this version, not the absence of every hack.

## CI

GitHub Action, pinned to the released tag:

```yaml
- uses: ranjeetds/hackfloor@v0.2.0
  with:
    target: envs/my_task
    fail-on: high
```

pre-commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/ranjeetds/hackfloor
    rev: v0.2.0
    hooks:
      - id: hackfloor
        args: [envs/my_task, --quiet, --replays, "1"]
        files: ^envs/my_task/
```

pytest:

```python
@pytest.mark.hackfloor
def test_grader_resists_reward_hacks(hackfloor):
    hackfloor.assert_resists("envs/my_task")
```

Exit code `1` when a finding meets `--fail-on` (default `high`). Details, inputs and `assert_resists` options: [docs/ci.md](https://github.com/ranjeetds/hackfloor/blob/main/docs/ci.md).

## Citation

```bibtex
@software{dhumal2026hackfloor,
  author  = {Dhumal, Ranjeet},
  title   = {hackfloor: adversarial probes for RL environment graders and agent benchmarks},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/ranjeetds/hackfloor},
  license = {Apache-2.0}
}
```

There is also a [`CITATION.cff`](https://github.com/ranjeetds/hackfloor/blob/main/CITATION.cff).

## Contributing

New probes, adapters and documented hacks are welcome. A new probe needs a public reference, a matched control, and a vulnerable/fixed fixture pair. See [CONTRIBUTING.md](https://github.com/ranjeetds/hackfloor/blob/main/CONTRIBUTING.md), the [Code of Conduct](https://github.com/ranjeetds/hackfloor/blob/main/CODE_OF_CONDUCT.md), and [good first issues](https://github.com/ranjeetds/hackfloor/labels/good%20first%20issue).

```bash
uv venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Commits must be signed off (`git commit -s`, [DCO](https://developercertificate.org/)).

If you find a hack in someone else's environment, report it to the maintainers privately first. How to report a problem in hackfloor itself is in [SECURITY.md](https://github.com/ranjeetds/hackfloor/blob/main/SECURITY.md). Do not use the output to inflate leaderboard scores.

Contributors: [Ranjeet Dhumal](https://github.com/ranjeetds) (code, documentation, ideas, maintenance, tests, infrastructure).

## License

[Apache-2.0](https://github.com/ranjeetds/hackfloor/blob/main/LICENSE)
