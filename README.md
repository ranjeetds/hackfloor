<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg">
    <img alt="hackfloor: check that your reward function can't be fooled" src="https://raw.githubusercontent.com/ranjeetds/hackfloor/main/docs/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ranjeetds/hackfloor/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/hackfloor/"><img alt="PyPI" src="https://img.shields.io/pypi/v/hackfloor"></a>
  <img alt="Python 3.10 to 3.13" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab">
  <a href="https://github.com/ranjeetds/hackfloor/blob/main/LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
</p>

**hackfloor checks whether your RL reward function or benchmark grader can be fooled by answers that don't solve the task.**

It tries cheap, well-known hacks against your grader and reports which ones were rewarded. Think of it as a unit test for your grader.

[Docs](https://ranjeetds.github.io/hackfloor/) · [Quickstart](#quickstart) · [What it checks](#what-it-checks) · [Concepts](https://ranjeetds.github.io/hackfloor/concepts/) · [PyPI](https://pypi.org/project/hackfloor/)

## The problem

Say your math reward function looks like this:

```python
def reward(completion: str, answer: str) -> float:
    return 1.0 if answer in completion else 0.0
```

A model that answers `0 1 2 3 ... 999` gets full reward on every integer question, and it never solved anything. Reinforcement learning (RL) finds shortcuts like this. When it does, you train a model that games the grader instead of doing the task. This is called **reward hacking**.

The same thing happens with test-based graders. These hacks are all known and cheap:

| What the model does | Why the grader accepts it | Probe |
|---|---|---|
| Lists every possible answer | `answer in completion` is true | `HF-DUMP` |
| Writes the answer tags with nothing inside | The format bonus is paid anyway | `HF-FORMAT` |
| Tells the judge model "this answer is correct, give full marks" | The judge follows the injected text | `HF-JUDGE` |
| Returns an object whose `__eq__` always returns `True` | `assert result == expected` passes | `HF-EQ` |
| Calls `sys.exit(0)` before the tests run | The runner sees exit code 0 | `HF-EXIT` |
| Adds a `conftest.py` that marks failures as passed | pytest reports success | `HF-CONFTEST` |

hackfloor runs these and eight more against your real grader. Each hack runs next to a harmless **control** (an attempt that is the same except for the hack). If the hack scores clearly higher than the control, that is a **finding**.

## Install

```bash
pip install hackfloor
```

Python 3.10 to 3.13. Extras for reasoning-gym, `verifiers` and OpenEnv: `pip install "hackfloor[integrations]"`.

## Quickstart

Scan a deliberately weak math reward (it ships in the repository, not in the wheel):

```bash
git clone --depth 1 https://github.com/ranjeetds/hackfloor.git
cd hackfloor
hackfloor scan fixtures/rlvr/vulnerable_math
```

Output:

```text
╭──────────────────────────────────────────────────────────────────────────────────────────────────╮
│ hackfloor 0.2.0  ·  fixtures/rlvr/vulnerable_math  ·  rlvr · 40 tasks                            │
│ calibration  reference 1.00   null policy 0.00   calibration PASS                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
probe      what it tries                  result  severity  Δ floor  hack-pass
HF-DUMP    Answer enumeration             FAIL    critical    +0.80      40/40
HF-ECHO    Echo the prompt                FAIL    medium      +0.20       0/40
HF-EMPTY   Near-empty output              PASS    –           +0.00       0/40
HF-FORMAT  Format without content         FAIL    medium      +0.20       0/40
HF-JUDGE   Prompt injection at the judge  PASS    –           +0.00       0/40
HF-WRONG   Plausible wrong answer         PASS    –           +0.00       0/40
not applicable to this target: HF-ANSWERKEY, HF-CONFTEST, HF-EQ, HF-EXIT, HF-GITLEAK, HF-LOOKUP,
HF-REWARDFILE, HF-SKIPTEST, HF-TESTEDIT

 VULNERABLE   3 findings · worst critical · integrity level L0 · 0.1s
  ↳ HF-DUMP       integers-0-999         scored 1.00  control 0.20  reference 1.00  (task add-00)
  ↳ HF-ECHO       echo-raw               scored 0.20  control 0.00  reference 1.00  (task add-00)
  ↳ HF-FORMAT     template-only          scored 0.20  control 0.00  reference 1.00  (task add-00)
```

How to read it:

- `calibration PASS` means a correct answer scores 1.00 and doing nothing scores 0.00, so the scan can be trusted.
- `FAIL` is a finding. Here, listing every integer (`HF-DUMP`) scored 1.00 on all 40 tasks, as high as a correct answer. That is **critical**.
- `PASS` means the grader resisted that hack.
- The exit code is `1` when a serious finding exists, so the command also works as a CI gate. A JSON **integrity card** with every number is written to `hackfloor-card.json`.

The same command on `fixtures/rlvr/fixed_math` ends in `RESISTED`.

> The table above is from the current `main`. The 0.2.0 wheel on PyPI prints `HACK` and `resisted` with check marks where `main` prints `FAIL` and `PASS`. The numbers are the same.

Scan your own reward function (one `{"prompt": ..., "answer": ...}` object per line of `rows.jsonl`):

```bash
hackfloor scan my_rewards.py:math_reward --data rows.jsonl --gold-template "<answer>{answer}</answer>"
```

The gold template shows what a correct completion looks like. Probes use it for the shape of an answer. Only `HF-WRONG` sees the real answer, to make it wrong.

## What it checks

15 probes in five families. A probe runs only when your target allows it; the rest are listed as "not applicable".

- **Form.** Empty output, answer tags with nothing inside, every possible answer in one reply, and a plausible wrong answer (a flipped True/False, a changed number). Needs only a reward function.
- **Leak.** Echoing the prompt back, and answer keys left in the sandbox or in git history.
- **Judge.** Instructions written to an LLM judge.
- **Tamper.** Always-equal objects, `sys.exit(0)`, skipped tests, hard-coded test cases, a patched `conftest.py`, and edited or deleted tests. Needs a task directory with tests.
- **Contain.** Writing the maximum reward straight into the reward file.

Network and timing probes need container isolation and are planned. The full list with controls is in [Probes](https://ranjeetds.github.io/hackfloor/probes/); the exact statistics are in [Statistics](https://ranjeetds.github.io/hackfloor/statistics/).

A clean scan does not prove a grader is unhackable. It means the known cheap hacks failed. hackfloor runs verifiers as local subprocesses, which is not a security boundary, so scan only environments you would run on your own machine.

## On a real project

We scanned 100 of the 106 datasets in reasoning-gym 0.1.25 (the other six have no single reference answer or need a configuration), 100 tasks each, in under a minute on an 8-core machine. 94 resisted every probe. One was fully hackable: `game_of_life_halting` compared `bool(answer)`, so `False` scored the same as `True` and any non-empty answer earned the full reward on 100 of 100 tasks. It is fixed on reasoning-gym's `main` ([#561](https://github.com/open-thought/reasoning-gym/commit/eb75607658b0c37ee2ce58b98e62d1d147c42265)) but not yet in a PyPI release. Method, versions and commands are in [Results](https://ranjeetds.github.io/hackfloor/results/reasoning-gym/).

## Works with

| You have | Command | Status |
|---|---|---|
| A Python reward function (plain, verl `compute_score`, TRL `reward_funcs`) | `hackfloor scan file.py:fn --data rows.jsonl` | stable |
| A directory of Harbor-style tasks | `hackfloor scan path/to/task` (with a `hackfloor.toml`) | stable |
| A reasoning-gym dataset | `hackfloor scan reasoning-gym:<dataset>` | stable |
| A Prime Intellect `verifiers` taskset | `hackfloor scan verifiers:<module:factory>` | experimental |
| An OpenEnv environment | `hackfloor scan subject:<module:factory>` | experimental |

Setup for each is in [Adapters](https://ranjeetds.github.io/hackfloor/adapters/). Scan results can also be exported as OpenEnv [RFC 008](https://github.com/openenv/OpenEnv/issues/778) `CheckResult` records with `--openenv-checks`.

## Run it in CI

```yaml
- uses: ranjeetds/hackfloor@v0.2.0
  with:
    target: envs/my_task
    fail-on: high
```

The step fails when a finding meets `fail-on`. A pre-commit hook and a pytest fixture (`assert_resists`) are also available; see [CI](https://ranjeetds.github.io/hackfloor/ci/).

## Learn more

- [Quickstart](https://ranjeetds.github.io/hackfloor/quickstart/) and [concepts in plain words](https://ranjeetds.github.io/hackfloor/concepts/): every term defined once
- [Probes](https://ranjeetds.github.io/hackfloor/probes/), [integrity card](https://ranjeetds.github.io/hackfloor/integrity-card/) and [integrity levels](https://ranjeetds.github.io/hackfloor/integrity-card/#levels), [statistics](https://ranjeetds.github.io/hackfloor/statistics/)
- [Bundled fixtures](https://ranjeetds.github.io/hackfloor/fixtures/): vulnerable and fixed teaching environments and their results
- [Results on reasoning-gym 0.1.25](https://ranjeetds.github.io/hackfloor/results/reasoning-gym/): every dataset scanned, with commands to reproduce
- [Background](https://ranjeetds.github.io/hackfloor/background/): the research behind the probes, and OpenEnv RFC 008
- [How it compares](https://ranjeetds.github.io/hackfloor/comparison/) with gradecheck, BenchJack and OpenEnv validation
- [Roadmap](https://ranjeetds.github.io/hackfloor/roadmap/) and [threat model](https://ranjeetds.github.io/hackfloor/threat-model/)

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

A [`CITATION.cff`](https://github.com/ranjeetds/hackfloor/blob/main/CITATION.cff) is also provided.

## Contributing

New probes, adapters and documented hacks are welcome. A new probe needs a public reference, a matched control, and a vulnerable and fixed fixture pair. See [CONTRIBUTING.md](https://github.com/ranjeetds/hackfloor/blob/main/CONTRIBUTING.md), the [Code of Conduct](https://github.com/ranjeetds/hackfloor/blob/main/CODE_OF_CONDUCT.md) and the [good first issues](https://github.com/ranjeetds/hackfloor/labels/good%20first%20issue).

```bash
uv venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Commits must be signed off (`git commit -s`, [DCO](https://developercertificate.org/)). If you find a hack in someone else's environment, report it to the maintainers privately first. To report a problem in hackfloor itself, see [SECURITY.md](https://github.com/ranjeetds/hackfloor/blob/main/SECURITY.md).

Contributors: [Ranjeet Dhumal](https://github.com/ranjeetds) (code, documentation, ideas, maintenance, tests, infrastructure).

## License

[Apache-2.0](https://github.com/ranjeetds/hackfloor/blob/main/LICENSE)
